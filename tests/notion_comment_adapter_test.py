from __future__ import annotations

import asyncio
import os
import sys
import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(__file__).resolve().parents[1]
HERMES_ROOT = Path(os.getenv("HERMES_AGENT_PATH") or Path.home() / ".hermes/hermes-agent")
sys.path.insert(0, str(HERMES_ROOT))
sys.path.insert(0, str(ROOT / "profiles/howie-ai/plugins/platforms"))

from notion import adapter  # noqa: E402
from gateway.session import build_session_key  # noqa: E402


class NotionCommentAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.state_directory = tempfile.TemporaryDirectory()

    async def asyncTearDown(self):
        self.state_directory.cleanup()

    def make_adapter(self):
        instance = adapter.NotionAdapter.__new__(adapter.NotionAdapter)
        instance.build_source = lambda **values: SimpleNamespace(**values)
        instance.handle_message = AsyncMock()
        instance.state = adapter.WebhookState(Path(self.state_directory.name) / "state.json")
        return instance

    async def test_trigger_comment_builds_ticket_context_for_ticket_session(self):
        instance = self.make_adapter()
        payload = {
            "entity": {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
            "data": {"page_id": "11111111-2222-3333-4444-555555555555"},
        }
        comment = {
            "text": "@VishanAI: what is blocked?",
            "discussion_id": "99999999-8888-7777-6666-555555555555",
            "created_by": {"id": "human-1"},
        }
        context = {"page": {"properties": {"Status": {"type": "status"}}}, "blocks": [], "open_comments": []}
        with patch.object(adapter.api, "get_comment", return_value=comment), patch.object(
            adapter.api, "get_bot_id", return_value="bot-1"
        ), patch.object(adapter.api, "get_ticket_context", return_value=context), patch.object(
            adapter.api, "comment_trigger", return_value="@vishanai"
        ):
            await instance._dispatch_comment(payload, "event-1", "workspace-1")
        instance.handle_message.assert_awaited_once()
        event = instance.handle_message.await_args.args[0]
        self.assertEqual(event.source.chat_id, "ticket:11111111-2222-3333-4444-555555555555")
        self.assertEqual(
            instance.state.reply_target("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
            "99999999-8888-7777-6666-555555555555",
        )
        self.assertIn("Question: what is blocked?", event.text)
        self.assertIn("Ticket context JSON:", event.text)

    async def test_non_trigger_and_own_comments_do_not_dispatch(self):
        payload = {
            "entity": {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
            "data": {"page_id": "11111111-2222-3333-4444-555555555555"},
        }
        for comment in (
            {"text": "ordinary note", "discussion_id": "d", "created_by": {"id": "human-1"}},
            {"text": "@vishanai loop", "discussion_id": "d", "created_by": {"id": "bot-1"}},
        ):
            instance = self.make_adapter()
            with patch.object(adapter.api, "get_comment", return_value=comment), patch.object(
                adapter.api, "get_bot_id", return_value="bot-1"
            ), patch.object(adapter.api, "comment_trigger", return_value="@vishanai"):
                await instance._dispatch_comment(payload, "event-1", "workspace-1")
            instance.handle_message.assert_not_awaited()

    async def test_send_routes_ticket_session_result_to_triggering_discussion(self):
        instance = self.make_adapter()
        instance.state.remember_reply_target("comment-1", "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        with patch.object(
            adapter.api,
            "create_comment_reply",
            return_value={"id": "reply-1", "discussion_id": "discussion-1"},
        ) as create:
            result = await instance.send(
                "ticket:11111111-2222-3333-4444-555555555555", "Answer", reply_to="comment-1"
            )
        self.assertTrue(result.success)
        self.assertEqual(result.message_id, "reply-1")
        self.assertEqual(instance.state.load()["last_reply"]["message_id"], "reply-1")
        create.assert_called_once_with("discussion:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "Answer")

        with patch.object(adapter.api, "create_comment_reply") as create:
            result = await instance.send("page-event", "Answer")
        self.assertFalse(result.success)
        create.assert_not_called()

    async def test_multiple_discussions_on_one_ticket_share_session_but_keep_reply_targets(self):
        instance = self.make_adapter()
        page_id = "11111111-2222-3333-4444-555555555555"
        comments = {
            "comment-1": {"text": "@vishanai first?", "discussion_id": "discussion-1", "created_by": {"id": "human"}},
            "comment-2": {"text": "@vishanai second?", "discussion_id": "discussion-2", "created_by": {"id": "human"}},
        }
        with patch.object(adapter.api, "get_comment", side_effect=lambda comment_id: comments[comment_id]), patch.object(
            adapter.api, "get_bot_id", return_value="bot"
        ), patch.object(
            adapter.api, "get_ticket_context", return_value={"page": {}, "blocks": [], "open_comments": []}
        ), patch.object(adapter.api, "comment_trigger", return_value="@vishanai"):
            for index, comment_id in enumerate(comments, start=1):
                await instance._dispatch_comment(
                    {"entity": {"id": comment_id}, "data": {"page_id": page_id}},
                    f"event-{index}",
                    "workspace-1",
                )

        events = [call.args[0] for call in instance.handle_message.await_args_list]
        self.assertEqual([event.source.chat_id for event in events], [f"ticket:{page_id}", f"ticket:{page_id}"])
        self.assertEqual(instance.state.reply_target("comment-1"), "discussion-1")
        self.assertEqual(instance.state.reply_target("comment-2"), "discussion-2")

    async def test_busy_ticket_session_queues_next_comment_turn(self):
        instance = adapter.NotionAdapter.__new__(adapter.NotionAdapter)
        adapter.BasePlatformAdapter.__init__(
            instance,
            adapter.PlatformConfig(enabled=True, extra={"group_sessions_per_user": True}),
            adapter.Platform.WEBHOOK,
        )
        instance.set_message_handler(AsyncMock(return_value=None))
        instance._busy_text_mode = "queue"
        instance._busy_text_debounce_seconds = 0
        source = instance.build_source(
            chat_id="ticket:11111111-2222-3333-4444-555555555555",
            chat_name="Notion ticket",
            chat_type="channel",
            user_id="workspace-1",
            user_name="Notion",
            scope_id="workspace-1",
        )
        session_key = build_session_key(source, group_sessions_per_user=True)
        blocker = asyncio.Event()
        owner = asyncio.create_task(blocker.wait())
        instance._active_sessions[session_key] = asyncio.Event()
        instance._session_tasks[session_key] = owner
        follow_up = adapter.MessageEvent(
            text="[Notion PKMS question]\nQuestion: second?",
            message_type=adapter.MessageType.TEXT,
            source=source,
            message_id="comment-2",
        )
        try:
            await instance.handle_message(follow_up)
            await asyncio.sleep(0.01)
            self.assertEqual(instance._pending_messages[session_key].message_id, "comment-2")
            self.assertFalse(instance._active_sessions[session_key].is_set())
        finally:
            owner.cancel()
            await asyncio.gather(owner, return_exceptions=True)

    async def test_signed_webhook_dispatches_comment_in_background(self):
        instance = self.make_adapter()
        instance.allowed_events = {"comment.created"}
        instance._background_tasks = set()
        with tempfile.TemporaryDirectory() as directory:
            instance.state = adapter.WebhookState(Path(directory) / "state.json")
            instance.state.capture_token("verification-token")
            payload = {
                "id": "event-1",
                "type": "comment.created",
                "workspace_id": "workspace-1",
                "entity": {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
                "data": {"page_id": "11111111-2222-3333-4444-555555555555"},
            }
            raw = json.dumps(payload, separators=(",", ":")).encode()
            signature = "sha256=" + hmac.new(b"verification-token", raw, hashlib.sha256).hexdigest()
            comment = {
                "text": "@vishanai what is blocked?",
                "discussion_id": "99999999-8888-7777-6666-555555555555",
                "created_by": {"id": "human-1"},
            }
            app = web.Application()
            app.router.add_post("/notion/webhook", instance._handle_webhook)
            with patch.object(adapter.api, "get_comment", return_value=comment), patch.object(
                adapter.api, "get_bot_id", return_value="bot-1"
            ), patch.object(
                adapter.api, "get_ticket_context", return_value={"page": {}, "blocks": [], "open_comments": []}
            ), patch.object(adapter.api, "comment_trigger", return_value="@vishanai"):
                async with TestClient(TestServer(app)) as client:
                    response = await client.post(
                        "/notion/webhook",
                        data=raw,
                        headers={"Content-Type": "application/json", "X-Notion-Signature": signature},
                    )
                    self.assertEqual(response.status, 200)
                    self.assertEqual((await response.json())["status"], "accepted")
                    if instance._background_tasks:
                        await list(instance._background_tasks)[0]
            instance.handle_message.assert_awaited_once()

    async def test_verification_handshake_accepts_token_when_signature_header_is_present(self):
        instance = self.make_adapter()
        with tempfile.TemporaryDirectory() as directory:
            instance.state = adapter.WebhookState(Path(directory) / "state.json")
            raw = json.dumps({"verification_token": "new-verification-token"}, separators=(",", ":")).encode()
            app = web.Application()
            app.router.add_post("/notion/webhook", instance._handle_webhook)
            async with TestClient(TestServer(app)) as client:
                response = await client.post(
                    "/notion/webhook",
                    data=raw,
                    headers={"Content-Type": "application/json", "X-Notion-Signature": "sha256=initial"},
                )
                self.assertEqual(response.status, 200)
                self.assertEqual((await response.json())["status"], "verification_token_captured")
            self.assertEqual(instance.state.load()["verification_token"], "new-verification-token")


if __name__ == "__main__":
    unittest.main()
