---
skill: pm-weekly
date: 2026-09-01
change_type: behavior
owner: skill-maintenance
status: pass
review_route: self_check
before_ref: skills/pm-weekly/SKILL.md
after_ref: skills/pm-weekly/SKILL.md
reasoning_basis: first_principles
proof_artifacts:
  - tests/contracts/test_company_os.py
  - skills/pm-weekly/evals/evals.json
eval_required: yes
---

# PM Weekly evidence-rollup audit

## Change

- Before: long-term consolidation required repeated or approved evidence but did
  not fully specify Person and workflow grouping.
- After: accepted outputs group by Person ID; comparable workflow samples group
  by workflow key with timing, acceptance, and baseline controls preserved.
- Why: Department reporting must answer who produced what, while SOP learning
  must distinguish a fast observation from a calibrated standard.
- Tradeoff accepted: missing active/wait measurements remain visible gaps and may
  delay baseline promotion.

## Binary rubric

| Check | Verdict | Evidence |
| --- | --- | --- |
| First-load sufficiency | pass | Grouping, comparison, promotion, and deduplication rules are explicit. |
| Golden calibration | pass | One-off, repeated accepted, faster candidate, and approved baseline branches differ. |
| Maintenance locality | pass | Skill owns decisions; Project, Department, Person, and SOP templates own artifact shape. |
| Composition clarity | pass | Project evidence feeds reports and entity memory through distinct grouping keys. |
| Task success rate | unknown | Requires the next operated Weekly eval. |
| Review TAS rate | unknown | No independent reviewer receipt exists yet. |

## Proof and follow-up

- Contract tests, eval lint, query lint, and full repository tests are required.
- Operate one Weekly run containing comparable timed samples and inspect the
  Department ledger, Person evidence, SOP interval, and unchanged baseline.
