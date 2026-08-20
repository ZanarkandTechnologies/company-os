---
template_id: ticket-template
template_version: "0.2.6"
ticket_id: TASK-0006
title: Hermes-native Notion webhook bridge
status: ready_for_operator_test
created_at: 2026-08-19T12:00:00+08:00
updated_at: 2026-08-19T13:05:00+08:00
claimed_by: codex-root
depends_on: [TASK-0004]
source_refs:
  - https://developers.notion.com/reference/webhooks
  - https://hermes-agent.nousresearch.com/docs/developer-guide/adding-platform-adapters
---

# TASK-0006: Hermes-native Notion webhook bridge

## Summary

Run the Notion webhook receiver as a source-owned `howie-ai` Hermes platform
plugin, reusing Hermes gateway lifecycle and Farplane's bounded, redacted
Notion transport principles. No standalone daemon, queue, database, or Node
service is introduced.

## Scope

- **In:** capture Notion's one-time verification token, verify subsequent
  `X-Notion-Signature` HMACs over raw bodies, persist bounded delivery IDs,
  dispatch normalized events to Hermes, and expose scoped page read/update
  tools with write opt-in and readback.
- **Out:** public tunnel provisioning, creating the Notion integration,
  registering the webhook in Notion, page-content crawling, and autonomous
  database schema changes.

## Delta

> **Before:** Hermes's generic webhook adapter does not recognize Notion's
> signature header or verification-token handshake, so a route script cannot
> safely receive Notion events.
>
> **After:** the `howie-ai` gateway hosts a Notion-aware endpoint itself and
> handles the handshake before normal Hermes authorization and agent dispatch.
>
> **Example:** Notion posts `verification_token`; the plugin stores it with
> owner-only permissions. Later signed `page.properties_updated` events are
> accepted once, while unsigned, invalid, and duplicate events are rejected or
> acknowledged without running the agent twice.

## Done / Proof

- [x] Protocol tests cover token capture, valid/invalid signatures, duplicate
  events, bounded state, and write gating.
- [x] Profile sync installs the enabled platform plugin without touching
  private runtime state.
- [x] Hermes can discover the plugin from the live `howie-ai` profile.
- [x] Post-apply verification passes against the live `howie-ai` profile.
- [x] Independent implementation review passes at TAS-A with no blocking
  findings.
- [x] Live Notion registration remains an explicit operator activation step if
  credentials or a public HTTPS URL are unavailable.

## State

- **Current:** source implementation, profile installation, isolated gateway
  proof, and independent TAS-A review are complete. Live activation is
  intentionally waiting on private operator inputs.
- **Next:** provide the private Notion token and HTTPS endpoint, start the live
  gateway, then paste the locally captured verification token into Notion.
