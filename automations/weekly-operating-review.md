---
automation_id: company-os-weekly-operating-review
automation_version: "0.2.0"
kind: company-os-automation
cadence: weekly
status: draft
owner: HermesCorp
input_window: current-reporting-week
opens_with:
  - outcome
  - why
processes:
  - plan-review
  - issue-promotion
  - decision-promotion
  - resource-promotion
  - skill-promotion
  - quality-follow-up
  - report-finalization
  - next-week-setup
---

# Weekly operating review

> **Outcome**
>
> Turn the weekly draft into an executive snapshot, promote useful records, and
> open the next reporting window.
>
> **Why**
>
> Keep Daily findings from becoming clutter by deciding what deserves to become
> an Issue, Decision, Resource, or Skill.

## Reads

- Current weekly report draft and its Daily receipts.
- Previous finalized report and current Project context.
- Related Tasks, Decisions, Resources, Skills, and People.

## Process lanes

Weekly lanes review Daily candidates by value gate, then either promote them or
leave them in the report with an explicit disposition.

> ### `plan-review`
>
> **Reviews:** planned work, actual Task evidence, and unresolved commitments.
>
> **Writes:** the executive summary, Plan versus actual, and proposed next-week commitments.

> ### `issue-promotion`
>
> **Reviews:** Problem candidates for recurrence, impact, evidence, and owner relevance.
>
> **Writes:** accepted candidates to Tasks with `Type = Issue`; otherwise a disposition.

> ### `decision-promotion`
>
> **Reviews:** Decision candidates for precedent value, rationale, and authority.
>
> **Writes:** a Decision record or a report-only disposition.

> ### `resource-promotion`
>
> **Reviews:** candidate knowledge against the future-value gate.
>
> **Writes:** a Resource record or a report-only disposition.

> ### `skill-promotion`
>
> **Reviews:** SOP candidates for repeatability evidence and owner approval.
>
> **Writes:** a Skill creation request or a report-only disposition.

> ### `quality-follow-up`
>
> **Reviews:** documentation-quality proposals against the approved write policy.
>
> **Writes:** an approved comment or edit, or a deferred follow-up.

> ### `report-finalization`
>
> **Reads:** the reviewed plan and every promotion disposition.
>
> **Writes:** one immutable weekly Report with links to evidence and promoted records.

> ### `next-week-setup`
>
> **Reads:** the finalized Report and unresolved commitments.
>
> **Writes:** the next weekly draft and proposed commitments for owner approval.

```text
weekly_operating_review(weekly_draft, project_context, promotion_policy)
  -> finalized_report + promoted_records + next_week_draft + receipt
state: freezes the current report; opens the next reporting window
```

## Flow

1. Run `plan-review`; carry unresolved commitments by reference and never delete
   canonical Tasks.
2. Run the four promotion lanes. Give every candidate a disposition, including
   duplicates and low-value observations that stay in the Report.
3. Run `quality-follow-up` under the company's approved write policy.
4. Run `report-finalization` and preserve links to evidence, dispositions, and
   promoted records.
5. Run `next-week-setup` and leave its proposed commitments for owner approval.

## Write boundary

Promotion requires the named value gate and owner-approved authority. Sharing
the report, sending chases, changing source documents, and publishing Skills
remain separately gated external actions.

## Completion proof

- The finalized report links plan, actual work, unresolved Issues, promotions,
  and source receipts.
- Every candidate has `Promoted`, `Duplicate`, `Monitor`, or `Dismissed`
  disposition.
- No canonical work item was cleared or deleted.
- The next weekly draft exists without copying the prior week's narrative.
