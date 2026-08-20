---
skill: hermes-company-os
date: 2026-08-20
change_type: structure
owner: skill-maintenance
status: pass
review_route: reviewer
before_ref: tickets/TASK-0011/ticket.md
after_ref: tickets/TASK-0012/ticket.md
reasoning_basis: first_principles
proof_artifacts:
  - .agents/skills/hermes-company-os/tests/test_workspace_template.py
  - .agents/skills/hermes-company-os/evals/evals.json
eval_required: yes
---

# Skill Audit

## Change

- Before: five component skills owned company-specific runtime configuration.
- After: one `.hermes.md` indexes five company surfaces; connectors own access
  and a separate receipt owns transient health.
- Why: the company stack is small enough to remain one readable operating map.
- Tradeoff accepted: large or permission-segmented companies may later need
  multiple workspaces or specialized procedural skills.

## First-Principles Reasoning

- Objective: let Hermes route ordinary company questions without first decoding
  the company's application topology.
- Placement logic: stable source routing belongs in startup workspace context;
  mutable health evidence belongs outside it; provider mechanics stay provider-owned.
- Expected behavior delta: onboarding asks for the stack once, tests routes, and
  collaboratively fills one template instead of scaffolding component skills.
- Proof needed: static template validation, natural behavior evals, independent
  review, and later owner-authorized representative connector checks.

## Binary Rubric

| Check | Verdict | Evidence |
| --- | --- | --- |
| `first_load_sufficiency` | pass | `SKILL.md` contains context, signature, numbered path, gotchas, proof, and output. |
| `reference_load_precision` | pass | Drive notes load only when Drive discovery is needed. |
| `missing_context_rate` | pass | Normal path is fully visible in `SKILL.md`. |
| `noisy_context_rate` | pass | The row template and operator detail are externally linked. |
| `duplicated_instruction_count` | pass | Template owns shape; skill owns execution; receipt owns health. |
| `prompt_size_tokens` | pass | `SKILL.md` is below the 200-line envelope. |
| `task_success_rate` | unknown | Live connector eval is correctly deferred; template/package proof passed. |
| `review_tas_rate` | pass | Independent rerun accepted template/package readiness at TAS-A. |
| `maintenance_locality` | pass | Workspace template is owned under the onboarding skill assets. |
| `composition_clarity` | pass | Signature names inputs, reads, writes, gates, routes, and failure conditions. |

## Proof Artifacts

- Skill-local evals: four updated natural cases in `evals/evals.json`.
- Structure evals: five focused template/package tests pass with
  `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .agents/skills/hermes-company-os/tests -p 'test_*.py' -v`.
- Reviewer receipt: initial TAS-B correctly identified stale component helpers;
  after their removal and a no-scaffold regression test, the rerun passed TAS-A
  at `tickets/TASK-0012/artifacts/review.md`.
- Validator: YAML/JSON parse and template-contract assertions pass.
- Eval required: yes; provider-backed behavior remains explicitly deferred in
  `evals/deferred.json` until isolated or owner-authorized connector routes exist.

## Before Behavior

- Onboarding produced or updated `company-work`, `company-people`,
  `company-knowledge`, `company-comms`, and `company-decisions` skills.

## After Behavior

- Onboarding renders one versioned `.hermes.md` with repeatable platform rows
  under Work, People, Knowledge, Communications, and Decisions.

## Followups

- Run the provider-backed canonical evals when isolated or owner-authorized
  connector routes are available; do not conflate that with template readiness.
