from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[3]
SCRIPT = REPOSITORY / "skills/setup-company-workspace/scripts/setup_workspace.py"
SPEC = importlib.util.spec_from_file_location("setup_workspace", SCRIPT)
assert SPEC and SPEC.loader
SETUP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SETUP)


def make_source(root: Path, status: str = "proposed-owner-review") -> Path:
    source = root / "source"
    (source / "automations").mkdir(parents=True)
    (source / "skills/setup-company-workspace").mkdir(parents=True)
    (source / "workspace.hermes.md").write_text(
        f"---\nstatus: {status}\n---\n# Workspace\n", encoding="utf-8"
    )
    (source / "automations/daily.md").write_text("daily\n", encoding="utf-8")
    (source / "skills/README.md").write_text("Not an installable package.\n", encoding="utf-8")
    (source / "skills/setup-company-workspace/SKILL.md").write_text(
        "# Setup company workspace\n", encoding="utf-8"
    )
    return source


class SetupWorkspaceTests(unittest.TestCase):
    def run_setup(
        self, source: Path, workspace: Path, profile_home: Path, *extra: str
    ) -> tuple[int, dict[str, object]]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--source-project", str(source),
             "--workspace", str(workspace), "--profile-home", str(profile_home), *extra],
            text=True, capture_output=True, check=False,
        )
        self.assertTrue(result.stdout, result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_preview_reports_allowlisted_changes_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_source(root)
            workspace, profile_home = root / "workspace", root / "profile"
            workspace.mkdir()
            profile_home.mkdir()
            code, receipt = self.run_setup(source, workspace, profile_home)
            self.assertEqual(code, 0)
            self.assertEqual(receipt["state"], "changes_pending")
            self.assertIn("workspace:.hermes.md", receipt["pending"])
            self.assertIn("profile:skills/setup-company-workspace/SKILL.md", receipt["pending"])
            self.assertNotIn("profile:skills/README.md", receipt["pending"])
            self.assertFalse((workspace / ".hermes.md").exists())
            self.assertEqual(receipt["deletion_count"], 0)

    def test_apply_refuses_unapproved_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_source(root)
            workspace, profile_home = root / "workspace", root / "profile"
            workspace.mkdir()
            profile_home.mkdir()
            code, receipt = self.run_setup(source, workspace, profile_home, "--apply")
            self.assertEqual(code, 2)
            self.assertEqual(receipt["blocker"], "workspace_context_requires_owner_approval")
            self.assertFalse((workspace / ".hermes.md").exists())

    def test_apply_refuses_approved_context_with_onboarding_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_source(root, "approved")
            (source / "workspace.hermes.md").write_text(
                "---\nstatus: approved\n---\n# {{COMPANY_NAME}}\n<!-- ONBOARDING: finish -->\n",
                encoding="utf-8",
            )
            workspace, profile_home = root / "workspace", root / "profile"
            workspace.mkdir()
            profile_home.mkdir()
            code, receipt = self.run_setup(source, workspace, profile_home, "--apply")
            self.assertEqual(code, 2)
            self.assertEqual(receipt["blocker"], "workspace_context_invalid")
            self.assertFalse((workspace / ".hermes.md").exists())

    def test_apply_copies_only_managed_sources_when_context_is_approved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_source(root, "approved")
            workspace = root / "profile" / "workspace"
            profile_home = workspace.parent
            workspace.mkdir(parents=True)
            code = SETUP.run(source, workspace, profile_home, apply=True)
            self.assertEqual(code, 0)
            self.assertEqual(
                (workspace / ".hermes.md").read_text(encoding="utf-8"),
                (source / "workspace.hermes.md").read_text(encoding="utf-8"),
            )
            self.assertEqual((workspace / "automations/daily.md").read_text(encoding="utf-8"), "daily\n")
            self.assertTrue((profile_home / "skills/setup-company-workspace/SKILL.md").is_file())

    def test_apply_preflights_all_destinations_before_copying(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_source(root, "approved")
            workspace = root / "profile" / "workspace"
            profile_home = workspace.parent
            (workspace / "automations/daily.md").mkdir(parents=True)
            code = SETUP.run(source, workspace, profile_home, apply=True)
            self.assertEqual(code, 2)
            self.assertFalse((workspace / ".hermes.md").exists())

    def test_source_project_cannot_be_runtime_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_source(root)
            profile_home = root / "profile"
            profile_home.mkdir()
            code, receipt = self.run_setup(source, source, profile_home)
            self.assertEqual(code, 2)
            self.assertEqual(receipt["blocker"], "workspace_must_be_outside_source_project")

    def test_symlinked_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_source(root)
            actual, workspace, profile_home = root / "actual", root / "workspace", root / "profile"
            actual.mkdir()
            workspace.symlink_to(actual, target_is_directory=True)
            profile_home.mkdir()
            code, receipt = self.run_setup(source, workspace, profile_home)
            self.assertEqual(code, 2)
            self.assertEqual(receipt["blocker"], "workspace_must_not_be_symlink")

    def test_workspace_may_use_normal_profile_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = make_source(root)
            profile_home = root / "profile"
            workspace = profile_home / "workspace"
            workspace.mkdir(parents=True)
            code, receipt = self.run_setup(source, workspace, profile_home)
            self.assertEqual(code, 0)
            self.assertEqual(receipt["state"], "changes_pending")


if __name__ == "__main__":
    unittest.main()
