---
template_id: company-os-weekly-report
template_version: "1.0.0"
name: "{{PROJECT_NAME}} — Week of {{WEEK_START}}"
report_type: "Project"
project: "{{PROJECT}}"
department: "{{DEPARTMENT}}"
week_start: "{{WEEK_START}}"
report_status: "{{REPORT_STATUS}}"
report_version: "{{REPORT_VERSION}}"
finalized_at: "{{FINALIZED_AT}}"
previous_report: "{{PREVIOUS_REPORT}}"
source_report_ids: "{{SOURCE_REPORT_IDS}}"
---

# {{PROJECT_NAME}} — Week of {{WEEK_START}}

## Summary

<!-- Exactly three evidence-backed sentences: material change, highest-leverage
attention, and next priority. No raw activity log. -->

{{SUMMARY}}

## Outcomes and open attention

| Outcome or attention | Current state | Evidence | Next owner action |
| --- | --- | --- | --- |
{{OUTCOME_ROWS}}

## Accepted outputs by employee

<!-- Include every accepted artifact-producing outcome in the evidence window,
not only actions needing management attention. Preserve exact Person, Work,
artifact, receiver acceptance, workflow key, and sourced active/wait time. -->

| Employee | Work | Accepted output and result | Workflow | Active / wait time | Acceptance evidence |
| --- | --- | --- | --- | --- | --- |
{{ACCEPTED_OUTPUT_ROWS}}

## Employee actions

<!-- Track evidence-backed employee actions or commitments that materially
affect this Project. Use the canonical Person label or link, state the expected
result, distinguish completed, progressing, blocked, missed, or unverified,
and name the next follow-up. Do not infer intent, personality, or a performance
rating from activity alone. The section may be empty when no material employee
action is evidenced in the reporting window.

GOLDEN EXAMPLE — replace every fact below.
| Aisha (PERSON-AISHA) | Sign the corrected construction pack | One approved measurement source before sample recheck | Blocked; approver is still missing | [TASK-101](task://TASK-101) | 2026-08-27 | Aisha names the approver; Nur rechecks within one working day |
END GOLDEN EXAMPLE -->

| Employee | Action or commitment | Expected result | Current state | Evidence | Due or review date | Next follow-up |
| --- | --- | --- | --- | --- | --- | --- |
{{EMPLOYEE_ACTION_ROWS}}

## Problems and inefficiencies

<!-- Combine grounded problems, inefficiencies, risks, blockers, and cost
consequences. Preserve the affected workflow step, dated baseline, impact,
recurrence/volume, time/wait loss, cost formula or explicit measurement gap,
confidence, next proof, and source links.

GOLDEN EXAMPLE — replace every fact below.
| Supplier updates arrive in three incompatible formats | Repeated manual remapping blocks the five-store comparison | MYR 300 over plan from recorded values | Confirm one import map by 2026-08-27 | [TASK-105](task://TASK-105) |
END GOLDEN EXAMPLE -->

| Workflow / affected step | Problem definition | Baseline window and volume | Time / wait loss | Cost consequence and formula | Confidence / measurement gaps | Next proof / intervention | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{{PROBLEM_OPPORTUNITY_ROWS}}

## Decisions

{{DECISIONS_VIEW_OR_LIST}}

## SOPs

<!-- Staged Daily candidates are clearly marked `Proposed` until Weekly
finalization verifies recurrence, owner, and proof. Do not mistake a candidate
for an adopted procedure. -->

{{SOPS_VIEW_OR_LIST}}

## Next-week priorities

<!-- This is the report's handoff, not a second live plan. Weekly updates the
canonical Project's This week's attention checklist separately. -->

{{NEXT_WEEK_HANDOFF}}

## Automation receipt

- `evidence_window:` {{START_TIMESTAMP}}..{{END_TIMESTAMP}}
- `sources_checked:` {{Stable source names or locators}}
- `source_gaps:` {{Missing or stale sources, or none}}
- `last_successful_daily_receipt:` {{Receipt locator}}
