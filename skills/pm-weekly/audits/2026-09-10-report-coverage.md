---
skill: pm-weekly
date: 2026-09-10
change_type: behavior
owner: skill-maintenance
status: pass
review_route: reviewer
before_ref: 2026-09-10-unblocking-weekly.md
after_ref: ../SKILL.md
reasoning_basis: eval
proof_artifacts: []
eval_required: yes
---

# Restore visible Weekly reporting coverage

## Change

- Before: accepted outputs and unblocking replaced Person progress; Company
  child links could satisfy coverage without a visible entry per Department.
- After: Project, Department and Company People progress cover supplied
  reporting people; Company has a named executive-summary entry per Department.
- Why: removing ratings must not remove progress visibility. Matching weakened
  template headings is not proof of the intended reporting contract.
- Tradeoff: concise Person status summaries coexist with exact accepted-output
  evidence; they must not repeat detailed artifact lists or blocker analysis.

## Proof

- New `visible_people_and_department_coverage` eval: four Projects, two
  Departments, five people; includes unaccepted in-progress work and an owner
  with insufficient progress evidence.
- Existing source fixtures remain unchanged; the coverage inventory adds an
  explicit synthetic reporting roster and a second Department.
- Fresh Hermes execution uses current repository source, local frozen inputs,
  JSON extraction followed by automation rendering. No provider or live install.
- Independent review checks user-visible coverage, not only template headings.
- `farplane lint evals --changed` and `git diff --check`: pass.
- Global skill validator: unavailable (`could not find Farplane repo root`).
- Runtime proof folder: `weekly-coverage.bA3U2K` in the private Hermes workspace.
- Fresh Hermes run completed in 4m15s: 14 artifacts rendered from JSON. Both
  Departments have executive entries; all five people have meaningful progress.
- Casey's unfinished progress and supplied review date remain visible; Jon is
  evidence-limited, not omitted or rated. Attribution preserves each role.
- All 14 rendered files match JSON text/headings; 108 local links resolve.
- Independent source, JSON and final Company/executive coverage review: pass.
- Some accepted-output and intervention detail still repeats across sections;
  this is a narrow coverage pass, not an all-rules prose-quality verdict.

## Evidence limits

- Synthetic local replay cannot prove complete real-company roster or live
  collection coverage. Missing roster/identity facts remain explicit gaps.
