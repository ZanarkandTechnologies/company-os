---
title: Discord delivery and mention-only assistant connector
status: implemented
owner: Company OS
updated_at: 2026-09-03
---

# Discord delivery and mention-only assistant connector

This connector supports two independent Discord capabilities for one approved
guild text channel:

- owner-report delivery through bounded Discord API tools, gated by
  `DISCORD_ENABLE_WRITES=true`; and
- a Gateway listener that replies only when the bot is explicitly mentioned,
  gated by `DISCORD_ASSISTANT_ENABLED=true`.

The listener ignores ordinary messages, bot-authored messages, other guilds,
and other channels. Replies are anchored to the triggering Discord message and
do not mention the author. It does not process slash commands or webhooks.

## Profile-only configuration

The following values belong in the private Hermes profile, never the source
repository or reviewed workspace document:

- `DISCORD_BOT_TOKEN`
- `DISCORD_OWNER_GUILD_ID`
- `DISCORD_OWNER_CHANNEL_ID`
- `DISCORD_ENABLE_WRITES`
- `DISCORD_ASSISTANT_ENABLED`
- `DISCORD_ALLOW_ALL_USERS`

The bot needs only View Channel, Send Messages, and Read Message History for
the one approved private text channel. The mention-only assistant additionally
requires Message Content intent in the Discord Developer Portal. Never grant
Administrator, Manage Messages, or member-management permissions.

When the assistant is enabled, setup also enables Discord's platform-scoped
user gate. This does not expose other Discord conversations: the adapter
discards DMs, other guilds, other channels, unmentioned messages, and bot
messages before they reach Hermes' shared authorization layer.

## Local verification

```bash
python3 -m unittest plugins.platforms.discord.tests.test_api plugins.platforms.discord.tests.test_adapter plugins.platforms.discord.tests.test_onboarding -v
```

These tests mock Discord completely. A provider-backed test is deferred until
the installer owns the explicit connection-test and receipt flow.
