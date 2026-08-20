---
ticket_id: TASK-0003
approval: approved
compiled_from_ticket_updated_at: 2026-08-12T10:15:00Z
---

# Native Goal Prompt

```text
/goal Run the following files as one Goal Packet.
Files:
- tickets/TASK-0003/ticket.md
- tickets/TASK-0003/program.md
- tickets/TASK-0003/progress.md
- ARCHITECTURE.md
- HARNESS.md
- docs/company-manager.md
- profiles/howie-ai/config.template.yaml
- profiles/howie-ai/profile.manifest.json
- profiles/howie-ai/SOUL.md
- profiles/howie-ai/skills/company-ops-manager/SKILL.md
- profiles/howie-ai/private-roster.example.json
- scripts/sync-howie-ai-profile.mjs
- scripts/company-manager.mjs
- scripts/run-company-manager-evals.mjs
- scripts/deliver-company-chases.mjs
- scripts/serve-dashboard.mjs
- dashboard/index.html
- package.json
- tests/company-manager.test.mjs
- tests/company-delivery.test.mjs
- tests/dashboard.test.mjs
- .farplane/evals/run_evals.py
- .farplane/evals/tasks/harness_tasks.json

Task: Complete only TASK-0003 Scope and Done / Proof. Build an honest local
development proof using the same `howie-ai` source profile, native filesystem
tickets in a dedicated test workspace, Kenji's allowlisted WhatsApp self-chat,
a private employee directory, a controlled `hermes send` worker, and Google's
official Drive MCP under a dedicated fake-data identity. Do not touch customer
data, customer VPS infrastructure, any non-test recipient, or a Drive location
outside the approved root. Do not treat workspace discipline or a tool allowlist
as a filesystem or multi-user authorization boundary.

Outbound boundary: the delivery worker is the sole source of `hermes send`.
It reads pending delivery drafts from canonical ticket progress, resolves an
employee ID through the private directory, and calls Hermes only when both
`--send` and `HOWIE_POC_ENABLE_SEND=1` are present. Default is dry-run. It
must record a terminal receipt and fail closed for a replay, cooldown, disabled
route, unknown employee, or invalid target. A normal self-chat response remains
the gateway's ordinary conversational reply. Retire the legacy manager-outbox
route; do not add cron or bulk delivery.

Tool boundary: configure only `googledrive` as an MCP. WhatsApp must expose
exactly `file`, `skills`, and `mcp-googledrive`; never enable `terminal`,
`web`, `browser`, `cronjob`, `delegation`, `messaging`, `kanban`, or another
MCP toolset to make the proof pass. File access is allowed only for the
dedicated test workspace by operating convention and skill instruction, not
because Hermes enforces a path sandbox. Test that source contract before any
interactive setup.

State boundary: do not preserve the current ticket-global mutable `chase`
object. Store follow-up schedule and escalation state on each unresolved human
requirement, and append every attempt/reply/escalation to the owning
`progress.md` with both requirement and employee IDs. The board’s next-chase
value must be derived so multiple people blocking one ticket cannot overwrite
one another. Derive any global employee cooldown from the newest matching
progress event across active tickets; it may defer a request but must not
rewrite the requirement-local schedule.

Approval: approved. Execute source-safe work. Stop and request Kenji's hands-on action at
the OAuth client/consent, model credential, Drive login, and WhatsApp QR gates.
Never write secrets or pairing/token data to the repository.

Logging: Read program.md first, then full ticket and only the latest 80 lines
of progress.md. Load any other source only for a named gap. Append the required
compact receipt after each turn.

Metric: Follow the hybrid provider. Three deterministic filesystem scenarios
prove ticket/delivery policy with created/modified/deleted deltas, hashes, and
bounded content snapshots; an actual pair of WhatsApp self-chat messages plus
official Drive MCP calls prove the real development integration. Keep local
simulation and live evidence visibly distinct in dashboard, trace, and demo.
The deterministic runner must consume only the three existing harness task IDs.
The
old `deliver:manager` and `deliver:outbox` commands, their workers, and their
tests must be absent; the new delivery command operates only from canonical
ticket/progress state.

After each turn: observe -> choose_next(objective, evidence, eligible_moves,
remaining_budget) -> execute | diagnose | report_now | request_feedback | stop
-> act -> verify -> write_back.

Context gate: ticket + program + latest 80 progress lines; target 300, hard
400. Drift reviewer: after the ticket-file/delivery contract and before final review.
Final checkpoint: source/config checks -> deterministic filesystem evals ->
Drive MCP smoke -> WhatsApp self-chat smoke -> browser/visual proof -> redacted demo ->
independent completion review -> ticket/progress writeback. Final handoff must
name exactly what was proven and what remains a production concern.
```
