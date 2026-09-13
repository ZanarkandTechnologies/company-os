---
{"output":"skills/pm-weekly/templates/area-operating-rollup.md","runtime":{"template_id":"company-os-area-operating-rollup","template_version":"0.9.0","name":"{{AREA_NAME}} — Week of {{WEEK_START}}","report_type":"Department","week_start":"{{WEEK_START}}","report_status":"{{REPORT_STATUS}}","report_version":"{{REPORT_VERSION}}","finalized_at":"{{FINALIZED_AT}}","previous_report":"{{PREVIOUS_REPORT}}","source_report_ids":"{{PROJECT_REPORTS}}","department":"{{AREA_NAME}}"},"refs":["organization.grouping"],"when":{"question":"organization.grouping","options":["project"]}}
---

# {{AREA_NAME}} — Week of {{WEEK_START}}

<!-- Step 4 renders JSON items as concise sourced bullets, not tables.
Retain supplied frontmatter and these headings in order. Empty items render
None. Omit the final optional health heading when its section is absent.
Use readable labels; retain exact IDs in metadata or source destinations. -->

## Summary

<!-- Up to three short bullets: material change, important attention, next priority. -->
{{SUMMARY}}

## Outcomes and open attention

<!-- Result or unresolved outcome → current evidence → needed next action.
Link every immediate child report; elevate material shared outcomes. -->
{{OUTCOMES_AND_OPEN_ATTENTION}}

## People progress

<!-- One named group per in-scope Person across all Department Projects:
evidenced change, current open work, blocker and next action, with Project links.
Include people without accepted outputs; label insufficient evidence explicitly.
Retain differing Project states; never infer ratings or completion. Summarize
state here; keep accepted artifact details below and intervention details later. -->
{{PEOPLE_PROGRESS}}

## Accepted outputs by employee

<!-- One bullet per deduplicated accepted Work/artifact: Person → output and
result → receiver acceptance source → Project report. Keep exact identity and workflow
provenance in metadata. No employee ratings or timing columns. -->
{{ACCEPTED_OUTPUTS}}

## Unblocking work

<!-- Dependency or known cause → impact → existing attempts → smallest proposed
intervention beyond another reminder → supplied owner, if known → completion
signal. Include only interventions requiring Department visibility.
Do not repeat accepted outputs or imply proposed actions were executed. -->
{{UNBLOCKING_WORK}}

## Problems and inefficiencies

<!-- Problem and affected workflow → evidenced consequence → bounded intervention
and success signal. Include recurrence or measured cost only when sourced;
keep material measurement gaps explicit. -->
{{PROBLEMS_AND_INEFFICIENCIES}}

## Decisions

<!-- Consequential choice → real tradeoff and rationale → consequence or review
trigger → source. Preserve proposed versus approved state. Routine choices do
not become durable Decision records. -->
{{DECISIONS}}

## SOPs

<!-- Recurrent comparable accepted work: skill(input files) => output files;
receiver/controls and proof → approved baseline → proposed improvement test.
Preserve baseline approval; no forced timing comparison. -->
{{SOPS}}

## Next-week priorities

<!-- Unresolved priority → smallest next action → supplied owner, if known →
observable completion signal. This is a handoff, not a duplicate live plan. -->
{{NEXT_WEEK_PRIORITIES}}

## System usefulness and gaps

<!-- Optional final footer: omit the entire section without a material snapshot
collection or evidence limitation. At most one concise bullet per affected Project:
issue → consequence → fix. Unknown coverage is explicit when material.
Sparse activity alone is not a system failure. -->
{{SYSTEM_USEFULNESS_AND_GAPS}}
