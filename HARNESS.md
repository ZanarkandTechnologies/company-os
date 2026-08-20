---
title: "Howie AI File-First Manager Harness"
status: test_ready
owner: HermesCorp
created_at: 2026-08-10
updated_at: 2026-08-12
source_refs:
  - https://github.com/NousResearch/hermes-agent/security
  - https://developers.google.com/workspace/drive/api/guides/about-files
  - https://developers.google.com/workspace/drive/api/reference/rest/v3/files/update
---

# Howie AI File-First Manager Harness

## Purpose

`howie-ai` is a bounded company-manager profile. It turns a meeting into
canonical filesystem tickets, checks only due blocked work, records a polite
chase under cooldown policy, accepts only scoped artifact evidence, and makes
the result visible in a Gantt/report dashboard.

```text
meeting note -> tickets/TASK-XXXX -> pulse -> recorded chase
  -> reply + scoped Drive input -> artifact + review
  -> archive -> weekly report + dashboard
```

## Canonical state

| Surface | Owner | Purpose |
| --- | --- | --- |
| `workspaces/howie-ai-poc/tickets/TASK-XXXX/` | Runtime | The task card: state, owner/reviewer, dates, inputs, follow-up history, artifact reference, and progress |
| `workspaces/howie-ai-poc/tickets/archive/` | Runtime | Approved completed task folders and their artifacts |
| `workspaces/howie-ai-poc/people/employees.private.json` | Runtime, private | Identity, test route policy, time zone, global cooldown, scoped mock-Drive policy |
| `workspaces/howie-ai-poc/drive-mock/howie-ai-shared/` | Runtime mock | Only files shared with the Howie agent identity in the deterministic proof |
| `workspaces/howie-ai-poc/reports/` | Runtime | Derived weekly report; never a second task list |
| `scripts/company-manager.mjs` | Repository | Single deterministic writer and dashboard API |

There is no company Hermes Kanban board, task JSON list, inbox folder, or
outbox folder in the active POC. Every unresolved human requirement owns its
own writable `follow_up` schedule; `progress.md` carries the immutable events
for its employee, requirement, delivery draft, receipt, and escalation. Board
next-chase and employee cooldown are derived views, not a second queue.

## Runtime contract

```text
scan_meeting(workspace, source) -> tickets_created
pulse(workspace, now) -> dependency-ready local worker starts + due requirement-local delivery drafts + bounded escalations
record_reply(workspace, ticket, employee, text) -> scoped_input | reject
publish_artifact(workspace, ticket) -> drive_reference + awaiting_review
review_artifact(workspace, ticket, reviewer, decision) -> archive | blocked
```

1. The meeting scanner creates only missing canonical IDs and records the
   meeting source in task-local progress.
2. A pulse starts only dependency-ready mock skills in bounded local worker
   slots, then examines due unresolved human requirements. Employee-global and
   requirement-local cooldowns must permit a `whatsapp_delivery_draft`. Two
   overdue follow-ups record one local escalation to `howie-ai`; no notification
   is sent from the manager or dashboard.
3. A reply only unblocks a task when the known owner responds and the required
   mock Drive input is accessible to `howie-ai` in the expected scope.
4. A mock skill template creates a task-local draft. Publication records a
   Drive file reference and moves the ticket to `awaiting_review`.
5. Only the named reviewer can approve; approval moves the whole task directory
   to the archive. Rejection returns it to `blocked` with a new review input.

## Drive rule

Tickets do not synchronize every update to Drive. They retain the Drive file
ID/URL, storage kind, and review state; the shared artifact remains canonical
in Drive. In production, use a dedicated Howie agent credential restricted to
the approved Shared Drive/project root, never Howie's personal credential.
Binary artifacts may be downloaded into a ticket artifact work directory and
updated by Drive file ID. Native Google Docs/Sheets/Slides must be handled as
native Workspace content/API operations, not blindly cloned and re-uploaded.

## Controlled sender and activation boundary

`scripts/deliver-company-chases.mjs` is the only sender route. It reads the
canonical ticket progress events, resolves the private directory, and writes
its receipt beside the owning ticket. It is dry-run by default; an actual
`hermes -p howie-ai send` requires both `--send` and
`HOWIE_POC_ENABLE_SEND=1`. It rejects unknown, disabled, unopted-in, malformed,
duplicate, stale, and cooldown-blocked drafts before invoking Hermes.

The source profile exposes WhatsApp exactly to `file`, `skills`, and the
filtered official `mcp-googledrive`. Native file access is a development
discipline limited to this dedicated workspace, not a sandbox or a production
authorization boundary.

## Safety and non-goals

- The deterministic proof has no live WhatsApp pairing, Google OAuth, Drive
  search, message send, cron, gateway, or real employee permission change.
- A future developer-run live smoke may use one private self-chat, one
  opted-in test recipient, and a dedicated fake-data Drive identity only after
  operator credential/consent and QR gates. It is not customer deployment.
- Dashboard employee settings demonstrate internal route eligibility only; they
  do not claim to change a Google Drive ACL.
- Hermes profiles and toolsets are not an authorization boundary. Production
  multi-user access requires separate persistent workspaces, credentials, and
  a gateway policy as described in [ARCHITECTURE.md](ARCHITECTURE.md).

## Acceptance proof

1. The supplied meeting creates four tickets with ID, timeline, reviewer, input
   dependency, and mock skill template.
2. Only one due Kenji chase is recorded; the remaining tasks observe global
   cooldown.
3. A matching reply plus scoped Drive source moves the geo task through draft,
   publication, review, and archive.
4. The dashboard/Gantt/report read exactly those ticket folders.
5. An unavailable Drive source, unknown employee, unauthorized reviewer, or
   duplicate meeting cannot create a false state transition. A missing source
   records a bounded preview-only expert chase while keeping the ticket blocked.
