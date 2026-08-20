---
template_id: ticket-template
template_version: "0.2.6"
ticket_id: TASK-0014
title: Extract the authored filesystem eval template for company projects
status: done
created_at: 2026-08-21T00:00:00+08:00
updated_at: 2026-08-21T03:30:00+08:00
claimed_by: codex-root
source_refs:
  - /Users/kenjipcx/Zanarkand Technologies/projects/HowieAI/mining/evals/README.md
  - /Users/kenjipcx/Zanarkand Technologies/projects/HowieAI/mining/scripts/authored-file-evals.mjs
  - /Users/kenjipcx/Zanarkand Technologies/projects/HowieAI/mining/dashboard/index.html
---

# TASK-0014: Extract the authored filesystem eval template for company projects

## Summary

Extract the proven Howie filesystem-eval authoring pattern into a small,
company-agnostic HermesCorp template, then install one Kamdar-owned instance in
the dedicated Kamdar source repository.

## Scope

- **In:** standalone browser editor, portable JSON cases, isolated fixture
  preparation, created/modified/deleted assertions, added/removed/present/absent
  content checks, optional real Hermes execution restricted to `file,skills`,
  generic tests, Kamdar Daily/Weekly starter cases, and workspace topology docs.
- **Out:** live Notion/Drive/email calls, scheduler deployment, copying Howie
  branding or fixtures, moving credentials, deleting either Kamdar directory,
  or changing the installed profile's gateway/runtime state.
- **Invariant:** HermesCorp owns only the reusable template; Kamdar owns its
  cases, runs, fixtures, profile, and workspace.

## Delta

> **Before:** the working eval builder exists only inside HowieAI's mining
> dashboard, while Kamdar's evals are prose cases with no executable file proof.
>
> **After:** HermesCorp ships a generic starter that company projects can copy;
> Kamdar has a working instance and the visible Codex project links to its
> existing canonical Hermes workspace.
>
> **Example:** a Kamdar Daily case starts with synthetic task/report files and
> passes only when the report is modified, the expected evidence is added, and
> forbidden “message sent” language remains absent.

## Change Plan

1. Add `templates/authored-filesystem-evals/` with the generic schema/evaluator,
   local server/editor, example case, package commands, and focused tests.
2. Add a root regression test so HermesCorp verifies the distributable template.
3. Copy the template into the canonical Kamdar workspace under
   `evals/filesystem/`, replace the example with Kamdar-owned Daily/Weekly
   synthetic cases, and document the relationship to the existing prose suite.
4. Keep the Kamdar source repository separate from the Hermes runtime workspace
   and document their explicit source-to-runtime boundary.

## Done / Proof

- [x] The template editor saves valid JSON definitions with file event and
      content relation assertions.
- [x] Preparation writes only inside a fresh isolated run workspace.
- [x] Real execution, when explicitly invoked, exposes only `file,skills` and
      records before/after snapshots plus check results.
- [x] HermesCorp template tests and existing repository tests pass (28/28).
- [x] Kamdar starter cases validate and the Kamdar repository tests pass (1
      Node test, 8 Python tests, and `context_valid=true`).
- [x] KamdarAI owns its source and eval harness while the existing
      `vishan-kamdar-ai` workspace remains separate runtime state.
- [x] The live Kamdar editor serves both cases and renders the complete authoring
      flow; browser proof is captured at `kamdar-eval-ui.png`.

## QA Strategy

Run the template's Node tests first, then HermesCorp `npm test`, Kamdar Python
tests and JSON validation, and a local HTTP smoke against the template and
Kamdar editor. Inspect Git status in both repositories and verify no secrets,
live receipts, profile state, or generated runs became tracked.

## State

- **Current:** template extraction, Kamdar installation, runtime separation,
  and local verification are complete.
- **Next:** run the two company cases against the live Hermes profile once its
  automation skills are ready; the harness intentionally requires explicit
  `HERMES_EVAL_PROFILE` configuration for that external execution.
