from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ANSWERS = "\n".join(
    (
        "Acme",
        "Operations workspace",
        "Asia/Kuala_Lumpur",
        "all",
        "linear", "https://linear.app/acme/projects",
        "linear", "https://linear.app/acme/tasks",
        "notion", "https://notion.so/acme/people",
        "notion", "https://notion.so/acme/sops",
        "notion", "https://notion.so/acme/reports",
        "gmail", "ops@example.invalid",
        "all", "company-operators", "telegram", "drafts",
        "prepare only",
        "y",
    )
)


class SetupInitTests(unittest.TestCase):
    @staticmethod
    def copy_setup(target: Path) -> None:
        for name in ("setup.py", "workspace.hermes.template.md"):
            (target / name).write_bytes((ROOT / name).read_bytes())
        (target / "apps" / "installer").mkdir(parents=True)
        (target / "apps" / "__init__.py").write_bytes(
            (ROOT / "apps" / "__init__.py").read_bytes()
        )
        for name in ("__init__.py", "runtime.py", "feature_setup.py"):
            (target / "apps" / "installer" / name).write_bytes(
                (ROOT / "apps" / "installer" / name).read_bytes()
            )
        (target / "apps" / "installer" / "provider_catalog.py").write_bytes(
            (ROOT / "apps" / "installer" / "provider_catalog.py").read_bytes()
        )
        shutil.copytree(
            ROOT / "apps" / "installer" / "schemas",
            target / "apps" / "installer" / "schemas",
        )
        shutil.copytree(
            ROOT / "apps" / "installer" / "cli",
            target / "apps" / "installer" / "cli",
        )
        shutil.copytree(ROOT / "apps/installer/providers", target / "apps/installer/providers")

    def run_setup(
        self, target: Path, command: str, answers: str = ANSWERS, *arguments: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(target / "setup.py"), command, *arguments],
            input=answers,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_selector_uses_public_prompt_toolkit_api(self) -> None:
        source = (ROOT / "apps" / "installer" / "cli" / "ui.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("from prompt_toolkit.widgets import CheckboxList", source)
        self.assertNotIn("hermes_cli.curses_ui", source)
        self.assertNotIn("import curses", source)

    def test_interactive_init_and_reconfigure_preserve_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_setup(target)

            first = self.run_setup(target, "init")
            self.assertEqual(first.returncode, 0, first.stderr)
            workspace = target / "workspace.hermes.md"
            content = workspace.read_text(encoding="utf-8")
            self.assertIn('company_name: "Acme"', content)
            self.assertIn("| `projects` | linear | https://linear.app/acme/projects |", content)
            self.assertIn(
                "| `owner report` | telegram | company-operators | "
                "prepare drafts for approval |",
                content,
            )
            self.assertNotIn("operator_review", content)
            self.assertNotIn("setup_test_sink", content)
            self.assertNotIn("REPLACE_ME", content)
            self.assertIn("status: draft", content)

            content = content.replace("# Company Workspace", "# Owner-edited Workspace")
            workspace.write_text(content, encoding="utf-8")
            second = self.run_setup(target, "configure", "\n" * 8)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("# Owner-edited Workspace", workspace.read_text(encoding="utf-8"))

    def test_blank_required_input_reprompts_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_setup(target)
            result = self.run_setup(target, "init", "\n" + ANSWERS)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("A value is required", result.stdout)
            self.assertNotIn("AttributeError", result.stderr)
            self.assertIn(
                'company_name: "Acme"',
                (target / "workspace.hermes.md").read_text(encoding="utf-8"),
            )

    def test_installed_feature_setup_stops_safely_before_runtime_apply_on_eof(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_setup(target)
            answers = "\n" + ANSWERS + "\nn\nn\n"
            result = self.run_setup(
                target,
                "install",
                answers,
                "--profile-home",
                str(target),
                "--installed",
            )
            self.assertEqual(result.returncode, 130, result.stderr)
            self.assertIn("Stopped safely", result.stdout)
            self.assertNotIn("Traceback", result.stderr)

    def test_early_runtime_error_does_not_crash_the_error_handler(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_setup(target)
            profile = target / "profile"
            result = self.run_setup(
                target,
                "install",
                "",
                "--profile-home",
                str(profile),
                "--installed",
                "--non-interactive",
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("Run setup interactively", result.stdout)
            self.assertNotIn("AttributeError", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_end_of_input_stops_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_setup(target)
            result = self.run_setup(target, "init", "")
            self.assertEqual(result.returncode, 130, result.stderr)
            self.assertIn("Stopped safely", result.stdout)
            self.assertNotIn("Traceback", result.stderr)

    def test_configure_preserves_owner_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_setup(target)
            first = self.run_setup(target, "init")
            self.assertEqual(first.returncode, 0, first.stderr)
            workspace = target / "workspace.hermes.md"
            workspace.write_text(
                workspace.read_text(encoding="utf-8").replace(
                    "# Company Workspace", "# Owner-edited Workspace"
                ).replace(
                    "| --- | --- | --- |\n<!-- /hermes:managed artifact-sync -->",
                    "| --- | --- | --- |\n"
                    "| `reports` | notion | https://notion.so/acme/private-reports |\n"
                    "<!-- /hermes:managed artifact-sync -->",
                ),
                encoding="utf-8",
            )
            result = self.run_setup(target, "configure", "\n" * 8)
            self.assertEqual(result.returncode, 0, result.stderr)
            configured = workspace.read_text(encoding="utf-8")
            self.assertIn("# Owner-edited Workspace", configured)
            self.assertIn(
                "| `reports` | notion | https://notion.so/acme/private-reports |",
                configured,
            )

    def test_existing_workspace_gets_new_managed_blocks_without_losing_prose(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_setup(target)
            first = self.run_setup(target, "init")
            self.assertEqual(first.returncode, 0, first.stderr)
            workspace = target / "workspace.hermes.md"
            content = workspace.read_text(encoding="utf-8")
            start = content.index("<!-- hermes:managed communications -->")
            end = content.index("<!-- /hermes:managed communications -->")
            end += len("<!-- /hermes:managed communications -->")
            content = content[:start] + "Legacy owner messaging notes.\n" + content[end:]
            start = content.index("<!-- hermes:managed artifact-sync -->")
            end = content.index("<!-- /hermes:managed artifact-sync -->")
            end += len("<!-- /hermes:managed artifact-sync -->")
            workspace.write_text(content[:start] + content[end:], encoding="utf-8")
            result = self.run_setup(target, "configure", "\n" * 8)
            self.assertEqual(result.returncode, 0, result.stderr)
            migrated = workspace.read_text(encoding="utf-8")
            self.assertIn("Legacy owner messaging notes.", migrated)
            self.assertIn("<!-- hermes:managed communications -->", migrated)
            self.assertIn("<!-- hermes:managed artifact-sync -->", migrated)

    def test_init_reuses_existing_workspace_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_setup(target)
            first = self.run_setup(target, "init")
            self.assertEqual(first.returncode, 0, first.stderr)
            workspace = target / "workspace.hermes.md"
            result = self.run_setup(target, "init", "\n" * 8)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Using existing", result.stdout)
            self.assertIn('company_name: "Acme"', workspace.read_text(encoding="utf-8"))

    def test_explicit_workspace_starts_from_company_neutral_template(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_setup(target)
            (target / "workspace.hermes.md").write_text(
                'company_name: "Existing Company"\n', encoding="utf-8"
            )
            clean = target / "new-company.md"
            result = self.run_setup(
                target, "init", ANSWERS, "--workspace", str(clean)
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("Existing Company", result.stdout)
            self.assertIn('company_name: "Acme"', clean.read_text(encoding="utf-8"))
            self.assertIn("company_name: REPLACE_ME", (target / "workspace.hermes.template.md").read_text())

    def test_declining_review_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_setup(target)
            answers = ANSWERS.rsplit("\n", 1)[0] + "\nn"
            result = self.run_setup(target, "init", answers)
            self.assertEqual(result.returncode, 1)
            self.assertFalse((target / "workspace.hermes.md").exists())
            self.assertIn("No changes written", result.stdout)

    def test_data_source_selection_only_prompts_for_selected_roles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_setup(target)
            answers = "\n".join((
                "Acme", "Operations workspace", "Asia/Kuala_Lumpur",
                "1,2",
                "linear", "https://linear.app/acme/projects",
                "linear", "https://linear.app/acme/tasks",
                "all", "company-operators", "telegram", "drafts",
                "prepare only", "y",
            ))
            result = self.run_setup(target, "init", answers)
            self.assertEqual(result.returncode, 0, result.stderr)
            content = (target / "workspace.hermes.md").read_text(encoding="utf-8")
            self.assertIn("| `projects` | linear |", content)
            self.assertIn("| `tasks` | linear |", content)
            self.assertIn("| `people` | — | — |", content)
            self.assertIn("| `sops` | — | — |", content)
            self.assertIn("| `reports` | — | — |", content)
            self.assertNotIn("REPLACE_ME", content)

    def test_data_sources_can_be_skipped_and_configured_later(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_setup(target)
            answers = "\n".join((
                "Acme", "Operations workspace", "Asia/Kuala_Lumpur",
                "",
                "all", "company-operators", "telegram", "drafts",
                "prepare only", "y",
            ))
            result = self.run_setup(target, "init", answers)
            self.assertEqual(result.returncode, 0, result.stderr)
            content = (target / "workspace.hermes.md").read_text(encoding="utf-8")
            self.assertIn("Data sources skipped", result.stdout)
            self.assertIn("| `projects` | — | — |", content)
            self.assertNotIn("REPLACE_ME", content)


if __name__ == "__main__":
    unittest.main()
