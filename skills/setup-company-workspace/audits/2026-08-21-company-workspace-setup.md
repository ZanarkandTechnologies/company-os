---
title: Initial company workspace setup skill audit
owner: skills/setup-company-workspace
status: accepted
kind: skill-audit
updated_at: 2026-08-21
---

# Initial audit

- Scope: install reviewed company context, automations, and skills into an existing separate Hermes runtime.
- Boundary: no profile overlay, connector credentials, live-state sync, or deletion.
- Deterministic proof: eight setup tests pass, including approved apply, unapproved
  refusal, preview-only behavior, source-boundary rejection, symlink rejection,
  unresolved-context rejection, collision preflight, and the normal nested
  Hermes workspace layout.
- Eval query review: `check_eval_queries.py --root .` passes all three natural
  operator cases; no skill name, checklist, invocation path, or answer-key
  wording appears in their prompts.
- Integration proof: a temporary approved source project installs only its
  workspace context, automation contract, and project skill while reporting
  zero deletions.
- Residual proof: each generated company project still requires its own owner
  review and fresh-session runtime proof.
- Registry validation: not applicable; HermesCorp has no generated skill
  registry or `check_skills.py` owner. JSON, line-count, eval-query, package,
  generated-project, and repository checks cover this package.

## Structure review

- First-load sufficiency: pass; the 79-line skill contains the source/runtime
  boundary, setup gates, command, proof, gotchas, and output contract.
- Project isolation: pass; the reusable package contains no customer name,
  private path, profile identifier, or connector choice.
- Proof-surface fit: pass for deterministic setup behavior; eight focused tests
  and an operated generated project cover preview, apply, refusal, isolation,
  and collision behavior.
- Independent review: deferred because this run disallows subagent delegation;
  inline checklist review found no unresolved structural blocker.

## Behavior eval review

- Suite: `skills/setup-company-workspace/evals/evals.json`.
- Dry run: `/private/tmp/hermescorp-setup-company-workspace-eval/20260820T205748Z-setup-company-workspace-structure/summary.json`
  projected all three cases with unchanged source hashes.
- Execution: interrupted after four minutes with no runner output, summary, or
  orphaned child process.
- Promotion decision: accept the deterministically proven scaffold and setup
  package; hold any claim that the three variable agent responses pass until a
  later Promptfoo run completes.
