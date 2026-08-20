---
name: financial-model
description: Prepare the weekly planning model once source assumptions have been approved.
metadata:
  hermes:
    requires_toolsets:
      - file
---

# Financial model

Use for a reviewable planning model once the ticket names its period, approved
source assumptions, scenarios, and finance reviewer. Save the model draft only
under the owning ticket's `artifacts/` directory. Use
[the template](templates/financial-model.md), cite every input, state missing
assumptions, and request finance review. Do not make a financing, spending, or
investment commitment.

Record `work_started` and `artifact_drafted`; leave the ticket blocked when an
assumption has no approved source or accountable owner.
