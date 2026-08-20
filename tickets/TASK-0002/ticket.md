---
ticket_id: TASK-0002
title: Dependency-aware company plan and human-request proof
status: complete
created_at: 2026-08-10T09:48:00Z
updated_at: 2026-08-10T10:45:00Z
goal_packet: true
---

# TASK-0002: Dependency-aware company plan and human-request proof

## Summary

Extend the file-first Howie simulator so a ticket can state both what it needs
and what it produces. The manager derives a dependency DAG from canonical
ticket folders, identifies the next human input worth requesting, and exposes
Timeline, Table and Dependencies views over that same state.

## Scope

- **In:** typed ticket requirements and skill outputs; DAG validation and
  readiness derivation; frozen geo → deck/model → weekly-report fixture;
  ticket-local Telegram-preview requests; development-only reply simulation;
  dependency-aware dashboard views; tests, browser proof, visual QA, reviewer
  receipt and a local demo.
- **Out:** live Telegram transport, chat IDs/tokens, inbound webhooks, Google
  Drive/OAuth, cron, generic PRD parsing, graph editing and user ACLs.
- **Constraint:** only `ticket.md` and ticket-local `progress.md` are mutable
  task state. Views and reports are projections, never a second board.

## Delta

> **Before:** a ticket lists blockers and a mock skill template but cannot say
> whether another ticket’s output satisfies an input.
>
> **After:** each requirement has a typed source and resolution record; skills
> declare outputs; the manager derives blocked-by/unblocks and previews the
> next Telegram request without sending it.
>
> **Example:** `TASK-1002` names `TASK-1001.geo-report` as its input. When the
> geo artifact is approved, the deck’s upstream requirement resolves; only its
> remaining Kenji direction request can block it.

## Contract

```text
validate_dependency_graph(tickets) -> acyclic producer/output registry | error
derive_readiness(tickets) -> requirements + blocked_by + unblocks + eligible_skills
preview_human_request(ticket, requirement, channel) -> progress_event
record_human_response(ticket, requirement, response) -> resolved requirement + readiness_delta
dashboard_projection(tickets, view) -> timeline | table | dependencies
```

## Change Plan

### Change 1: Canonical dependency model

Extend the meeting fixture and `company-manager` validation/projection so
requirements can name a human response or a producer ticket/skill output.
Reject cycles, unknown producers and outputs; derive readiness from the same
filesystem ticket folders; persist only bounded progress events.

### Change 2: Human-request boundary

Add a safe `telegram_preview` request record and a development-only simulated
reply action. The simulation is an explicit test entrypoint—not a product
control and not a delivery adapter.

### Change 3: One state, three views

Replace scenario-toolbar actions with a view selector plus a clearly labelled
developer simulation panel. Implement Timeline, Table and Dependencies views
from one dashboard payload; show upstream inputs and downstream impacts on the
ticket inspector.

### Change 4: Proof harness

Cover graph validation, no-premature-work rules, request preview/reply, all
views, narrow layout, no console errors and no external side effect.

## Done

- [x] Tickets declare human and skill-output requirements plus skill outputs.
- [x] The frozen scenario shows geo report unblocking deck/model and all three
  inputs unblocking the weekly report.
- [x] Cycle/unknown-producer/unknown-output cases fail before a write.
- [x] A pulse records one Telegram preview only when a human requirement is
  eligible; the development simulation records a reply and updates readiness.
- [x] Timeline, Table and Dependencies views use the same ticket projection.
- [x] Dashboard makes developer simulation distinct from human-facing request
  intent and never claims a real send.
- [x] Tests, browser/visual QA, independent review and a local demo prove the
  full frozen path.

## QA Strategy

```yaml
proof_weight: hybrid
critical_path:
  - frozen meeting -> dependency graph -> due human request preview
  - simulated Kenji reply -> geo skill -> approved output
  - downstream readiness -> dependency/table/timeline views -> weekly report
checks:
  - unit/integration: DAG validation, output resolution, cooldown/request policy, no premature skill transition
  - negative: cycle, unknown output, unknown employee, disabled route and inaccessible input fail closed
  - browser: view changes use one state, dependency labels are visible, narrow viewport has no page overflow, console/page errors are zero
  - visual_qa: desktop dependency view and narrow table/timeline evidence
  - reviewer: independent implementation and completion review
  - demo: local narrated MP4 only; no external transport claim
residual_risk: real Telegram identity, delivery receipts and Google Workspace authorization remain unproven by design.
```

## State

- **Current:** Complete. The dependency-aware frozen scenario, three-view
  dashboard, local proof video, and independent completion review passed.
- **Next:** any live Telegram, Google Drive authorization, cron, or ACL work
  requires a separate approved adapter ticket.
- **Blockers:** none for this local POC.

## Links

- PRD: `docs/prd.md`
- Existing simulator contract: `HARNESS.md`, `docs/company-manager.md`
- Existing POC: `tickets/TASK-0001/ticket.md`
- Goal Packet review: `tickets/TASK-0002/artifacts/goal-packet-review.md` (`TAS-A`, pass)
- Browser proof: `tickets/TASK-0002/artifacts/browser/browser-proof.json`
- Visual QA: `tickets/TASK-0002/artifacts/browser/visual-qa.md`
- Demo: `tickets/TASK-0002/artifacts/demo/2026-08-10-dependency-proof/final.mp4`
- Completion review: `tickets/TASK-0002/artifacts/completion-review.md` (`TAS-A`, pass)
