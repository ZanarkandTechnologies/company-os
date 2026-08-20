---
template_id: ticket-template
template_version: "0.2.6"
ticket_id: TASK-0007
title: Codex-first Hermes SME onboarding skill prototype
status: ready_for_operator_test
created_at: 2026-08-19T04:24:43+08:00
updated_at: 2026-08-19T04:38:00+08:00
claimed_by: codex-root
depends_on: []
---

# TASK-0007: Codex-first Hermes SME onboarding skill prototype

## Summary

Prove one honest onboarding loop inside Codex: a company owner selects Google
Drive for the Knowledge component; Hermes verifies the connected tool, samples
the structure read-only, returns an evidence-backed workability verdict, and
uses `skill-creator` to draft a template-compliant `company-knowledge` skill.
The prototype stops before installing that component skill when no approved
company root has been selected.

## Scope

- **In:** one project-local onboarding skill under `.agents/skills`; one real
  connected Google Drive probe; bounded metadata-only structure sampling; a
  five-dimension doctor verdict; a template-compliant component-skill draft;
  skill-local QA/evals; validation and independent review.
- **Out:** a setup UI, a new connector CLI, OAuth implementation, writes to
  Drive, broad file ingestion, all five company components, production rollout,
  or installing a component skill whose source boundary is unresolved.
- **Constraint:** connector credentials stay with the existing Codex plugin;
  source-controlled artifacts contain no token, email address, Drive ID, or
  unrelated private filename.

## Delta

> **Before:** Hermes onboarding exists only as a conversation design and has no
> discoverable Codex skill or operated connection proof.
>
> **After:** Codex can load `hermes-sme-onboarding`, run a bounded doctor pass,
> draft a company component skill through the standard template, and stop at a
> concrete source-selection gate.
>
> **Example:** Google Drive authentication and listing pass, but a mixed
> personal root with no Shared Drive scores `fragile`; onboarding recommends a
> dedicated company folder and leaves `company-knowledge` uninstalled until the
> owner selects that root.

## Contract

```text
onboard_company(goal, selected_tools?, declared_structure?)
  -> component_skill_drafts + workability_report + health_receipt

doctor_component(component, connector, bounded_probe)
  -> blocked | fragile | workable | strong
```

## Change Plan

### Change 1: Codex onboarding skill

Create a template-compliant Tier 3 skill that owns connector selection,
component mapping, declared/discovered branches, read-only doctor checks,
approval gates, `skill-creator` routing, and health receipts.

### Change 2: One live Knowledge/Drive slice

Use the connected Google Drive plugin to verify identity and list capability,
sample only root metadata and recent viewed metadata, score the observed
structure, and write a sanitized receipt.

### Change 3: Generated skill proof

Draft `company-knowledge` with the standard skill sections, an explicit
unresolved-root failure, and a natural eval row. Do not publish it to
`.agents/skills` until the owner approves a company root.

## Done / Proof

- [x] Codex project-skill discovery points to `.agents/skills`.
- [x] Onboarding `SKILL.md`, QA, provider reference, and eval rows validate.
- [x] Live Drive health receipt records bounded, sanitized evidence.
- [x] Workability verdict explains every dimension and proposes the smallest
      safe repair.
- [x] Generated `company-knowledge` draft follows skill-template `0.3.2` and
      refuses an unscoped search.
- [x] Eval execution and independent review accept the prototype or name the
      exact blocker.

## State

- **Current:** prototype accepted at TAS-A and ready for the owner-operated root
  selection step.
- **Next:** select an existing company-only Drive folder or explicitly approve
  creation of a dedicated folder; then install and test `company-knowledge`.
