from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "scripts" / "notion_webhook_onboard.py"
SPEC = importlib.util.spec_from_file_location("notion_webhook_onboard", SCRIPT)
onboard = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(onboard)


class NotionWebhookOnboardingTests(unittest.TestCase):
    def test_root_page_url_parses_and_invalid_input_stops(self):
        expected = "725195b6-78ee-4750-9994-6dfaedf086c0"
        self.assertEqual(
            onboard.parse_page_id("https://notion.so/Test-725195b678ee475099946dfaedf086c0"),
            expected,
        )
        self.assertEqual(onboard.parse_page_id(expected), expected)
        with self.assertRaisesRegex(onboard.OnboardError, "page ID"):
            onboard.parse_page_id("https://notion.so/no-page-here")

    def test_state_is_scoped_to_the_selected_hermes_profile(self):
        profile = Path("/srv/hermes/profiles/kamdar-ai")
        self.assertEqual(
            onboard.state_path(profile),
            profile / "state" / "notion-webhook.json",
        )

    def test_dry_run_is_ngrok_only_and_replies_are_not_a_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = onboard.configure(
                root,
                "https://notion.so/Test-725195b678ee475099946dfaedf086c0",
                "@vishanai",
                "",
                True,
            )
        self.assertEqual(value["state"], "ready")
        self.assertEqual(value["ingress"], "ngrok")
        self.assertTrue(value["comment_replies"])
        self.assertFalse(value["page_property_writes"])
        self.assertNotIn("NOTION_ENABLE_COMMENT_REPLIES", value["planned_settings"])
        self.assertNotIn("caddy", json.dumps(value).lower())
        self.assertNotIn("nginx", json.dumps(value).lower())
        self.assertNotIn("traefik", json.dumps(value).lower())

    def test_service_uses_doppler_without_embedding_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o755)
            content = onboard.ngrok_unit(root, "/usr/bin/ngrok", "/usr/bin/doppler")
        self.assertIn("doppler run --scope", content)
        self.assertIn("ngrok http http://127.0.0.1:8645", content)
        self.assertIn("NoNewPrivileges=true", content)
        self.assertNotIn("authtoken", content.lower())
        self.assertNotIn("reverse_proxy", content)

    def test_headless_login_returns_clickable_url(self):
        with patch.dict(os.environ, {"SSH_CONNECTION": "1 2 3 4"}, clear=False), patch.dict(
            os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}, clear=False
        ), patch.object(onboard.webbrowser, "open") as opened:
            value = onboard.browser_open("ngrok")
        self.assertEqual(value["state"], "human_required")
        self.assertFalse(value["browser_opened"])
        self.assertEqual(value["url"], onboard.NGROK_LOGIN_URL)
        opened.assert_not_called()

    def test_discovery_persists_scope_and_restarts_hermes(self):
        discovered = {
            "sources": [
                {"id": "source-1", "title": "Tasks"},
                {"id": "source-2", "title": "Projects"},
            ]
        }
        completed = subprocess.CompletedProcess([], 0, json.dumps(discovered), "")
        with tempfile.TemporaryDirectory() as directory, patch.object(
            onboard, "require_command", return_value="/usr/bin/doppler"
        ), patch.object(onboard, "get_doppler_value_via_runtime", return_value="root-page"), patch.object(
            onboard, "run", return_value=completed
        ), patch.object(onboard, "set_doppler_values") as stored, patch.object(
            onboard, "detect_hermes_service", return_value="hermes.service"
        ), patch.object(onboard, "restart_service") as restarted:
            value = onboard.discover(Path(directory), "")
        self.assertEqual(value["discovered_table_count"], 2)
        stored.assert_called_once_with(Path(directory), {"NOTION_ALLOWED_DATA_SOURCES": "source-1,source-2"})
        restarted.assert_called_once_with("hermes.service")

    def test_finalize_requires_and_persists_real_reply_proof(self):
        incomplete = {"verification_token": "token", "workspace_id": "workspace-1", "last_reply": {}}
        with tempfile.TemporaryDirectory() as directory, patch.object(
            onboard, "read_state", return_value=incomplete
        ):
            waiting = onboard.finalize(Path(directory), "")
        self.assertEqual(waiting["action"], "wait_for_reply")
        complete = {
            "verification_token": "token",
            "workspace_id": "workspace-1",
            "last_reply": {"message_id": "reply-1"},
        }
        with tempfile.TemporaryDirectory() as directory, patch.object(
            onboard, "read_state", return_value=complete
        ), patch.object(onboard, "set_doppler_values") as stored, patch.object(
            onboard, "detect_hermes_service", return_value="hermes.service"
        ), patch.object(onboard, "restart_service"), patch.object(
            onboard, "get_public_doppler_value", return_value="https://example.ngrok.app/notion/webhook"
        ):
            ready = onboard.finalize(Path(directory), "")
        self.assertTrue(ready["workspace_locked"])
        self.assertTrue(ready["reply_observed"])
        stored.assert_called_once_with(
            Path(directory),
            {"NOTION_ALLOWED_WORKSPACES": "workspace-1", "NOTION_ALLOW_ALL_WORKSPACES": "false"},
        )

    def test_status_cannot_be_ready_until_workspace_is_actually_locked(self):
        state = {
            "verification_token": "token",
            "workspace_id": "workspace-1",
            "last_reply": {"message_id": "reply-1"},
        }
        open_settings = {
            "NOTION_ALLOWED_DATA_SOURCES": "source-1",
            "NOTION_ALLOWED_WORKSPACES": "",
            "NOTION_ALLOW_ALL_WORKSPACES": "true",
        }
        with tempfile.TemporaryDirectory() as directory, patch.object(
            onboard, "read_state", return_value=state
        ), patch.object(onboard, "doppler_secret_names", return_value=set(open_settings)), patch.object(
            onboard, "get_public_doppler_value", return_value="https://example.ngrok.app/notion/webhook"
        ), patch.object(onboard, "get_doppler_values_via_runtime", return_value=open_settings), patch.object(
            onboard, "local_health", return_value=True
        ), patch.object(onboard, "ngrok_public_url", return_value="https://example.ngrok.app"):
            value = onboard.status(Path(directory))
        self.assertEqual(value["state"], "human_required")
        self.assertFalse(value["workspace_locked"])

    def test_reconfigure_resets_old_subscription_and_reply_proof(self):
        stale = {
            "verification_token": "old-token",
            "workspace_id": "old-workspace",
            "seen": {"old-event": 1},
            "reply_targets": {"old-comment": {"discussion_id": "old-discussion", "saved_at": 1}},
            "last_reply": {"message_id": "old-reply"},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = onboard.state_path(root)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(stale), encoding="utf-8")
            with patch.object(onboard.sys, "platform", "linux"), patch.object(
                onboard.Path, "exists", return_value=True
            ), patch.object(onboard, "doppler_secret_names", return_value=onboard.ALLOWED_SECURE_KEYS), patch.object(
                onboard, "local_health", return_value=True
            ), patch.object(onboard, "install_ngrok", return_value="/usr/bin/ngrok"), patch.object(
                onboard, "set_doppler_values"
            ) as stored, patch.object(onboard, "install_ngrok_service"), patch.object(
                onboard, "wait_for_ngrok", return_value="https://new.ngrok.app"
            ), patch.object(onboard, "detect_hermes_service", return_value="hermes.service"), patch.object(
                onboard, "restart_service"
            ), patch.object(onboard, "webhook_reachable", return_value=True), patch.object(
                onboard, "browser_open", return_value={"browser_opened": False}
            ):
                value = onboard.configure(
                    root,
                    "https://notion.so/Test-725195b678ee475099946dfaedf086c0",
                    "@vishanai",
                    "",
                    False,
                )
            reset = onboard.read_state(root)
        self.assertEqual(value["endpoint"], "https://new.ngrok.app/notion/webhook")
        self.assertEqual(reset["verification_token"], "")
        self.assertEqual(reset["workspace_id"], "")
        self.assertEqual(reset["reply_targets"], {})
        self.assertEqual(reset["last_reply"], {})
        first_settings = stored.call_args_list[0].args[1]
        self.assertEqual(first_settings["NOTION_ALLOWED_WORKSPACES"], "")
        self.assertEqual(first_settings["NOTION_ALLOWED_DATA_SOURCES"], "")

    def test_preflight_blocks_when_listener_is_not_healthy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            connector = root / "plugins" / "platforms" / "notion"
            connector.mkdir(parents=True)
            (connector / "plugin.yaml").write_text("name: notion\n", encoding="utf-8")
            with patch.object(onboard.sys, "platform", "linux"), patch.object(
                onboard.Path, "exists", return_value=True
            ), patch.object(onboard.shutil, "which", return_value="/usr/bin/tool"), patch.object(
                onboard, "doppler_secret_names", return_value=onboard.ALLOWED_SECURE_KEYS
            ), patch.object(onboard, "local_health", return_value=False):
                value = onboard.preflight(root)
        self.assertEqual(value["state"], "blocked")
        self.assertEqual(value["blocker"], "hermes_notion_listener")

    def test_cli_dry_run_returns_structured_json(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "configure",
                "--root-page-url",
                "https://notion.so/Test-725195b678ee475099946dfaedf086c0",
                "--mention",
                "@hermes",
                "--dry-run",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["state"], "ready")
        self.assertTrue(value["comment_replies"])

    def test_cli_requires_company_agent_mention(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "configure",
                "--root-page-url",
                "https://notion.so/Test-725195b678ee475099946dfaedf086c0",
                "--dry-run",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--mention", result.stderr)


if __name__ == "__main__":
    unittest.main()
