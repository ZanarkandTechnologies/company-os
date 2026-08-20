---
ticket_id: TASK-0003
trigger: active_goal
approval: approved
compiled_from_ticket_updated_at: 2026-08-12T10:15:00Z
generated_prompt: tickets/TASK-0003/goal-prompt.md
---

# Goal Program: Real-integration Howie dev POC

## Objective and mutable surface

Complete only TASK-0003's Scope and Done conditions. Mutable source is limited
to the `howie-ai` source profile, canonical filesystem ticket manager and
delivery-worker code/tests, dashboard proof rendering, ticket-scoped proof
artifacts, and the documentation required by the ticket. Private profile
runtime configuration is mutable only through the documented source sync and
interactive operator-authentication gates.

## Budget and stops

- **Window:** active until the approved POC is test-ready or one of the human
  gates requires Kenji's input; no numeric time or token budget was supplied.
- **Spend:** do not create paid infrastructure or send to a non-test recipient.
  Google OAuth/client consent, model provider credentials, a dedicated fake-data
  Drive identity, and WhatsApp QR pairing are explicit operator gates.
- **Stop complete:** all Done / Proof checks pass, including redacted real
  Drive and WhatsApp smoke evidence plus independent review.
- **Stop blocked:** a Google OAuth client, consent, model credential, QR scan,
  allowlisted test number, or approved test folder is required from Kenji.
- **Stop report:** the packet changes materially, evidence contradicts the
  stated connector path, or the remaining activity needs a product decision.

## Metric / provider

Use a **hybrid** provider: deterministic filesystem tests prove file/delivery
policy behavior; a manually observed self-chat plus official Drive MCP smoke
proves the real connection. Guards: one dedicated fake-data identity/root, a dedicated Howie
test workspace, WhatsApp `file`/`skills`/filtered Drive toolsets only, one
paired phone, and an employee-directory-checked delivery worker. A normal
gateway response to an allowlisted inbound chat is permitted. A proactive chase
is permitted only through the worker's explicit `--send` plus
`HOWIE_POC_ENABLE_SEND=1` gates; no cron or bulk delivery is allowed. The
anti-metric is any claim of enterprise authorization, customer deployment,
broad Drive access, filesystem sandboxing, or uncontrolled autonomous delivery
that the proof cannot support. Follow-up state is scoped
to each unresolved human requirement, with `progress.md` holding immutable
requirement-and-employee events; a ticket/board next-chase field is derived
only and never overwrites another blocker’s schedule. Only the newest
applicable progress event across active tickets may establish a global employee
cooldown; it delays the current request without altering the
requirement-local schedule.

## Decision backbone

`observe -> choose_next(objective, evidence, eligible_moves, remaining_budget) -> execute | diagnose | report_now | request_feedback | stop -> act -> verify -> write_back`

Prefer source-safe and deterministic checks before opening any auth/pairing
path. Never broaden a capability merely to make a demo pass.

## First-load context gate

Initial read is full `ticket.md`, full `program.md`, and at most the latest 80
lines of `progress.md`. Target 300 lines; block and consolidate above 400.
The fixed ownership packet additionally names `package.json`,
`scripts/deliver-company-chases.mjs`, `tests/company-delivery.test.mjs`,
`fixtures/company-manager/people/employees.private.example.json`,
`.farplane/evals/run_evals.py`, and `.farplane/evals/tasks/harness_tasks.json`
for delivery and deterministic-eval changes. Verify the retired `deliver:manager` /
`deliver:outbox` commands and their scripts/tests are absent rather than adding
deleted files to the Goal context. Load `ARCHITECTURE.md`,
`HARNESS.md`, profile files, source, and tests only to resolve a named
integration or proof gap.

## Logging and drift

Append a compact receipt to `progress.md` after each turn:

```yaml
observation:
evidence: []
learning:
decision: execute | diagnose | report_now | request_feedback | stop | blocked
remaining_budget:
next_action:
```

Run `goal-drift-reviewer` after the ticket-file/delivery contract and before completion
review. Regenerate this packet if the connector, scope, data boundary, or proof
policy changes materially.

## Proof route

Run automated profile/file/delivery checks first, then three isolated
deterministic filesystem scenarios using the existing rows and replayable
file-delta, hash, and content snapshots. The
source config must expose WhatsApp to exactly `file`, `skills`, and
`mcp-googledrive`; no terminal, unrelated dynamic MCP toolset, or hidden path
sandbox claim may be added to make an eval pass. Next
perform the official Drive MCP authentication and fake-identity/root smoke
check; then pair WhatsApp in self-chat mode and execute the two-message live
path plus one allowlisted, explicit-gate delivery-worker smoke. Hermes may reply
normally in that same allowed chat; the sender alone may call `hermes send`.
Then capture dashboard/browser
evidence, visual QA, a redacted local demo, and independent review. No proof
artifact may imply that simulated events are real, that real test events are
production, or that the profile is a multi-user authorization boundary.

## Delayed check-in

`mode: not_applicable` — the Goal is an integration proof with immediate
observable outcomes, not a delayed-reward product experiment.
