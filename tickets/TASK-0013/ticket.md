---
template_id: ticket-template
template_version: "0.2.6"
ticket_id: TASK-0013
title: Onboard the Notion webhook from inside Hermes
status: ready_for_operator_test
created_at: 2026-08-20T15:00:00+08:00
updated_at: 2026-08-20T15:00:00+08:00
claimed_by: codex-root
depends_on: [TASK-0009, TASK-0010]
source_refs:
  - https://ngrok.com/docs/agent
  - https://ngrok.com/docs/agent/config/v3
  - https://ngrok.com/download/linux
  - https://docs.doppler.com/docs/setting-secrets
---

# TASK-0013: Onboard the Notion webhook from inside Hermes

## Summary

Ship a root Company OS skill, synchronized into a Hermes profile distribution,
that turns an already-running Hermes profile into a live
Notion comment webhook through ngrok. The skill owns the conversational human
gates while one deterministic, resumable CLI owns installation, Doppler
configuration, tunnel lifecycle, verification state, table discovery, workspace
lockdown, and live-reply proof.

## Scope

- **In:** root-owned reusable skill, profile distribution copy, ngrok-only ingress, browser login handoff,
  Doppler-scoped configuration, automatic data-source discovery, one live
  comment/reply proof, tests, eval cases, and a redacted status receipt.
- **Out:** installing Hermes, provisioning a VPS, configuring Caddy/Nginx/
  Traefik, DNS, page-property writes, or accepting secrets in chat.
- **Invariant:** Notion comment replies are always enabled; page-property writes
  remain disabled by default; long-lived account credentials never enter chat,
  logs, or process arguments. Only the dedicated verification phase may surface
  Notion's webhook verification token for pasting into Notion.

## Delta

> **Before:** activation requires an operator to understand proxy, Doppler,
> systemd, ngrok, workspace, and webhook-verification commands.
>
> **After:** Hermes asks for the Notion root page and mention, opens the required
> login pages, executes deterministic phases, and stops only for browser login,
> Notion verification, and one test comment.
>
> **Example:** “Set up Notion using this root page” returns a permanent ngrok
> webhook URL and finishes only after a reply is recorded in Notion.

## Done / Proof

- [x] Installed Kamdar profile discovers the onboarding skill.
- [x] CLI dry-run and unit tests prove ngrok-only, secret-safe, idempotent phases.
- [x] Comment replies cannot be disabled through onboarding configuration.
- [x] Connector persists a successful reply receipt for end-to-end readiness.
- [x] Skill structure, eval JSON, focused tests, full tests, and review pass.

## State

- **Current:** implementation and local installation complete; independent QA
  and re-review pass.
- **Next:** invoke the skill from Hermes on the Linux company VPS and preserve
  its final live `status` receipt.
