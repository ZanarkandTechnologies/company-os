---
automation_id: company-os-weekly-operating-review
automation_version: "0.3.0"
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

## Output template

Fill every process row. Each promotion lane must return a disposition even when
it creates no durable record.

| Process | Decision or result | Evidence | Owned write |
| --- | --- | --- | --- |
| `plan-review` | {{Material plan-versus-actual conclusion and next-week proposal}} | {{Report, Task, and prior-report links}} | {{Executive summary and next-week draft delta}} |
| `issue-promotion` | {{Candidate plus Promoted \| Duplicate \| Monitor \| Dismissed}} | {{Recurrence, impact, source, and owner context}} | {{Task with Type = Issue, or report-only disposition}} |
| `decision-promotion` | {{Candidate plus Promoted \| Duplicate \| Monitor \| Dismissed}} | {{Precedent, rationale, and authority evidence}} | {{Decision record, or report-only disposition}} |
| `resource-promotion` | {{Candidate plus Promoted \| Duplicate \| Monitor \| Dismissed}} | {{Future-use evidence and source}} | {{Resource record, or report-only disposition}} |
| `skill-promotion` | {{Candidate plus Promoted \| Duplicate \| Monitor \| Dismissed}} | {{Repeatability evidence and owner approval}} | {{Skill creation request, or report-only disposition}} |
| `quality-follow-up` | {{Approved \| Deferred \| Dismissed proposal}} | {{Document gap and write-policy evidence}} | {{Approved comment or edit, or report-only follow-up}} |
| `report-finalization` | {{Finalization result}} | {{Reviewed draft and all dispositions}} | {{One immutable weekly Report}} |
| `next-week-setup` | {{Carried commitments and proposed priorities}} | {{Final report and canonical Task links}} | {{Next weekly draft; no Task deletion}} |

### Receipt

- `review_window:` {{WEEK_START}}..{{WEEK_END}}
- `candidates_reviewed:` {{Count by promotion lane}}
- `records_promoted:` {{Created record links, or none}}
- `source_gaps:` {{Missing or stale sources, or none}}
- `finalized_report:` {{Immutable Report locator}}
- `next_week_draft:` {{Draft locator}}

## Golden example

### Input and context

- Project: Northstar customer onboarding.
- Weekly draft: the launch task is blocked; incomplete vendor packets have
  reached Legal three times; the four-step handoff and vendor checklist are
  candidates; no approved Decision candidate exists.
- Policy: record promotion is allowed after owner review, but document edits
  and outgoing chases require separate approval.

### Accepted output

| Process | Decision or result | Evidence | Owned write |
| --- | --- | --- | --- |
| `plan-review` | Launch readiness missed plan because Legal lacked a complete packet; next week prioritizes closing that dependency. | Weekly draft, `task://NS-42` | Write the three-sentence executive summary and propose one next-week commitment. |
| `issue-promotion` | `Promoted`: recurring incomplete vendor packets materially delay onboarding. | Three linked occurrences and owner confirmation | Create Task `NS-57` with `Type = Issue`. |
| `decision-promotion` | `Dismissed`: no future-useful choice with rationale and authority exists. | Weekly Decision candidate section | Keep the disposition in the Report only. |
| `resource-promotion` | `Promoted`: the checklist will be reused for future vendor handoffs. | Checklist plus owner confirmation | Create one Resource linked to `NS-42`. |
| `skill-promotion` | `Monitor`: the four-step handoff is repeated, but the owner has not approved it as procedure. | Meeting notes and owner gap | Keep the candidate in the Report. |
| `quality-follow-up` | `Deferred`: proposed checklist fields are useful, but edits are not approved. | Document-quality proposal and write policy | Record a follow-up; do not edit the document. |
| `report-finalization` | All candidates have dispositions and every conclusion links to evidence. | Reviewed weekly draft | Freeze one immutable Weekly Report. |
| `next-week-setup` | Carry `NS-42` and link new Issue `NS-57`; propose, but do not auto-approve, the packet-completion commitment. | Final Report and canonical Tasks | Open the next weekly draft. |

### Why it passes

- Every candidate receives a disposition; only records that pass their value
  gate are promoted.
- Canonical Tasks are linked forward rather than copied, cleared, or deleted.
- Approval boundaries still govern document edits and outgoing messages.

### Tempting negative

Promote every candidate, rewrite the checklist, send the chase, and copy all
unfinished Task text into the next report.

Why it fails: promotion is selective, external writes remain gated, and the
next report should reference canonical work instead of duplicating it.

### Transferable invariants

- Return one explicit disposition per candidate and evidence for every promotion.
- Finalize the current report before opening the next reporting window.

### Non-copyable facts and wording

- Northstar, `NS-42`, `NS-57`, the three occurrences, the vendor packet, and
  every example locator belong only to this fixture.
- Generate fresh conclusions and wording from the current company's evidence.

### Proof receipt

```yaml
golden_case: company-os-weekly-operating-review/northstar-promotion-review
source_refs:
  - synthetic weekly Report, Task, Meeting, and document locators in this example
qa_refs:
  - every candidate receives one allowed disposition
  - external writes remain approval-gated
accepted_because:
  - promotion follows value gates and the next draft links canonical Tasks
heldout_required: true
review_input: candidate + transferable_invariants + current_company_context
review_excludes: Northstar fixture facts and wording
```

## Completion proof

- The finalized report links plan, actual work, unresolved Issues, promotions,
  and source receipts.
- Every candidate has `Promoted`, `Duplicate`, `Monitor`, or `Dismissed`
  disposition.
- No canonical work item was cleared or deleted.
- The next weekly draft exists without copying the prior week's narrative.
