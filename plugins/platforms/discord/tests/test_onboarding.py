from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from apps.installer.schemas.workspace import MessagingApp, parse_workspace_communications
from plugins.platforms.discord import onboarding


WORKSPACE = """---
status: approved
---
<!-- hermes:managed communications -->
| Message | App | Send to | Behavior |
| --- | --- | --- | --- |
<!-- /hermes:managed communications -->
"""


class DiscordOnboardingTests(unittest.TestCase):
    def test_configuration_binds_the_private_channel_as_a_draft_only_owner_route(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            profile = Path(raw)
            (profile / "distribution.yaml").write_text("name: company-os\n", encoding="utf-8")
            (profile / "workspace.hermes.md").write_text(WORKSPACE, encoding="utf-8")
            live = profile / "workspace" / ".hermes.md"
            live.parent.mkdir()
            live.write_text(WORKSPACE, encoding="utf-8")
            client = SimpleNamespace(
                validate_token=lambda: None,
                resolve_target=lambda _guild, _channel: SimpleNamespace(
                    guild_id="12345678901234567",
                    channel_id="23456789012345678",
                    channel_name="hermes-test",
                ),
            )
            saved = {}
            with patch.object(onboarding, "DiscordClient", return_value=client), patch.object(
                onboarding, "_prompt_secret", return_value="test-token"
            ), patch.object(onboarding, "_prompt_text", side_effect=["12345678901234567", "23456789012345678"]), patch.object(
                onboarding.runtime, "save_profile_secret", side_effect=lambda _home, key, value: saved.__setitem__(key, value)
            ), patch.object(
                onboarding, "confirm", return_value=False
            ):
                onboarding.configure_owner_route(profile)

            bindings = parse_workspace_communications(
                (profile / "workspace.hermes.md").read_text(encoding="utf-8")
            ).communications
            self.assertEqual(len(bindings), 1)
            self.assertEqual(bindings[0].app, MessagingApp.DISCORD)
            self.assertEqual(bindings[0].send_to, "#hermes-test")
            self.assertEqual(bindings[0].behavior.value, "prepare drafts for approval")
            self.assertEqual(live.read_text(encoding="utf-8"), (profile / "workspace.hermes.md").read_text(encoding="utf-8"))
            self.assertEqual(saved["DISCORD_ASSISTANT_ENABLED"], "false")
            self.assertEqual(saved["DISCORD_ALLOW_ALL_USERS"], "false")

    def test_assistant_enables_the_bounded_discord_user_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            profile = Path(raw)
            (profile / "distribution.yaml").write_text("name: company-os\n", encoding="utf-8")
            (profile / "workspace.hermes.md").write_text(WORKSPACE, encoding="utf-8")
            live = profile / "workspace" / ".hermes.md"
            live.parent.mkdir()
            live.write_text(WORKSPACE, encoding="utf-8")
            client = SimpleNamespace(
                validate_token=lambda: None,
                resolve_target=lambda _guild, _channel: SimpleNamespace(
                    guild_id="12345678901234567",
                    channel_id="23456789012345678",
                    channel_name="hermes-test",
                ),
            )
            saved = {}
            commands = []
            with patch.object(onboarding, "DiscordClient", return_value=client), patch.object(
                onboarding, "_prompt_secret", return_value="test-token"
            ), patch.object(
                onboarding, "_prompt_text", side_effect=["12345678901234567", "23456789012345678"]
            ), patch.object(
                onboarding.runtime, "save_profile_secret", side_effect=lambda _home, key, value: saved.__setitem__(key, value)
            ), patch.object(
                onboarding.runtime, "run_command", side_effect=lambda args, _home: commands.append(args)
            ), patch.object(onboarding, "confirm", return_value=True):
                onboarding.configure_owner_route(profile)

            self.assertEqual(saved["DISCORD_ASSISTANT_ENABLED"], "true")
            self.assertEqual(saved["DISCORD_ALLOW_ALL_USERS"], "true")
            self.assertEqual(commands[0][:3], ["hermes", "plugins", "enable"])
            self.assertEqual(commands[1], ["hermes", "config", "set", "platforms.discord.enabled", "true"])
            self.assertEqual(
                commands[2:],
                [
                    ["hermes", "config", "set", "platforms.discord.home_channel.platform", "discord"],
                    ["hermes", "config", "set", "platforms.discord.home_channel.chat_id", "23456789012345678"],
                    ["hermes", "config", "set", "platforms.discord.home_channel.name", "#hermes-test"],
                    ["hermes", "config", "set", "platforms.discord.home_channel.scope_id", "12345678901234567"],
                ],
            )
