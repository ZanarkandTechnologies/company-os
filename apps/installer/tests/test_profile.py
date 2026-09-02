from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[3]
SCRIPT = PROJECT / "apps/installer/profile.py"
SPEC = importlib.util.spec_from_file_location("setup_profile", SCRIPT)
assert SPEC and SPEC.loader
PROFILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE)


class SetupProfileTests(unittest.TestCase):
    def test_apply_enables_and_verifies_host_backed_docker_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile_home = Path(temporary)
            workspace = profile_home / "workspace"

            def fake_command(arguments, selected_profile, **kwargs):
                del selected_profile, kwargs
                joined = " ".join(str(item) for item in arguments)
                if "workspace.py" in joined:
                    return subprocess.CompletedProcess(
                        arguments, 0, json.dumps({"state": "configured", "pending": []}), ""
                    )
                if arguments[-2:] == ["get", "terminal.backend"]:
                    return subprocess.CompletedProcess(arguments, 0, "docker\n", "")
                if arguments[-2:] == ["get", "terminal.cwd"]:
                    return subprocess.CompletedProcess(arguments, 0, f"{workspace}\n", "")
                if arguments[-2:] == [
                    "get", "terminal.docker_mount_cwd_to_workspace"
                ]:
                    return subprocess.CompletedProcess(arguments, 0, "true\n", "")
                return subprocess.CompletedProcess(arguments, 0, "", "")

            gateway = subprocess.CompletedProcess(
                ["hermes", "gateway", "status"], 0,
                "✓ Gateway is running (PID: 123)\n", "",
            )
            with (
                patch.object(PROFILE, "run_command", side_effect=fake_command) as commands,
                patch.object(PROFILE, "cron_plan", return_value=[]),
                patch.object(PROFILE, "apply_cron"),
                patch.object(PROFILE.subprocess, "run", return_value=gateway),
            ):
                self.assertEqual(PROFILE.run(profile_home, apply=True), 0)

            invoked = [call.args[0] for call in commands.call_args_list]
            self.assertIn(
                [
                    "hermes", "config", "set",
                    "terminal.docker_mount_cwd_to_workspace", "true",
                ],
                invoked,
            )

    def test_gateway_readiness_uses_status_text_not_exit_code(self) -> None:
        stopped = subprocess.CompletedProcess(
            ["hermes", "gateway", "status"], 0, "✗ Gateway is not running\n", ""
        )
        running = subprocess.CompletedProcess(
            ["hermes", "gateway", "status"], 0, "✓ Gateway is running (PID: 123)\n", ""
        )
        self.assertFalse(PROFILE.gateway_is_running(stopped))
        self.assertTrue(PROFILE.gateway_is_running(running))

    def test_notion_plugin_enabled_reads_native_plugin_inventory(self) -> None:
        profile_home = Path("/tmp/client-profile")
        payload = json.dumps(
            [{"name": "notion-platform", "status": "enabled", "source": "user"}]
        )
        completed = subprocess.CompletedProcess([], 0, payload, "")
        with patch.object(PROFILE, "run_command", return_value=completed) as run_command:
            self.assertTrue(PROFILE.notion_plugin_enabled(profile_home))
        self.assertEqual(
            run_command.call_args.args[0],
            ["hermes", "plugins", "list", "--user", "--json"],
        )

    def test_enable_notion_plugin_declines_tool_override_and_verifies(self) -> None:
        profile_home = Path("/tmp/client-profile")
        enabled = subprocess.CompletedProcess(
            [], 0, json.dumps([{"name": "notion-platform", "status": "enabled"}]), ""
        )
        with patch.object(
            PROFILE,
            "run_command",
            side_effect=[subprocess.CompletedProcess([], 0, "", ""),
                         subprocess.CompletedProcess([], 0, "", ""), enabled],
        ) as run_command:
            PROFILE.enable_notion_plugin(profile_home)
        commands = [call.args[0] for call in run_command.call_args_list]
        self.assertEqual(
            commands[0],
            ["hermes", "plugins", "enable", "platforms/notion", "--no-allow-tool-override"],
        )
        self.assertEqual(commands[1], ["hermes", "plugins", "doctor", "platforms/notion"])

    def test_missing_jobs_plan_creates_every_managed_job_with_client_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile_home = Path(temporary)
            workspace = profile_home / "workspace"
            workspace.mkdir()
            (workspace / ".hermes.md").write_text(
                'company_name: "Example Co"\ncompany_timezone: "Europe/London"\n',
                encoding="utf-8",
            )
            actions = PROFILE.cron_plan(profile_home, workspace)
            self.assertEqual([item["action"] for item in actions], ["create"] * 3)
            self.assertEqual(actions[0]["schedule"], "0 8 * * 1-5")
            self.assertEqual(actions[1]["schedule"], "0 18 * * 5")
            self.assertEqual(actions[2]["schedule"], "0 9 * * 1")
            for action in actions:
                self.assertEqual(action["workdir"], str(workspace))
                self.assertIn(str(workspace / ".hermes.md"), action["prompt"])
                self.assertIn("Example Co Company OS", action["prompt"])
                self.assertIn("Europe/London", action["prompt"])

    def test_legacy_job_names_are_migrated_to_generic_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile_home = Path(temporary)
            workspace = profile_home / "workspace"
            cron = profile_home / "cron"
            workspace.mkdir()
            cron.mkdir()
            (cron / "jobs.json").write_text(
                json.dumps({"jobs": [{
                    "id": "daily-id",
                    "name": "Company OS Daily Operating Update",
                    "schedule": "0 8 * * 1-5",
                }]}),
                encoding="utf-8",
            )
            actions = PROFILE.cron_plan(profile_home, workspace)
            self.assertEqual(actions[0]["action"], "update")
            self.assertEqual(actions[0]["id"], "daily-id")
            self.assertEqual(actions[0]["name"], "Company OS Daily Operating Update")

    def test_exact_jobs_are_in_sync(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile_home = Path(temporary)
            workspace = profile_home / "workspace"
            cron = profile_home / "cron"
            workspace.mkdir()
            cron.mkdir()
            jobs = []
            for index, spec in enumerate(PROFILE.SCHEDULES, start=1):
                desired = PROFILE.desired_job(spec, workspace)
                jobs.append(
                    {
                        "id": str(index),
                        "name": desired["name"],
                        "schedule": {"kind": "cron", "expr": desired["schedule"]},
                        "prompt": desired["prompt"],
                        "workdir": desired["workdir"],
                        "deliver": "local",
                        "enabled": True,
                    }
                )
            (cron / "jobs.json").write_text(json.dumps({"jobs": jobs}), encoding="utf-8")
            activation = profile_home / PROFILE.ACTIVATION_RECEIPT
            activation.parent.mkdir(parents=True, exist_ok=True)
            activation.write_text(
                json.dumps(
                    {
                        "status": "activated",
                        "schedule_configuration_hash": (
                            PROFILE.schedule_configuration_hash(profile_home, workspace)
                        ),
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                [item["action"] for item in PROFILE.cron_plan(profile_home, workspace)],
                ["in_sync"] * 3,
            )

    def test_drifted_job_is_updated_and_duplicate_name_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile_home = Path(temporary)
            workspace = profile_home / "workspace"
            cron = profile_home / "cron"
            workspace.mkdir()
            cron.mkdir()
            name = PROFILE.SCHEDULES[0]["name"]
            (cron / "jobs.json").write_text(
                json.dumps({"jobs": [{"id": "1", "name": name, "schedule": "daily"}]}),
                encoding="utf-8",
            )
            self.assertEqual(PROFILE.cron_plan(profile_home, workspace)[0]["action"], "update")
            duplicate = {"jobs": [{"id": "1", "name": name}, {"id": "2", "name": name}]}
            (cron / "jobs.json").write_text(json.dumps(duplicate), encoding="utf-8")
            with self.assertRaisesRegex(PROFILE.ProfileSetupError, "duplicate_cron_name"):
                PROFILE.cron_plan(profile_home, workspace)

    def test_apply_cron_uses_native_create_and_edit_commands(self) -> None:
        profile_home = Path("/tmp/client-profile")
        actions = [
            {
                "action": "create", "name": "Daily", "schedule": "0 8 * * 1-5",
                "prompt": "daily prompt", "workdir": "/tmp/client-profile/workspace",
                "deliver": "local",
            },
            {
                "action": "update", "id": "weekly-id", "name": "Weekly",
                "schedule": "0 18 * * 5", "prompt": "weekly prompt",
                "workdir": "/tmp/client-profile/workspace", "deliver": "local",
            },
        ]
        installed_jobs = [
            {"id": "daily-id", "name": PROFILE.SCHEDULES[0]["name"], "enabled": True},
            {"id": "weekly-id", "name": PROFILE.SCHEDULES[1]["name"], "enabled": True},
            {"id": "meeting-id", "name": PROFILE.SCHEDULES[2]["name"], "enabled": True},
        ]
        with (
            patch.object(PROFILE, "run_command") as run_command,
            patch.object(PROFILE, "read_jobs", return_value=installed_jobs),
        ):
            PROFILE.apply_cron(profile_home, actions)
        commands = [call.args[0] for call in run_command.call_args_list]
        create, edit = commands[:2]
        self.assertEqual(create[:4], ["hermes", "cron", "create", "0 8 * * 1-5"])
        self.assertEqual(edit[:4], ["hermes", "cron", "edit", "weekly-id"])
        self.assertIn("--workdir", create)
        self.assertIn("--workdir", edit)
        self.assertEqual(
            commands[2:],
            [["hermes", "cron", "pause", "daily-id"], ["hermes", "cron", "pause", "weekly-id"], ["hermes", "cron", "pause", "meeting-id"]],
        )

    def test_unproved_profile_pauses_managed_schedules(self) -> None:
        profile_home = Path("/tmp/client-profile")
        jobs = [
            {"id": str(index), "name": spec["name"], "enabled": True}
            for index, spec in enumerate(PROFILE.SCHEDULES, start=1)
        ]
        with (
            patch.object(PROFILE, "read_jobs", return_value=jobs),
            patch.object(PROFILE, "run_command") as run_command,
        ):
            PROFILE.set_managed_schedules_enabled(profile_home, False)
        self.assertEqual(
            [call.args[0] for call in run_command.call_args_list],
            [["hermes", "cron", "pause", "1"], ["hermes", "cron", "pause", "2"], ["hermes", "cron", "pause", "3"]],
        )

    def test_activation_requires_and_records_proof_before_resuming(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile_home = Path(temporary)
            jobs = [
                {"id": str(index), "name": spec["name"], "enabled": False}
                for index, spec in enumerate(PROFILE.SCHEDULES, start=1)
            ]
            enabled_jobs = [
                {
                    "id": str(index),
                    "name": spec["name"],
                    "enabled": True,
                    "schedule": spec["schedule"],
                    "prompt": PROFILE.desired_job(spec, profile_home / "workspace")["prompt"],
                    "workdir": str(profile_home / "workspace"),
                    "deliver": "local",
                }
                for index, spec in enumerate(PROFILE.SCHEDULES, start=1)
            ]
            with (
                patch.object(PROFILE, "read_jobs", side_effect=[jobs, enabled_jobs]),
                patch.object(PROFILE, "run_command") as run_command,
            ):
                receipt = PROFILE.activate_managed_schedules(
                    profile_home,
                    {"live_health": "health.json", "readiness_run_id": "ready", "eval_run_id": "eval"},
                )
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "activated")
            self.assertEqual(payload["proof"]["eval_run_id"], "eval")
            self.assertEqual(
                [call.args[0] for call in run_command.call_args_list],
                [["hermes", "cron", "resume", "1"], ["hermes", "cron", "resume", "2"], ["hermes", "cron", "resume", "3"]],
            )

    def test_failed_activation_repauses_jobs_and_commits_no_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile_home = Path(temporary)
            disabled = [
                {"id": str(index), "name": spec["name"], "enabled": False}
                for index, spec in enumerate(PROFILE.SCHEDULES, start=1)
            ]
            partially_enabled = [
                {"id": "1", "name": PROFILE.SCHEDULES[0]["name"], "enabled": True},
                {"id": "2", "name": PROFILE.SCHEDULES[1]["name"], "enabled": False},
                {"id": "3", "name": PROFILE.SCHEDULES[2]["name"], "enabled": False},
            ]
            with (
                patch.object(
                    PROFILE,
                    "read_jobs",
                    side_effect=[disabled, partially_enabled, partially_enabled],
                ),
                patch.object(PROFILE, "run_command") as run_command,
            ):
                with self.assertRaisesRegex(
                    PROFILE.ProfileSetupError, "cron_activation_verification_failed"
                ):
                    PROFILE.activate_managed_schedules(profile_home, {"eval_run_id": "eval"})
            self.assertFalse((profile_home / PROFILE.ACTIVATION_RECEIPT).exists())
            self.assertFalse((profile_home / "state" / "setup-proof.pending.json").exists())
            self.assertEqual(
                [call.args[0] for call in run_command.call_args_list],
                [
                    ["hermes", "cron", "resume", "1"],
                    ["hermes", "cron", "resume", "2"],
                    ["hermes", "cron", "resume", "3"],
                    ["hermes", "cron", "pause", "1"],
                ],
            )


if __name__ == "__main__":
    unittest.main()
