---
automation_id: company-os-daily-operating-update
automation_version: "0.4.0"
kind: company-os-automation
cadence: daily
status: draft
owner: HermesCorp
input_window: since-last-successful-receipt
opens_with:
  - outcome
  - why
processes:
  - progress-extraction
  - problem-extraction
  - decision-extraction
  - sop-extraction
  - resource-extraction
  - document-quality
  - record-completeness
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

- Tasks changed since the last successful receipt, including `Meeting` rows
  and their embedded notes.
- Documents changed in the same window.
- Current Projects, weekly report drafts, Decisions, Resources, Skills, and
  People needed for context and deduplication.

## Process lanes

Each lane reads the same deduplicated evidence bundle and writes only its owned
section in the current weekly report draft.

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

> ### `document-quality`
>
> **Looks for:** changed or high-risk documents with stale facts, missing ownership,
> weak structure, or unclear evidence.
>
> **Writes:** proposed improvements. It does not comment or edit without policy.

> ### `record-completeness`
>
> **Looks for:** changed Tasks, Meeting notes, and documents whose missing
> owner, result, rationale, evidence, next action, or source detail prevents an
> accurate report or a useful promotion decision.
>
> **Writes:** one specific question on the source record when the company has
> approved internal comments for that surface; otherwise a comment proposal.
> It never asks for facts available elsewhere or repeats an unresolved request.

> ### `chase-planning`
>
> **Looks for:** stale commitments with a named owner and a useful next question.
>
> **Writes:** proposed chases with recipient, reason, channel, and timing. Sending
> remains separately gated.

> ### `weekly-draft-projection`
>
> **Reads:** the candidate sets produced by the other lanes.
>
> **Writes:** one deduplicated delta to the matching current weekly Report.

```text
daily_operating_update(window, sources, current_weekly_report)
  -> weekly_report_delta + candidate_sets + information_requests + chase_proposals + receipt
state: source watermarks advance only after successful reads; candidates upsert by source fingerprint
```

## Flow

1. Resolve the last successful watermark and collect one bounded evidence
   bundle with stable source locators.
2. Deduplicate unchanged or previously processed evidence.
3. Run the six extraction and quality lanes against that bundle.
4. Run `record-completeness` against the bundle and lane gaps. Ask only for
   missing facts that would change the report or a promotion decision. Post a
   source-local comment only under an approved comment policy; otherwise save
   a proposal.
5. Run `chase-planning` from the progress results. Send nothing unless the
   company has approved the channel, timing, recipients, and frequency policy.
6. Run `weekly-draft-projection` and upsert by source fingerprint.
7. Write a receipt containing the evidence window, sources checked, source
   gaps, candidate counts, information requests, proposed chases, and next
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
| `document-quality` | {{Changed or high-risk document gap, or No finding}} | {{Stable source links}} | {{Proposed improvement or No write}} |
| `record-completeness` | {{Missing fact, why it blocks reporting or promotion, and the one useful question, or Complete}} | {{Changed source and prior-request links}} | {{Posted internal comment \| Comment proposal \| No write}} |
| `chase-planning` | {{Recipient, stale commitment, useful question, timing, or No chase}} | {{Progress finding links}} | {{Draft proposal only or No write}} |
| `weekly-draft-projection` | {{Candidate counts and dedupe result}} | {{Candidate and prior receipt links}} | {{One upserted weekly Report delta}} |

### Receipt

- `window:` {{START_TIMESTAMP}}..{{END_TIMESTAMP}}
- `sources_checked:` {{Stable source names or locators}}
- `source_gaps:` {{Missing or stale sources, or none}}
- `information_requests:` {{Posted comments and proposals, or none}}
- `next_watermark:` {{Advance only for successful connector reads}}

## Golden example

### Input and context

- Project: Northstar customer onboarding.
- Changed evidence: Task `NS-42` has been blocked for three days. Its Meeting
  notes say Legal received an incomplete vendor packet for the third time, Ava
  owns the follow-up, and the team again used the same four-step handoff.
- Changed document: `Vendor handoff checklist`, which has no owner, review date,
  or required-input list.

### Accepted output

| Process | Result | Evidence | Owned write |
| --- | --- | --- | --- |
| `progress-extraction` | `NS-42` is blocked; launch timing is now at risk. | `task://NS-42`, `meeting://NS-42/2026-08-20` | Update Plan versus actual. |
| `problem-extraction` | Incomplete vendor packets have blocked Legal three times. | `meeting://NS-42/2026-08-20` | Add one recurring-problem candidate. |
| `decision-extraction` | No finding; no choice with rationale and authority was recorded. | Same Meeting notes | No write. |
| `sop-extraction` | The four-step handoff is a candidate, but its repeatability still needs owner review. | Same Meeting notes | Add one SOP candidate. |
| `resource-extraction` | The checklist has future reuse value for every vendor handoff. | `doc://vendor-handoff-checklist` | Add one Resource candidate. |
| `document-quality` | The checklist lacks an owner, review date, and required inputs. | Same document | Propose those three additions; do not edit. |
| `record-completeness` | The evidence never names which packet inputs were missing, so the blocker cannot be prevented or documented accurately. Ask Ava: “Which required packet inputs were missing, and where should the complete list live?” | `task://NS-42`, prior requests: none | Post one Task comment because internal Task comments are approved; do not edit the notes or checklist. |
| `chase-planning` | Draft a question to Ava asking when the complete packet will reach Legal. | `task://NS-42` | Save a chase proposal; do not send. |
| `weekly-draft-projection` | Four candidates and one progress delta; no matching fingerprints existed. | Current candidate set and prior receipt | Upsert one deduplicated weekly Report delta. |

### Why it passes

- Every lane reports independently from one shared evidence bundle.
- Candidates remain in the weekly draft; no Issue, Resource, Decision, or Skill
  is promoted. The only posted message is the policy-approved source comment;
  the stale-work chase remains a proposal.
- The result distinguishes `No finding` from unavailable evidence.

### Tempting negative

Create an Issue, publish the checklist as a Resource, turn the handoff into a
Skill, post “please add more detail” on every source, and send the chase.

Why it fails: Daily stages evidence for Weekly review and has no authority to
promote records, edit source documents, repeat vague information requests, or
send a chase.

### Transferable invariants

- Reuse one bounded evidence pass, but return a result for every process lane.
- Link every retained finding to its source and upsert by source fingerprint.
- Ask for missing information only when the answer changes a report or
  promotion decision; distinguish that request from chasing stale work.

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
  - one evidence bundle produces source-linked, deduplicated lane outputs and one specific information request
heldout_required: true
review_input: candidate + transferable_invariants + current_company_context
review_excludes: Northstar fixture facts and wording
```

## Completion proof

- Every retained finding links to source evidence.
- Rerunning the same window produces no duplicate candidates.
- Failed connectors remain visible source gaps and do not advance their
  watermark.
- Information requests name the missing fact and its consequence, and reruns
  do not repeat an unresolved comment.
- The current weekly report identifies the last successful Daily receipt.
