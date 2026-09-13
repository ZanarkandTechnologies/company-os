---
skill: pm-daily
date: 2026-09-10
change_type: behavior
owner: skill-maintenance
status: pass
review_route: reviewer
eval_required: yes
---

# Preserve truth across corrections, outages and repeated runs

- Before: history retention did not explicitly supersede resolved claims;
  duplicate-message rules did not cover prior runs; incomplete comments could
  look like evidence that a question had not been asked or answered.
- After: newer evidenced corrections supersede current claims; missing reads
  retain last supported evidence; repeated questions need a new supported trigger.
- Fresh Hermes resilience replay passed: accepted 120-row validation retained,
  approval resolved without invented publication, no repeated questions,
  foreign-client claims or executed source injection. Independent review passed.
- Related Step 4 supplied-readback replay blocked stale, unreadable and
  render-conflicted effects. No provider operations were attempted.
- Proof: `preprod-hardening.VRGLcA/review.md` under the private Hermes workspace.
- Eval/query lint and diff checks passed; global skill validator could not find
  its Farplane root. No install or end-to-end production claim.
- Wider risk map: [evaluation guide](../../../docs/evaluation.md#pre-production-hardening--2026-09-10).
