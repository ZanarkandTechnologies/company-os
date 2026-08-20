---
template_id: ticket-template
template_version: "0.2.6"
ticket_id: TASK-0008
title: Package Hermes Company OS for operator testing
status: ready_for_operator_test
created_at: 2026-08-19T05:00:00+08:00
updated_at: 2026-08-19T08:10:00+08:00
claimed_by: codex-root
depends_on: [TASK-0007]
---

# TASK-0008: Package Hermes Company OS for operator testing

## Summary

Rename the proven onboarding owner to `hermes-company-os`, add a deterministic
standard-library helper for discovering and scaffolding company skills, and
embed five opinionated component templates without introducing a second stack
or configuration schema.

## Scope

- **In:** rename the existing skill owner; preserve its Drive doctor behavior;
  add `inventory`, `fetch`, `scaffold`, and `validate`; embed Work, People,
  Knowledge, Communications, and Decisions templates; add focused tests,
  validation, eval proof, and independent review.
- **Out:** provider API implementation, OAuth handling, external writes,
  production tenant storage, setup UI, or installing unresolved company skills.
- **Invariant:** an installed component's `SKILL.md` is its configuration and
  operating contract. The helper may fetch that file but must not derive or
  persist a parallel stack schema.

## Delta

> **Before:** `hermes-sme-onboarding` proves one Drive workflow but has no
> deterministic helper or reusable component templates.
>
> **After:** `hermes-company-os` inventories and fetches installed component
> skills, scaffolds one of five embedded templates, validates its contract, and
> retains the approval-gated provider doctor.
>
> **Example:** `company_skills.py scaffold --component knowledge` creates a
> blocked `company-knowledge` draft; the conversational skill fills its approved
> source through `skill-creator` before installation.

## Done / Proof

- [x] Old owner removed and `hermes-company-os` is discoverable.
- [x] Helper commands pass focused unit and command-line tests.
- [x] Five templates scaffold into valid, safely blocked drafts.
- [x] Existing Google Drive behavior eval still passes.
- [x] Focused validators, QA audit, and independent review pass for the declared
      Knowledge/Drive operator-test boundary.

## State

- **Current:** ready for narrow operator testing of Knowledge/Drive and the
  deterministic component-template mechanics.
- **Next:** run the operator conversation against the connected Drive and choose
  a company-only folder boundary; multi-component Notion remains deferred.
