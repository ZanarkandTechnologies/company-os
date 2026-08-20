---
automation_id: company-os-daily-operating-update
automation_version: "0.2.0"
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
  -> weekly_report_delta + candidate_sets + chase_proposals + receipt
state: source watermarks advance only after successful reads; candidates upsert by source fingerprint
```

## Flow

1. Resolve the last successful watermark and collect one bounded evidence
   bundle with stable source locators.
2. Deduplicate unchanged or previously processed evidence.
3. Run the six extraction and quality lanes against that bundle.
4. Run `chase-planning` from the progress results. Send nothing unless the
   company has approved the channel, timing, recipients, and frequency policy.
5. Run `weekly-draft-projection` and upsert by source fingerprint.
6. Write a receipt containing the evidence window, sources checked, source
   gaps, candidate counts, proposed chases, and next watermark.

## Write boundary

The Daily automation may update the current weekly draft and explicit task
progress supported by source evidence. It must not promote Issues, Decisions,
Resources, or Skills; finalize reports; invent rationale; or send unapproved
external messages.

## Completion proof

- Every retained finding links to source evidence.
- Rerunning the same window produces no duplicate candidates.
- Failed connectors remain visible source gaps and do not advance their
  watermark.
- The current weekly report identifies the last successful Daily receipt.
