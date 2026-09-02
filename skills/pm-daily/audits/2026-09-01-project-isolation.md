---
skill: pm-daily
date: 2026-09-01
change_type: behavior
owner: skill-maintenance
status: pass
review_route: self_check
before_ref: skills/pm-daily/SKILL.md
after_ref: skills/pm-daily/SKILL.md
reasoning_basis: first_principles
proof_artifacts:
  - tests/contracts/test_company_os.py
  - skills/pm-daily/evals/evals.json
eval_required: yes
---

# PM Daily Project-isolation audit

## Change

- Before: one skill invocation received every selected Project.
- After: the automation partitions once-fetched context and invokes the skill
  once per exact Project packet.
- Why: unrelated Project context and overlapping writes made failures harder to
  attribute.
- Tradeoff accepted: the parent automation must validate and deduplicate several
  isolated results.

## Binary rubric

| Check | Verdict | Evidence |
| --- | --- | --- |
| First-load sufficiency | pass | One-Project input, output, relation gate, and proof boundary are explicit. |
| Actor boundary | pass | Subagent spawning remains in the automation, not the reusable skill. |
| Maintenance locality | pass | Orchestration changed in the automation; Project analysis changed in PM Daily. |
| Composition clarity | pass | Fetch, partition, isolated analysis, merge, and apply are visible in the diagram. |
| Task success rate | unknown | Requires the next operated Daily eval. |
| Review TAS rate | unknown | No independent reviewer receipt exists yet. |

## Proof and follow-up

- Contract tests, eval lint, query lint, and full repository tests are required.
- Operate one Daily run and verify disjoint changed paths plus action deduplication.
