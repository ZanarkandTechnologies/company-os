---
skill: hermes-company-os
date: 2026-08-19
change_type: structure
owner: skill-maintenance
status: pass
review_route: reviewer
before_ref: .agents/skills/hermes-sme-onboarding/SKILL.md
after_ref: .agents/skills/hermes-company-os/SKILL.md
reasoning_basis: first_principles
proof_artifacts:
  - tickets/TASK-0008/artifacts/lean-receipt.md
  - .farplane/evals/runs/20260819-073656-hermes-company-os-drive-smoke-r2/summary.json
  - .farplane/evals/runs/20260819-074141-hermes-company-os-scaffold-smoke-r3/summary.json
  - .farplane/evals/runs/20260819-074824-hermes-company-os-remaining-cases-r3/summary.json
  - tickets/TASK-0008/artifacts/validation-receipt.md
  - tickets/TASK-0008/artifacts/completion-review.md
eval_required: yes
---

# Skill Audit

## Change

- Before: the onboarding prototype had one provider workflow but no reusable
  component scaffold or deterministic package inspection.
- After: Hermes Company OS owns conversational setup while one standard-library
  helper inventories, fetches, scaffolds, and validates five embedded component
  templates.
- Why: make the accepted product shape operator-testable without a setup UI or
  parallel configuration model.
- Tradeoff accepted: Hermes owns five opinionated templates and must evolve them
  deliberately as component behavior changes.

## First-Principles Reasoning

- Objective: make company setup repeatable while keeping company meaning inside
  readable skills.
- Placement logic: deterministic filesystem work belongs in `scripts/`; output
  skeletons belong in `assets/templates/`; provider judgment remains first-load
  skill behavior.
- Expected behavior delta: a missing component starts from a stable blocked
  template and an existing component is fetched whole rather than reconstructed.
- Proof needed: unit tests, template scaffold checks, validators, operated
  behavior eval, and independent review.

## Binary Rubric

| Check | Verdict | Evidence |
| --- | --- | --- |
| `first_load_sufficiency` | pass | The skill exposes inventory, diagnosis, scaffold, authoring, proof, and closeout. |
| `reference_load_precision` | pass | Drive detail is conditional; templates and helper have exact use conditions. |
| `missing_context_rate` | pass | Drive and scaffold clean-room cases both completed from skill plus supplied state. |
| `noisy_context_rate` | pass | Five template bodies are not loaded during every onboarding call. |
| `duplicated_instruction_count` | pass | Component SKILL.md remains the sole configuration contract. |
| `prompt_size_tokens` | pass | Root SKILL.md remains below the 200-line contract. |
| `task_success_rate` | pass | Four unit tests pass and all three canonical SLC behavior cases earned A. |
| `review_tas_rate` | pass | Narrowed operator-testing re-review returned TAS-A. |
| `maintenance_locality` | pass | Helper, templates, QA, provider reference, evals, and audit are co-located. |
| `composition_clarity` | pass | Script copies/checks; skill-creator judges/customizes; provider tools connect. |

## Proof Artifacts

- Skill-local evals: `.agents/skills/hermes-company-os/evals/evals.json`
- Structure evals: package and generated draft pass `quick_validate.py`; all
  five embedded templates scaffold into validator-compatible packages; helper
  unit suite passes 3/3; eval-query lint passes.
- Reviewer receipt: `tickets/TASK-0008/artifacts/completion-review.md` (TAS-A).
- Validator: skill-creator quick validator plus package helper validation.
- Eval required: yes; Drive boundary, embedded scaffold, and connection-failure
  cases passed A. Multi-component Notion is explicitly deferred until isolated.
- Evidence gaps: multi-component Notion proof deferred; full Farplane validator replaced by
  the ticket-level focused validation receipt because its installed copy cannot
  locate the required repository root.

## Before Behavior

- The agent could diagnose Drive but had to construct component packages from
  generic instructions.

## After Behavior

- The agent can inspect installed company skill contracts and copy exactly one
  domain-specific, safely blocked template before company customization.

## Followups

- `no_self_improve_reason`: this packages a newly accepted product boundary;
  there is no stable operator-use baseline yet for an optimization loop.
