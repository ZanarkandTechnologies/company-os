---
name: compliance-report
description: Draft a cited compliance report from verified evidence for named reviewer approval.
metadata:
  hermes:
    requires_toolsets:
      - file
---

# Compliance report

Use this skill when a ticket requests a reviewable compliance register, control
assessment, or action report. It creates a draft, not legal advice, a legal
opinion, or a certification.

## Skill signature

```text
compliance_report(ticket, verified_sources, reviewer)
  -> reviewable compliance draft | blocked
reads: canonical ticket, verified DriveFileRef(s), approved source excerpts
writes: tickets/TASK-XXXX/artifacts/compliance-report-draft.md + progress event
proof: every finding has source provenance, owner, due state, and named review
```

## Todo

1. Require an exact ticket, a named compliance reviewer, and verified source
   references from `drive-company-files`. If evidence lacks provenance or a
   source is missing, keep the ticket blocked and record the gap.
2. Extract only supported obligations, control observations, evidence gaps,
   owners, and due dates. Do not infer a regulation, legal conclusion, control
   effectiveness, or certification from incomplete source material.
3. Populate [the compliance-report template](templates/compliance-report.md)
   under the owning ticket's `artifacts/` directory. Cite each finding with its
   verified source file ID/title and the relevant source location or excerpt.
4. Append `work_started` and `artifact_drafted` events with source provenance to
   the ticket's `progress.md`, set the artifact to review pending, and name the
   compliance reviewer.
5. Mark the ticket done only after the named reviewer records an explicit
   approval. Reviewer changes or rejected findings return the ticket to blocked
   or in-progress with a new source-backed action.

## Gates and completion

- Reject unverified Drive references, missing reviewer assignment, and findings
  with no source citation, owner, or next action.
- Keep raw private contacts, Drive root IDs, OAuth details, and unrelated
  employee data out of the draft and progress history.
- A populated draft is complete only when every register row has a disposition,
  evidence citation, accountable owner, and review state; it is never a claim
  of legal compliance.

## Output

Return the artifact path, cited source IDs/titles, unresolved evidence gaps,
named reviewer, and review state. Do not report a legal conclusion.
