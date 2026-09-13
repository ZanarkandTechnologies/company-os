---
skill: pm-weekly
date: 2026-09-10
change_type: behavior
owner: skill-maintenance
status: pass
review_route: reviewer
eval_required: yes
---

# Preserve closed-Project results and honest interval coverage

- Before: current Active-only discovery could lose a Project's weekly results;
  missing intervals could appear complete, and week-keyed snapshots could be overwritten.
- After: report the frozen interval Project set, including known closures;
  do not create next-week memory for closed Projects; preserve gaps and run evidence.
- Fresh Hermes replay retained the archived Project and Casey without reopening
  work, and exposed the missing September 8–9 interval. Targeted review passed.
- Review caught raw IDs, duplicate carry-forward and unsafe historical-receipt
  recovery wording; source was tightened and the Hermes correction passed
  independent targeted review. All three Active Projects retain next-week
  memory; archived Storefront Design has none and is not reopened.
- Proof: `preprod-hardening.VRGLcA/review.md` under the private Hermes workspace.
- Eval/query lint and diff checks passed; global skill validator could not find
  its Farplane root. Run-path changes remain source-reviewed, not crash-tested.
- Wider risk map: [evaluation guide](../../../docs/evaluation.md#pre-production-hardening--2026-09-10).
