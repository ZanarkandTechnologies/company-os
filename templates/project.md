---
template_id: company-os-project
template_version: "0.6.0"
name: "{{PROJECT_NAME}}"
project_id: "{{PROJECT_ID}}"
department: "{{DEPARTMENT}}"
owner: "{{OWNER}}"
status: "{{STATUS}}"
priority: "{{PRIORITY}}"
start_date: "{{START_DATE}}"
due_date: "{{DUE_DATE}}"
progress: "{{PROGRESS}}"
---

# {{PROJECT_NAME}}

## Overview

**Goal:** {{One sentence on the outcome. One sentence on why it matters.}}

## Project knowledge

<!--
Store proprietary, project-specific facts, findings, constraints, and source-backed
insights that should guide future operating decisions. Keep the conclusion,
operational impact, source, and review condition. Do not paste raw meeting
transcripts or repeat Work Item status.

LIFECYCLE
During Daily or Weekly: add only knowledge that changes a current or future
Project decision. Correct or remove it when the source changes. Keep it here
until an explicit, later wiki extraction proves cross-project reuse.

GOLDEN EXAMPLE — concise, source-linked, and actionable
### Supplier reconciliation constraint
- **Known:** Supplier updates arrive in three formats, so variance cannot be
  compared until counts are normalised.
- **Impact:** Rollout remains blocked; the owner needs a source-linked
  reconciliation step before the five-store decision.
- **Evidence:** [Pilot review](meeting://MEETING-042) ·
  [Reconciliation task](task://TASK-124)
- **Review:** Replace this after the next five-store sample.
END GOLDEN EXAMPLE
-->

{{PROJECT_KNOWLEDGE}}

## This week's attention

**Planning window:** {{WEEK_OF}}

<!-- LIFECYCLE
At weekly planning: replace this checklist with the approved priorities.
During the week: append only material blockers, stale work, or decisions needed;
check an item only when the linked work is complete or management attention ends.
At the next weekly planning: remove completed/non-material rows and rewrite the
remaining rows from the approved new plan. Do not copy every Task row here.

GOLDEN EXAMPLE — replace every fact below; it demonstrates required detail.
- [ ] **P0 · Blocked · due 2026-08-28** — Confirm payment approval.
  **Owner:** Finance owner · **Why now:** launch cannot proceed without it.
  **Evidence:** [Task TASK-124](task://TASK-124)
- [ ] **P1 · Stale 3d · due 2026-08-29** — Obtain revised supplier commitment.
  **Owner:** Operations owner · **Why now:** schedule variance is increasing.
  **Evidence:** [Task TASK-125](task://TASK-125)
- [ ] **P2 · Decision needed · due 2026-08-30** — Choose pilot rollout threshold.
  **Owner:** Project owner · **Why now:** the team cannot close the next-week plan.
  **Evidence:** [Decision draft DEC-018](decision://DEC-018)
END GOLDEN EXAMPLE -->

{{WEEKLY_ATTENTION_CHECKLIST}}

## Tasks

{{TASKS_VIEW_OR_LIST — prefer a native linked database filtered to this Project,
hide completed work, and sort Priority then due date; otherwise render a concise
linked Markdown list with Task, status, owner, due date, and source.}}

## Decisions made

{{DECISIONS_VIEW_OR_LIST — prefer a native linked database filtered to this
Project and approved/current Decisions; otherwise render a concise linked list.}}
