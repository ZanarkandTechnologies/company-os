---
automation_id: company-os-daily-operating-update
automation_version: "0.6.0"
kind: company-os-automation
cadence: daily
status: draft
owner: HermesCorp
input_window: current-local-day
opens_with:
  - outcome
  - why
processes:
  - progress-extraction
  - problem-extraction
  - decision-extraction
  - sop-extraction
  - resource-extraction
  - documentation-template-check
  - chase-planning
  - weekly-draft-projection
---

# Daily operating update

> **Outcome**
>
> Read each changed source once, detect useful operating signals, and keep the
> current weekly Report up to date without creating permanent records too early.
>
> **Why**
>
> Give the owner a current operating picture while every process reuses the same
> Tasks, Meeting notes, and documents.

## Reads

- Tasks, including `Meeting` rows and embedded notes, created or edited during
  the current local day.
- Documents and company records created or edited during the current local day.
- The matching Notion template for each record type.
- Current Projects, weekly report drafts, Decisions, Resources, Skills, and
  People needed for context and deduplication.

## Process lanes

Each lane reads the same deduplicated evidence bundle. Extraction lanes update
the weekly draft, the documentation check comments on its source record, and
chase planning produces proposals only.

> ### `progress-extraction`
>
> **Looks for:** meaningful progress, changed commitments, blockers, and stale work.
>
> **Writes:** Plan-versus-actual updates. It never sends a chase.

> ### `problem-extraction`
>
> **Looks for:** recurring blockers, operating failures, and unresolved risks.
>
> **Writes:** Problem candidates with evidence and no weekly disposition yet.

> ### `decision-extraction`
>
> **Looks for:** choices that may guide future work.
>
> **Writes:** Decision candidates that still need rationale and authority.

> ### `sop-extraction`
>
> **Looks for:** repeatable steps performed by people or agents.
>
> **Writes:** SOP candidates that still need repeatability evidence and owner review.

> ### `resource-extraction`
>
> **Looks for:** notes or documents with future reuse value.
>
> **Writes:** Resource candidates that pass the future-value gate.

> ### `documentation-template-check`
>
> **Looks for:** Tasks, Meeting notes, and documents created or edited today.
> It resolves the applicable Notion template by record type and checks the
> required properties and section expectations against the edited record.
>
> **Writes:** one source comment listing only the information still missing for
> documentation. It comments when the company has approved internal comments
> for that surface; otherwise it saves the exact comment as a proposal. It does
> not edit the record, create a weekly candidate, ask for information available
> elsewhere, or repeat an unresolved comment.

> ### `chase-planning`
>
> **Looks for:** stale commitments with a named owner and a useful next question.
>
> **Writes:** proposed chases with recipient, reason, channel, and timing. Sending
> remains separately gated.

> ### `weekly-draft-projection`
>
> **Reads:** the candidate sets produced by the five extraction lanes. It does
> not ingest documentation-check comments.
>
> **Writes:** one deduplicated delta to the matching current weekly Report.

```text
daily_operating_update(window, sources, current_weekly_report)
  -> weekly_report_delta + candidate_sets + documentation_comments + chase_proposals + receipt
state: source watermarks advance only after successful reads; candidates upsert by source fingerprint
```

## Flow

1. Resolve the last successful watermark and collect one bounded evidence
   bundle with stable source locators.
2. Deduplicate unchanged or previously processed evidence.
3. Run the five extraction lanes against that bundle.
4. For each record created or edited today, run `documentation-template-check`:
   resolve its Notion template, compare required properties and sections, and
   post one source-local comment containing the missing items. If comments are
   not approved, save the exact comment as a proposal. If no template is
   configured, record a source gap instead of inventing requirements.
5. Run `chase-planning` from the progress results. Send nothing unless the
   company has approved the channel, timing, recipients, and frequency policy.
6. Run `weekly-draft-projection` and upsert extraction candidates by source
   fingerprint. Do not project documentation comments into the weekly draft.
7. Write a receipt containing the evidence window, templates checked, source
   gaps, candidate counts, documentation comments, proposed chases, and next
   watermark.

## Write boundary

The Daily automation may update the current weekly draft and explicit task
progress supported by source evidence. It may post one focused internal comment
on a source record only when onboarding has approved that surface and policy.
It must not promote Issues, Decisions, Resources, or Skills; finalize reports;
invent rationale; edit the underlying source content; or send unapproved
messages.

## Output template

Fill every process row. Use `No finding` when a lane ran successfully but found
nothing; use `Source gap` when evidence was unavailable.

