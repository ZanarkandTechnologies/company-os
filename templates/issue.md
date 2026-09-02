---
template_id: company-os-issue
template_version: "1.0.0"
name: "{{ISSUE_NAME}}"
work_item_id: "{{ISSUE_ID}}"
project: "{{PROJECT}}"
department: "{{DEPARTMENT}}"
owner: "{{OWNER}}"
type: "Issue"
status: "{{STATUS}}"
ai_review: "{{AI_REVIEW}}"
priority: "{{PRIORITY}}"
start_date: "{{START_DATE}}"
due_date: "{{DUE_DATE}}"
progress: "{{PROGRESS}}"
last_meaningful_update: "{{LAST_MEANINGFUL_UPDATE}}"
severity: "{{SEVERITY}}"
detected_at: "{{DETECTED_AT}}"
next_review: "{{NEXT_REVIEW}}"
workflow: "{{WORKFLOW}}"
workflow_step: "{{WORKFLOW_STEP}}"
baseline_date: "{{BASELINE_DATE}}"
---

# {{ISSUE_NAME}}

## Problem and impact

<!-- Facts only: what is failing, who is affected, the consequence, and whether
it recurred. Do not present an inference as a fact.

GOLDEN EXAMPLE — replace every fact below; it demonstrates useful detail.
**Observed:** Manual count evidence missed the variance review in three pilots.
**Impact:** The replenishment owner could not approve the next order on time.
END GOLDEN EXAMPLE -->

{{PROBLEM_AND_IMPACT}}

## Before baseline and economics

<!-- Preserve the immutable baseline before intervention: affected workflow and
step, measurement window, recurrence, volume, time lost per occurrence, waiting
time, affected people, loaded hourly-cost basis, direct-cost formula, delay or
revenue impact, evidence, and confidence. Never invent a wage, duration, volume,
or financial value. Name every missing measurement and its owner.

GOLDEN EXAMPLE — replace every fact below.
- **Affected workflow / step:** Supplier comparison / normalise incoming file.
- **Window and volume:** W34; six files per week.
- **Time loss:** 35 minutes rework per file.
- **Direct cost:** 6 × 35/60 × MYR 42 = MYR 147/week.
- **Confidence:** Medium; four observed files and two owner estimates.
END GOLDEN EXAMPLE -->

{{BEFORE_BASELINE_AND_ECONOMICS}}

## Evidence and reproduction

<!-- Link the source evidence and smallest repeatable reproduction path. State
an explicit evidence gap when no reproduction is yet known. -->

{{EVIDENCE_AND_REPRODUCTION}}

## Diagnosis

<!-- Hypothesis, contributing factors, confidence, evidence still needed, and
what would confirm or refute it. -->

{{DIAGNOSIS}}

## Containment and next action

<!-- Immediate mitigation, named owner, due date, and next review point. -->

{{CONTAINMENT_AND_NEXT_ACTION}}

## Intervention and measurement plan

<!-- The bounded change to test, owner, test window, expected effect, guard
metrics, and exact evidence that will be collected. -->

{{INTERVENTION_AND_MEASUREMENT_PLAN}}

## Resolution and verification

<!-- Fix, verification evidence, remaining risk, and linked Decisions or Skills. -->

{{RESOLUTION_AND_VERIFICATION}}

## After measurement and verified value

<!-- Compare the same measures and evidence window used in the Before baseline.
Show time/cost change and formula, confidence, remaining risk, and whether the
value is observed or still forecast. -->

{{AFTER_MEASUREMENT_AND_VERIFIED_VALUE}}

## Related records

<!-- Linked Projects, Work, Decisions, Reports, Skills, and source material. -->

{{RELATED_RECORDS}}
