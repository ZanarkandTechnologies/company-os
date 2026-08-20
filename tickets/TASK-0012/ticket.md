---
template_id: ticket-template
template_version: "0.2.6"
ticket_id: TASK-0012
title: Replace component-skill onboarding with one company workspace context
status: complete
created_at: 2026-08-20T15:00:00+08:00
updated_at: 2026-08-20T16:00:00+08:00
depends_on: [TASK-0011]
source_refs:
  - skills/company-os-onboarding/SKILL.md
  - docs/hermes-company-os-onboarding.md
---

# TASK-0012: Replace component-skill onboarding with one company workspace context

## Summary

Make one workspace-scoped `.hermes.md` the durable company operating index and
reduce onboarding to connector checks plus collaborative template completion.

## Scope

- **In:** one metadata-bearing template, five company surfaces, multi-platform
  rows, simplified skill contract, QA checklist, operator guide, and retirement
  of the superseded component-skill scaffold route.
- **Out:** live connector authentication and rendering a customer-specific installation.

## Delta

> **Before:** onboarding generated separate component skills as company configuration.
>
> **After:** onboarding fills one owner-reviewed `.hermes.md`; skills/CLIs/MCPs
> remain interaction routes and a separate receipt stores transient health.
>
> **Example:** Notion can appear under Work, People, and Decisions while Google
> Drive appears under Knowledge, each with route, links, and structure.

## Done / Proof

- [x] Source-owned template contains metadata and the five surfaces.
- [x] Additional platforms are represented by duplicated Markdown rows.
- [x] Skill and QA contracts describe one workspace context plus a receipt.
- [x] Operator guide matches the simplified flow.
- [x] Legacy component scripts and templates are absent, with a regression test.
- [x] Template and package checks pass.
- [x] Independent review accepts the change at TAS-A.

## Links

- Template: `skills/company-os-onboarding/assets/templates/company-workspace.hermes.md`
- Skill: `skills/company-os-onboarding/SKILL.md`
- Guide: `docs/hermes-company-os-onboarding.md`
- Review: `tickets/TASK-0012/artifacts/review.md`
