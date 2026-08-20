---
template_id: ticket-template
template_version: "0.2.6"
ticket_id: TASK-0011
title: Complete Drive to Company Knowledge onboarding MVP
status: ready_for_operator_test
created_at: 2026-08-20T12:00:00+08:00
updated_at: 2026-08-20T13:00:00+08:00
claimed_by: codex-root
depends_on: [TASK-0008]
source_refs:
  - docs/prd-hermes-company-os-onboarding.md
  - .agents/skills/hermes-company-os/SKILL.md
---

# TASK-0011: Complete Drive to Company Knowledge onboarding MVP

## Summary

Implement the smallest complete conversational onboarding lifecycle: a missing
`company-knowledge` skill backed by one owner-approved Google Drive boundary.

## Scope

- **In:** resumable receipt, deterministic next step, bounded probe/doctor
  evidence, deterministic draft render, external skill-creator review receipt,
  preview, hash-bound approval, collision-safe promotion, and health gate.
- **Out:** live Drive writes, other providers/components, existing-skill update,
  setup UI, account-wide ingestion, or companies over 20 people.
- **Invariant:** component `SKILL.md` remains the sole runtime configuration.

## Delta

> **Before:** Hermes could scaffold and diagnose pieces of onboarding but could
> not resume or safely install a proven company component end to end.
>
> **After:** one CLI drives the accepted Drive → Knowledge lifecycle and returns
> `healthy` only after every human and proof gate passes.
>
> **Example:** an interrupted session resumes at its next unanswered question,
> installs the exact reviewed draft, answers inside its approved fixture root,
> and refuses the same lookup outside that root.

## Done / Proof

- [x] Start inventories all five component skills and persists resumable state.
- [x] Next-step resolver covers declared and consented discovery branches.
- [x] Draft contains provider, boundary, role, exclusions, write policy, and
      health question with no unresolved placeholders.
- [x] External skill-creator receipt and owner approval bind the exact draft hash.
- [x] Promotion refuses collision; healthy requires inside success, provenance,
      and outside refusal.
- [x] Focused and repository tests pass in isolated temporary workspaces.
- [x] Independent re-review accepts the repaired slice at TAS-A.

## State

- **Current:** local MVP is ready for operator testing.
- **Next:** begin a live session with one owner-approved Drive test folder and
  representative company Knowledge question.

## Links

- Implementation: `.agents/skills/hermes-company-os/scripts/onboarding.py`
- Tests: `.agents/skills/hermes-company-os/tests/test_onboarding.py`
- Proof: `artifacts/qa.md`
- Review: `artifacts/review.md`
