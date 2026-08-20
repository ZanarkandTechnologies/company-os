---
ticket_id: TASK-0005
title: Hermes SME website and shared brand system
status: complete
created_at: 2026-08-17T00:00:00+08:00
updated_at: 2026-08-17T17:03:05+08:00
depends_on: []
---

# TASK-0005: Hermes SME website and shared brand system

## Summary

Create a new public-facing Hermes SME site beside the existing operator
dashboard. Extract a dependency-free brandkit and small browser modules that
future Hermes surfaces can reuse. Explain the operating model as durable
systems—not agent memory: applications remain operational sources of truth,
facts live in a queryable company wiki, decisions live in an auditable ledger,
and approved procedures compile into versioned skills.

## Scope

- **In:** reusable CSS tokens/components; reusable browser modules; one static
  SME homepage; the four change routes; architecture documentation; local
  server; focused tests; desktop and mobile browser proof.
- **Out:** replacing the existing company-manager dashboard, live integrations,
  authentication, a real wiki backend, a decision database, skill generation,
  deployment, analytics, contact forms, and external writes.
- **Constraint:** use the existing static/Node platform with no new frontend
  dependency. References inform principles; no source site code, custom fonts,
  images, or protected creative is copied.

## Delta

> **Before:** Hermes had a monolithic operator dashboard and no reusable public
> brand surface explaining where company knowledge and accountability live.
>
> **After:** `web/shared/` owns the brandkit and browser modules; `web/sme/`
> presents the four company-change routes and the three durable systems in a
> restrained public site, while the operator dashboard remains intact.
>
> **Example:** a procedure change is first approved in the decision ledger,
> then compiled into a versioned skill with its source decision and evaluation
> contract. A new fact goes to the wiki instead; an application change goes to
> the integration platform.

## Contract

```text
route_company_change(change)
  -> connected_app | company_wiki | decision_ledger | skill_compiler

dream_procedure(approved_decision, procedure, evidence)
  -> versioned_skill + source_refs + eval_contract

render_sme_site(brandkit, operating_model)
  -> accessible_static_page + reusable_modules + browser_proof
```

## Change Plan

### Change 1: Durable operating model

Document record ownership, allowed flows, audit fields, and the explicit
stateless-agent boundary in `docs/sme-operating-model.md`.

### Change 2: Shared web layer

Add `web/shared/hermes-brandkit.css`, `site-shell.js`, and `system-router.js`.
The system must use a near-black ground, bone text, square one-pixel borders,
grotesk/mono typography, and sparing signal-green/soft-orange accents.

### Change 3: SME homepage

Add the approved landing and design specifications plus the one-page site under
`web/sme/`. The story sequence is: operating thesis, three systems, change
router, procedure-to-skill compiler, decision accountability, no-agent-memory
principle, and a restrained final action.

### Change 4: Proof

Add a native static server and structural/server tests. Capture desktop and
mobile screenshots, validate no page/console errors, keyboard interaction,
reduced-motion behavior, and responsive overflow.

## QA Strategy

- **Required TAS:** TAS-A with no blocking findings.
- **Rubric families:** user-intent-satisfaction, UI quality, frontend
  guidelines, frontend code maintainability, code quality, documentation
  quality, evidence quality, and integration readiness.
- **Structural proof:** focused SME tests plus the full existing repository
  test suite.
- **Rendered proof:** Chromium captures and assertions at 1440×1000,
  390×844, and 320×800, including keyboard routing, URL state, reduced motion,
  runtime errors, and horizontal overflow.
- **Independent proof:** completion reviewer inspects the implementation,
  screenshots, browser receipt, and test results.

## Done / Proof

- [x] Shared brandkit and modules have at least one real consumer.
- [x] Four change types route to the correct durable owner.
- [x] Decision records show approver, responsible owner, dates, rationale, and
  supersession.
- [x] Procedures compile into skills; facts remain in the wiki; application
  state remains in applications.
- [x] Existing operator dashboard behavior passes the full regression suite.
- [x] New tests and rendered browser QA pass at desktop and mobile widths.

## State

- **Current:** complete; independent TAS-A review passed with no blockers
- **Next:** none within this ticket
- **Blockers:** none

## Links

- Operating model: `docs/sme-operating-model.md`
- Landing specification: `web/sme/LANDING_SPEC.md`
- Visual system: `web/sme/DESIGN_BRIEF.md`
- Browser proof: `tickets/TASK-0005/artifacts/browser/visual-qa.md`
- Completion review: `tickets/TASK-0005/artifacts/completion-review.md`
