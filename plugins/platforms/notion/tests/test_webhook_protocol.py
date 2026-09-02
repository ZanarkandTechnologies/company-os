from __future__ import annotations

import hashlib
import hmac
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from plugins.platforms.notion import api  # noqa: E402
from plugins.platforms.notion import protocol  # noqa: E402


class NotionWebhookProtocolTests(unittest.TestCase):
    def test_signature_accepts_exact_raw_body_only(self) -> None:
        body = b'{"id":"event-1"}'
        token = "verification-secret"
        signature = "sha256=" + hmac.new(token.encode(), body, hashlib.sha256).hexdigest()
        self.assertTrue(protocol.valid_signature(body, signature, token))
        self.assertFalse(protocol.valid_signature(body + b" ", signature, token))
        self.assertFalse(protocol.valid_signature(body, "sha256=bad", token))

    def test_state_is_owner_only_bounded_and_preserves_silence_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            clock = [1_000_000.0]
            path = Path(directory) / "state.json"
            state = protocol.WebhookState(path, now=lambda: clock[0])
            self.assertTrue(state.capture_token("first"))
            self.assertFalse(state.capture_token("second"))
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
            self.assertTrue(state.remember_reply_target("comment-1", "discussion-1", allow_silence=True))
            self.assertEqual(state.reply_target("comment-1"), "discussion-1")
            self.assertTrue(state.reply_may_be_silent("comment-1"))
            clock[0] += protocol.REPLY_TARGET_TTL_SECONDS + 1
            self.assertEqual(state.reply_target("comment-1"), "")
            self.assertFalse(state.reply_may_be_silent("comment-1"))

    def test_comment_parent_accepts_page_or_block_and_rejects_missing_parent(self) -> None:
        page = "11111111-2222-3333-4444-555555555555"
        block = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        self.assertEqual(api.comment_parent_id({"parent": {"page_id": page}}), page)
        self.assertEqual(api.comment_parent_id({"parent": {"block_id": block}}), block)
        with self.assertRaisesRegex(ValueError, "comment parent"):
            api.comment_parent_id({"parent": {}})

    def test_list_comments_paginates_and_keeps_thread_identity(self) -> None:
        parent = "11111111-2222-3333-4444-555555555555"
        first = {"id": "c1", "discussion_id": "d1", "rich_text": [{"plain_text": "First"}]}
        second = {"id": "c2", "discussion_id": "d1", "rich_text": [{"plain_text": "Second"}]}

        def fake_request(method, path, body=None):
            del body
            self.assertEqual(method, "GET")
            if "start_cursor" not in path:
                return {"results": [first], "has_more": True, "next_cursor": "next"}
            return {"results": [second], "has_more": False}

        with patch.object(api, "_request", side_effect=fake_request):
            comments = api.list_comments(parent)
        self.assertEqual([item["text"] for item in comments], ["First", "Second"])
        self.assertEqual({item["discussion_id"] for item in comments}, {"d1"})

    def test_page_property_writes_remain_disabled_by_default(self) -> None:
        with patch.dict(os.environ, {"NOTION_ENABLE_WRITES": "false"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "writes are disabled"):
                api.update_page_properties("11111111-2222-3333-4444-555555555555", {})

if __name__ == "__main__":
    unittest.main()
