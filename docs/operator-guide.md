---
title: Company OS operator guide
status: active
owner: Company OS
created_at: 2026-08-27
updated_at: 2026-08-31
system_id: SYS-0001
refs:
  - prd.md
  - ../automations/daily-operating-update.md
  - ../automations/weekly-operating-review.md
  - ../templates/README.md
  - ../workspace.hermes.md
  - tuning-sop.md
---

# Company OS operator guide

## Purpose

People record work and evidence in Notion. The Company OS uses those records to
prepare follow-ups, weekly reports, Decisions, and SOPs without asking people to
maintain the same information in several places.

The current repository is configured for frozen or isolated evaluation.
Production Notion writes and employee messages remain proposal-only until the
production routes and authority are approved.

## The databases

| Database | What it owns | What it does not own |
| --- | --- | --- |
| **Projects** | Human-operated source records: goal, owner, Department, current plan, and links to related Work. | Private management assessments, accumulated agent memory, or weekly report history. |
| **Work items** | Tasks, Features, Issues, and Meetings. This is where people record progress, evidence, blockers, decisions, completion notes, commitments, and discussion. | Cross-Project precedent or reusable procedures after promotion. |
| **People** | Public/shared identity, role, authority, approved contact channels, and route references. | Employee Memory, management assessments, or inferred permissions. |
| **Reports** | An optional provider copy of approved finalized Project, Department, or Company reports. | Canonical reports, Project Memory, or entity memory. |
| **Decisions / SOPs** | Optional provider views when a long-term-memory destination is explicitly configured. | Canonical memory or automatic publication targets. |
| **Hermes local workspace** | Canonical short-term memory under `weeks/`, long-term entity memory under `memory/`, finalized local reports, and outbound artifacts. | Provider permissions or employee-facing source records. |

Problems do not need a separate database. A material problem becomes an
`Issue` in Work, linked to the affected workflow or SOP step. Its page preserves
the Before baseline, economics or measurement gaps, intervention, and later
After measurement.

```text
Projects + Work + Meetings + People directory
                       |
                       v
+------------------------------------------------+
| Private local workspace                        |
| weeks/<week>/project-memory/ = short-term memory|
| memory/{employees,sops,decisions,issues}/      |
|                              = long-term memory|
| weeks/<week>/reports/         = local reports  |
+----------------------+-------------------------+
                       |
             configured one-way copies
                       v
       private Notion/Drive memory destination
       or management report dashboard
```

## The normal operating loop

```text
EMPLOYEE                     COMPANY OS                    MANAGER
   |                             |                            |
   |-- records progress -------->|                            |
   |                             |-- asks for missing facts ->|
   |<-- receives clear follow-up-|                            |
   |                             |                            |
   |                             |-- prepares weekly view --->|
   |                             |   outcomes, risks, owners   |
   |                             |                            |
   |-- adds late evidence ------>|-- carries open work ------>|
   |                             |   into the next review      |
```

The agent keeps its working notes private. Employees continue using their
normal Work records. Documentation and progress questions return to those exact
records as comments. Managers read the private consolidated view with links
back to the evidence.

The lean Company OS setup connects Projects and Work as read-write sources, keeps
the People directory read-only for stable employee IDs, and leaves both the
artifact-sync and communications tables empty. That stores Project Memory,
Employee/SOP/Decision/Issue Memory, and Final reports only in the private Hermes
workspace. Add a provider destination or owner message only when Company OS wants a
second copy or notification.

## Optional provider copies

Local storage is automatic. Add a row only when a secondary copy is wanted:

```text
| Artifact | Provider | Destination |
| --- | --- | --- |
| `long-term memory` | notion | https://...private-memory... |
| `reports` | notion | https://...management-reports... |
```

No row means local-only. Provider and destination must both be present. The
copy runs only after the local write reads back, uses a stable action key, and
upserts the completed local Markdown rather than regenerating it from an
incremental extraction. It never imports provider edits into memory. Memory URLs must be private and
operator-approved. Progress and documentation questions remain comments on the
exact Work item; they are not memory synchronization.
Never reuse the public/shared People URL for `long-term memory`; validation
rejects that collision before a provider action is planned.

## 1. Log your work in tickets

Use the correct Work type:

- **Task** for ordinary execution.
- **Feature** for a bounded value opportunity with explicit scope and
  acceptance.
- **Issue** for a problem that needs diagnosis, a baseline, an intervention,
  and verification.
- **Meeting** for discussion whose Decisions and commitments must be captured.

At minimum, keep these facts current:

1. Project, owner, status, due date, progress, and last meaningful update.
2. What changed today.
3. Evidence: a source link, result, document, screenshot, number, or Meeting.
4. Current blocker and who owns it, or an explicit statement that there is no
   blocker.
5. Next action and commitment date.
6. On completion: outcome, acceptance evidence, important decision and reason,
   handoff, and any reusable method or recurring problem observed.

Good completion note:

```text
Outcome: The reconciliation sheet is now the release gate for the three-store pilot.
Evidence: Linked signed pilot sheet and approval Meeting.
Decision: Use the signed sheet instead of supplier emails because it preserves
one comparable baseline. Accepted tradeoff: one manual normalization step remains.
Handoff: Nur owns the final two store comparisons by 28 August.
Reusable method: retain the original supplier file and attach the normalized output.
```

Weak completion note:

```text
Done. Sheet updated.
```

## 2. Chat with the agent through Notion ticket comments

