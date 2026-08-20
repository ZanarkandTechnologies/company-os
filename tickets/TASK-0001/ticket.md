---
ticket_id: TASK-0001
title: File-first Howie company manager proof simulator
status: completed
created_at: 2026-08-10T12:00:00Z
updated_at: 2026-08-10T17:23:51Z
depends_on: []
---

# TASK-0001: File-first Howie company manager proof simulator

## Summary

Build a local, deterministic proof simulator for the company-manager loop:
weekly meeting notes create canonical filesystem tickets; a pulse chases
blocked dependencies according to employee policy; staff replies and scoped
Drive artifacts update the board; completion and weekly reporting are visible
in an operator dashboard. No real WhatsApp pairing, Drive OAuth, gateway,
cron, or external message delivery is part of this ticket.

## Scope

- In: filesystem tickets, private employee directory template, Drive mock,
  mocked artifact skills/templates, deterministic meeting scan/pulse/reply/
  artifact/review/report commands, Gantt dashboard, admin access mock, unit
  and browser proof, an MP4 demo.
- Out: live Google Drive credentials, real Drive permissions, real WhatsApp
  sends, unrestricted file search, multi-workspace employee isolation.
- Constraint: tickets are the sole task record. No separate task JSON list,
  inbox folder, or outbox folder. A ticket-local progress record may preserve
  a pending/sent/failed chase so retries are idempotent.

## Delta

> **Before:** A JSON manager ledger projected tasks and delivery drafts; the
> work card was not the canonical filesystem object.
>
> **After:** `workspaces/howie-ai/tickets/TASK-XXXX/` owns the task description,
> deadline, required inputs, review request, chase history, Drive artifact
> reference, and append-only progress. A mock scenario proves the manager loop.
>
> **Example:** Scanning the weekly meeting note creates four blocked tasks;
> a pulse politely chases Kenji for the geo input; Kenji's reply and scoped mock
> Drive file unblocks it; its template artifact is published to mock Drive,
> reviewed, archived, and reflected in the weekly report and Gantt.

## Contract

```text
scan_meeting(workspace, meeting_note) -> created_ticket_ids
pulse(workspace, now) -> chase_events + escalation_events + stale_ticket_ids
record_reply(workspace, ticket_id, employee_id, reply) -> ticket_delta
sync_artifact(workspace, ticket_id, artifact) -> drive_reference + review_wait
review_artifact(workspace, ticket_id, reviewer_id, decision) -> done | blocked
```

The ticket frontmatter contains the bounded current state: canonical ID, title,
description, workstream, owner/reviewer IDs, dates, status, blocking inputs,
artifact references, review state, and per-ticket chase fields. `progress.md`
contains immutable meeting, chase, reply, Drive, skill, and review events.

Employee data holds contact policy only: canonical employee ID, display name,
timezone, allowed contact route, global cooldown, and allowed mock Drive scope.
It does not become the task system. The POC Drive search reads only mock files
shared with `howie-ai`; the production direction is an isolated Howie agent
identity granted an explicit project Shared Drive folder, not Howie's personal
credentials.

Statuses: `blocked` means an identified dependency/input/review is outstanding
and may be chased; `in_progress` means the mock skill has an artifact draft;
`awaiting_review` means the artifact is in Drive and needs an explicit reviewer;
`done` is archived after approved review. A stale task is a blocked task whose
per-ticket next chase is due; it is not a separately inferred status.

## Change Plan

### Change 1: Canonical simulator

```yaml
files:
  read: [HARNESS.md, profiles/howie-ai/SOUL.md, fixtures/]
  edit: [scripts/company-manager.mjs, fixtures/company-manager/, skills/mock-*, tests/company-manager.test.mjs]
operation: Replace the JSON-board POC path with file-first ticket creation, pulse, reply, artifact, review, report, and Drive-mock behavior.
proof: deterministic CLI scenario plus unit/integration tests.
failure: invalid ticket or directory data fails closed without an external side effect.
```

### Change 2: Operator dashboard

