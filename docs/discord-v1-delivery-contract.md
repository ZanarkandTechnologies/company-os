---
title: Discord v1 delivery contract
status: proposed
owner: Company OS
updated_at: 2026-09-03
refs:
  - ../apps/installer/schemas/workspace.py
  - ../apps/installer/docs/sinks.md
  - ../automations/daily-operating-update.md
  - ../automations/weekly-operating-review.md
---

# Discord v1 delivery contract

Discord v1 is a controlled outbound owner-delivery channel. It is not an
interactive chat agent, a source of company evidence, or an employee messaging
route. This document records the target capability. The connector is now
source-available, but an exact route and a confirmed test receipt are still
required before Discord can deliver automatically.

## Intended scope

- Deliver an `owner report` and `owner alert` only to one reviewed private
  Discord text channel in one reviewed guild.
- Keep generated Project Memory, reports, drafts, and receipts canonical in
  the private Hermes workspace.
- Allow draft-only mode without a Discord API call.
- Allow automatic sending only after one bounded connection test reaches the
  exact configured channel and the named owner confirms receipt.

## Routing and authority

The private Hermes profile will hold the bot token, guild ID, channel ID, and
redacted connection receipt. The reviewed workspace will name only the business
recipient and selected behavior. It must never contain a token, Discord invite,
webhook URL, guild ID, or channel ID.

The connector must resolve the channel, require that it belongs to the reviewed
guild, and retain a hash of that exact target in its receipt. Any change to the
app, named recipient, behavior, guild, or channel invalidates the receipt.
There is no fallback to a DM, another channel, another guild, or another app.

## Safety boundary

- The bot receives only View Channel, Send Messages, and Read Message History;
  it never receives Administrator, Manage Messages, or broad member-management
  permissions.
- The bot must not send `@everyone`, `@here`, user mentions, or role mentions.
- Discord v1 does not read ordinary chat messages, use Message Content intent,
  accept commands, or create/modify company records.
- Each report chunk is at most 2,000 characters and has a stable delivery token.
  A retry reads the exact approved channel and sends only chunks absent from the
  receipt and message history.
- Provider failure leaves the local artifact intact and records `blocked` or
  `failed`; it never chooses a substitute destination.

## Activation gates

Before Discord can deliver automatically, Company OS must validate the
profile-only credential and exact target, record an explicit owner connection
test, validate the resulting receipt, and run an opt-in live acceptance test.
Inbound slash commands are a separate, future capability.
