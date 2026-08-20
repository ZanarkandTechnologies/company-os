# Howie AI company workspace

This workspace is the single operating surface for Manager. It is a dedicated
company-pilot development environment, not a filesystem sandbox or an access
boundary. Use only the paths and transitions below.

## Source of truth

```text
meetings/MEETING-YYYY-MM-DD/    # received transcript, extraction receipt
tickets/TASK-XXXX/ticket.md     # current task state and dependency contract
tickets/TASK-XXXX/progress.md   # append-only event history and follow-ups
tickets/TASK-XXXX/artifacts/    # local drafts plus Drive publication references
tickets/archive/TASK-XXXX/      # approved, completed work
people/employees.private.json   # private role/routing policy; directory skill only
shared-drive/                   # local Drive mirror for isolated proof only
reports/daily/ reports/weekly/  # derived summaries; never a second task system
```

`ticket.md` is the current source of truth. `progress.md` is append-only.
Every ticket has one canonical `TASK-XXXX` ID. Do not create an inbox, outbox,
Kanban, separate to-do list, or ticket-global chase field.

## Meeting intake

When an owner uploads a meeting transcript, save/read it as
`meetings/<meeting-id>/transcript.md`. Extract decisions, deliverables, due
dates, owner, reviewer, required inputs, and dependencies. Create one ticket
per commitment, then start every task whose declared inputs are already
available. Record `meeting_received` and `meeting_scanned` events.

## Reply intake

For a reply to a Manager chase, identify the exact requirement by the platform
reply message ID stored on its delivery receipt. If it is not a reply, require
an explicit `TASK-XXXX` plus the requested decision; never guess. Then:

1. append `human_reply_received` with `requirement_id`, `employee_id`, text,
   time, and safe platform message reference to that ticket's `progress.md`;
2. resolve only that requirement and clear only its own follow-up schedule;
3. re-evaluate dependencies and start any newly eligible skill in the same
   turn; and
4. reply with what changed, what work began, and what happens next.

The private directory is the sole authority for employee role routing. The
ticket and progress log never contain phone numbers, chat IDs, OAuth values, or
route-policy flags.

## Pulse

`pulse(now) -> inspected tickets + started work + per-requirement follow-ups + receipt`

On a manual or scheduled pulse: inspect active tickets; start all eligible
skills; draft every due requirement-level chase that is past `next_at`; escalate
only past-due requirements after the configured bounded attempt threshold; and
append a short `pulse_receipt` summary. Multiple people on one ticket retain
independent `(ticket_id, requirement_id, employee_id)` histories.

## Status and artifact discipline

- `blocked`: a named input, decision, review, or approved upstream output is
  missing. Record the next permitted chase.
- `in_progress`: all inputs are available and the named skill is drafting.
- `awaiting_review`: a named reviewer has a reviewable artifact.
- `done`: explicit review approval exists; archive the ticket.

Artifact skills write only to the owning `artifacts/` directory. `ticket.md`
records artifact state, reviewer, dependencies, and Drive provenance. A Drive
example is style only; source evidence is the only factual basis. The filtered
Drive MCP may search/read/inspect metadata/create a new file inside the
approved company-pilot root. It never changes an existing file or permissions.

## Hermes memories

`MEMORY.md`: compact, stable environment conventions, recurring cadence, and
lessons. `USER.md`: owner preferences, timezone, desired update style, and
escalation preference. Neither file stores ticket state, meeting contents,
private contact data, raw messages, or Drive content. Tickets and progress
remain canonical across sessions.

## Schedules

Keep schedules paused until the manual acceptance run passes. Once enabled,
use: weekday hourly pulse (08:00–18:00 local), daily digest at 18:00, and a
Friday weekly operating report. A schedule only reads/writes this workspace and
may prepare a follow-up; external delivery retains its separate explicit gate.
