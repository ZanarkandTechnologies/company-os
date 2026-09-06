from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERMES_ROOT = Path.home() / ".hermes/hermes-agent"
WINDOWS_HERMES_ROOT = Path.home() / "AppData/Local/hermes/hermes-agent"
sys.path.insert(0, str(WINDOWS_HERMES_ROOT if WINDOWS_HERMES_ROOT.is_dir() else HERMES_ROOT))

from plugins.platforms.discord.adapter import mentioned_question


class DiscordAdapterTests(unittest.TestCase):
    def message(self, **changes):
        payload = {
            "guild_id": "12345678901234567",
            "channel_id": "23456789012345678",
            "id": "34567890123456789",
            "content": "<@45678901234567890> what is blocked?",
            "author": {"id": "56789012345678901", "username": "person"},
            "mentions": [{"id": "45678901234567890"}],
        }
        payload.update(changes)
        return payload

    def test_exact_channel_mention_returns_only_the_question(self):
        self.assertEqual(
            mentioned_question(self.message(), "45678901234567890", "12345678901234567", "23456789012345678"),
            "what is blocked?",
        )

    def test_other_channel_unmentioned_and_bot_messages_are_ignored(self):
        values = [
            self.message(channel_id="99999999999999999"),
            self.message(mentions=[], content="what is blocked?"),
            self.message(author={"id": "56789012345678901", "bot": True}),
        ]
        for payload in values:
            self.assertEqual(mentioned_question(payload, "45678901234567890", "12345678901234567", "23456789012345678"), "")

    def test_role_assigned_to_bot_is_treated_as_a_mention(self):
        role_id = "67890123456789012"
        payload = self.message(
            content=f"<@&{role_id}> say hello",
            mentions=[],
            mention_roles=[role_id],
        )
        self.assertEqual(
            mentioned_question(payload, "45678901234567890", "12345678901234567", "23456789012345678", {role_id}),
            "say hello",
        )
        self.assertEqual(
            mentioned_question(payload, "45678901234567890", "12345678901234567", "23456789012345678", {"78901234567890123"}),
            "",
        )
