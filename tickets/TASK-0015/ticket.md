---
template_id: ticket-template
template_version: "0.2.6"
ticket_id: TASK-0015
title: Scaffold lean company source projects
status: done
created_at: 2026-08-21T00:00:00+08:00
updated_at: 2026-08-21T04:30:00+08:00
claimed_by: codex-root
source_refs:
  - templates/company-project/AGENTS.md
  - skills/setup-company-workspace/SKILL.md
---

# TASK-0015: Scaffold lean company source projects

## Summary

Turn the proven dedicated-company source/runtime split into a company-agnostic project
scaffold composed from HermesCorp's canonical workspace, automation, skill, and
filesystem-eval assets.

## Scope

- **In:** root `workspace.hermes.md`, automations, project skills, evals,
  scripts, tests, explicit source-to-runtime setup, and deterministic scaffold
  proof.
- **Out:** company data, profiles, plugins, connector credentials, live
  workspaces, deployment overlays, GitHub repository creation, and runtime
  installation.

## Delta

> **Before:** HermesCorp owns reusable pieces, but starting a dedicated company
> project requires assembling them manually.
>
> **After:** one safe command creates the lean source project without copying
> any company fixture or runtime state.
>
> **Example:** scaffolding Example Textiles produces a reviewed root context,
> Daily/Weekly contracts, setup skill, filesystem eval UI, and tests—without
> `configs/`, `plugins/`, `profile/`, or `workspaces/`.

## Done / Proof

- [x] Scaffold composes canonical assets and replaces company placeholders.
- [x] Existing targets and invalid timezones fail without partial output.
- [x] Generated project and setup-skill tests pass.
- [x] HermesCorp's existing tests remain green.
- [x] No company-specific data or runtime directory enters HermesCorp.

## State

- **Current:** implementation and verification complete.
- **Proof:** 11 onboarding, 12 webhook, 8 documentation-check, 8 workspace-
  setup, 2 scaffold, 1 generated-layout, 8 generated setup, 1 generated Node,
  and 28 repository Node tests pass; eval-query lint and JSON checks pass.
- **Eval limitation:** the three-case Promptfoo dry run projected successfully,
  but the live comparison was stopped after four silent minutes. No behavioral
  pass-rate claim is included in this ticket.
- **Next:** use the scaffold for the next company project and keep company data
  in that generated repository.
