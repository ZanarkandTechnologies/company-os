---
name: cash-flow-forecast
description: Draft a reviewable 13-week cash forecast from approved finance assumptions.
metadata:
  hermes:
    requires_toolsets:
      - file
---

# Cash-flow forecast

Use for a dated runway or cash-planning deliverable. Require approved opening
cash, pricing/revenue case, operating-cost assumption, and a named finance
reviewer. Read only verified ticket inputs or approved Drive evidence; do not
invent figures, funding availability, or a financing recommendation.

Populate [the template](templates/cash-flow-forecast.md) in the owning ticket's
`artifacts/` directory. Cite every source and label every unapproved scenario.
Record `work_started` and `artifact_drafted` in `progress.md`, then set the
ticket to `awaiting_review`. Missing finance assumptions remain a separate
human requirement with its own follow-up schedule.

Completion is a reviewable planning draft, not a treasury instruction or a
financial commitment.
