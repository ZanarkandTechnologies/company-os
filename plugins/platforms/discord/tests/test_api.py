from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from plugins.platforms.discord import adapter, api  # noqa: E402


GUILD_ID = "123456789012345678"
CHANNEL_ID = "234567890123456789"
MESSAGE_ID = "345678901234567890"
TOKEN = "test-token"


class DiscordApiTests(unittest.TestCase):
    def client(self) -> api.DiscordClient:
        return api.DiscordClient(TOKEN)

    def test_target_rejects_non_snowflake_identifiers(self) -> None:
        with self.assertRaisesRegex(ValueError, "discord_guild_id"):
            api.DiscordTarget("not-a-guild", CHANNEL_ID)
        with self.assertRaisesRegex(ValueError, "discord_channel_id"):
            api.DiscordTarget(GUILD_ID, "not-a-channel")

    def test_resolve_target_requires_exact_guild_text_channel(self) -> None:
        client = self.client()
        with patch.object(
            client,
            "_request",
            side_effect=[{"id": GUILD_ID}, {"id": CHANNEL_ID, "guild_id": GUILD_ID, "type": 0, "name": "owner-private"}],
        ):
            target = client.resolve_target(GUILD_ID, CHANNEL_ID)
        self.assertEqual(target.exact_target, f"discord:{GUILD_ID}:{CHANNEL_ID}")
        self.assertEqual(target.channel_name, "owner-private")

    def test_resolve_target_rejects_other_guild_and_non_text_channel(self) -> None:
        client = self.client()
        with patch.object(
            client,
            "_request",
            side_effect=[{"id": GUILD_ID}, {"id": CHANNEL_ID, "guild_id": "999999999999999999", "type": 0}],
        ):
            with self.assertRaisesRegex(api.DiscordApiError, "outside_approved_guild"):
                client.resolve_target(GUILD_ID, CHANNEL_ID)

    def test_bot_roles_are_resolved_from_the_exact_guild_member(self) -> None:
        client = self.client()
        bot_id = "456789012345678901"
        role_id = "567890123456789012"
        with patch.object(client, "_request", return_value={"roles": [role_id, "invalid"]}) as request:
            roles = client.bot_role_ids(GUILD_ID, bot_id)
        self.assertEqual(roles, {role_id})
        self.assertEqual(request.call_args.args[:2], ("GET", f"/guilds/{GUILD_ID}/members/{bot_id}"))
        with patch.object(
            client,
            "_request",
            side_effect=[{"id": GUILD_ID}, {"id": CHANNEL_ID, "guild_id": GUILD_ID, "type": 2}],
        ):
            with self.assertRaisesRegex(api.DiscordApiError, "must_be_text"):
                client.resolve_target(GUILD_ID, CHANNEL_ID)

    def test_send_is_mention_safe_and_returns_exact_receipt(self) -> None:
        client = self.client()
        target = api.DiscordTarget(GUILD_ID, CHANNEL_ID)
        with patch.object(client, "_request", return_value={"id": MESSAGE_ID, "channel_id": CHANNEL_ID}) as request:
            receipt = client.send_message(target, "@everyone report for <@123>")
        self.assertEqual(receipt["exact_target"], f"discord:{GUILD_ID}:{CHANNEL_ID}")
        body = request.call_args.args[2]
        self.assertEqual(body["allowed_mentions"], {"parse": [], "replied_user": False})
        self.assertNotIn("@everyone", body["content"])
        self.assertNotIn("<@123>", body["content"])

    def test_send_rejects_unbounded_content_or_target_mismatch(self) -> None:
        client = self.client()
        target = api.DiscordTarget(GUILD_ID, CHANNEL_ID)
        with self.assertRaisesRegex(ValueError, "exceeds_2000"):
            client.send_message(target, "x" * 2_001)
        with patch.object(client, "_request", return_value={"id": MESSAGE_ID, "channel_id": GUILD_ID}):
            with self.assertRaisesRegex(api.DiscordApiError, "target_mismatch"):
                client.send_message(target, "safe")

    def test_reply_is_anchored_without_ping(self) -> None:
        client = self.client()
        target = api.DiscordTarget(GUILD_ID, CHANNEL_ID)
        with patch.object(client, "_request", return_value={"id": MESSAGE_ID, "channel_id": CHANNEL_ID}) as request:
            client.send_message(target, "answer", reply_to=MESSAGE_ID)
        body = request.call_args.args[2]
        self.assertEqual(body["message_reference"], {"message_id": MESSAGE_ID, "channel_id": CHANNEL_ID})
        self.assertFalse(body["allowed_mentions"]["replied_user"])

    def test_split_delivery_is_safe_bounded_and_retry_addressable(self) -> None:
        token = "a" * 64
        chunks = api.split_delivery("@here " + "x" * 4_000, token)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= api.MAX_MESSAGE_LENGTH for chunk in chunks))
        self.assertTrue(all(f"[company-os:{token}:part " in chunk for chunk in chunks))
        self.assertTrue(all("@here" not in chunk for chunk in chunks))
        with self.assertRaisesRegex(ValueError, "message_too_long"):
            api.split_delivery("x" * 100_000, token)

    def test_write_tool_is_disabled_until_explicitly_enabled(self) -> None:
        with patch.dict("os.environ", {"DISCORD_ENABLE_WRITES": "false"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "writes are disabled"):
                api.discord_send_message({"content": "do not send"})

    def test_list_messages_keeps_only_the_approved_channel(self) -> None:
        client = self.client()
        target = api.DiscordTarget(GUILD_ID, CHANNEL_ID)
        with patch.object(
            client,
            "_request",
            return_value=[
                {"id": MESSAGE_ID, "channel_id": CHANNEL_ID, "content": "approved"},
                {"id": "456789012345678901", "channel_id": GUILD_ID, "content": "other"},
            ],
        ):
            messages = client.list_messages(target)
        self.assertEqual(messages, [{"id": MESSAGE_ID, "channel_id": CHANNEL_ID, "content": "approved"}])


class DiscordPluginRegistrationTests(unittest.TestCase):
    def test_plugin_registers_only_bounded_owner_channel_tools(self) -> None:
        registered: list[dict] = []
        platforms: list[dict] = []

        class Context:
            def register_tool(self, **kwargs) -> None:
                registered.append(kwargs)

            def register_platform(self, **kwargs) -> None:
                platforms.append(kwargs)

        adapter.register(Context())
        self.assertEqual(
            [item["name"] for item in registered],
            ["discord_get_channel", "discord_list_messages", "discord_send_message"],
        )
        self.assertTrue(all(item["toolset"] == "discord_connector" for item in registered))
        self.assertEqual([item["name"] for item in platforms], ["discord"])
        self.assertIs(platforms[0]["adapter_factory"], adapter.DiscordAdapter)


if __name__ == "__main__":
    unittest.main()
