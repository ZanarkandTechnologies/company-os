---
template_id: company-os-company-operating-rollup
template_version: "0.7.0"
name: "Company OS — Week of {{WEEK_START}}"
report_type: "Company"
week_start: "{{WEEK_START}}"
report_status: "{{REPORT_STATUS}}"
report_version: "{{REPORT_VERSION}}"
finalized_at: "{{FINALIZED_AT}}"
previous_report: "{{PREVIOUS_REPORT}}"
source_report_ids: "{{AREA_REPORTS}}"
---

# Company OS — Week of {{WEEK_START}}

## Summary

<!-- Exactly three evidence-backed sentences: material company change,
highest-leverage attention, and next company priority. -->

{{SUMMARY}}

## Outcomes and open attention

| Area | Current result | Open attention | Next owner action | Source report |
| --- | --- | --- | --- | --- |
{{DEPARTMENT_RESULT_ROWS}}

## Employee actions

<!-- Roll up only evidence-backed employee actions that require Company
visibility because they cross Areas, gate a material company outcome, or need
executive follow-up. Preserve the canonical Person label or link and source
Area report. Do not infer intent, personality, or a performance rating. The
section may be empty when no action needs Company visibility.

GOLDEN EXAMPLE — replace every fact below.
| Darren (PERSON-DARREN) | Prove the guest checkout path | Ecommerce | Unverified; failed order and trace are missing | [Area report](report://ECOM-W35) | 2026-08-29 | Ecommerce lead reviews the reproduced failure and passing order |
END GOLDEN EXAMPLE -->

| Employee | Action or commitment | Area | Current state | Evidence / source report | Due or review date | Company follow-up |
| --- | --- | --- | --- | --- | --- | --- |
{{EMPLOYEE_ACTION_ROWS}}

## Problems and inefficiencies

<!-- Company rows only when the problem crosses Areas or has a material
shared impact. The proposed intervention stays bounded and testable.

GOLDEN EXAMPLE — replace every fact below; it demonstrates useful detail.
| Supplier evidence reaches Merchandising and CMT in incompatible formats | Merchandising, CMT | Two Area reports cite the same reconciliation delay | Draft one source-linked exception brief with a proposed common intake format | Trial for the next two reviews; success = both leads identify a variance decision in under 10 minutes. |
END GOLDEN EXAMPLE -->

| Problem | Areas / workflows | Evidence and recurrence | Quantified baseline or measurement gap | Confidence | Narrow intervention | First test and success signal |
| --- | --- | --- | --- | --- | --- | --- |
{{PROBLEM_OPPORTUNITY_ROWS}}

## Decisions

{{DECISIONS_VIEW_OR_LIST}}

## SOPs

<!-- Include only cross-Area or materially important workflow opportunities.
Distinguish the approved baseline, latest comparable evidence, and a proposed
test; never present the fastest sample as the new standard automatically. -->

{{SOPS_VIEW_OR_LIST}}

## Next-week priorities

{{NEXT_WEEK_HANDOFF}}

## Automation receipt

- `evidence_window:` {{START_TIMESTAMP}}..{{END_TIMESTAMP}}
- `area_reports:` {{Area rollup locators}}
- `source_gaps:` {{Missing Area reports or source evidence, or none}}
- `previous_company_report:` {{Report locator or none}}
