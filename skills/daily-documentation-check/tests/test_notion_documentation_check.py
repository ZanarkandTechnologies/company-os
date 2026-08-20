from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "notion_documentation_check.py"
SPEC = importlib.util.spec_from_file_location("notion_documentation_check", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class DailyDocumentationCheckTests(unittest.TestCase):
    def test_local_day_uses_dst_aware_utc_boundaries(self) -> None:
        start, end = module.utc_window("America/New_York", date(2026, 3, 8))
        self.assertEqual(start, "2026-03-08T05:00:00Z")
        self.assertEqual(end, "2026-03-09T04:00:00Z")

    def test_marker_is_stable_across_order_and_whitespace(self) -> None:
        first = module.marker("page", "template", ["Next action", " Due date "])
        second = module.marker("page", "template", ["due   date", "next action"])
        self.assertEqual(first, second)

    def test_proposal_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "request.json"
            request.write_text(json.dumps({
                "page_id": "page-1", "template_ref": "template-1",
                "missing_items": ["next action"],
                "comment": "For documentation, could you add the next action?",
            }), encoding="utf-8")
            args = type("Args", (), {"input": request, "apply": False})()
            with patch.object(module, "list_comments", return_value=[]), patch.object(module, "emit") as emit:
                self.assertEqual(module.comment(args), 0)
            self.assertEqual(emit.call_args.args[0], "proposal")

    def test_existing_marker_prevents_duplicate_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "request.json"
            payload = {
                "page_id": "page-1", "template_ref": "template-1",
                "missing_items": ["next action"],
                "comment": "For documentation, could you add the next action?",
            }
            request.write_text(json.dumps(payload), encoding="utf-8")
            tag = module.marker("page-1", "template-1", ["next action"])
            args = type("Args", (), {"input": request, "apply": True, "comment_policy": "approved"})()
            with patch.object(module, "list_comments", return_value=[{"id": "c1", "text": tag}]), patch.object(module, "run_ntn") as run, patch.object(module, "emit") as emit:
                self.assertEqual(module.comment(args), 0)
            run.assert_not_called()
            self.assertEqual(emit.call_args.args[0], "duplicate")

    def test_apply_requires_approved_comment_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "request.json"
            request.write_text(json.dumps({
                "page_id": "page-1", "template_ref": "template-1",
                "missing_items": ["next action"], "comment": "Please add the next action.",
            }), encoding="utf-8")
            args = type("Args", (), {
                "input": request, "apply": True, "comment_policy": "proposal-only",
            })()
            with patch.object(module, "list_comments", return_value=[]), patch.object(module, "run_ntn") as run:
                with self.assertRaisesRegex(module.CheckError, "comment_policy_not_approved"):
                    module.comment(args)
            run.assert_not_called()

    def test_comment_listing_uses_query_parameters(self) -> None:
        with patch.object(module, "run_ntn", return_value='{"results": []}') as run:
            self.assertEqual(module.list_comments("page-1"), [])
        self.assertIn("block_id==page-1", run.call_args.args)
        self.assertIn("page_size==100", run.call_args.args)

    def test_fetch_marks_bounded_query_partial(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mapping = Path(directory) / "templates.json"
            mapping.write_text('{"templates":{"Task":"template"}}', encoding="utf-8")
            args = type("Args", (), {
                "data_source_id": "work", "template_map": mapping, "type_property": "Type",
                "timezone": "Asia/Kuala_Lumpur", "date": "2026-08-20", "page_size": 1,
            })()
            response = {"results": [{
                "id": "page-1", "url": "https://notion.so/page-1",
                "last_edited_time": "2026-08-20T01:00:00Z",
                "properties": {"Type": {"select": {"name": "Task"}}},
            }], "has_more": True}
            with patch.object(module, "query_records", return_value=response), patch.object(module, "page_markdown", side_effect=["# Template", "# Record"]), patch.object(module, "list_comments", return_value=[]), patch.object(module, "emit") as emit:
                self.assertEqual(module.fetch(args), 0)
            self.assertTrue(emit.call_args.kwargs["partial"])
            self.assertEqual(emit.call_args.kwargs["records"][0]["template_page_id"], "template")

    def test_fetch_routes_each_record_type_to_its_template(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mapping = Path(directory) / "templates.json"
            mapping.write_text('{"templates":{"Task":"task-template","Meeting":"meeting-template"}}', encoding="utf-8")
            args = type("Args", (), {
                "data_source_id": "work", "template_map": mapping, "type_property": "Type",
                "timezone": "Asia/Kuala_Lumpur", "date": "2026-08-20", "page_size": 25,
            })()
            response = {"results": [
                {"id": "task-1", "properties": {"Type": {"select": {"name": "Task"}}}},
                {"id": "meeting-1", "properties": {"Type": {"select": {"name": "Meeting"}}}},
                {"id": "issue-1", "properties": {"Type": {"select": {"name": "Issue"}}}},
            ], "has_more": False}
            with patch.object(module, "query_records", return_value=response), patch.object(module, "page_markdown", side_effect=["# Meeting template", "# Task template", "# Task", "# Meeting"]), patch.object(module, "list_comments", return_value=[]), patch.object(module, "emit") as emit:
                self.assertEqual(module.fetch(args), 0)
            records = emit.call_args.kwargs["records"]
            self.assertEqual(records[0]["template_page_id"], "task-template")
            self.assertEqual(records[1]["template_page_id"], "meeting-template")
            self.assertEqual(records[2]["configuration_gap"], "unmapped_template")


if __name__ == "__main__":
    unittest.main()
