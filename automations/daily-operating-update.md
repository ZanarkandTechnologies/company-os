---
automation_id: company-os-daily-operating-update
automation_version: "0.1.0"
kind: company-os-automation
cadence: daily
status: draft
owner: HermesCorp
input_window: since-last-successful-receipt
---

# Daily operating update

## Objective

Ingest each changed source once, detect useful operating signals, and build the
current weekly report without prematurely creating permanent company records.

## Reads

- Tasks changed since the last successful receipt, including `Meeting` rows
  and their embedded notes.
- Documents changed in the same window.
- Current Projects, weekly report drafts, Decisions, Resources, Skills, and
  People needed for context and deduplication.

## Flow

1. Resolve the last successful watermark and collect one bounded evidence
   bundle with stable source locators.
2. Deduplicate unchanged or previously processed evidence.
3. Run independent analyses over that same bundle:
   - summarize meaningful task progress and identify stale commitments;
   - add or update problem candidates in the weekly draft;
   - stage decision candidates only when future precedent may matter;
   - stage SOP candidates only when behavior appears repeatable;
   - stage Resource candidates only when the future-value filter passes;
   - inspect changed or high-risk documents and propose quality improvements.
4. Upsert findings into the matching current weekly report by source
   fingerprint. Do not append a duplicate finding on rerun.
5. Propose bounded progress chases for stale Tasks. Send nothing unless the
   company has approved the channel, timing, recipients, and frequency policy.
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
