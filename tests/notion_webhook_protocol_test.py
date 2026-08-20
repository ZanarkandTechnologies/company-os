from __future__ import annotations

import hashlib
import hmac
import importlib.util
import os
import stat
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "profiles/howie-ai/plugins/platforms/notion/protocol.py"
SPEC = importlib.util.spec_from_file_location("notion_protocol", MODULE_PATH)
protocol = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(protocol)

API_PATH = ROOT / "profiles/howie-ai/plugins/platforms/notion/api.py"
API_SPEC = importlib.util.spec_from_file_location("notion_api", API_PATH)
notion_api = importlib.util.module_from_spec(API_SPEC)
assert API_SPEC and API_SPEC.loader
API_SPEC.loader.exec_module(notion_api)


class NotionProtocolTests(unittest.TestCase):
    def test_signature_accepts_exact_raw_body_only(self):
        body = b'{"id":"event-1"}'
        token = "verification-secret"
        signature = "sha256=" + hmac.new(token.encode(), body, hashlib.sha256).hexdigest()
        self.assertTrue(protocol.valid_signature(body, signature, token))
        self.assertFalse(protocol.valid_signature(body + b" ", signature, token))
        self.assertFalse(protocol.valid_signature(body, "sha256=bad", token))
        self.assertFalse(protocol.valid_signature(body, signature, ""))

    def test_token_capture_is_first_write_and_owner_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = protocol.WebhookState(path)
            self.assertTrue(state.capture_token("first"))
            self.assertTrue(state.capture_token("first"))
            self.assertFalse(state.capture_token("second"))
            self.assertEqual(state.load()["verification_token"], "first")
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def test_event_dedup_is_persistent_ttl_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            clock = [1_000_000.0]
            path = Path(directory) / "state.json"
            state = protocol.WebhookState(path, now=lambda: clock[0])
            self.assertTrue(state.mark_once("event-1"))
            self.assertFalse(state.mark_once("event-1"))
            self.assertFalse(state.mark_once(""))
            clock[0] += protocol.SEEN_TTL_SECONDS + 1
            self.assertTrue(state.mark_once("event-1"))
            for index in range(protocol.MAX_SEEN_EVENTS + 20):
                clock[0] += 1
                self.assertTrue(state.mark_once(f"event-{index + 2}"))
            self.assertLessEqual(len(state.load()["seen"]), protocol.MAX_SEEN_EVENTS)

    def test_workspace_capture_is_first_write(self):
        with tempfile.TemporaryDirectory() as directory:
            state = protocol.WebhookState(Path(directory) / "state.json")
            self.assertTrue(state.remember_workspace("workspace-1"))
            self.assertTrue(state.remember_workspace("workspace-1"))
            self.assertFalse(state.remember_workspace("workspace-2"))
            self.assertFalse(state.remember_workspace(""))
            self.assertEqual(state.load()["workspace_id"], "workspace-1")

    def test_reply_targets_are_persistent_ttl_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            clock = [1_000_000.0]
            path = Path(directory) / "state.json"
            state = protocol.WebhookState(path, now=lambda: clock[0])
            self.assertTrue(state.remember_reply_target("comment-1", "discussion-1"))
            self.assertEqual(protocol.WebhookState(path, now=lambda: clock[0]).reply_target("comment-1"), "discussion-1")
            self.assertFalse(state.remember_reply_target("", "discussion-2"))
            for index in range(protocol.MAX_REPLY_TARGETS + 20):
                clock[0] += 1
                self.assertTrue(state.remember_reply_target(f"comment-{index + 2}", f"discussion-{index + 2}"))
            self.assertLessEqual(len(state.load()["reply_targets"]), protocol.MAX_REPLY_TARGETS)
            clock[0] += protocol.REPLY_TARGET_TTL_SECONDS + 1
            self.assertEqual(state.reply_target(f"comment-{protocol.MAX_REPLY_TARGETS + 21}"), "")

    def test_successful_reply_receipt_is_persistent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = protocol.WebhookState(path, now=lambda: 1_000_000.0)
            self.assertTrue(state.remember_sent_reply("comment-1", "reply-1"))
            self.assertFalse(state.remember_sent_reply("", "reply-2"))
            receipt = protocol.WebhookState(path).load()["last_reply"]
            self.assertEqual(receipt["comment_id"], "comment-1")
            self.assertEqual(receipt["message_id"], "reply-1")
            self.assertEqual(receipt["sent_at"], 1_000_000.0)

    def test_page_updates_are_disabled_by_default(self):
        with patch.dict(os.environ, {"NOTION_ENABLE_WRITES": "false"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "writes are disabled"):
                notion_api.update_page_properties("page-1", {"Status": {"status": {"name": "Done"}}})

    def test_page_ids_cannot_escape_the_pages_endpoint(self):
        with self.assertRaisesRegex(ValueError, "Notion UUID"):
            notion_api.get_page("../users")
        self.assertEqual(
            notion_api._page_id("01234567-89ab-cdef-0123-456789abcdef"),
            "01234567-89ab-cdef-0123-456789abcdef",
        )

    def test_data_source_catalog_validates_root_and_paginates(self):
        root = "01234567-89ab-cdef-0123-456789abcdef"
        source_1 = "11111111-1111-1111-1111-111111111111"
        source_2 = "22222222-2222-2222-2222-222222222222"

        def fake_request(method, path, body=None):
            if path == f"/pages/{root}":
                return {"id": root, "properties": {"title": {"type": "title"}}}
            if path == "/search" and not body.get("start_cursor"):
                return {
                    "results": [{"id": source_1, "title": [{"plain_text": "Tasks"}], "properties": {"Status": {"id": "s", "type": "status"}}}],
                    "has_more": True,
                    "next_cursor": "cursor-1",
                }
            if path == "/search" and body.get("start_cursor") == "cursor-1":
                return {"results": [{"id": source_2, "title": [{"plain_text": "Projects"}], "properties": {}}], "has_more": False}
            self.fail(f"unexpected request: {method} {path} {body}")

        with patch.dict(os.environ, {"NOTION_ROOT_PAGE_ID": root, "NOTION_ALLOWED_DATA_SOURCES": f"{source_1},{source_2}"}, clear=False), patch.object(notion_api, "_request", side_effect=fake_request):
            catalog = notion_api.list_data_sources()
        self.assertEqual([item["title"] for item in catalog["data_sources"]], ["Tasks", "Projects"])
        self.assertEqual(catalog["data_sources"][0]["properties"]["Status"]["type"], "status")

    def test_ticket_context_reads_blocks_and_open_comments(self):
        page = "01234567-89ab-cdef-0123-456789abcdef"
        block = "11111111-2222-3333-4444-555555555555"
        source = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"

        def fake_request(method, path, body=None):
            del body
            if path == f"/pages/{page}":
                return {"id": page, "parent": {"type": "data_source_id", "data_source_id": source}, "properties": {"Name": {"type": "title"}}}
            if path == f"/blocks/{page}/children?page_size=100":
                return {"results": [{"id": block, "type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Ticket body"}]}, "has_children": False}], "has_more": False}
            if path == f"/comments?block_id={page}&page_size=100":
                return {"results": [{"id": "c1", "discussion_id": "d1", "rich_text": [{"plain_text": "Page comment"}]}], "has_more": False}
            if path == f"/comments?block_id={block}&page_size=100":
                return {"results": [{"id": "c2", "discussion_id": "d2", "rich_text": [{"plain_text": "Inline comment"}]}], "has_more": False}
            self.fail(f"unexpected request: {method} {path}")

        with patch.dict(os.environ, {"NOTION_ALLOWED_DATA_SOURCES": source}, clear=False), patch.object(notion_api, "_request", side_effect=fake_request):
            context = notion_api.get_ticket_context(page)
        self.assertEqual(context["blocks"][0]["text"], "Ticket body")
        self.assertEqual([item["text"] for item in context["open_comments"]], ["Page comment", "Inline comment"])
        self.assertFalse(context["limits"]["resolved_comments_available"])

    def test_ticket_context_rejects_pages_outside_catalog(self):
        page = "01234567-89ab-cdef-0123-456789abcdef"
        allowed = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
        other = "cccccccc-1111-2222-3333-dddddddddddd"
        with patch.dict(os.environ, {"NOTION_ALLOWED_DATA_SOURCES": allowed}, clear=False), patch.object(
            notion_api,
            "_request",
            return_value={"id": page, "parent": {"type": "data_source_id", "data_source_id": other}, "properties": {}},
        ):
            with self.assertRaisesRegex(RuntimeError, "outside the configured PKMS"):
                notion_api.get_ticket_context(page)

    def test_comment_replies_are_always_enabled_and_use_discussion_id(self):
        discussion = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        with patch.dict(os.environ, {"NOTION_ENABLE_COMMENT_REPLIES": "false"}, clear=False), patch.object(
            notion_api,
            "_request",
            return_value={"id": "reply-1", "discussion_id": discussion},
        ) as request:
            result = notion_api.create_comment_reply(f"discussion:{discussion}", "Answer")
        self.assertEqual(result["id"], "reply-1")
        payload = request.call_args.args[2]
        self.assertEqual(payload["discussion_id"], discussion)
        self.assertEqual(payload["rich_text"][0]["text"]["content"], "Answer")


if __name__ == "__main__":
    unittest.main()
