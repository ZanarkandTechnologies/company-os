from __future__ import annotations

import json
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[3]
SCRIPT = PROJECT / "apps/installer/workspace.py"
SPEC = importlib.util.spec_from_file_location("setup_workspace", SCRIPT)
assert SPEC and SPEC.loader
SETUP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SETUP)


class SetupWorkspaceTests(unittest.TestCase):
    def run_setup(self, workspace: Path, profile_home: Path, *extra: str) -> tuple[int, dict[str, Any]]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--workspace", str(workspace),
             "--profile-home", str(profile_home), *extra],
            text=True, capture_output=True, check=False,
        )
        self.assertTrue(result.stdout, result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_preview_reports_allowlisted_changes_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace, profile_home = root / "workspace", root / "profile"
            workspace.mkdir()
            profile_home.mkdir()
            code, receipt = self.run_setup(workspace, profile_home)
            self.assertEqual(code, 0)
            self.assertEqual(receipt["state"], "changes_pending")
            self.assertIn("workspace:.hermes.md", receipt["pending"])
            self.assertTrue(any(item.startswith("workspace:templates/")
                                for item in receipt["pending"]))
            self.assertIn("profile:plugins/platforms/notion/plugin.yaml", receipt["pending"])
            self.assertFalse((workspace / ".hermes.md").exists())

    def test_apply_refuses_unapproved_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            workspace, profile_home = root / "workspace", root / "profile"
            source.mkdir()
            (source / "automations").mkdir()
            (source / "templates").mkdir()
            workspace.mkdir()
            profile_home.mkdir()
            config = source / "workspace.hermes.md"
            config.write_text("---\nstatus: proposed-owner-review\n---\n# Workspace\n", encoding="utf-8")
            output = io.StringIO()
            with patch.object(SETUP, "PROJECT", source), patch.object(SETUP, "CONFIG", config), redirect_stdout(output):
                code = SETUP.run(workspace, profile_home, apply=True)
            receipt = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            self.assertEqual(receipt["blocker"], "workspace_context_requires_owner_approval")
            self.assertFalse((workspace / ".hermes.md").exists())

    def test_apply_copies_only_managed_sources_when_context_is_approved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            workspace = root / "profile" / "workspace"
            profile_home = workspace.parent
            source.mkdir(parents=True)
            (source / "automations").mkdir()
            (source / "apps/installer/prompts").mkdir(parents=True)
            (source / "skills/pm-daily").mkdir(parents=True)
            (source / "skills/pm-daily/templates").mkdir(parents=True)
            (source / "skills/pm-daily/evals/fixtures").mkdir(parents=True)
            (source / "templates").mkdir()
            (source / "plugins/platforms/notion").mkdir(parents=True)
            workspace.mkdir(parents=True)
            config = source / "workspace.hermes.md"
            config.write_text("---\nstatus: approved\n---\n# Workspace\n", encoding="utf-8")
            (source / "automations/daily.md").write_text("daily\n", encoding="utf-8")
            (source / "apps/installer/prompts/preflight.md").write_text(
                "preflight\n", encoding="utf-8"
            )
            (source / "skills/pm-daily/SKILL.md").write_text("skill\n", encoding="utf-8")
            (source / "skills/pm-daily/templates/project-memory.md").write_text("memory\n", encoding="utf-8")
            (source / "skills/pm-daily/evals/evals.json").write_text('{"evals": []}\n', encoding="utf-8")
            (source / "skills/pm-daily/evals/fixtures/snapshot.json").write_text("{}\n", encoding="utf-8")
            (source / "skills/pm-daily/development_only.pyc").write_text("development only\n", encoding="utf-8")
            (source / "templates/project.md").write_text("project\n", encoding="utf-8")
            (source / "plugins/platforms/notion/plugin.yaml").write_text("name: notion-platform\n", encoding="utf-8")
            with patch.object(SETUP, "PROJECT", source), patch.object(SETUP, "CONFIG", config):
                code = SETUP.run(workspace, profile_home, apply=True)
            self.assertEqual(code, 0)
            self.assertEqual((workspace / ".hermes.md").read_text(encoding="utf-8"), config.read_text(encoding="utf-8"))
            self.assertEqual((workspace / "automations/daily.md").read_text(encoding="utf-8"), "daily\n")
            self.assertEqual(
                (workspace / "prompts/preflight.md").read_text(encoding="utf-8"),
                "preflight\n",
            )
            self.assertEqual((workspace / "skills/pm-daily/SKILL.md").read_text(encoding="utf-8"), "skill\n")
            self.assertEqual((workspace / "skills/pm-daily/templates/project-memory.md").read_text(encoding="utf-8"), "memory\n")
            self.assertEqual(
                (workspace / "skills/pm-daily/evals/evals.json").read_text(encoding="utf-8"),
                '{"evals": []}\n',
            )
            self.assertEqual(
                (workspace / "skills/pm-daily/evals/fixtures/snapshot.json").read_text(encoding="utf-8"),
                "{}\n",
            )
            self.assertFalse((workspace / "skills/pm-daily/development_only.pyc").exists())
            self.assertEqual((workspace / "templates/project.md").read_text(encoding="utf-8"), "project\n")
            self.assertEqual(
                (profile_home / "plugins/platforms/notion/plugin.yaml").read_text(encoding="utf-8"),
                "name: notion-platform\n",
            )

    def test_apply_preflights_all_destinations_before_copying(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            workspace = root / "profile" / "workspace"
            profile_home = workspace.parent
            source.mkdir(parents=True)
            (source / "automations").mkdir()
            (source / "templates").mkdir()
            (workspace / "automations/daily.md").mkdir(parents=True)
            config = source / "workspace.hermes.md"
            config.write_text("---\nstatus: approved\n---\n# Workspace\n", encoding="utf-8")
            (source / "automations/daily.md").write_text("daily\n", encoding="utf-8")
            (source / "templates/project.md").write_text("project\n", encoding="utf-8")
            with patch.object(SETUP, "PROJECT", source), patch.object(SETUP, "CONFIG", config):
                code = SETUP.run(workspace, profile_home, apply=True)
            self.assertEqual(code, 2)
            self.assertFalse((workspace / ".hermes.md").exists())

    def test_source_project_cannot_be_runtime_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile_home = Path(temporary) / "profile"
            profile_home.mkdir()
            code, receipt = self.run_setup(PROJECT, profile_home)
            self.assertEqual(code, 2)
            self.assertEqual(receipt["blocker"], "workspace_must_be_outside_source_project")

    def test_symlinked_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            actual, workspace, profile_home = root / "actual", root / "workspace", root / "profile"
            actual.mkdir()
            workspace.symlink_to(actual, target_is_directory=True)
            profile_home.mkdir()
            code, receipt = self.run_setup(workspace, profile_home)
            self.assertEqual(code, 2)
            self.assertEqual(receipt["blocker"], "workspace_must_not_be_symlink")

    def test_workspace_may_use_normal_profile_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile_home = Path(temporary) / "profile"
            workspace = profile_home / "workspace"
            workspace.mkdir(parents=True)
            code, receipt = self.run_setup(workspace, profile_home)
            self.assertEqual(code, 0)
            self.assertEqual(receipt["state"], "changes_pending")

    def test_installed_distribution_may_install_its_own_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile_home = Path(temporary) / "profile"
            workspace = profile_home / "workspace"
            (profile_home / "automations").mkdir(parents=True)
            (profile_home / "skills/pm-daily").mkdir(parents=True)
            (profile_home / "templates").mkdir()
            (profile_home / "plugins/platforms/notion").mkdir(parents=True)
            workspace.mkdir()
            config = profile_home / "workspace.hermes.md"
            config.write_text("---\nstatus: approved\n---\n# Workspace\n", encoding="utf-8")
            (profile_home / "distribution.yaml").write_text(
                "name: test\nsource: /tmp/source\ninstalled_at: 2026-08-27T00:00:00Z\n",
                encoding="utf-8",
            )
            (profile_home / "automations/daily.md").write_text("daily\n", encoding="utf-8")
            with patch.object(SETUP, "PROJECT", profile_home), patch.object(SETUP, "CONFIG", config):
                code = SETUP.run(workspace, profile_home, apply=True, installed_distribution=True)
            self.assertEqual(code, 0)
            self.assertEqual((workspace / ".hermes.md").read_text(encoding="utf-8"), config.read_text(encoding="utf-8"))
            self.assertEqual((workspace / "automations/daily.md").read_text(encoding="utf-8"), "daily\n")

    def test_source_checkout_cannot_claim_installed_distribution_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile_home = Path(temporary) / "profile"
            workspace = profile_home / "workspace"
            workspace.mkdir(parents=True)
            code, receipt = self.run_setup(
                workspace, profile_home, "--installed-distribution"
            )
            self.assertEqual(code, 2)
            self.assertEqual(
                receipt["blocker"], "installed_distribution_profile_home_must_equal_source"
            )


if __name__ == "__main__":
    unittest.main()
