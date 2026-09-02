from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.installer import runtime
from apps.installer.cli.flows import lifecycle


ROOT = Path(__file__).resolve().parents[3]


class SetupLaunchTests(unittest.TestCase):
    @staticmethod
    def existing_profile(root: Path) -> Path:
        profile = root / "profiles" / "company-os"
        (profile / "workspace").mkdir(parents=True)
        (profile / "cron").mkdir()
        (profile / "distribution.yaml").write_text("name: company-os\n", encoding="utf-8")
        (profile / "workspace.hermes.md").write_text(
            "---\nstatus: approved\n---\n", encoding="utf-8"
        )
        (profile / "workspace" / ".hermes.md").write_text("ready\n", encoding="utf-8")
        (profile / "cron" / "jobs.json").write_text(
            '{"jobs": ['
            '{"name": "Company OS Daily Operating Update"},'
            '{"name": "Company OS Weekly Operating Review"}'
            ']}\n',
            encoding="utf-8",
        )
        (profile / ".env").write_text("OPENAI_API_KEY=test-only\n", encoding="utf-8")
        return profile

    @staticmethod
    def run_launch(profile: Path, answer: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "setup.py"),
                "launch",
                "--profile-home",
                str(profile),
            ],
            input=answer,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_existing_profile_health_choice_requests_live_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = self.existing_profile(Path(temporary))
            result = self.run_launch(profile, "6\n")
            self.assertEqual(result.returncode, 12, result.stderr)
            self.assertIn("Existing installation found", result.stdout)
            self.assertIn("Run full health check", result.stdout)

    def test_existing_profile_dashboard_choice_requests_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = self.existing_profile(Path(temporary))
            result = self.run_launch(profile, "9\n")
            self.assertEqual(result.returncode, 13, result.stderr)

    def test_existing_profile_exit_does_not_mutate_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = self.existing_profile(Path(temporary))
            before = {
                path.relative_to(profile): path.read_bytes()
                for path in profile.rglob("*")
                if path.is_file()
            }
            result = self.run_launch(profile, "10\n")
            after = {
                path.relative_to(profile): path.read_bytes()
                for path in profile.rglob("*")
                if path.is_file()
            }
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(after, before)

    def test_incomplete_profile_can_exit_without_resuming(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary) / "profiles" / "company-os"
            profile.mkdir(parents=True)
            (profile / "distribution.yaml").write_text(
                "name: company-os\n", encoding="utf-8"
            )
            before = (profile / "distribution.yaml").read_bytes()
            result = self.run_launch(profile, "exit\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("incomplete installation was found", result.stdout)
            self.assertEqual((profile / "distribution.yaml").read_bytes(), before)
            self.assertEqual(
                [path.name for path in profile.iterdir()], ["distribution.yaml"]
            )

    def test_incomplete_profile_offers_recoverable_fresh_start(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary) / "profiles" / "company-os"
            profile.mkdir(parents=True)
            (profile / "distribution.yaml").write_text(
                "name: company-os\n", encoding="utf-8"
            )
            result = self.run_launch(profile, "start-over\nn\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("No setup changes were made", result.stdout)
            self.assertEqual(
                [path.name for path in profile.iterdir()], ["distribution.yaml"]
            )

    def test_fresh_start_archives_incomplete_profile_and_relaunches_clean(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary) / "profiles" / "company-os"
            profile.mkdir(parents=True)
            (profile / "workspace.hermes.md").write_text(
                "saved draft\n", encoding="utf-8"
            )

            def install_distribution(source: Path, target: Path) -> str:
                self.assertTrue((source / "workspace.hermes.md").is_file())
                self.assertFalse(target.exists())
                target.mkdir(parents=True)
                (target / "setup.py").write_text("# installed\n", encoding="utf-8")
                (target / "workspace.hermes.md").write_text(
                    "copied draft\n", encoding="utf-8"
                )
                return "installed"

            with patch.object(
                runtime,
                "install_or_update_distribution",
                side_effect=install_distribution,
            ), patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0)):
                result = lifecycle._fresh_start(profile)

            self.assertEqual(result, 0)
            self.assertFalse((profile / "workspace.hermes.md").exists())
            self.assertTrue((profile / lifecycle.FRESH_START_MARKER).is_file())
            backups = list(profile.parent.glob("company-os.incomplete-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(
                (backups[0] / "workspace.hermes.md").read_text(encoding="utf-8"),
                "saved draft\n",
            )

    def test_existing_profile_integration_choice_requests_certification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = self.existing_profile(Path(temporary))
            result = self.run_launch(profile, "3\n")
            self.assertEqual(result.returncode, 14, result.stderr)
            self.assertIn("Test integrations", result.stdout)

    def test_existing_profile_preflight_choice_requests_data_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = self.existing_profile(Path(temporary))
            result = self.run_launch(profile, "4\n")
            self.assertEqual(result.returncode, 15, result.stderr)
            self.assertIn("Check data readiness", result.stdout)

    def test_existing_profile_eval_choice_requests_full_eval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = self.existing_profile(Path(temporary))
            result = self.run_launch(profile, "5\n")
            self.assertEqual(result.returncode, 16, result.stderr)
            self.assertIn("Run full eval and open dossier", result.stdout)

    def test_existing_profile_dossier_choice_requests_latest_dossier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = self.existing_profile(Path(temporary))
            result = self.run_launch(profile, "8\n")
            self.assertEqual(result.returncode, 17, result.stderr)

    def test_workspace_action_uses_profile_owned_configuration(self) -> None:
        source = (
            ROOT / "apps" / "installer" / "cli" / "flows" / "lifecycle.py"
        ).read_text(encoding="utf-8")
        self.assertIn('workspace = profile_home / "workspace.hermes.md"', source)
        self.assertIn("configure_features(profile_home)", source)
        self.assertIn('source_root / "apps" / "installer" / "profile.py"', source)
        self.assertIn('receipt["entry_point"] = "setup.py workspace"', source)

    def test_software_update_rerenders_saved_feature_answers(self) -> None:
        source = (
            ROOT / "apps" / "installer" / "cli" / "flows" / "lifecycle.py"
        ).read_text(encoding="utf-8")
        update = source.split("def update_command", 1)[1]
        self.assertIn('profile_home / "config" / "setup-answers.json"', update)
        self.assertIn("render_files(", update)
        self.assertIn('profile_home / "automations" / name', update)
        self.assertLess(
            update.index("feature_setup_migration_required"),
            update.index("runtime.install_or_update_distribution"),
        )

    def test_install_calls_webhook_selector_with_supported_arguments(self) -> None:
        tree = ast.parse(
            (ROOT / "apps" / "installer" / "cli" / "flows" / "lifecycle.py").read_text(
                encoding="utf-8"
            )
        )
        selector = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_choose_webhook"
        )
        accepted = {argument.arg for argument in selector.args.args + selector.args.kwonlyargs}
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_choose_webhook"
        ]
        self.assertEqual(len(calls), 1)
        self.assertTrue({keyword.arg for keyword in calls[0].keywords} <= accepted)

    def test_repair_can_replace_existing_ngrok_configuration(self) -> None:
        source = (
            ROOT / "apps" / "installer" / "cli" / "flows" / "lifecycle.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Revalidate or replace the saved Notion/ngrok webhook credentials?",
            source,
        )
        self.assertIn("_configure_webhook(profile_home)", source)

    def test_model_setup_must_produce_a_configured_credential(self) -> None:
        profile = Path("/tmp/company-os-profile")
        with patch.object(
            runtime, "model_auth_configured", side_effect=[False, True]
        ):
            with patch.object(lifecycle, "run_visible", return_value=0) as visible:
                lifecycle._configure_model(profile, non_interactive=False)
        visible.assert_called_once_with(["hermes", "setup", "model"], profile)

        with patch.object(runtime, "model_auth_configured", return_value=False):
            with patch.object(lifecycle, "run_visible", return_value=0):
                with self.assertRaisesRegex(
                    runtime.RuntimeSetupError, "model_auth_incomplete"
                ):
                    lifecycle._configure_model(profile, non_interactive=False)

    def test_missing_model_auth_fails_closed_without_interactive_input(self) -> None:
        with patch.object(runtime, "model_auth_configured", return_value=False):
            with patch.object(lifecycle, "run_visible") as visible:
                with self.assertRaisesRegex(
                    runtime.RuntimeSetupError, "model_auth_requires_input"
                ):
                    lifecycle._configure_model(
                        Path("/tmp/company-os-profile"), non_interactive=True
                    )
        visible.assert_not_called()

    def test_telegram_setup_is_one_time_and_noninteractive_fails_closed(self) -> None:
        requirements = {"weekly.report_recipients": ("gmail", "telegram")}
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            with self.assertRaisesRegex(
                runtime.RuntimeSetupError, "telegram_gateway_requires_input"
            ):
                lifecycle._configure_telegram_if_needed(
                    profile, requirements, non_interactive=True
                )

            with patch.object(lifecycle, "run_visible", return_value=0) as visible:
                with patch.object(
                    runtime,
                    "telegram_gateway_configured",
                    side_effect=[False, True, True],
                ):
                    lifecycle._configure_telegram_if_needed(
                        profile, requirements, non_interactive=False
                    )
                    lifecycle._configure_telegram_if_needed(
                        profile, requirements, non_interactive=False
                    )
            visible.assert_called_once_with(["hermes", "gateway", "setup"], profile)

    def test_whatsapp_setup_is_one_time_and_noninteractive_fails_closed(self) -> None:
        requirements = {"weekly.report_recipients": ("whatsapp",)}
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            with self.assertRaisesRegex(
                runtime.RuntimeSetupError, "whatsapp_gateway_requires_input"
            ):
                lifecycle._configure_whatsapp_if_needed(
                    profile, requirements, non_interactive=True
                )
            with patch.object(lifecycle, "run_visible", return_value=0) as visible:
                with patch.object(
                    runtime, "whatsapp_gateway_configured", side_effect=[False, True]
                ):
                    lifecycle._configure_whatsapp_if_needed(
                        profile, requirements, non_interactive=False
                    )
            visible.assert_called_once_with(["hermes", "whatsapp"], profile)


if __name__ == "__main__":
    unittest.main()
