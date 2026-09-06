from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.installer import runtime


ROOT = Path(__file__).resolve().parents[3]


class SetupRuntimeTests(unittest.TestCase):
    def test_runtime_health_requires_weekly_meeting_ticket_job(self) -> None:
        self.assertIn(
            "Company OS Weekly Meeting Ticket", runtime.EXPECTED_CRON_NAMES
        )

    def test_mcp_connection_requires_success_marker_not_only_zero_exit(self) -> None:
        failed_zero = subprocess.CompletedProcess(
            [], 0, "✗ Connection failed: login required", ""
        )
        connected = subprocess.CompletedProcess([], 0, "✓ Connected\n✓ Tools discovered", "")
        self.assertFalse(runtime.mcp_connection_ready(failed_zero))
        self.assertTrue(runtime.mcp_connection_ready(connected))

    def test_default_profile_home_uses_named_profile(self) -> None:
        with patch.dict(os.environ, {"HERMES_HOME": "/opt/data"}, clear=False):
            with patch.dict(os.environ, {"COMPANY_OS_PROFILE_HOME": ""}, clear=False):
                self.assertEqual(
                    runtime.default_profile_home(),
                    Path("/opt/data/profiles/company-os"),
                )

    def test_blank_or_comment_only_credentials_are_not_configured(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            (profile / ".env").write_text(
                "OPENAI_API_KEY=\n"
                "NOTION_TOKEN=\"\"\n"
                "NOTION_WEBHOOK_PUBLIC_URL=   # missing\n"
                "NOUS_API_KEY='   '\n"
                "XAI_API_KEY=old-value\n"
                "XAI_API_KEY=\n"
                "COMPOSIO_API_KEY=real-value\n",
                encoding="utf-8",
            )
            (profile / "secrets").mkdir()
            (profile / "secrets/ngrok.yml").write_text(
                "placeholder\n", encoding="utf-8"
            )
            self.assertEqual(
                runtime.configured_secret_names(profile), {"COMPOSIO_API_KEY"}
            )
            self.assertFalse(runtime.model_auth_configured(profile))
            self.assertFalse(runtime.webhook_enabled(profile))

    def test_metadata_only_auth_file_is_not_model_auth(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            (profile / "auth.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "providers": {},
                        "credential_pool": {},
                        "updated_at": "2026-09-01T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
            (profile / "oauth.json").write_text(
                json.dumps({"notion": {"access_token": "not-a-model-token"}}),
                encoding="utf-8",
            )

            self.assertFalse(runtime.model_auth_configured(profile))

    def test_provider_auth_record_is_model_auth(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            (profile / "auth.json").write_text(
                json.dumps({"providers": {"openrouter": {"configured": True}}}),
                encoding="utf-8",
            )

            self.assertTrue(runtime.model_auth_configured(profile))

    def test_current_codex_oauth_marker_is_model_auth(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            (profile / "config.yaml").write_text(
                "model:\n  provider: openai-codex\n", encoding="utf-8"
            )
            (profile / "auth.json").write_text(
                json.dumps({"active_provider": "openai-codex", "providers": {}}),
                encoding="utf-8",
            )

            self.assertTrue(runtime.model_auth_configured(profile))

    def test_gateway_lane_reads_only_the_selected_profile_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary) / "profiles" / runtime.PROFILE_NAME
            profile.mkdir(parents=True)
            (profile / "gateway_state.json").write_text(
                json.dumps(
                    {
                        "gateway_state": "running",
                        "hermes_home": str(profile),
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                runtime._gateway_lane(profile, lambda *_args, **_kwargs: None)["status"],
                "pass",
            )
            (profile / "gateway_state.json").write_text(
                json.dumps(
                    {
                        "gateway_state": "running",
                        "hermes_home": str(profile.parent),
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                runtime._gateway_lane(profile, lambda *_args, **_kwargs: None)["status"],
                "fail",
            )

    def test_failed_ngrok_candidate_restores_previous_ingress_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            old_url = "https://old-name.ngrok-free.app/notion/webhook"
            (profile / ".env").write_text(
                f"NOTION_WEBHOOK_PUBLIC_URL={old_url}\n", encoding="utf-8"
            )
            config = profile / runtime.NGROK_CONFIG_RELATIVE
            config.parent.mkdir()
            config.write_text("old-config\n", encoding="utf-8")
            state = profile / runtime.WEBHOOK_STATE_RELATIVE
            state.parent.mkdir()
            state.write_text('{"verification_token":"old"}\n', encoding="utf-8")

            runtime.begin_ngrok_update(profile)
            config.write_text("bad-candidate\n", encoding="utf-8")
            state.write_text('{"verification_token":""}\n', encoding="utf-8")
            with patch.object(runtime, "save_profile_secret") as save_secret:
                runtime.rollback_ngrok_update(profile)

            self.assertEqual(config.read_text(encoding="utf-8"), "old-config\n")
            self.assertEqual(
                json.loads(state.read_text(encoding="utf-8"))["verification_token"],
                "old",
            )
            save_secret.assert_called_once_with(
                profile, "NOTION_WEBHOOK_PUBLIC_URL", old_url
            )
            self.assertFalse((profile / runtime.NGROK_UPDATE_RELATIVE).exists())

    def test_first_failed_ngrok_candidate_leaves_webhook_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            runtime.begin_ngrok_update(profile)
            runtime.save_ngrok_config(
                profile,
                "bad-token",
                "https://new-name.ngrok-free.app",
            )
            with patch.object(runtime, "remove_profile_secret") as remove_secret:
                runtime.rollback_ngrok_update(profile)
            self.assertFalse((profile / runtime.NGROK_CONFIG_RELATIVE).exists())
            remove_secret.assert_called_once_with(
                profile, "NOTION_WEBHOOK_PUBLIC_URL"
            )

    def test_ngrok_rollback_can_retry_after_secret_restore_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            old_url = "https://old-name.ngrok-free.app/notion/webhook"
            (profile / ".env").write_text(
                f"NOTION_WEBHOOK_PUBLIC_URL={old_url}\n", encoding="utf-8"
            )
            config = profile / runtime.NGROK_CONFIG_RELATIVE
            config.parent.mkdir()
            config.write_text("old-config\n", encoding="utf-8")
            runtime.begin_ngrok_update(profile)
            config.write_text("bad-candidate\n", encoding="utf-8")

            with patch.object(
                runtime,
                "save_profile_secret",
                side_effect=runtime.RuntimeSetupError("write_interrupted"),
            ):
                with self.assertRaisesRegex(
                    runtime.RuntimeSetupError, "write_interrupted"
                ):
                    runtime.rollback_ngrok_update(profile)
            self.assertEqual(config.read_text(encoding="utf-8"), "old-config\n")
            self.assertTrue((profile / runtime.NGROK_ROLLBACK_RELATIVE).is_file())
            self.assertTrue((profile / runtime.NGROK_UPDATE_RELATIVE).is_file())

            with patch.object(runtime, "save_profile_secret"):
                runtime.rollback_ngrok_update(profile)
            self.assertEqual(config.read_text(encoding="utf-8"), "old-config\n")
            self.assertFalse((profile / runtime.NGROK_UPDATE_RELATIVE).exists())

    def test_ngrok_rollback_retains_marker_when_snapshot_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            config = profile / runtime.NGROK_CONFIG_RELATIVE
            config.parent.mkdir()
            config.write_text("old-config\n", encoding="utf-8")
            runtime.begin_ngrok_update(profile)
            (profile / runtime.NGROK_ROLLBACK_RELATIVE).unlink()
            config.write_text("candidate\n", encoding="utf-8")

            with self.assertRaisesRegex(
                runtime.RuntimeSetupError, "ngrok_rollback_config_missing"
            ):
                runtime.rollback_ngrok_update(profile)
            self.assertEqual(config.read_text(encoding="utf-8"), "candidate\n")
            self.assertTrue((profile / runtime.NGROK_UPDATE_RELATIVE).is_file())

    def test_ngrok_commit_marker_is_atomic_before_snapshot_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            config = profile / runtime.NGROK_CONFIG_RELATIVE
            config.parent.mkdir()
            config.write_text("old-config\n", encoding="utf-8")
            runtime.begin_ngrok_update(profile)
            rollback_config = profile / runtime.NGROK_ROLLBACK_RELATIVE
            original_unlink = Path.unlink

            def interrupted_unlink(path: Path, *args, **kwargs):
                if path == rollback_config:
                    raise OSError("cleanup interrupted")
                return original_unlink(path, *args, **kwargs)

            with patch.object(Path, "unlink", interrupted_unlink):
                with self.assertRaisesRegex(OSError, "cleanup interrupted"):
                    runtime.commit_ngrok_update(profile)
            self.assertFalse((profile / runtime.NGROK_UPDATE_RELATIVE).exists())
            self.assertTrue(rollback_config.is_file())

    def test_webhook_ingress_waits_for_public_gateway_health(self) -> None:
        profile = Path("/tmp/company-os-profile")
        with patch.object(
            runtime,
            "webhook_public_url",
            return_value="https://assigned-name.ngrok-free.app/notion/webhook",
        ):
            with patch.object(
                runtime,
                "_http_json",
                side_effect=[(False, {}), (True, {"ok": True})],
            ) as request:
                with patch.object(runtime.time, "sleep"):
                    with patch.object(
                        runtime.time, "monotonic", side_effect=[0.0, 0.1, 0.2]
                    ):
                        self.assertTrue(
                            runtime.wait_for_webhook_ingress(profile, timeout=30)
                        )
        self.assertEqual(request.call_count, 2)

    def test_ngrok_config_is_profile_owned_and_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            path = runtime.save_ngrok_config(
                profile,
                "test-token",
                "https://assigned-name.ngrok-free.app",
            )
            self.assertEqual(path, profile / "secrets/ngrok.yml")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            config = path.read_text(encoding="utf-8")
            self.assertIn('authtoken: "test-token"', config)
            self.assertIn('url: "https://assigned-name.ngrok-free.app"', config)
            self.assertIn("url: http://host.docker.internal:8645", config)
            (profile / ".env").write_text(
                "NOTION_TOKEN=not-real\n"
                "NOTION_WEBHOOK_PUBLIC_URL=https://example.invalid/notion/webhook\n",
                encoding="utf-8",
            )
            self.assertTrue(runtime.webhook_enabled(profile))

    def test_notion_mcp_configuration_uses_hermes_config_owner(self) -> None:
        profile = Path("/tmp/company-os-profile")
        calls: list[list[str]] = []

        def fake_run(arguments, profile_home, **kwargs):
            self.assertEqual(profile_home, profile)
            calls.append(arguments)
            if kwargs.get("check") is False:
                return subprocess.CompletedProcess(arguments, 1, "", "not set")
            return subprocess.CompletedProcess(arguments, 0, "", "")

        with patch.object(runtime, "run_command", side_effect=fake_run):
            runtime.configure_notion_mcp(profile)
        self.assertEqual(len(calls), 3)
        self.assertIn(
            [
                "hermes", "config", "set", "--force",
                "mcp_servers.notion.url", runtime.NOTION_MCP_URL,
            ],
            calls,
        )
        self.assertFalse(any("npx" in item for call in calls for item in call))

    def test_messaging_mcp_exposes_only_required_message_tools(self) -> None:
        profile = Path("/tmp/company-os-profile")
        calls: list[tuple[list[str], bool]] = []

        def fake_run(arguments, profile_home, **kwargs):
            self.assertEqual(profile_home, profile)
            calls.append((arguments, kwargs.get("check", True)))
            return subprocess.CompletedProcess(
                arguments,
                0,
                "✓ Connected\n✓ Tools discovered" if arguments[1:3] == ["mcp", "test"] else "",
                "",
            )

        with patch.object(runtime, "run_command", side_effect=fake_run):
            runtime.configure_messaging_mcp(profile)

        settings = {call[0][-2]: call[0][-1] for call in calls[:-1]}
        self.assertEqual(settings["mcp_servers.company_os_messaging.command"], "hermes")
        self.assertEqual(settings["mcp_servers.company_os_messaging.args"], '["mcp","serve"]')
        self.assertEqual(
            settings["mcp_servers.company_os_messaging.tools.include"],
            '["messages_send","messages_read","channels_list",'
            '"conversations_list","conversation_get"]',
        )
        self.assertEqual(
            calls[-1],
            (["hermes", "mcp", "test", "company_os_messaging"], False),
        )

    def test_mcp_connection_ready_accepts_windows_mojibake_success_markers(self) -> None:
        result = subprocess.CompletedProcess(
            ["hermes", "mcp", "test", "notion"],
            0,
            "âœ“ Connected\nâœ“ Tools discovered: 42\n",
            "",
        )
        self.assertTrue(runtime.mcp_connection_ready(result))

    def test_whatsapp_requires_enabled_secret_and_paired_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            (profile / ".env").write_text("WHATSAPP_ENABLED=true\n", encoding="utf-8")
            self.assertFalse(runtime.whatsapp_gateway_configured(profile))
            credentials = profile / "platforms/whatsapp/session/creds.json"
            credentials.parent.mkdir(parents=True)
            credentials.write_text("{}\n", encoding="utf-8")
            self.assertTrue(runtime.whatsapp_gateway_configured(profile))

    def test_catalog_mcp_install_uses_hermes_owner_and_validates_name(self) -> None:
        profile = Path("/tmp/company-os-profile")
        calls: list[list[str]] = []

        def fake_run(arguments, profile_home, **kwargs):
            del kwargs
            self.assertEqual(profile_home, profile)
            calls.append(arguments)
            return subprocess.CompletedProcess(arguments, 0, "", "")

        with patch.object(runtime, "run_command", side_effect=fake_run):
            runtime.install_catalog_mcp(profile, "linear")
        self.assertEqual(
            calls,
            [
                ["hermes", "config", "get", "mcp_servers.linear.url"],
                ["hermes", "mcp", "install", "linear"],
            ],
        )
        with self.assertRaisesRegex(runtime.RuntimeSetupError, "invalid_mcp_catalog_name"):
            runtime.install_catalog_mcp(profile, "../../unsafe")

    def test_catalog_mcp_install_skips_an_existing_registration(self) -> None:
        profile = Path("/tmp/company-os-profile")
        with patch.object(
            runtime,
            "run_command",
            return_value=subprocess.CompletedProcess(
                [], 0, runtime.NOTION_MCP_URL + "\n", ""
            ),
        ) as run:
            runtime.install_catalog_mcp(profile, "notion")

        run.assert_called_once_with(
            ["hermes", "config", "get", "mcp_servers.notion.url"],
            profile,
            check=False,
        )

    def test_remote_mcp_url_is_written_through_stdin_not_process_arguments(self) -> None:
        profile = Path("/tmp/company-os-profile")
        calls: list[tuple[list[str], str | None]] = []

        def fake_run(arguments, profile_home, **kwargs):
            self.assertEqual(profile_home, profile)
            calls.append((arguments, kwargs.get("input_text")))
            return subprocess.CompletedProcess(arguments, 0, "", "")

        with patch.object(runtime, "run_command", side_effect=fake_run):
            with patch.object(runtime, "hermes_python", return_value=Path("/hermes/python")):
                runtime.configure_remote_mcp(
                    profile,
                    "composio-google",
                    "https://app.composio.dev/tool_router/v3/test/mcp",
                    headers={"x-api-key": "${COMPOSIO_API_KEY}"},
                )
        self.assertEqual(len(calls), 1)
        self.assertNotIn("app.composio.dev", " ".join(calls[0][0]))
        payload = json.loads(calls[0][1] or "{}")
        self.assertIn("app.composio.dev", payload["url"])
        self.assertEqual(
            json.loads(payload["headers"]),
            {"x-api-key": "${COMPOSIO_API_KEY}"},
        )

    def test_remote_mcp_rejects_invalid_headers_before_writing_config(self) -> None:
        with patch.object(runtime, "run_command") as run_command:
            with self.assertRaisesRegex(
                runtime.RuntimeSetupError, "invalid_remote_mcp_headers"
            ):
                runtime.configure_remote_mcp(
                    Path("/tmp/company-os-profile"),
                    "composio-google",
                    "https://app.composio.dev/tool_router/v3/test/mcp",
                    headers={"x-api-key": ""},
                )
        run_command.assert_not_called()

    def test_webhook_url_requires_stable_public_https_hostname(self) -> None:
        self.assertEqual(
            runtime.normalize_webhook_url("https://Hermes.Example.com/"),
            "https://hermes.example.com/notion/webhook",
        )
        self.assertEqual(
            runtime.normalize_webhook_url(
                "https://hermes.example.com/notion/webhook/"
            ),
            "https://hermes.example.com/notion/webhook",
        )
        self.assertEqual(
            runtime.normalize_webhook_url("https://assigned-name.ngrok-free.app"),
            "https://assigned-name.ngrok-free.app/notion/webhook",
        )
        rejected = (
            "http://hermes.example.com",
            "https://random.trycloudflare.com",
            "https://localhost",
            "https://127.0.0.1",
            "https://hermes.example.com/other",
            "https://hermes.example.com?token=value",
            "https://hermes.example.com:8443",
        )
        for value in rejected:
            with self.subTest(value=value), self.assertRaises(runtime.RuntimeSetupError):
                runtime.normalize_webhook_url(value)

    def test_webhook_public_url_reads_only_the_named_profile_value(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            (profile / ".env").write_text(
                "NOTION_TOKEN=never-return-this\n"
                "NOTION_WEBHOOK_PUBLIC_URL='https://hermes.example.com/notion/webhook'\n",
                encoding="utf-8",
            )
            self.assertEqual(
                runtime.webhook_public_url(profile),
                "https://hermes.example.com/notion/webhook",
            )

    def test_hostname_rotation_resets_only_endpoint_bound_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            (profile / ".env").write_text(
                "NOTION_TOKEN=not-real\n"
                "NOTION_WEBHOOK_PUBLIC_URL=https://old-name.ngrok-free.app/notion/webhook\n",
                encoding="utf-8",
            )
            state_path = profile / "state" / "notion-webhook.json"
            state_path.parent.mkdir()
            original = {
                "verification_token": "old-verification-token",
                "workspace_id": "workspace-1",
                "seen": {"event-1": 1.0},
                "reply_targets": {"comment-1": {"discussion_id": "thread-1"}},
                "last_reply": {"message_id": "reply-1"},
            }
            state_path.write_text(json.dumps(original), encoding="utf-8")
            with patch.object(runtime, "save_profile_secret"):
                with patch.object(runtime, "run_command"):
                    runtime.configure_notion_webhook(
                        profile, "https://new-name.ngrok-free.app"
                    )
            rotated = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(rotated["verification_token"], "")
            self.assertEqual(rotated["workspace_id"], "workspace-1")
            self.assertEqual(rotated["seen"], {"event-1": 1.0})
            self.assertEqual(rotated["last_reply"], {"message_id": "reply-1"})
            self.assertEqual(stat.S_IMODE(state_path.stat().st_mode), 0o600)

    def test_same_hostname_preserves_verification_during_authtoken_rotation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            endpoint = "https://same-name.ngrok-free.app/notion/webhook"
            (profile / ".env").write_text(
                f"NOTION_TOKEN=not-real\nNOTION_WEBHOOK_PUBLIC_URL={endpoint}\n",
                encoding="utf-8",
            )
            state_path = profile / "state" / "notion-webhook.json"
            state_path.parent.mkdir()
            state_path.write_text(
                json.dumps({"verification_token": "keep-me"}), encoding="utf-8"
            )
            with patch.object(runtime, "save_profile_secret"):
                with patch.object(runtime, "run_command"):
                    runtime.configure_notion_webhook(profile, endpoint)
            self.assertEqual(
                json.loads(state_path.read_text(encoding="utf-8"))["verification_token"],
                "keep-me",
            )

    def test_live_webhook_lanes_probe_local_and_public_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            runtime.save_ngrok_config(
                profile,
                "test-token",
                "https://assigned-name.ngrok-free.app",
            )
            (profile / ".env").write_text(
                "NOTION_TOKEN=not-real\n"
                "NOTION_WEBHOOK_PUBLIC_URL=https://hermes.example.com/notion/webhook\n",
                encoding="utf-8",
            )

            def fake_json(url, timeout=3.0):
                del timeout
                if url.endswith("/notion/health"):
                    return True, {"ok": True, "verification_token_captured": True}
                return False, {}

            with patch.object(runtime, "_http_json", side_effect=fake_json):
                with patch.object(runtime, "_http_post_status", return_value=401):
                    lanes = runtime._webhook_lanes(profile, live=True)
            self.assertEqual(
                {lane["name"]: lane["status"] for lane in lanes},
                {
                    "notion_webhook": "pass",
                    "public_endpoint": "pass",
                    "signature_rejection": "pass",
                },
            )

    def test_apply_approval_promotes_only_the_workspace_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace.hermes.md"
            before = "---\nstatus: draft\n---\n# Owner content\nstatus: prose\n"
            workspace.write_text(before, encoding="utf-8")
            runtime.approve_workspace_context(workspace)
            after = workspace.read_text(encoding="utf-8")
            self.assertEqual(
                after,
                "---\nstatus: approved\n---\n# Owner content\nstatus: prose\n",
            )
            runtime.approve_workspace_context(workspace)
            self.assertEqual(workspace.read_text(encoding="utf-8"), after)

    def _ready_profile(self, root: Path) -> Path:
        profile = root / "profiles" / runtime.PROFILE_NAME
        workspace = profile / "workspace"
        cron = profile / "cron"
        workspace.mkdir(parents=True)
        cron.mkdir()
        for name in ("distribution.yaml", "setup.py", "workspace.hermes.md"):
            (profile / name).write_text("ready\n", encoding="utf-8")
        (workspace / ".hermes.md").write_text("ready\n", encoding="utf-8")
        (profile / ".env").write_text(
            "OPENROUTER_API_KEY=not-a-real-secret\n", encoding="utf-8"
        )
        for name in ("pm-daily", "pm-weekly"):
            skill = profile / "skills" / name / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(f"# {name}\n", encoding="utf-8")
        (cron / "jobs.json").write_text(
            json.dumps(
                {
                    "jobs": [
                        {"name": name, "enabled": True}
                        for name in sorted(runtime.EXPECTED_CRON_NAMES)
                    ]
                }
            ),
            encoding="utf-8",
        )
        (profile / "gateway_state.json").write_text(
            json.dumps(
                {
                    "gateway_state": "running",
                    "hermes_home": str(profile),
                }
            ),
            encoding="utf-8",
        )
        return profile

    def test_verify_returns_ready_without_claiming_skipped_webhook(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = self._ready_profile(Path(temporary))
            workspace = profile / "workspace"

            def fake_run(arguments, profile_home, **kwargs):
                del profile_home, kwargs
                joined = " ".join(arguments)
                if "terminal.cwd" in joined:
                    output = str(workspace)
                elif "terminal.backend" in joined:
                    output = "docker"
                elif "terminal.docker_mount_cwd_to_workspace" in joined:
                    output = "true"
                elif "docker run" in joined:
                    output = "COMPANY_OS_DOCKER_BACKEND_OK"
                elif "mcp_servers.notion.url" in joined:
                    output = runtime.NOTION_MCP_URL
                else:
                    output = ""
                return subprocess.CompletedProcess(arguments, 0, output, "")

            receipt = runtime.verify_profile(profile, command_runner=fake_run)
            self.assertEqual(receipt["status"], "ready")
            self.assertEqual(
                next(lane for lane in receipt["lanes"] if lane["name"] == "skill_packages")["status"],
                "pass",
            )
            webhook = next(
                lane for lane in receipt["lanes"] if lane["name"] == "notion_webhook"
            )
            self.assertEqual(webhook["status"], "skip")
            self.assertFalse(webhook["required"])

    def test_verify_blocks_when_required_runtime_state_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary) / "profiles" / runtime.PROFILE_NAME
            profile.mkdir(parents=True)

            def failed(arguments, profile_home, **kwargs):
                del profile_home, kwargs
                return subprocess.CompletedProcess(arguments, 1, "", "not ready")

            receipt = runtime.verify_profile(profile, command_runner=failed)
            self.assertEqual(receipt["status"], "blocked")
            self.assertTrue(
                any(
                    lane["required"] and lane["status"] == "fail"
                    for lane in receipt["lanes"]
                )
            )

    def test_receipt_is_owner_only_and_contains_no_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            receipt = {"status": "partial", "lanes": []}
            path = runtime.write_receipt(profile, receipt)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), receipt)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_compose_keeps_webhook_private_and_uses_profile_ngrok_config(self) -> None:
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        self.assertNotIn("gateway:", compose)
        self.assertNotIn("dashboard:", compose)
        self.assertNotIn("setup:", compose)
        self.assertIn("${COMPANY_OS_PROFILE_HOME}/secrets/ngrok.yml", compose)
        self.assertIn("/etc/ngrok.yml", compose)
        self.assertIn("ngrok/ngrok:latest@sha256:", compose)
        self.assertIn('user: "10000:10000"', compose)
        self.assertNotIn("nousresearch/hermes-agent", compose)
        self.assertNotIn("cloudflared", compose.lower())

    def test_windows_launcher_exposes_only_one_setup_surface(self) -> None:
        launcher = (ROOT / "setup.cmd").read_text(encoding="utf-8")
        self.assertIn('call :run_setup launch', launcher)
        self.assertIn('"%HERMES_PYTHON%" "%~dp0setup.py" %*', launcher)
        self.assertIn('set "HERMES_HOME=%COMPANY_OS_PROFILE_HOME%"', launcher)
        self.assertIn('if "%COMPANY_OS_ACTION%"=="10" goto full_proof', launcher)
        self.assertIn('if "%COMPANY_OS_ACTION%"=="11" goto static_verify', launcher)
        self.assertIn('if "%COMPANY_OS_ACTION%"=="14" goto certify', launcher)
        self.assertIn('if "%COMPANY_OS_ACTION%"=="15" goto preflight_check', launcher)
        self.assertIn('if "%COMPANY_OS_ACTION%"=="16" goto eval_check', launcher)
        self.assertIn('if "%COMPANY_OS_ACTION%"=="17" goto dossier', launcher)
        self.assertIn("call :run_setup verify --live", launcher)
        self.assertIn("call :run_setup doctor preflight", launcher)
        self.assertIn("call :run_setup doctor eval --open", launcher)
        self.assertIn("call :run_setup doctor activate", launcher)
        self.assertIn("call :run_setup webhook-ingress-ready --wait 30", launcher)
        self.assertIn("hermes gateway run", launcher)
        self.assertIn("call :selected_gateway_running", launcher)
        self.assertIn('findstr /c:"Gateway is running (PID:"', launcher)
        self.assertNotIn('findstr /i /c:"running"', launcher)
        self.assertIn("A gateway running for another profile is not accepted.", launcher)
        self.assertNotIn("docker compose up -d gateway", launcher)
        self.assertNotIn("run --rm setup", launcher)
        self.assertNotIn("compose --profile setup --profile webhook pull", launcher)
        self.assertNotIn("run --rm setup install", launcher)
        self.assertNotIn("NOTION_TOKEN", launcher)
        self.assertIn("up -d --force-recreate ngrok", launcher)
        self.assertIn("assigned endpoint did not become reachable", launcher)
        self.assertIn("ps --status running --services ngrok", launcher)

    def test_macos_launcher_preserves_setup_and_webhook_transactions(self) -> None:
        launcher = (ROOT / "setup.sh").read_text(encoding="utf-8")
        self.assertIn('HERMES_PYTHON="${HOME}/.hermes/hermes-agent/venv/bin/python"', launcher)
        self.assertIn('export HERMES_HOME="$COMPANY_OS_PROFILE_HOME"', launcher)
        self.assertIn("run_setup launch", launcher)
        self.assertIn("run_setup verify --live", launcher)
        self.assertIn("run_setup doctor preflight", launcher)
        self.assertIn("run_setup doctor eval --open", launcher)
        self.assertIn("run_setup doctor activate", launcher)
        self.assertIn("run_setup webhook-ingress-ready --wait 30", launcher)
        self.assertIn("run_setup webhook-rollback", launcher)
        self.assertIn("run_setup webhook-commit", launcher)
        self.assertIn("selected_gateway_running", launcher)
        self.assertIn('grep -Fq "Gateway is running (PID:"', launcher)
        self.assertNotIn("grep -qi running", launcher)
        self.assertIn("A gateway running for another profile is not accepted.", launcher)
        self.assertIn('open "http://localhost:9119"', launcher)
        self.assertNotIn("run --rm setup", launcher)
        self.assertNotIn("NOTION_TOKEN", launcher)

    def test_customer_compose_commands_preserve_the_setup_entry_point(self) -> None:
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        self.assertNotIn("setup:", compose)

        surfaces = [ROOT / "README.md"]
        for pattern in ("*.cmd", "*.ps1", "*.sh"):
            surfaces.extend(ROOT.glob(pattern))
            surfaces.extend((ROOT / "apps").rglob(pattern))
        surfaces.extend((ROOT / "docs").rglob("*.md"))
        setup_run = re.compile(
            r"\bdocker(?:\s+compose|-compose)\b.*\brun\b.*?\bsetup\b(?P<command>.*)$",
            re.IGNORECASE,
        )

        def preserves_setup_entry_point(line: str) -> bool:
            match = setup_run.search(line)
            if not match:
                return True
            command = match.group("command").strip()
            return not command or command.startswith("python /distribution/setup.py")

        for unsafe in (
            "docker compose run setup launch",
            "docker compose --profile setup run setup verify --live",
            "docker-compose run --rm setup certify",
        ):
            self.assertFalse(preserves_setup_entry_point(unsafe))
        self.assertTrue(preserves_setup_entry_point("docker compose run --rm setup"))

        invalid: list[str] = []
        for path in surfaces:
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if not preserves_setup_entry_point(line):
                    invalid.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}")
        self.assertEqual(invalid, [])

if __name__ == "__main__":
    unittest.main()