```yaml
files:
  read: [dashboard/index.html, scripts/serve-dashboard.mjs]
  edit: [dashboard/index.html, scripts/serve-dashboard.mjs, tests/dashboard.test.mjs]
operation: Render task cards, Gantt, weekly report, Drive references, pulse activity, and mock employee access controls from the simulator API.
proof: browser screenshot, DOM assertions, interaction test, no console/page errors.
failure: dashboard errors must not mutate board state; access controls must state that they are POC route policy, not real Drive ACLs.
```

### Change 3: Demo proof

```yaml
files:
  read: [tests/, dashboard/, fixtures/company-manager/]
  edit: [tickets/TASK-0001/artifacts/qa/, tickets/TASK-0001/artifacts/demo/]
operation: Capture the full mock scenario in tests and a concise 45-90 second MP4.
proof: passing test output, screenshots, ffprobe report, reviewer receipt.
failure: no MP4 pass claim without passing tests, media probe, and independent review.
```

## Key dashboard states

1. Empty/ready workspace before the meeting scan.
2. Four newly created blocked tasks and a four-lane timeline/Gantt.
3. Pulse results with a per-ticket chase and the next permitted reminder.
4. Reply + Drive evidence moves geo report from blocked to in-progress, then
   to awaiting review and done.
5. Weekly report and employee access settings.

## Done

- [x] Mock meeting note creates fundraising deck, geo report, Excel model, and
  weekly report tasks with canonical IDs, owners, reviewer, timeline, and skill
  dependencies.
- [x] Pulse uses both ticket-local and employee-global cooldown fields.
- [x] Reply, scoped Drive search, artifact generation, Drive publication, and
  review update the ticket and dashboard correctly.
- [x] Weekly report/Gantt and access-admin mock are visible.
- [x] Tests, browser evidence, demo MP4, and independent review pass.

## QA Strategy

```yaml
proof_weight: hybrid
checks:
  - unit/integration test: meeting -> ticket -> pulse -> reply -> artifact -> review -> archive -> weekly report
  - negative test: unavailable Drive file and cooldown prevent a false state transition/send
  - browser: dashboard states, timeline, mock access control, console/page errors
  - visual QA: named screenshots at desktop and narrow width
  - agent QA: tester flow and separate evidence-review lane
  - demo: ffprobe + frame inspection + independent review
delegated_lanes: [manager-engine, dashboard, reviewer]
evidence_paths: [tickets/TASK-0001/artifacts/qa/, tickets/TASK-0001/artifacts/demo/]
final_checkpoint: reviewer
residual_risk: Live WhatsApp/Drive authorization remains deliberately out of scope.
```

## State

- Current: completed local proof POC
- Next: only a separately approved live-adapter/identity phase
- Blockers: none within the mock-only ticket boundary

## Links

- Independent QA result: `tickets/TASK-0001/artifacts/qa/2026-08-10_171003_independent-tester/result.json`
- Independent QA report: `tickets/TASK-0001/artifacts/qa/2026-08-10_171003_independent-tester/report.md`
- Independent tester receipt: `tickets/TASK-0001/artifacts/qa/independent-tester-report.md`
- Best independent evidence: `tickets/TASK-0001/artifacts/qa/2026-08-10_171003_independent-tester/screens/safari-final-dashboard-activated.png`
- Independent QA verdict: `revise` after rerun; earlier unknown `/api/*` route blocker resolved.
- Browser / narrow proof: `tickets/TASK-0001/artifacts/demo/2026-08-10-file-first-poc/browser/browser-proof.json`
- Visual QA: `tickets/TASK-0001/artifacts/qa/visual-qa.md`
- Dashboard redesign brief: `tickets/TASK-0001/artifacts/dashboard-redesign/design-brief.md`
- Dashboard redesign proof + QA: `tickets/TASK-0001/artifacts/dashboard-redesign/browser/browser-proof.json`, `tickets/TASK-0001/artifacts/dashboard-redesign/visual-qa.md`, `tickets/TASK-0001/artifacts/dashboard-redesign/independent-review.md` (`TAS-A`, pass)
- Demo MP4 + probe: `tickets/TASK-0001/artifacts/demo/2026-08-10-file-first-poc/final.mp4`, `media-probe.json`
- Final independent review: `tickets/TASK-0001/artifacts/demo/2026-08-10-file-first-poc/reviews/independent-review.md` (`TAS-A`, pass)
