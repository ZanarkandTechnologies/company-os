---
skill: notion-webhook-onboarding
date: 2026-08-20
change_type: behavior
owner: skill-maintenance
status: pass
review_route: reviewer
before_ref: tickets/TASK-0009/ticket.md
after_ref: tickets/TASK-0013/ticket.md
reasoning_basis: first_principles
proof_artifacts:
  - profiles/kamdar-ai/skills/notion-webhook-onboarding/tests/test_onboarding_cli.py
  - profiles/kamdar-ai/skills/notion-webhook-onboarding/evals/evals.json
  - .farplane/evals/runs/20260820-054455-notion-webhook-onboarding-candidate-r5/summary.json
  - .farplane/evals/runs/20260820-054710-notion-webhook-onboarding-candidate-r6/summary.json
  - .farplane/evals/runs/20260820-054922-notion-webhook-onboarding-browser-r7/summary.json
eval_required: yes
no_self_improve_reason: "This is a bounded first implementation with deterministic lifecycle tests and a focused behavior suite; no repeated optimization target or measured baseline warrants a Goal-backed self-improve loop."
---

# Skill Audit

## Change

- Before: operators manually composed Caddy, systemd, Doppler, webhook
  verification, table discovery, workspace enrollment, and smoke-test commands.
- After: one profile-owned Hermes skill wraps resumable JSON phases and uses
  ngrok as the only ingress for the MVP.
- Why: the operator needs a repeatable Notion activation flow, not deployment
  infrastructure guidance.
- Tradeoff accepted: ngrok becomes an external dependency and authenticated
  Doppler writes are required during onboarding.

## First-Principles Reasoning

- Objective: go from an existing Hermes profile to one observed Notion reply
  with the fewest technical decisions.
- Placement logic: conversational handoffs live in `SKILL.md`; repeatable system
  mutations live in one standard-library Python CLI; connector truth remains in
  the existing Notion plugin.
- Expected behavior delta: the operator supplies a root page and optional
  mention, completes browser login/verification, and leaves one test comment.
- Proof needed: deterministic phase tests, isolated profile installation,
  connector regressions, natural behavior evals, and independent review.

## Binary Rubric

| Check | Verdict | Evidence |
| --- | --- | --- |
| `first_load_sufficiency` | pass | `SKILL.md` contains the ordered preflight-to-live-reply path and human gates. |
| `reference_load_precision` | pass | No conditional reference is needed; deterministic detail is owned by the script. |
| `missing_context_rate` | pass | Root URL and optional mention are the only conversational inputs. |
| `noisy_context_rate` | pass | Proxy, VPS provisioning, Hermes installation, DNS, and model choice are explicitly excluded. |
| `duplicated_instruction_count` | pass | Skill owns routing; script owns execution; connector owns Notion behavior. |
| `prompt_size_tokens` | pass | `SKILL.md` remains below the 200-line envelope. |
| `task_success_rate` | pass | Latest targeted eval receipt for every one of four cases is TAS-A. |
| `review_tas_rate` | pass | Independent implementation re-review returned TAS-A. |
| `maintenance_locality` | pass | The skill and helper ship together in the Kamdar profile distribution. |
| `composition_clarity` | pass | Signature names inputs, reads, writes, work, and receipts. |

## Proof Artifacts

- Skill-local evals: four natural behavior cases; query-spoiler lint passes.
- Structure evals: ten onboarding CLI tests plus distribution and connector
  regression tests.
- Reviewer receipt: TAS-A/pass at `tickets/TASK-0013/artifacts/review.md`.
- Validator: JSON parsing, Python compilation, isolated Hermes profile install,
  and skill discovery pass.
- Eval required: yes; conversational routing can regress independently of the
  deterministic CLI.
- Evidence gaps: a live Linux/ngrok/Notion run remains the operator test and is
  not simulated by local tests.

## Before Behavior

- The operator had to understand and manually coordinate infrastructure and
  webhook activation commands.

## After Behavior

- Hermes executes preflight, ngrok setup, browser handoffs, verification,
  discovery, one-comment proof, and workspace lockdown as one resumable flow.

## Followups

- Run the skill on the company VPS and preserve the first live `status` receipt.
