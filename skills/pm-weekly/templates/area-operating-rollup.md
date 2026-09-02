---
template_id: company-os-area-operating-rollup
template_version: "0.7.0"
name: "{{AREA_NAME}} — Week of {{WEEK_START}}"
report_type: "Area"
area: "{{AREA_NAME}}"
week_start: "{{WEEK_START}}"
report_status: "{{REPORT_STATUS}}"
report_version: "{{REPORT_VERSION}}"
finalized_at: "{{FINALIZED_AT}}"
previous_report: "{{PREVIOUS_REPORT}}"
source_report_ids: "{{PROJECT_REPORTS}}"
---

# {{AREA_NAME}} — Week of {{WEEK_START}}

## Summary

<!-- Exactly three evidence-backed sentences: material change across Projects,
highest-leverage attention, and next Area priority. -->

{{SUMMARY}}

## Outcomes and open attention

| Project | Current result | Open attention | Next owner action | Source report |
| --- | --- | --- | --- | --- |
{{PROJECT_RESULT_ROWS}}

## Accepted outputs by employee

<!-- Roll up every accepted artifact-producing outcome from the Department's
Project summaries so a manager can answer who produced what. Deduplicate by
Work and artifact; preserve sourced active/wait time and acceptance evidence. -->

| Employee | Accepted output and result | Project | Workflow | Active / wait time | Evidence / Project summary |
| --- | --- | --- | --- | --- | --- |
{{ACCEPTED_OUTPUT_ROWS}}

## Employee actions

<!-- Roll up only evidence-backed employee actions that require Area visibility
because they unblock multiple Projects, need management follow-up, or show a
material completed result. Preserve the canonical Person label or link and the
source Project report. Do not infer intent, personality, or a performance
rating. The section may be empty when no action needs Area visibility.

GOLDEN EXAMPLE — replace every fact below.
| Aisha (PERSON-AISHA) | Close the controlled-pack handoff | CMT Pipeline | Blocked; signed approver missing | [Project report](report://PROJECT-W35) | 2026-08-27 | Area lead reviews the signed pack before line booking |
END GOLDEN EXAMPLE -->

| Employee | Action or commitment | Project | Current state | Evidence / source report | Due or review date | Area follow-up |
| --- | --- | --- | --- | --- | --- | --- |
{{EMPLOYEE_ACTION_ROWS}}

## Problems and inefficiencies

<!-- Group only problems whose evidence crosses Projects or is material to the
Area. Each row has a bounded first test, never a generic AI wish.

GOLDEN EXAMPLE — replace every fact below; it demonstrates useful detail.
| Store-count evidence is absent in two inventory Projects | Penang Replenishment, Allocation Rules | [Project reports](report://W34) both identify the same missing count source | Produce one exception brief that links the two source reports and names the evidence owner | Trial at the next department review; success = the lead assigns one owner and date without reopening raw Work. |
END GOLDEN EXAMPLE -->

| Problem | Projects / workflows | Evidence and recurrence | Quantified baseline or measurement gap | Confidence | Narrow intervention | First test and success signal |
| --- | --- | --- | --- | --- | --- | --- |
{{PROBLEM_OPPORTUNITY_ROWS}}

## Decisions

{{DECISIONS_VIEW_OR_LIST}}

## SOPs

<!-- Compare identical workflow keys across Project summaries. Show sample
count, active/wait range or measurement gap, approved baseline, observed
control-preserving opportunity, and the next bounded test. -->

{{SOPS_VIEW_OR_LIST}}

## Next-week priorities

{{NEXT_WEEK_HANDOFF}}

## Automation receipt

- `evidence_window:` {{START_TIMESTAMP}}..{{END_TIMESTAMP}}
- `project_reports:` {{Canonical Project report locators}}
- `source_gaps:` {{Missing Project reports or source evidence, or none}}
- `previous_area_report:` {{Report locator or none}}
