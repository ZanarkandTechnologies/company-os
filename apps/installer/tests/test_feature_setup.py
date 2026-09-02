from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.installer.feature_setup import (
    FeatureSetupError,
    bindings_for_workspace,
    load_answers,
    render_file,
    render_text,
    save_answers,
    selected_bindings,
    write_batch,
)
from apps.installer.provider_catalog import load_catalog


class FeatureSetupTests(unittest.TestCase):
    def test_answers_round_trip_without_runtime_indirection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config" / "setup-answers.json"
            save_answers(
                path,
                {"daily.projects": "Fetch Projects from an exact URL."},
                {"daily.projects": "preset_1"},
                {"daily.projects": ("notion",)},
                {"daily.projects": {"notion": "https://notion.so/projects"}},
            )
            self.assertEqual(
                load_answers(path),
                {"daily.projects": "Fetch Projects from an exact URL."},
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 3)
            self.assertEqual(payload["selections"]["daily.projects"], "preset_1")
            self.assertEqual(payload["provider_requirements"]["daily.projects"], ["notion"])
            self.assertEqual(
                payload["provider_targets"]["daily.projects"]["notion"],
                "https://notion.so/projects",
            )

    def test_renderer_hardcodes_answer_inside_named_slot(self) -> None:
        template = "before\n<!-- setup:daily.projects -->\nold\n<!-- /setup:daily.projects -->\nafter\n"
        rendered, slots = render_text(
            template, {"daily.projects": "Fetch Projects from https://example.invalid."}
        )
        self.assertIn("Fetch Projects from https://example.invalid.", rendered)
        self.assertNotIn("\nold\n", rendered)
        self.assertEqual(slots, ("daily.projects",))
        self.assertNotIn("setup-answers.json", rendered)

    def test_renderer_rejects_missing_and_duplicate_slots(self) -> None:
        with self.assertRaisesRegex(FeatureSetupError, "answers_missing"):
            render_text("<!-- setup:a -->x<!-- /setup:a -->", {})
        duplicate = (
            "<!-- setup:a -->x<!-- /setup:a -->"
            "<!-- setup:a -->y<!-- /setup:a -->"
        )
        with self.assertRaisesRegex(FeatureSetupError, "slot_duplicate"):
            render_text(duplicate, {"a": "z"})
        with self.assertRaisesRegex(FeatureSetupError, "contains_marker"):
            render_text(
                "<!-- setup:a -->x<!-- /setup:a -->",
                {"a": "<!-- setup:evil -->"},
            )

    def test_preview_does_not_write_and_apply_does(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "daily.md"
            path.write_text(
                "<!-- setup:a -->\nold\n<!-- /setup:a -->\n", encoding="utf-8"
            )
            preview = render_file(path, {"a": "new"}, apply=False)
            self.assertTrue(preview.changed)
            self.assertIn("old", path.read_text(encoding="utf-8"))
            render_file(path, {"a": "new"}, apply=True)
            self.assertIn("new", path.read_text(encoding="utf-8"))

    def test_feature_answers_derive_only_required_provider_connections(self) -> None:
        bindings = selected_bindings(
            {
                "daily.projects": "Fetch Projects from `https://notion.so/projects`.",
                "daily.people": "Fetch People from `https://notion.so/people`.",
                "daily.progress_route": "Use Gmail when preferred.",
                "weekly.report_recipients": "Send with Gmail to owner@example.com.",
                "weekly.reports_destination": "Upload to https://drive.google.com/drive/folders/abc.",
            },
            load_catalog(),
            {
                "daily.projects": ("notion",),
                "daily.progress_route": ("notion", "gmail"),
                "weekly.reports_destination": ("google_drive",),
            },
            {
                "daily.projects": {"notion": "https://notion.so/projects"},
                "daily.people": {"notion": "https://notion.so/people"},
                "weekly.reports_destination": {
                    "google_drive": "https://drive.google.com/drive/folders/abc"
                },
            },
        )
        self.assertEqual(
            {(item["data_source"], item["provider"]["id"]) for item in bindings},
            {
                ("projects", "notion"),
                ("people", "notion"),
                ("operator_email", "gmail"),
                ("storage", "google_drive"),
            },
        )

    def test_saved_feature_answers_override_legacy_workspace_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace.hermes.md"
            workspace.write_text("legacy content without managed tables\n", encoding="utf-8")
            save_answers(
                root / "config" / "setup-answers.json",
                {"daily.projects": "Fetch from `https://notion.so/projects`."},
                {"daily.projects": "preset_1"},
                {"daily.projects": ("notion",)},
                {"daily.projects": {"notion": "https://notion.so/projects"}},
            )
            bindings = bindings_for_workspace(workspace, load_catalog())
            self.assertEqual(
                [(item["data_source"], item["provider"]["id"]) for item in bindings],
                [("projects", "notion")],
            )

    def test_notion_comment_route_requires_a_notion_source(self) -> None:
        with self.assertRaisesRegex(
            FeatureSetupError, "notion_source_required_for_notion_comments"
        ):
            selected_bindings(
                {
                    "daily.projects": "Fetch Projects from a custom warehouse.",
                    "daily.documentation_route": "Comment on the exact Notion Work item.",
                },
                load_catalog(),
                {"daily.documentation_route": ("notion",)},
                {},
            )

    def test_provider_authorization_is_not_inferred_from_answer_words(self) -> None:
        bindings = selected_bindings(
            {
                "daily.projects": "Fetch from https://notion.so/projects.",
                "weekly.report_recipients": "The word Gmail appears here.",
            },
            load_catalog(),
            {"daily.projects": ("notion",)},
            {"daily.projects": {"notion": "https://notion.so/projects"}},
        )
        self.assertEqual(
            [(item["data_source"], item["provider"]["id"]) for item in bindings],
            [("projects", "notion")],
        )

    def test_each_drive_destination_gets_its_own_exact_certification_case(self) -> None:
        bindings = selected_bindings(
            {
                "weekly.reports_destination": "Use https://drive.google.com/drive/folders/reports.",
                "weekly.sops_destination": "Use https://drive.google.com/drive/folders/sops.",
            },
            load_catalog(),
            {
                "weekly.reports_destination": ("google_drive",),
                "weekly.sops_destination": ("google_drive",),
            },
            {
                "weekly.reports_destination": {
                    "google_drive": "https://drive.google.com/drive/folders/reports"
                },
                "weekly.sops_destination": {
                    "google_drive": "https://drive.google.com/drive/folders/sops"
                },
            },
        )
        self.assertEqual(
            [item["source"] for item in bindings],
            [
                "https://drive.google.com/drive/folders/reports",
                "https://drive.google.com/drive/folders/sops",
            ],
        )
        self.assertEqual(len({item["case_id"] for item in bindings}), 2)

    def test_provider_target_must_be_hardcoded_in_its_rendered_answer(self) -> None:
        with self.assertRaisesRegex(FeatureSetupError, "provider_target_not_rendered"):
            selected_bindings(
                {"daily.projects": "Fetch from a different source."},
                load_catalog(),
                {"daily.projects": ("notion",)},
                {"daily.projects": {"notion": "https://notion.so/projects"}},
            )

    def test_batch_write_restores_every_prior_file_after_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.md"
            second = root / "second.md"
            first.write_text("first-old\n", encoding="utf-8")
            second.write_text("second-old\n", encoding="utf-8")
            from apps.installer import feature_setup

            original_write = feature_setup._atomic_write
            calls = 0

            def fail_second(path: Path, content: str) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated write failure")
                original_write(path, content)

            with patch.object(feature_setup, "_atomic_write", side_effect=fail_second):
                with self.assertRaisesRegex(OSError, "simulated"):
                    write_batch({first: "first-new\n", second: "second-new\n"})
            self.assertEqual(first.read_text(encoding="utf-8"), "first-old\n")
            self.assertEqual(second.read_text(encoding="utf-8"), "second-old\n")


if __name__ == "__main__":
    unittest.main()
