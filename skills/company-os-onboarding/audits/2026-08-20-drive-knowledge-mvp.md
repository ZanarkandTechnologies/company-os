---
skill: hermes-company-os
date: 2026-08-20
change_type: behavior
owner: skill-maintenance
status: pass
review_route: reviewer
ticket_ref: tickets/TASK-0011/ticket.md
eval_required: yes
---

# Drive → Knowledge MVP Skill Audit

## Delta

- Before: the skill described onboarding but had no resumable lifecycle or safe
  deterministic promotion path.
- After: one driver derives the next action, records sanitized evidence, renders
  one accepted Knowledge skill, requires exact external skill-creator review
  and owner approval, promotes without overwrite, and gates healthy on scoped
  success/refusal evidence.
- Tradeoff: only missing Google Drive-backed Knowledge skills are supported.

## QA Verdicts

| Check | Verdict | Evidence |
| --- | --- | --- |
| ownership / lean reuse | pass | Existing skill, helper, and template owners were extended. |
| first-load / line budget | pass | Normal route and gates are visible in 191 lines. |
| parallel config | pass | Receipt is temporary; component skill is runtime config. |
| deterministic proof | pass | Seven isolated helper/lifecycle tests pass. |
| review integrity | pass | Missing/mismatched external review hash is refused. |
| privacy / discovery | pass | Bounded read-only schema and secret-field rejection. |
| promotion / health | pass | Collision refusal and three-part health gate pass. |
| full skill validator | deferred | Installed validator requires a Farplane repo root. |
| live Drive eval | deferred | Requires an owner-approved test folder. |

## Proof

- Focused Python suite: 7 passed.
- Python compile and skill-creator quick validation: passed.
- Repository suite: 29 passed.
- Independent repair re-review: TAS-A.
- `no_self_improve_reason`: no operator-use baseline exists yet.