Start a new discussion with the configured mention, such as `@hermes`. After
Hermes joins that open discussion, follow-up comments in the same thread do not
need the tag. A separate discussion still requires the mention. Keep the
conversation on the source ticket so the page, question, answer, and evidence
stay together.

Useful requests:

```text
@hermes review this ticket for completion quality. Tell me only what is
missing, why it matters, and which section I should update.
```

```text
I answered your decision-rationale question under Notes > Decision.
Re-review the page and tell me whether anything required is still missing.
```

```text
@hermes summarize the current blocker and propose the next owner action. Do
not change the ticket.
```

Expected interaction:

```text
Human comment
     |
     v
Agent reads the complete authorized page and exact open discussion
     |
     +--> comment is for Hermes: replies or re-reviews
     |
     `--> human-to-human or acknowledgement: stays silent
                         |
                         v
                  Human edits page or replies
                         |
                         v
              Same discussion reaches Agent again
```

The Notion bridge proves that an authorized comment can reach Hermes and receive
a reply. The Daily contract now protects the processing state, but the bridge is
not yet a deterministic event-driven Daily runner. A mention can request an
immediate re-review; otherwise the next Daily run re-fetches the Done item while
its `AI review` is not `Processed`. Never treat a reply or posted question alone
as proof that the ticket is ready to be processed.

## 3. Ask the agent to create a ticket through comments

The safe interaction is proposal first. Put the request on the relevant Project
or source Work page and include the desired outcome, owner, timing, and evidence.

```text
@hermes draft a Task for the remaining two store comparisons.
Project: Penang Replenishment.
Owner: Nur.
Due: 28 August 2026.
Done means: both comparisons are attached and variances are reviewed.
Source: this ticket and TASK-103.
Show me the proposed title, fields, body, and source links before any write.
```

```text
Comment request
      |
      v
Agent resolves Project, owner, type, template, and source
      |
      +--> missing or ambiguous fact: asks one bounded question
      |
      `--> complete request: returns a template-complete proposal
                                  |
                                  v
                         authorized create route
                                  |
                                  v
                         new Work URL + receipt
```

There is not yet a dedicated schema-backed “create Work from comment” contract
in this repository. Treat this as a chat-assisted drafting path until a create
route, dedupe key, authority check, and write receipt are implemented and
evaluated. The agent must never guess the Project, owner, database, or due date.

## 4. Chat with the agent over Telegram

Use Telegram for short manager interactions, not as the canonical work log.
Ask for a summary, a list of blockers, or a ticket proposal. Source facts remain
on the relevant Notion record; derived management state belongs in the private
weekly report unless an approved outbound mapping publishes it elsewhere.

Useful requests:

```text
What active Project targets are at risk this week? For each, cite the Work item
and tell me whether the delay has a documented cause.
```

```text
Draft a Task from this note: supplier B still owes the normalized count file.
Ask me for any required field you cannot resolve. Do not create it yet.
```

```text
Show me today's documentation questions grouped by owner, with links to the
source Work items.
```

```text
Telegram request
       |
       v
Agent reads authorized canonical records
       |
       +--> answer or proposal in Telegram
       |
       `--> derived management state -> private Project Memory
```

Do not paste credentials, personal contact details, or private files into
Telegram. A Telegram message is not evidence that an employee received or read
a request unless the provider route and receipt explicitly prove that claim.

## 5. Daily agent task

Daily reads one bounded local-day window in `Asia/Kuala_Lumpur`. It reconciles
active Projects and changed Work, appends grounded observations to private
Project Memory, and prepares any documentation request or owner chase. It does
not rescan unrelated history, invent missing facts, or mark Work `Processed`
merely because it posted a question.

The behavior contract lives in [`PM Daily`](../skills/pm-daily/SKILL.md).
The automation owns only scheduling, snapshot acquisition, invocation, review,
and authorized delivery.

## 6. Weekly agent task

Weekly freezes the complete Project Memory set instead of rescanning Work or
Meetings. It builds the Project, Department, and Company reports, updates only
qualified long-term memory, and carries unresolved items into next week. Frozen
notes and finalized reports remain immutable.

The behavior and promotion contract lives in
[`PM Weekly`](../skills/pm-weekly/SKILL.md). The automation owns only the
weekly boundary, invocation, review, and authorized delivery.

## When documentation is poor

PM Daily owns the documentation-quality decision and draft behavior. Operators
should inspect the skill-produced draft and source link; they should not invent
a separate recovery state machine in this manual.

To change the wording, output structure, or decision behavior itself, use the
[maintenance and tuning SOP](tuning-sop.md). Do not tune installed runtime
copies directly.

## Operator checklist

### During the day

- Log meaningful progress on the source Work item.
- Link evidence instead of pasting unsupported conclusions.
- Keep owner, due date, blocker, and next action current.
- Reply to documentation questions on the same page or edit the named section.
- Ask the agent to re-review after the update.

### After the Daily run

- Inspect blocked or conflicted effects.
- Check that at-risk targets cite evidence and a real due date.
- Check that incomplete tickets remain open for review, not silently
  `Processed`.
- Check that no duplicate question or chase was sent.

### After the Weekly run

- Confirm every active Project has a Final Project report or a named gap.
- Confirm every candidate has a disposition and source links.
- Confirm promoted Decisions and SOPs meet their type-specific gates.
- Confirm next-week attention has an owner and date for each commitment.
- Treat a provider receipt as delivery proof only to the extent it actually
  records the destination and read-back.

Grounding: current local automation, template, workspace, and Notion onboarding
contracts. No external source was needed for this operator guide.
