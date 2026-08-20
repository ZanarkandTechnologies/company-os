---
template_id: ticket-template
template_version: "0.2.6"
ticket_id: TASK-0009
title: Package Kamdar AI for VPS deployment
status: ready_for_operator_test
created_at: 2026-08-19T16:15:00+08:00
updated_at: 2026-08-19T17:40:00+08:00
claimed_by: codex-root
depends_on: [TASK-0006]
source_refs:
  - https://hermes-agent.nousresearch.com/docs/reference/profile-commands
  - https://hermes-agent.nousresearch.com/docs/getting-started/quickstart
  - https://developers.notion.com/reference/webhooks
  - https://docs.doppler.com/docs/service-tokens
  - https://caddyserver.com/docs/install
---

# TASK-0009: Package Kamdar AI for VPS deployment

## Summary

Package the proven Hermes-native Notion connector as a standalone Hermes
profile distribution and add an idempotent Debian/Ubuntu VPS bootstrap path.
The installed gateway runs under systemd, reads secrets through a scoped
Doppler service token, binds its Notion listener to loopback, and exposes only
the health and webhook paths through Caddy.

## Scope

- **In:** versioned profile distribution, source-owned Notion plugin, VPS
  bootstrap, systemd/Caddy templates, redacted readiness checks, local install
  proof, and operator runbook.
- **Out:** provisioning a VPS or domain, pushing a private Git repository,
  generating live production credentials, changing DNS, or registering the
  final Notion subscription.
- **Invariant:** no Notion, model-provider, Doppler, or webhook verification
  secret may be committed or printed by verification commands.

## Delta

> **Before:** Kamdar's working profile and Notion plugin exist only in local
> Hermes state and cannot be installed reproducibly on another machine.
>
> **After:** a standalone profile distribution can be installed locally or
> from a private Git URL, then bootstrapped on a VPS behind Caddy and Doppler.
>
> **Example:** a fresh Ubuntu VPS installs the distribution, reads a scoped
> Doppler service token, starts `kamdar-hermes.service`, and serves
> `/notion/health` before the operator registers the Notion webhook.

## Done / Proof

- [x] Distribution installs into an isolated Hermes home without credentials.
- [x] Installed profile discovers `notion-platform` and `notion_connector`.
- [x] Deployment scripts pass syntax/static safety checks.
- [x] Local gateway health check passes with Doppler-injected development
      credentials.
- [x] Independent QA and implementation review accept the package or name the
      exact blocker.

## State

- **Current:** package is ready for operator testing; QA and implementation
  review both passed with no blockers.
- **Next:** publish or copy the package to Kamdar's VPS, run the bootstrap with
  the permanent hostname and scoped Doppler service token, then complete the
  Notion verification handshake.

## Links

- Local proof: `artifacts/qa.md`
- Independent QA: `artifacts/qa-review.md`
- Implementation/security review: `artifacts/review.md`
