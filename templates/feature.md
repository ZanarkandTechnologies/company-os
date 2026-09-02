---
template_id: company-os-feature
template_version: "0.1.0"
name: "{{WORK_ITEM_NAME}}"
work_item_id: "{{WORK_ITEM_ID}}"
project: "{{PROJECT}}"
department: "{{DEPARTMENT}}"
owner: "{{OWNER}}"
type: "Feature"
status: "{{STATUS}}"
ai_review: "{{AI_REVIEW}}"
priority: "{{PRIORITY}}"
start_date: "{{START_DATE}}"
due_date: "{{DUE_DATE}}"
progress: "{{PROGRESS}}"
last_meaningful_update: "{{LAST_MEANINGFUL_UPDATE}}"
---

# {{WORK_ITEM_NAME}}

## Problem and value

<!-- State who has the problem, the observed evidence, and the value of solving
it. Do not start from a proposed solution.

GOLDEN EXAMPLE — replace every fact below; it demonstrates useful detail.
**Problem:** Store managers receive three supplier updates in different formats,
which delays replenishment decisions by two days.
**Evidence:** This happened in three weekly reviews; see [review notes](meeting://MEETING-042).
**Value:** A same-day variance brief lets the replenishment owner act before the
next ordering cutoff.
END GOLDEN EXAMPLE -->

{{PROBLEM_AND_VALUE}}

## Scope for this cycle

<!-- Name the first bounded slice and the explicit non-goals. -->

**In scope:** {{IN_SCOPE}}

**Not in scope:** {{OUT_OF_SCOPE}}

## Success and acceptance

<!-- Define the observable result, evidence needed, and the person who accepts
it. Prefer a small test before committing to a broad rollout. -->

{{SUCCESS_AND_ACCEPTANCE}}

## Notes

<!-- Freeform research, options, implementation notes, decisions, and links. -->

{{NOTES}}
