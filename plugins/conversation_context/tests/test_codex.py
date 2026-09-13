from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from plugins.conversation_context.codex import collect, read_session
from plugins.conversation_context.intake import IntakeError, canonical, publish_bundle, read_project
from plugins.conversation_context.models import Binding, Bundle


class CodexConversationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sessions = self.root / "sessions"
        self.sessions.mkdir()
        self.binding = Binding(source="codex_local", member_id="PERSON-AISHA", cwd=str(self.root / "repo"),
                               session_roots=[str(self.sessions)])
        self.path = self.sessions / "rollout-example.jsonl"

    def records(self) -> list[dict]:
        return [
            {"type": "session_meta", "payload": {"id": "session-1", "cwd": self.binding.cwd}},
            {"type": "response_item", "payload": {"type": "reasoning", "text": "reasoning-private-marker"}},
            {"type": "event_msg", "timestamp": "2026-08-25T10:00:00+08:00",
             "payload": {"type": "user_message", "message": "Investigate the missing supplier key."}},
            {"type": "response_item", "payload": {"type": "function_call_output", "output": "tool-private-marker"}},
            {"type": "event_msg", "timestamp": "2026-08-25T10:01:00+08:00",
             "payload": {"type": "agent_message", "message": "The integration needs credentials."}},
        ]

    def write(self, records: list[dict]) -> None:
        self.path.write_bytes(b"".join(canonical(item) for item in records))

    def test_collect_only_user_and_assistant_messages_with_partial_coverage(self) -> None:
        self.write(self.records())
        (self.sessions / "auth.json").write_text("never read me")
        result = collect(self.binding, "PROJ-CMT", "2026-W35", "Asia/Kuala_Lumpur")
        self.assertEqual(result.coverage, "partial")
        self.assertEqual(len(result.conversations), 1)
        self.assertEqual([item.role for item in result.conversations[0].messages], ["user", "assistant"])
        self.assertNotIn("private-marker", result.model_dump_json())
        again = collect(self.binding, "PROJ-CMT", "2026-W35", "Asia/Kuala_Lumpur")
        self.assertEqual(result.conversations, again.conversations)

    def test_other_project_body_is_not_parsed(self) -> None:
        header = self.records()[0]
        header["payload"]["cwd"] = str(self.root / "unrelated")
        self.path.write_bytes(canonical(header) + b"malformed private body\n")
        self.assertIsNone(read_session(self.path, self.binding, "2026-W35", "Asia/Kuala_Lumpur"))

    def test_older_session_can_have_messages_in_current_week(self) -> None:
        records = self.records()
        records[0]["timestamp"] = "2026-01-01T00:00:00Z"
        self.write(records)
        result = collect(self.binding, "PROJ-CMT", "2026-W35", "Asia/Kuala_Lumpur")
        self.assertEqual(len(result.conversations), 1)
        self.assertEqual(collect(self.binding, "PROJ-CMT", "2026-W34", "Asia/Kuala_Lumpur").conversations, [])

    def test_partial_last_line_and_compaction_do_not_publish_stale_claims(self) -> None:
        self.write(self.records())
        with self.path.open("ab") as stream:
            stream.write(b'{"unfinished":')
        result = collect(self.binding, "PROJ-CMT", "2026-W35", "Asia/Kuala_Lumpur")
        self.assertEqual(result.conversations, [])
        self.assertIn("incomplete_retry", result.coverage_note)
        records = self.records() + [{"type": "compacted", "payload": {}}]
        self.write(records)
        result = collect(self.binding, "PROJ-CMT", "2026-W35", "Asia/Kuala_Lumpur")
        self.assertEqual(result.conversations, [])
        self.assertIn("manual_selection", result.coverage_note)

    def test_project_change_is_rejected(self) -> None:
        self.write(self.records() + [{"type": "turn_context", "payload": {"cwd": str(self.root / "other")}}])
        result = collect(self.binding, "PROJ-CMT", "2026-W35", "Asia/Kuala_Lumpur")
        self.assertEqual(result.conversations, [])
        self.assertIn("project_changed", result.coverage_note)

    def test_duplicate_archived_copy_does_not_duplicate_conversation(self) -> None:
        self.write(self.records())
        (self.sessions / "rollout-copy.jsonl").write_bytes(self.path.read_bytes())
        self.assertEqual(len(collect(self.binding, "PROJ-CMT", "2026-W35", "Asia/Kuala_Lumpur").conversations), 1)
        records = self.records()
        records[-1]["payload"]["message"] = "Conflicting history"
        (self.sessions / "rollout-copy.jsonl").write_bytes(b"".join(canonical(item) for item in records))
        with self.assertRaisesRegex(IntakeError, "duplicate_session_conflict"):
            collect(self.binding, "PROJ-CMT", "2026-W35", "Asia/Kuala_Lumpur")

    def test_scan_budget_fails_closed(self) -> None:
        self.write(self.records())
        with patch("plugins.conversation_context.codex.MAX_SCAN_BYTES", 1):
            with self.assertRaisesRegex(IntakeError, "scan_limit"):
                collect(self.binding, "PROJ-CMT", "2026-W35", "Asia/Kuala_Lumpur")

    def desktop_records(self) -> list[dict]:
        return [self.records()[0],
                {"type": "response_item", "payload": {"type": "message", "role": "user",
                    "content": [{"type": "input_text", "text": "injected-context-private-marker"}]}},
                {"type": "event_msg", "timestamp": "2026-08-25T10:00:00+08:00",
                 "payload": {"type": "item_completed", "item": {"type": "UserMessage", "id": "user-native-1",
                    "content": [{"type": "text", "text": "Investigate the supplier key.", "text_elements": []}]}}},
                {"type": "event_msg", "timestamp": "2026-08-25T10:01:00+08:00",
                 "payload": {"type": "item_completed", "item": {"type": "AgentMessage", "id": "agent-progress",
                    "phase": "commentary", "content": [{"type": "Text", "text": "progress-private-marker"}]}}},
                {"type": "event_msg", "timestamp": "2026-08-25T10:02:00+08:00",
                 "payload": {"type": "item_completed", "item": {"type": "AgentMessage", "id": "agent-final-1",
                    "phase": "final_answer", "content": [{"type": "Text", "text": "The credentials are missing."}]}}}]

    def test_desktop_format_excludes_injected_context_and_duplicate_response_items(self) -> None:
        self.write(self.desktop_records())
        result = collect(self.binding, "PROJ-CMT", "2026-W35", "Asia/Kuala_Lumpur")
        self.assertEqual(len(result.conversations), 1)
        messages = result.conversations[0].messages
        self.assertEqual([item.role for item in messages], ["user", "assistant"])
        self.assertTrue(all(item.message_id.startswith("item-") for item in messages))
        self.assertNotIn("private-marker", result.model_dump_json())
        before = messages[0].message_id
        records = self.desktop_records()
        records.insert(1, {"type": "token_usage_record", "payload": {}})
        self.write(records)
        self.assertEqual(collect(self.binding, "PROJ-CMT", "2026-W35", "Asia/Kuala_Lumpur").conversations[0].messages[0].message_id, before)

    def test_mixed_formats_report_gap_instead_of_double_counting(self) -> None:
        self.write(self.desktop_records() + [self.records()[2]])
        result = collect(self.binding, "PROJ-CMT", "2026-W35", "Asia/Kuala_Lumpur")
        self.assertEqual(result.conversations, [])
        self.assertIn("mixed_message_formats", result.coverage_note)

    def test_native_read_tool_collects_only_configured_local_binding(self) -> None:
        self.write(self.records())
        (self.root / "policy.json").write_bytes(canonical({"schema_version": 1, "timezone": "Asia/Kuala_Lumpur",
            "projects": {"PROJ-CMT": [self.binding.model_dump()]}}))
        result = read_project(self.root, "PROJ-CMT", "2026-W35", ["codex_local"])
        self.assertEqual(len(result["conversations"]), 1)
        self.assertTrue(result["conversations"][0]["messages"][0]["evidence_id"].startswith("chat-"))

    def test_withdrawn_week_suppresses_automatic_codex_reads(self) -> None:
        (self.root / "policy.json").write_bytes(canonical({"schema_version": 1, "timezone": "Asia/Kuala_Lumpur",
            "projects": {"PROJ-CMT": [self.binding.model_dump()]}}))
        bundle = Bundle(schema_version=1, project_id="PROJ-CMT", member_id="PERSON-AISHA", source="codex_local",
                        week="2026-W35", timezone="Asia/Kuala_Lumpur", collected_at="2026-08-30T22:00:00+08:00",
                        coverage="withdrawn", coverage_note="Member withdrew this week.", conversations=[])
        publish_bundle(self.root, bundle)
        with patch("plugins.conversation_context.codex.collect", side_effect=AssertionError("must not collect")):
            result = read_project(self.root, "PROJ-CMT", "2026-W35")
        self.assertEqual(result["coverage"][0]["status"], "withdrawn")
        self.assertEqual(result["conversations"], [])
