---
name: pm-weekly
description: Turn a frozen Project Memory set into Project evidence summaries, Department and Company reports, and grounded long-term memory updates.
---

# PM Weekly

## Use when

Run after the final Daily update for the week. This skill reads the complete
frozen Project set and edits local artifacts only. It does not fetch provider
data, send the executive report, or sync files.

## Inputs

- Every `weeks/<week>/project-memory/project--<project-id>.md`
- Existing Project, Department, and Company reports for comparison
- Existing `memory/{employees,sops,issues,decisions}/` entries
- `templates/{weekly-report,area-operating-rollup,company-operating-rollup}.md`
- `templates/executive-distribution.md`
- `../pm-daily/templates/project-memory.md` for next-week initialization
- Shared entity templates under the repository `templates/` directory

## Workflow

- [ ] **1 — Freeze the complete weekly input.**
  Rule: enumerate every expected active Project before analysis. Do not proceed
  from a partial Project set or mix weeks.
  Assert: each selected Project has one readable current-week memory file; gaps
  are named and affected rollups remain blocked.

- [ ] **2 — Finalize Project evidence summaries.**
  Rule: use the weekly-report template and compare with the previous report.
  Separate observed results, open attention, problems, decisions, SOP signals,
  accepted artifact-producing outcomes by Person, and next actions. Preserve
  measurement gaps instead of estimating value.
  Assert: every material claim cites Project Memory evidence and each Final
  report has the complete template structure.

- [ ] **3 — Roll reports upward.**
  Rule: Department reports read only Final Project reports; the Company report
  reads only Final Department reports. Use their matching templates.
  Assert: each rollup links all immediate source reports and never hides a
  blocked or missing child report.

- [ ] **4 — Consolidate long-term memory.**
  Rule: group accepted outcomes by exact Person ID and comparable workflow
  samples by exact `workflow_key` across Project summaries. Employee Memory
  receives accepted outputs and material unresolved actions without ratings.
  SOP Memory compares only samples with the same output and acceptance controls;
  it preserves active versus waiting time, rework, exceptions, and evidence.
  Keep the current interval separate from the durable baseline. A faster sample
  becomes a bounded improvement test, not a baseline replacement. Update a
  baseline only from comparable receiver-accepted evidence plus explicit
  approval. One observation may remain Project-only.
  Assert: updates preserve prior valid context, cite immediate source summaries,
  do not double-count one Work item, and label unmeasured Before/After values as
  gaps. Every accepted artifact-producing outcome appears in its Person's latest
  weekly evidence and its Department's accepted-output rollup.

- [ ] **5 — Carry attention forward and draft distribution.**
  Rule: initialize next week from unresolved work only. Render the executive
  distribution template from the complete Final Company report.
  Assert: resolved items do not reappear; the draft contains no invented
  provider URL or delivery receipt.

- [ ] **6 — Verify and return the output files.**
  Rule: inspect the changed-file list and reread every changed artifact. Return
  each exact changed path and the matching artifact type below to the automation.
  Assert:
  - Every finalized Project summary exists at
    `weeks/<week>/reports/projects/project--<project-id>.md` and is returned as
    `project_report`.
  - Every required Department report exists at
    `weeks/<week>/reports/departments/department--<department-id>.md` and is
    returned as `department_report`.
  - The final Company report exists at `weeks/<week>/reports/company.md` and is
    returned as `company_report`.
  - Grounded long-term updates exist only under `memory/employees/` as
    `employee_memory`, `memory/sops/` as `sop_memory`, `memory/issues/` as
    `issue_memory`, or `memory/decisions/` as `decision_memory`.
  - Next-week Project Memory exists only under
    `weeks/<next-week>/project-memory/`, contains unresolved attention only, and
    is returned as `next_week_project_memory`.
  - One executive distribution draft exists under `weeks/<week>/outbound/` and
    is returned as `executive_distribution`.
  - Only those declared outputs changed, templates are complete, source links
    resolve to the frozen input, and no provider action was attempted.

## Golden behavior

A workflow observed once stays in its Project summary with measurement gaps. A
repeated, receiver-accepted workflow updates the SOP's latest interval evidence.
Weekly may propose the fastest control-preserving method as a test, but it does
not replace an approved baseline without comparable evidence and explicit
approval.
