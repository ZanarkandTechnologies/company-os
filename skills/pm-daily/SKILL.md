---
name: pm-daily
description: Turn one Project-scoped Daily packet and its current weekly Project Memory into grounded memory updates and message drafts.
---

# PM Daily

## Use when

Run once for one selected Project after the automation has fetched and
partitioned recent Work by exact Project relation. This skill edits local
artifacts only. It does not fetch provider data, post comments, send messages,
sync files, or coordinate other Projects.

## Inputs

- One Project packet derived from `daily/context/daily-snapshot-YYYY-MM-DD.json`
- `weeks/<week>/project-memory/project--<project-id>.md` for that Project
- `templates/project-memory.md`
- `templates/documentation-request.md`
- `templates/employee-followups.md`

The snapshot must contain exact Project, Work, source provider, provider record
ID, relation, status, date, source reference, and source revision values. Keep a
source URL when the provider supplies one. Person values are optional. Missing
evidence stays missing.

## Workflow

- [ ] **1 — Validate the Project packet.**
  Rule: accept only Work whose exact relation matches the packet's Project.
  Never match by title or infer a Project, Person, route, date, or status.
  Assert: every proposed change cites source IDs and belongs to the packet's
  Project; unresolved Project or source relations are gaps and produce no edit.
  A missing Person blocks only optional direct delivery, not a draft routed to
  the exact Work source reference.

- [ ] **2 — Update Project Memory in place.**
  Rule: read the complete existing file and memory template. Preserve valid
  history and unrelated content. Update the operating picture, durable Project
  knowledge, and this week's attention from current evidence. Do not copy full
  ticket bodies or meeting transcripts.
  Assert: the file still matches the template headings; every new claim cites
  an exact source ID; unresolved targets and blockers are not silently removed.

- [ ] **3 — Draft documentation requests.**
  First classify each completed Work item as `empty`, `sparse`, or `reviewable`
  from the completeness facts and preserved source values. Title and status
  without a usable body or update is `empty`; partial operating context is
  `sparse`. Record every reason, including `no_page_body`, `no_progress`,
  `no_owner`, `no_due_date`, `no_next_action`, and `no_completion_evidence`.
  Rule: review completed Work only. When evidence is insufficient, render one
  precise request from the documentation template. Ask only for facts needed
  to verify the claimed outcome. A completed empty or sparse Work item without
  an outcome or evidence may produce one request. Sufficient Work produces no
  draft.
  Assert: each draft names the exact Work item, missing evidence, intended
  recipient when known, and source reference without inventing metrics or a
  delivery route.

- [ ] **4 — Draft progress follow-ups.**
  Classify active Work using the same completeness rule before deciding whether
  to chase it.
  Rule: chase only stale, overdue, blocked, or materially ambiguous Work. Use
  the progress template and ask one answerable question tied to the next action.
  An active empty or sparse Work item may produce one follow-up that asks for
  its current status, next action, and blocker.
  Assert: healthy or recently updated Work produces no draft; one issue does
  not create duplicate documentation and progress messages; every skipped Work
  item returns its exact skip reason.

- [ ] **5 — Verify and return the output files.**
  Rule: inspect the changed-file list and reread every changed artifact. Return
  each exact changed path and its artifact type to the automation.
  Assert:
  - `weeks/<week>/project-memory/project--<project-id>.md` exists and matches
    the Project Memory template, or the result explicitly records no change.
  - Every documentation request exists at
    `daily/messages/documentation/work--<work-id>.md` and its frontmatter has
    `artifact_type: documentation_request`, the exact `work_id`, exact
    `source_provider`, `provider_record_id`, and exact `source_reference`.
    `source_url` is required only when the provider returned one.
  - Every progress follow-up exists at
    `daily/messages/progress/work--<work-id>.md` and its frontmatter has
    `artifact_type: progress_followup`, the exact `work_id`, exact
    `source_provider`, `provider_record_id`, and exact `source_reference`.
    `source_url` is required only when the provider returned one.
  - Only those declared outputs changed, all Markdown is readable, every claim
    is grounded, and no provider action was attempted.

## Golden behavior

When a completed Work item claims a result but lacks the measurement source,
retain its factual progress in Project Memory and draft a documentation request
for that source. Do not mark the result verified, estimate the number, or also
send a generic progress chase.
