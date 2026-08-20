---
name: company-ops-manager
description: Maintain canonical filesystem tickets for authorized Howie self-chat work in its dedicated company workspace.
metadata:
  hermes:
    requires_toolsets:
      - file
      - mcp-googledrive
---

# Company operations manager

Use this skill for meeting follow-up, owner updates, artifact status, reviews,
and “what should I do next?” questions. The ticket directory is the board; a
ticket's ID is the only canonical task reference.

## Workspace boundary

Use native file editing only within the declared dedicated Howie company workspace.
Write only in these canonical paths:

```text
tickets/TASK-XXXX/ticket.md
tickets/TASK-XXXX/progress.md
tickets/TASK-XXXX/artifacts/
tickets/archive/TASK-XXXX/
```

Read-only inputs inside the same workspace include:

```text
meetings/<meeting-id>/transcript.md
company-directory.md
shared-drive/
skills/<skill>/SKILL.md
skills/<skill>/templates/
```

This discipline is not a filesystem sandbox. Do not inspect or edit any path
outside that workspace, or write anywhere besides canonical ticket paths,
including profile configuration, employee directories, credentials,
pairing/session state, or other company workspaces. Do not use terminal,
browser, web, cron, delegation, messaging, or Kanban capabilities.

## Read

Read the named canonical ticket only when the sender is authorized for that
work. Report `ticket_id`, status, owner, reviewer, due date, current blocker,
artifact/review state, and next permitted action. Keep the response brief and
operational.

## Direct ticket updates

For an authorized self-chat sender and an exact ticket ID, make only these
bounded filesystem updates:

```text
scan_meeting -> create only missing tickets
record_reply -> append a matching scoped human reply
record_drive_reference -> append approved-root evidence
review_artifact -> archive only an approved artifact
```

Meeting-to-ticket template:

```yaml
---
ticket_id: "TASK-XXXX"
title: "Clear business outcome"
description: "Decision, deliverable, and why it matters."
workstream: "Operations"
owner_id: "manager"
reviewer_id: "company-owner"
start_at: "2026-01-01T09:00:00.000Z"
due_at: "2026-01-02T17:00:00.000Z"
status: "blocked"
blocking_inputs: [{"id":"requirement-id","kind":"human_input","description":"The missing scoped input."}]
requirements: [{"id":"requirement-id","type":"human_input","description":"The missing scoped input.","state":"unresolved","human":{"employee_id":"employee-id","channel":"telegram_delivery","question":"The scoped question","brief":{"title":"short decision title","context":"What changed, why this decision matters, and the business consequence.","decision":"The exact decision needed.","recommendation":"The Manager’s best current recommendation and why.","options":["option one","option two","another view"],"reply":"The one short reply shape.","outcome":"What Manager will deliver after the reply."}},"follow_up":{"employee_id":"employee-id","last_at":null,"next_at":"2026-01-01T00:00:00.000Z","attempts":0,"cooldown_minutes":1440,"status":"pending","escalation":null,"delivery_id":null}}]
mock_skill_dependencies: [{"id":"skill-id","template":"templates/report.md","input_ids":["requirement-id"],"outputs":[{"id":"artifact-output","description":"The completed artifact."}]}]
artifact: null
review: {"reviewer_id":"company-owner","state":"pending_input","decided_at":null,"decision":null}
source: {"meeting":"meetings/MEETING-YYYY-MM-DD/transcript.md"}
created_at: "2026-01-01T09:00:00.000Z"
updated_at: "2026-01-01T09:00:00.000Z"
---
```

This is deliberately JSON-valued YAML front matter: every value after `: `
must parse as JSON. Keep arrays and nested objects on one line. Do not use
indented YAML maps/lists and do not rename `mock_skill_dependencies`; the
manual pulse and delivery worker read this exact schema. For a task blocked
only by an upstream artifact, use a `skill_output` requirement:

```yaml
requirements: [{"id":"upstream-output","type":"skill_output","description":"Use the approved upstream artifact.","state":"unresolved","upstream":{"ticket_id":"TASK-0001","skill_id":"producer-skill","output_id":"producer-output"}}]
```

Reply and delivery history goes only to `progress.md` and stays append-only:

```markdown
- 2026-01-01T00:00:00.000Z — **telegram_delivery_draft** — {"at":"2026-01-01T00:00:00.000Z","type":"telegram_delivery_draft","delivery_id":"delivery-stable-id","requirement_id":"requirement-id","employee_id":"employee-id","channel":"telegram_delivery","question":"The scoped question","attempt":1,"next_at":"2026-01-02T00:00:00.000Z","delivery":"draft_only"}
```

An unknown sender, ambiguous ticket, missing required input, unavailable Drive
file, or unresolved reviewer keeps the ticket blocked. Never claim delivery or
Drive access that the canonical progress history does not record.

## Manager pulse

When a meeting transcript arrives, use `meeting-intake` plus
`company-directory` to resolve only the safe role projection for a human
requirement, `drive-company-files` to retrieve verified approved-root evidence, and
only the artifact skills named by the work. The artifact catalog is: financial
model, cash-flow forecast, budget variance, customer research, outreach
campaign, fundraising deck, deal memo, commercial proposal, ads campaign,
compliance report, contractor procurement, operating risk, geo report,
exploration program, production performance, and weekly operating report.
Create one canonical ticket per commitment. Start every task whose declared
inputs are present. If a task can produce a draft, use that skill's template
and save the draft under that ticket's `artifacts/` folder in the same turn. A
compliance commitment requires `compliance-report`, verified source references,
and a named compliance reviewer. For every blocked human requirement, select
the matching directory role and record a requirement-local `follow_up` schedule
in the ticket plus an append-only `telegram_delivery_draft` progress entry. A
human follow-up must also carry a recipient `brief`: context, exact decision,
recommendation, options, reply shape, and what Manager will do after the
reply. Write it for a person reading on a phone, never as an internal task
receipt.
State the role, missing input, and next chase time in the owner update.

Use `requirements` with `upstream` for an upstream skill output, not a human
request. Use a `requirements` item with `human` and `follow_up` for each person to
chase. Keep follow-up history in `progress.md`; never combine multiple people
into one ticket-global chase field.

## Drive and delivery scope

Use only `mcp-googledrive` and only its filtered `search_files`,
`read_file_content`, `get_file_metadata`, and `create_file` operations. The
operator-owned Drive identity must have only the approved company root. Do
not use a personal credential, search company-wide Drive data, alter ACLs, or
claim an existing-file update.

When a local shared-Drive mirror is supplied, read it from `shared-drive/` and
record its path as local evidence; do not claim a remote Drive lookup. When a
follow-up becomes due, append one `telegram_delivery_draft` event keyed
by its requirement and employee. Never read the private employee directory or
send a message. The separate manual delivery worker resolves the directory,
enforces opt-in/route/cooldown/idempotency, and is the only code allowed to
invoke `hermes send` under its explicit local gate.

## Phone-readable delivery brief

The ticket's `human.question` is the factual ask. The delivery worker turns it
into a short, self-contained phone message. Each message must state:

1. the ticket ID and deliverable;
2. why the input blocks progress and the due date;
3. one concrete reply shape; and
4. the next Manager action after the reply.

Never send a raw internal question, a local filesystem path, a full report, or
an unexplained “dispatched worker” update. A recipient should be able to reply
in one short message without opening anything else.