| Process | Result | Evidence | Owned write |
| --- | --- | --- | --- |
| `progress-extraction` | {{Meaningful progress, blocker, stale commitment, or No finding}} | {{Stable source links}} | {{Plan-versus-actual delta or No write}} |
| `problem-extraction` | {{Problem candidate with recurrence and impact, or No finding}} | {{Stable source links}} | {{Weekly Problems observed delta or No write}} |
| `decision-extraction` | {{Future-precedent candidate plus missing rationale or authority, or No finding}} | {{Stable source links}} | {{Weekly Decision candidate or No write}} |
| `sop-extraction` | {{Repeated workflow candidate plus repeatability evidence, or No finding}} | {{Stable source links}} | {{Weekly SOP candidate or No write}} |
| `resource-extraction` | {{Future-useful knowledge candidate, or No finding}} | {{Stable source links}} | {{Weekly Resource candidate or No write}} |
| `documentation-template-check` | {{Record type, template used, and missing required information, or Complete}} | {{Edited source, template, and prior-comment links}} | {{Posted source comment \| Comment proposal \| No write}} |
| `chase-planning` | {{Recipient, stale commitment, useful question, timing, or No chase}} | {{Progress finding links}} | {{Draft proposal only or No write}} |
| `weekly-draft-projection` | {{Candidate counts and dedupe result}} | {{Candidate and prior receipt links}} | {{One upserted weekly Report delta}} |

### Receipt

- `window:` {{START_TIMESTAMP}}..{{END_TIMESTAMP}}
- `sources_checked:` {{Stable source names or locators}}
- `source_gaps:` {{Missing or stale sources, or none}}
- `documentation_template_checks:` {{Records checked, template used, and result}}
- `documentation_comments:` {{Posted comments and proposals, or none}}
- `next_watermark:` {{Advance only for successful connector reads}}

## Golden example

### Input and context

- Project: Northstar customer onboarding.
- Changed evidence: Ava's Task `NS-42` was edited today. It says Legal received
  an incomplete vendor packet for the third time and the team repeated the same
  four-step handoff, but its Outcome does not define done, Current status has no
  next action or date, and Evidence does not link the packet.
- Template: the Notion Task template requires those entries in Outcome, Current
  status, and Evidence.

### Accepted output

| Process | Result | Evidence | Owned write |
| --- | --- | --- | --- |
| `progress-extraction` | `NS-42` is blocked; launch timing is now at risk. | `task://NS-42`, `meeting://NS-42/2026-08-20` | Update Plan versus actual. |
| `problem-extraction` | Incomplete vendor packets have blocked Legal three times. | `meeting://NS-42/2026-08-20` | Add one recurring-problem candidate. |
| `decision-extraction` | No finding; no choice with rationale and authority was recorded. | Same Meeting notes | No write. |
| `sop-extraction` | The four-step handoff is a candidate, but its repeatability still needs owner review. | Same Meeting notes | Add one SOP candidate. |
| `resource-extraction` | No finding; the edited Task contains no standalone knowledge with future reuse value. | `task://NS-42` | No write. |
| `documentation-template-check` | Task template gaps: Outcome does not define done; Current status lacks the next action and date; Evidence does not link the packet. | `task://NS-42`, `template://task`, prior comments: none | Post: “For documentation, could you define done, add the next action and date, and link the vendor packet?” Do not edit the Task. |
| `chase-planning` | Draft a question to Ava asking when the complete packet will reach Legal. | `task://NS-42` | Save a chase proposal; do not send. |
| `weekly-draft-projection` | Two candidates and one progress delta; no matching fingerprints existed. | Current candidate set and prior receipt | Upsert one deduplicated weekly Report delta. |

### Why it passes

- Every lane reports independently from one shared evidence bundle.
- Candidates remain in the weekly draft; no Issue, Resource, Decision, or Skill
  is promoted. The only posted message is the policy-approved source comment;
  the stale-work chase remains a proposal.
- The documentation comment is based on the Task template and remains on the
  Task; Weekly does not process it.
- The result distinguishes `No finding` from unavailable evidence.

### Tempting negative

Create an Issue, publish a Resource, post “please add more detail” without
checking a template, add the documentation gap to Weekly, and send the chase.

Why it fails: Daily stages evidence for Weekly review and has no authority to
promote records, invent template requirements, edit source documents, route
documentation comments into Weekly, or send a chase.

### Transferable invariants

- Reuse one bounded evidence pass, but return a result for every process lane.
- Link every retained finding to its source and upsert by source fingerprint.
- Check only records created or edited today, use the matching configured
  template, and keep the resulting comment on the source record.

### Non-copyable facts and wording

- Northstar, Ava, the three occurrences, the four-step handoff, and every
  example locator belong only to this fixture.
- Generate fresh findings and wording from the current company's evidence.

### Proof receipt

```yaml
golden_case: company-os-daily-operating-update/northstar-blocked-handoff
source_refs:
  - synthetic Task, Meeting, and document locators in this example
qa_refs:
  - every process lane returns a result
  - Daily promotes nothing and makes no ungated write
accepted_because:
  - the Task is checked against its configured template and receives one specific source comment
heldout_required: true
review_input: candidate + transferable_invariants + current_company_context
review_excludes: Northstar fixture facts and wording
```

## Completion proof

- Every retained finding links to source evidence.
- Rerunning the same window produces no duplicate candidates.
- Failed connectors remain visible source gaps and do not advance their
  watermark.
- Documentation checks name the record and template used, list only missing
  requirements, and do not repeat an unresolved comment.
- The current weekly report identifies the last successful Daily receipt.
