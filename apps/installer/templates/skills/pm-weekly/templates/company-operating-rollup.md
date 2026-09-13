---
{"output":"skills/pm-weekly/templates/company-operating-rollup.md","runtime":{"template_id":"company-os-company-operating-rollup","template_version":"0.9.0","name":"${answer__company_name} — Week of {{WEEK_START}}","report_type":"Company","week_start":"{{WEEK_START}}","report_status":"{{REPORT_STATUS}}","report_version":"{{REPORT_VERSION}}","finalized_at":"{{FINALIZED_AT}}","previous_report":"{{PREVIOUS_REPORT}}","source_report_ids":"{{AREA_REPORTS}}"},"refs":["organization.grouping","company.name"]}
---

# ${answer__company_name} — Week of {{WEEK_START}}

<!-- Step 4 renders JSON items as concise sourced bullets, not tables.
Retain supplied frontmatter and these headings in order. Empty items render
None. Omit the final optional health heading when its section is absent.
Use readable labels; retain exact IDs in metadata or source destinations. -->

## Summary

<!-- Up to three short bullets: material change, important attention, next priority. -->
{{SUMMARY}}

## Department executive summary

<!-- One concise named entry for EVERY Department: result/change, open attention,
next priority and source report. Quiet or evidence-limited Departments remain
visible with the supported state. Do not replace coverage with a merged narrative
or a list of links. The Summary above prioritizes; this section covers all. -->
{{DEPARTMENT_EXECUTIVE_SUMMARY}}

## People progress

<!-- One named group per in-scope Person across Departments: scope, evidenced
progress, open work/blocker and next action, with Department report links.
Include people without accepted outputs and explicit evidence gaps. Deduplicate
exact identity while preserving different ${unit} states. Do not repeat artifact
lists or intervention detail; no ratings or unsupported personal conclusions. -->
{{PEOPLE_PROGRESS}}

## Unblocking work

<!-- Dependency or known cause → impact → existing attempts → smallest proposed
intervention beyond another reminder → supplied owner, if known → completion
signal. Include only interventions requiring Company visibility.
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
collection or evidence limitation. At most one concise bullet per affected ${unit}:
issue → consequence → fix. Unknown coverage is explicit when material.
Sparse activity alone is not a system failure. -->
{{SYSTEM_USEFULNESS_AND_GAPS}}
