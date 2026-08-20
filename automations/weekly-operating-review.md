---
automation_id: company-os-weekly-operating-review
automation_version: "0.1.0"
kind: company-os-automation
cadence: weekly
status: draft
owner: HermesCorp
input_window: current-reporting-week
---

# Weekly operating review

## Objective

Turn the accumulated weekly draft into an executive snapshot, selectively
promote future-useful records, and open the next reporting window.

## Reads

- Current weekly report draft and its Daily receipts.
- Previous finalized report and current Project context.
- Related Tasks, Decisions, Resources, Skills, and People.

## Flow

1. Reconcile the week's planned work against actual task evidence. Carry
   unresolved commitments forward by reference; never delete canonical Tasks.
2. Produce the three-sentence executive summary, what went well, main problems,
   follow-ups, and proposed next-week commitments.
3. Review each accumulated candidate:
   - promote an accepted problem into Tasks with `Type = Issue`;
   - promote a decision only when it has future precedent and confirmed
     rationale and authority;
   - promote content into Resources only when the future-value gate passes;
   - promote an SOP into Skills only when it is repeatable and owner-reviewed;
   - leave duplicates, weak evidence, and low-value observations in the report
     with a disposition.
4. Review documentation-quality proposals. Apply or comment only under the
   company's approved write policy.
5. Freeze the weekly report as immutable and preserve links to every promoted
   record and source receipt.
6. Update each Project's short Current context from the finalized report, open
   the next weekly draft, and stage next-week commitments for owner approval.

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
