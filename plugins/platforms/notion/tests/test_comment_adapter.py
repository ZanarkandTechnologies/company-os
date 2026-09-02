from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[4]
HERMES_ROOT = Path.home() / ".hermes/hermes-agent"
sys.path.insert(0, str(HERMES_ROOT))
sys.path.insert(0, str(ROOT))

from gateway.session import SessionSource, build_session_key  # noqa: E402
from plugins.platforms.notion import adapter  # noqa: E402


PAGE_ID = "11111111-2222-3333-4444-555555555555"
COMMENT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
DISCUSSION_ID = "99999999-8888-7777-6666-555555555555"
OTHER_DISCUSSION_ID = "88888888-7777-6666-5555-444444444444"


def comment(
    comment_id: str,
    text: str,
    discussion_id: str = DISCUSSION_ID,
    author: str = "human-1",
    created_time: str = "2026-08-27T00:00:00Z",
) -> dict[str, object]:
    return {
        "id": comment_id,
        "text": text,
        "discussion_id": discussion_id,
        "created_by": {"id": author},
        "created_time": created_time,
        "parent": {"type": "page_id", "page_id": PAGE_ID},
    }


class NotionCommentAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.state_directory = tempfile.TemporaryDirectory()

    async def asyncTearDown(self) -> None:
        self.state_directory.cleanup()

    def make_adapter(self) -> Any:
        instance: Any = adapter.NotionAdapter.__new__(adapter.NotionAdapter)
        instance.build_source = lambda **values: SessionSource(
            platform=adapter.Platform.WEBHOOK,
            **values,
        )
        instance.handle_message = AsyncMock()
        instance.state = adapter.WebhookState(Path(self.state_directory.name) / "state.json")
        return instance

    def test_default_trigger_is_company_neutral(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(adapter.api.comment_trigger(), "@hermes")

    async def dispatch(
        self,
        current: dict[str, object],
        open_comments: list[dict[str, object]],
        *,
        bot_id: str = "bot-1",
    ) -> Any:
        instance = self.make_adapter()
        payload = {"entity": {"id": current["id"]}, "data": {"page_id": PAGE_ID}}
        context = {"page": {"id": PAGE_ID}, "blocks": [], "open_comments": [{"text": "other thread"}], "limits": {}}
        with patch.object(adapter.api, "get_comment", return_value=current), patch.object(
            adapter.api, "get_bot_id", return_value=bot_id
        ), patch.object(adapter.api, "list_comments", return_value=open_comments), patch.object(
            adapter.api, "get_ticket_context", return_value=context
        ), patch.object(adapter.api, "comment_trigger", return_value="@companyos"):
            await instance._dispatch_comment(payload, "event-1", "workspace-1")
        return instance

    async def test_explicit_trigger_activates_exact_discussion_and_requires_reply(self) -> None:
        current = comment(COMMENT_ID, "@CompanyOS: what is blocked?")
        instance = await self.dispatch(current, [current])

        instance.handle_message.assert_awaited_once()
        event = instance.handle_message.await_args.args[0]
        self.assertEqual(event.source.chat_id, f"ticket:{PAGE_ID}")
        self.assertEqual(event.source.chat_type, "thread")
        self.assertEqual(event.source.thread_id, DISCUSSION_ID)
        self.assertIn("Mode: explicit", event.text)
        self.assertIn("Latest comment: what is blocked?", event.text)
        self.assertFalse(instance.state.reply_may_be_silent(COMMENT_ID))

    async def test_untagged_follow_up_after_hermes_reply_receives_full_ordered_thread(self) -> None:
        trigger = comment("11111111-aaaa-bbbb-cccc-111111111111", "@companyos what is blocked?", created_time="2026-08-27T00:00:00Z")
        bot_reply = comment("22222222-aaaa-bbbb-cccc-222222222222", "The supplier date is missing.", author="bot-1", created_time="2026-08-27T00:01:00Z")
        current = comment(COMMENT_ID, "It arrives Friday. Is that enough?", created_time="2026-08-27T00:02:00Z")
        instance = await self.dispatch(current, [current, bot_reply, trigger])

        instance.handle_message.assert_awaited_once()
        event = instance.handle_message.await_args.args[0]
        self.assertIn("Mode: continuation", event.text)
        self.assertIn("Latest comment: It arrives Friday. Is that enough?", event.text)
        discussion_json = event.text.split("Full open discussion JSON: ", 1)[1].split("\nTicket context JSON:", 1)[0]
        self.assertLess(discussion_json.index("what is blocked?"), discussion_json.index("supplier date is missing"))
        self.assertLess(discussion_json.index("supplier date is missing"), discussion_json.index("It arrives Friday"))
        self.assertNotIn("other thread", event.text)
        self.assertTrue(instance.state.reply_may_be_silent(COMMENT_ID))

    async def test_prior_trigger_activates_follow_up_even_before_first_reply_finishes(self) -> None:
        trigger = comment("11111111-aaaa-bbbb-cccc-111111111111", "@companyos inspect this")
        current = comment(COMMENT_ID, "Also check the commitment date", created_time="2026-08-27T00:01:00Z")
        instance = await self.dispatch(current, [trigger, current])
        instance.handle_message.assert_awaited_once()

    async def test_untagged_fresh_or_other_discussion_is_ignored(self) -> None:
        current = comment(COMMENT_ID, "Human coordination only")
        other_bot = comment(
            "11111111-aaaa-bbbb-cccc-111111111111",
            "I previously replied elsewhere",
            discussion_id=OTHER_DISCUSSION_ID,
            author="bot-1",
        )
        instance = await self.dispatch(current, [other_bot, current])
        instance.handle_message.assert_not_awaited()

    async def test_later_trigger_does_not_retroactively_activate_delayed_follow_up(self) -> None:
        current = comment(COMMENT_ID, "This arrived before anyone invoked Hermes")
        later_trigger = comment(
            "11111111-aaaa-bbbb-cccc-111111111111",
            "@companyos help with the later question",
            created_time="2026-08-27T00:01:00Z",
        )
        instance = await self.dispatch(current, [later_trigger, current])
        instance.handle_message.assert_not_awaited()

    async def test_own_bot_comment_never_dispatches_or_fetches_thread(self) -> None:
        current = comment(COMMENT_ID, "Bot response", author="bot-1")
        instance = self.make_adapter()
        payload = {"entity": {"id": COMMENT_ID}, "data": {"page_id": PAGE_ID}}
        with patch.object(adapter.api, "get_comment", return_value=current), patch.object(
            adapter.api, "get_bot_id", return_value="bot-1"
        ), patch.object(adapter.api, "list_comments") as list_comments:
            await instance._dispatch_comment(payload, "event-1", "workspace-1")
        instance.handle_message.assert_not_awaited()
        list_comments.assert_not_called()

    async def test_discussion_id_isolates_session_keys_and_same_thread_is_shared(self) -> None:
        first = comment(COMMENT_ID, "@companyos first?")
        second = comment(
            "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
            "@companyos second?",
            discussion_id=OTHER_DISCUSSION_ID,
        )
        first_instance = await self.dispatch(first, [first])
        second_instance = await self.dispatch(second, [second])
        first_source = first_instance.handle_message.await_args.args[0].source
        second_source = second_instance.handle_message.await_args.args[0].source
        first_key = build_session_key(first_source, group_sessions_per_user=True)
        second_key = build_session_key(second_source, group_sessions_per_user=True)
        self.assertNotEqual(first_key, second_key)

        same_thread_other_author = cast(SessionSource, SimpleNamespace(**vars(first_source)))
        same_thread_other_author.user_id = "workspace-2"
        shared_key = build_session_key(same_thread_other_author, group_sessions_per_user=True)
        self.assertEqual(first_key, shared_key)

    async def test_exact_no_reply_is_suppressed_only_for_optional_follow_up(self) -> None:
        instance = self.make_adapter()
        instance.state.remember_reply_target("optional", DISCUSSION_ID, allow_silence=True)
        instance.state.remember_reply_target("explicit", DISCUSSION_ID, allow_silence=False)

        with patch.object(adapter.api, "create_comment_reply") as create:
            result = await instance.send(f"ticket:{PAGE_ID}", adapter.NO_REPLY_MARKER, reply_to="optional")
            self.assertTrue(result.success)
            self.assertTrue(result.raw_response["suppressed"])
            create.assert_not_called()

            result = await instance.send(f"ticket:{PAGE_ID}", adapter.NO_REPLY_MARKER, reply_to="explicit")
            self.assertFalse(result.success)
            create.assert_not_called()

    async def test_mixed_marker_text_is_posted_and_reply_stays_in_exact_discussion(self) -> None:
        instance = self.make_adapter()
        instance.state.remember_reply_target("optional", DISCUSSION_ID, allow_silence=True)
        content = f"{adapter.NO_REPLY_MARKER}\nThis is visible text"
        with patch.object(
            adapter.api,
            "create_comment_reply",
            return_value={"id": "reply-1", "discussion_id": DISCUSSION_ID},
        ) as create:
            result = await instance.send(f"ticket:{PAGE_ID}", content, reply_to="optional")
        self.assertTrue(result.success)
        create.assert_called_once_with(f"discussion:{DISCUSSION_ID}", content)


if __name__ == "__main__":
    unittest.main()
