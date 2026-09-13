from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from plugins.conversation_context import read_conversations
from plugins.conversation_context.__main__ import main
from plugins.conversation_context.intake import IntakeError, canonical, digest, publish_bundle, read_project
from plugins.conversation_context.models import Bundle


def example() -> dict:
    return {"schema_version": 1, "project_id": "PROJ-CMT", "member_id": "PERSON-AISHA",
            "source": "chatgpt_manual", "week": "2026-W35", "timezone": "Asia/Kuala_Lumpur",
            "collected_at": "2026-08-30T22:00:00+08:00", "coverage": "partial",
            "coverage_note": "Member-selected work conversation; other chats not submitted.",
            "conversations": [{"conversation_id": "chat-1", "revision": "r1",
                               "source_reference": "member-submission:chat-1", "task_id": "TASK-101",
                               "messages": [{"message_id": "m1", "role": "user",
                                             "occurred_at": "2026-08-25T10:00:00+08:00",
                                             "text": "Waiting for supplier credentials."},
                                            {"message_id": "m2", "role": "assistant",
                                             "occurred_at": "2026-08-25T10:01:00+08:00",
                                             "text": "I completed the integration."}]}]}


class ConversationIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = {"schema_version": 1, "timezone": "Asia/Kuala_Lumpur", "projects": {
            "PROJ-CMT": [{"source": "chatgpt_manual", "member_id": "PERSON-AISHA"}]}}
        self.write_policy()

    def write_policy(self) -> None:
        (self.root / "policy.json").write_bytes(canonical(self.policy))

    def test_import_read_and_repeat_preserve_roles_and_stable_evidence(self) -> None:
        bundle = Bundle.model_validate(example())
        receipt = publish_bundle(self.root, bundle)
        self.assertEqual(receipt["status"], "imported")
        first = read_project(self.root, "PROJ-CMT", "2026-W35")
        second = read_project(self.root, "PROJ-CMT", "2026-W35")
        self.assertEqual(first, second)
        self.assertEqual(publish_bundle(self.root, bundle)["status"], "unchanged")
        messages = first["conversations"][0]["messages"]
        self.assertEqual([item["role"] for item in messages], ["user", "assistant"])
        self.assertEqual(messages[1]["text"], "I completed the integration.")
        self.assertNotEqual(messages[0]["evidence_id"], messages[1]["evidence_id"])
        self.assertEqual(first["status"], "partial")

    def test_update_requires_matching_digest_and_keeps_observation_identity(self) -> None:
        original = Bundle.model_validate(example())
        receipt = publish_bundle(self.root, original)
        before = read_project(self.root, "PROJ-CMT", "2026-W35")["conversations"][0]["messages"][0]
        revised = example()
        revised["conversations"][0]["revision"] = "r2"
        revised["conversations"][0]["messages"][0]["text"] = "Credentials received; integration not yet tested."
        with self.assertRaisesRegex(IntakeError, "revision_conflict"):
            publish_bundle(self.root, Bundle.model_validate(revised))
        publish_bundle(self.root, Bundle.model_validate(revised), receipt["source_digest"])
        after = read_project(self.root, "PROJ-CMT", "2026-W35")["conversations"][0]["messages"][0]
        self.assertEqual(before["evidence_id"], after["evidence_id"])
        self.assertNotEqual(before["content_digest"], after["content_digest"])

    def test_missing_source_is_unavailable_not_empty_success(self) -> None:
        result = read_project(self.root, "PROJ-CMT", "2026-W35")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["coverage"][0]["status"], "unavailable")
        self.assertEqual(result["conversations"], [])

    def test_unauthorized_member_project_and_traversal_are_rejected(self) -> None:
        for project in ["OTHER", "../PROJ-CMT"]:
            with self.assertRaisesRegex(IntakeError, "project_not_authorized"):
                read_project(self.root, project, "2026-W35")
        data = example()
        data["member_id"] = "PERSON-OTHER"
        with self.assertRaisesRegex(IntakeError, "source_not_authorized"):
            publish_bundle(self.root, Bundle.model_validate(data))

    def test_wrong_file_identity_and_unknown_fields_never_return_content(self) -> None:
        bundle = Bundle.model_validate(example())
        publish_bundle(self.root, bundle)
        path = self.root / "2026-W35/project--PROJ-CMT/chatgpt_manual--PERSON-AISHA.json"
        for key, value in [("project_id", "OTHER"), ("credentials", "private-marker")]:
            data = example()
            data[key] = value
            path.write_bytes(canonical(data))
            result = read_project(self.root, "PROJ-CMT", "2026-W35")
            self.assertEqual(result["conversations"], [])
            self.assertNotIn("private-marker", json.dumps(result))

    def test_duplicate_messages_and_outside_week_or_naive_dates_are_rejected(self) -> None:
        for date in ["2026-08-23T10:00:00+08:00", "2026-08-25T10:00:00", "2026-08-31T00:00:00+08:00"]:
            data = example()
            data["conversations"][0]["messages"][0]["occurred_at"] = date
            with self.assertRaises(ValueError):
                Bundle.model_validate(data)
        data = example()
        data["conversations"][0]["messages"].append(copy.deepcopy(data["conversations"][0]["messages"][0]))
        with self.assertRaises(ValueError):
            Bundle.model_validate(data)

    def test_week_is_evaluated_in_company_timezone(self) -> None:
        data = example()
        data["conversations"][0]["messages"][0]["occurred_at"] = "2026-08-23T16:00:00Z"
        Bundle.model_validate(data)  # Monday midnight in Kuala Lumpur.

    def test_withdrawal_removes_returned_text_and_preserves_coverage(self) -> None:
        receipt = publish_bundle(self.root, Bundle.model_validate(example()))
        data = example()
        data.update(coverage="withdrawn", coverage_note="Member withdrew this submission.", conversations=[])
        publish_bundle(self.root, Bundle.model_validate(data), receipt["source_digest"])
        result = read_project(self.root, "PROJ-CMT", "2026-W35")
        self.assertEqual(result["conversations"], [])
        self.assertEqual(result["coverage"][0]["status"], "withdrawn")

    def test_disabled_tool_does_not_read_files(self) -> None:
        with patch.dict("os.environ", {"COMPANY_OS_CONVERSATION_INTAKE": ""}), patch(
            "plugins.conversation_context.read_project", side_effect=AssertionError("must not read")
        ):
            self.assertEqual(json.loads(read_conversations())["status"], "disabled")

    def test_private_root_refuses_repository_and_symlink(self) -> None:
        (self.root / ".git").mkdir()
        with self.assertRaisesRegex(IntakeError, "outside_source_repository"):
            read_project(self.root, "PROJ-CMT", "2026-W35")

    def test_oversized_input_is_reported_without_body(self) -> None:
        publish_bundle(self.root, Bundle.model_validate(example()))
        path = self.root / "2026-W35/project--PROJ-CMT/chatgpt_manual--PERSON-AISHA.json"
        path.write_bytes(b"x" * 262145)
        result = read_project(self.root, "PROJ-CMT", "2026-W35")
        self.assertEqual(result["coverage"][0]["note"], "intake_file_too_large")
        self.assertEqual(result["conversations"], [])

    def test_selected_sources_do_not_read_other_bindings(self) -> None:
        publish_bundle(self.root, Bundle.model_validate(example()))
        result = read_project(self.root, "PROJ-CMT", "2026-W35", ["codex_manual"])
        self.assertEqual(result["conversations"], [])
        self.assertEqual(result["coverage"], [])

    def test_cli_validation_never_prints_conversation_bodies(self) -> None:
        publish_bundle(self.root, Bundle.model_validate(example()))
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["validate", "--root", str(self.root), "--project", "PROJ-CMT", "--week", "2026-W35"])
        self.assertEqual(code, 1)
        self.assertNotIn("credentials", output.getvalue())
        self.assertNotIn("conversations", output.getvalue())

    def test_symlink_cannot_escape_intake(self) -> None:
        target = self.root / "elsewhere"
        target.mkdir()
        link = self.root / "2026-W35"
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("Host cannot create symlinks")
        result = read_project(self.root, "PROJ-CMT", "2026-W35")
        self.assertEqual(result["coverage"][0]["note"], "intake_links_forbidden")

    def test_import_lock_preserves_existing_bundle(self) -> None:
        bundle = Bundle.model_validate(example())
        receipt = publish_bundle(self.root, bundle)
        path = self.root / "2026-W35/project--PROJ-CMT/chatgpt_manual--PERSON-AISHA.json"
        path.with_suffix(".lock").touch()
        with self.assertRaisesRegex(IntakeError, "intake_import_busy"):
            publish_bundle(self.root, bundle)
        self.assertEqual(digest(path.read_bytes()), receipt["source_digest"])
