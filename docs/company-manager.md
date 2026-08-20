---
title: "File-first company-manager API"
status: active
owner: HermesCorp
ticket: TASK-0003
---

# File-first company-manager API

`scripts/company-manager.mjs` is the deterministic local POC API used by the
dashboard and CLI. `tickets/TASK-XXXX/` is the only task record; employee
policy, mock Drive references, reports, and templates are supporting evidence.

```text
inspectBoard({ workspaceRoot }) -> board
scanMeeting({ workspaceRoot, write }) -> createdTicketIds
runPulse({ workspaceRoot, now, maxWorkers?, write }) -> local worker dispatches + chases + escalations + cooldowns
dispatchEligibleWorkers({ workspaceRoot, now, maxWorkers?, write }) -> local worker dispatches
previewHumanRequest({ workspaceRoot, ticketId, requirementId, now, write }) -> ticket-local telegram_delivery_draft
recordHumanResponse({ workspaceRoot, ticketId, requirementId, employeeId, text, now, write }) -> resolved requirement + readiness
recordReply({ workspaceRoot, ticketId, employeeId, text, write }) -> ticket delta
publishArtifact({ workspaceRoot, ticketId, write }) -> Drive mock + review wait
reviewArtifact({ workspaceRoot, ticketId, reviewerId, decision, write }) -> done | blocked
seedDemo({ workspaceRoot, write }) -> deterministic fake policy/evidence + tickets
generateWeeklyReport({ workspaceRoot, now, write }) -> derived markdown
dashboardState({ workspaceRoot, now? }) -> serializable dashboard state
runDashboardAction({ workspaceRoot, action, enabled: true, ... }) -> result + state
setEmployeeRoutePolicy({ workspaceRoot, employeeId, enabled, write }) -> fake route policy only
readTicketProgressEvents({ workspaceRoot }) -> immutable canonical ticket events
appendDeliveryReceipt({ workspaceRoot, ticketId, deliveryId, ... }) -> owning progress.md receipt
deliverCompanyChases({ workspaceRoot, send?, now? }) -> dry-run | sent | failed | rejected
```

`write: false` is a preview for every manager mutation. The POC reads only
`drive-mock/howie-ai-shared/`; a `binary_local_edit` source has a local-edit
MIME type and no native Workspace format, while a published artifact is
`native_workspace` with an explicit Workspace MIME type. No manager function
sends a message, accesses live Drive, starts cron, or creates a Kanban card.
`scripts/deliver-company-chases.mjs` is the sole sender: it defaults to a
local dry run and invokes `hermes -p howie-ai send` only with both `--send`
and `HOWIE_POC_ENABLE_SEND=1`. It reads drafts and writes receipts only in
canonical ticket progress files; it has no outbox folder or second state
machine.

## Isolated filesystem evals

The dashboard’s **Evals** tab is a proof viewer, not an operating surface.
`POST /api/evals/run` materializes each frozen scenario in its own temporary
workspace: it seeds the mock Drive and private employee directory, loads the
meeting summary, runs the local transitions, then records a machine-readable
trace plus a replayable file proof under `workspaces/howie-ai/eval-runs/`.
`GET /api/evals/latest` reads that evidence. The temporary scenario workspace
is removed after each probe, and the normal company tickets are untouched.

```text
runCompanyManagerEvals() -> trace[] + filesystem.{meeting_delta, workflow_delta, final_files[]} + checks[]
```

Each final file carries a SHA-256 and each canonical ticket/progress/artifact
file carries a bounded content preview. The two deltas show what the meeting
created and what the later workflow created, modified, or deleted. The trace
names fixture setup, meeting input, local human responses, worker dispatch,
review, follow-up, and escalation. It is intentionally labelled as recorded
simulator activity rather than an agent chat or live service call.

For dashboard clicks, `runDashboardAction` requires `enabled: true` as the
execution gate. Its `toggle_employee_access` action separately takes
`routeEnabled: boolean`, changing only the fake private roster's route gate.

## Dependency projection (TASK-0002)

Every new fixture ticket declares `requirements` and mock skill `input_ids` /
`outputs` in `ticket.md`. A requirement is either a `human_input` with a
`telegram_delivery` question and requirement-local `follow_up` state, or a
`skill_output` naming an upstream
`ticket_id`, `skill_id`, and `output_id`. `validateDependencyGraph(tickets)`
rejects unknown producers, unknown outputs, and cycles before a writer changes
files.

`dashboardState().board.tasks[*]` preserves the existing fields and adds:

```text
requirements: [{ id, type, description, state, resolution,
  human?: { employeeId, channel, question },
  followUp?: { employeeId, lastAt, nextAt, attempts, deliveryId, status, escalation },
  upstream?: { ticketId, skillId, outputId } }]
blockedBy: [{ requirementId, type, description, ...human or upstream reference }]
unblocks: [{ ticketId, requirementId, skillId, outputId }]
skillOutputs: [{ skillId, outputId, description, approved, approvedAt }]
readiness: { state, unresolvedRequirementIds, eligibleSkillIds }
eligibleHumanRequest: null | { requirementId, employeeId, channel, question, dueAt, due }
outstandingPeople: [{ requirementId, description, employeeId, followUp }]
pendingDeliveries: [{ at, ticketId, requirementId, employeeId, deliveryId, status }]
```

`runPulse` first starts at most two dependency-ready mock skills in stable
ticket order, then writes a ticket-local `telegram_delivery_draft` only when the
named human requirement is due, dependency-eligible, route-enabled, and
inside cooldown policy. A worker transition writes `mock_worker_dispatched`
and `mock_skill_draft_ready`; it stages a local draft and never starts a real
process. `runDashboardAction({ action: "preview_human_request", ... })`
records only the local-draft half of this loop. Neither path sends Telegram.
Development UI may call
`runDashboardAction({ action: "simulate_human_response", ticketId,
requirementId, employeeId, text, now, enabled: true })`; the bounded local
reply resolves only that human requirement. The next pulse starts its skill
only after all declared inputs are resolved. Approval automatically records
resolution of matching downstream output requirements; it does not auto-run
their skills.

Each unresolved human requirement owns its own `follow_up` object:
`employee_id`, `last_at`, `next_at`, `attempts`, `cooldown_minutes`,
`delivery_id`, and optional escalation. Board `nextChaseAt` is the earliest
unresolved requirement value; it is never written at ticket level. Employee
global cooldown is derived from the newest matching delivery event in active
ticket progress and may defer a draft without changing another requirement's
schedule. Every draft, inbound reply, escalation, dry run, sent receipt, and
failed receipt includes both `requirement_id` and `employee_id`.

`dashboardState()` also supplies sanitized `deliveryEvents` and
`deliveryTimeline`. They contain IDs, timestamps, action status, and receipt
reason only—never a Telegram target. The private employee directory validates
a numeric Telegram chat ID, inbound/outbound permission, explicit test opt-in, timezone,
global/requirement cooldowns, route state, and mock Drive scopes. It remains
runtime-only and is not a task store.

If a Drive-backed reply cannot find its expected scoped mock file, the ticket
stays blocked and writes a `telegram_delivery_draft` with
`action: request_scoped_source_refresh`; it never treats absence as proof. Two
overdue requirement-local follow-ups record one `ticket_escalated` event for
the local `howie-ai` manager. Both are local ticket records, never sends or
new queues.
