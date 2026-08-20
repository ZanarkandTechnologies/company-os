---
title: "Hermes Company OS"
status: active
owner: HermesCorp
---

# Hermes Company OS

Hermes Company OS is the opinionated company layer on top of Hermes. Hermes
provides the agent runtime; Company OS gives it a reliable way to understand
and operate a real company through the tools people already use.

The product does not treat opaque agent memory as the company system of record.
It connects the existing stack, discovers the sources the company actually
uses, installs a reviewed `.hermes.md` operating map, and proves that Hermes can
retrieve representative context through each route. Notion, Google Drive,
Gmail, and other source applications remain authoritative.

```text
company + current stack
  -> verified connectors
  -> discovered operating sources
  -> reviewed .hermes.md company map
  -> representative lookup proof
  -> optional company channels and procedures
```

## What Company OS adds

- **Company context:** one concise map of Work, People, Knowledge,
  Communications, and Decisions, including source links, structure, routes,
  and authority boundaries.
- **Opinionated onboarding:** a chat-led flow that asks for the current stack
  once, verifies available skills, CLIs, or MCPs, proposes the map, and records
  unresolved gaps without blocking the first useful install.
- **Operational use:** reusable skills for procedures and optional channels that
  let people work with Hermes from company surfaces such as Notion comments.
- **Inspectable proof:** connection receipts and representative reads instead
  of claims based on a connector merely being installed.

Company operating facts stay in source applications and the `.hermes.md` map.
Repeatable procedures may become skills. Transient health, setup evidence, and
runtime state stay outside the company context file.

## Start here

- [`company-os-onboarding`](skills/company-os-onboarding/SKILL.md) — connect the
  current stack and install the company map.
- [`notion-webhook-onboarding`](skills/notion-webhook-onboarding/SKILL.md) — add
  Notion comments as an optional channel after core onboarding succeeds.
- [`daily-documentation-check`](skills/daily-documentation-check/SKILL.md) —
  check today’s Notion Work records against their configured template and
  propose or post one focused source comment.
- [Onboarding guide](docs/hermes-company-os-onboarding.md) — product flow,
  ownership, completion, and safety boundaries.
- [Company record templates](templates/) — metadata-backed Project, Task,
  Resource, Decision, and Weekly Report pages. Durable operating records start
  with an Outcome/Why value card; Weekly Reports open with the executive result
  the reader needs.
- [Automation index](automations.md) — Daily accumulation and Weekly
  finalization contracts.
- [Authored filesystem eval template](templates/authored-filesystem-evals/README.md)
  — local UI and isolated runner for created/modified/deleted file events plus
  added/removed/present/absent content assertions.
- [Company architecture](ARCHITECTURE.md) — isolated company workspace model.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/company-os-onboarding/tests -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/notion-webhook-onboarding/tests -p 'test_*.py' -v
npm test
```

## Template boundary

HermesCorp contains reusable Company OS templates, skills, automations, and
generic contract tests. Company profiles, company-specific eval fixtures, live
workspaces, generated runs, and deployments belong in their dedicated project
directories, never in HermesCorp.

This boundary applies even when the material is sanitized, synthetic, ignored
by Git, or useful as evaluation evidence. Sanitizing company-specific material
does not make HermesCorp its owner.

| Belongs in HermesCorp | Belongs in the company project |
| --- | --- |
| Reusable skills and connector procedures | Installed or deployable Hermes profiles |
| Blank `.hermes.md` and record templates | Rendered company `.hermes.md` files |
| Company-agnostic automation contracts | Live workspaces, receipts, runs, and generated state |
| Minimal generic contract fixtures | Company-specific fixtures, eval suites, and test corpora |
| Generic setup and validation tools | Customer configuration, deployment files, and private examples |

Do not add top-level `profiles/`, `workspaces/`, `tenants/`, or
`fixtures/evals/` directories here. For example, Howie evaluation assets belong
in `HowieAI/company-os-evals`; Kamdar deployment assets belong in the KamdarAI
project. When an experiment becomes specific to one company, move its profile,
fixtures, runners, and tests together rather than leaving a copy in HermesCorp.

- [Manager harness](HARNESS.md) — file-first company-manager runtime.
- [POC guide](POC.md) — controlled activation path.
- [Manager API](docs/company-manager.md) — deterministic local commands.
- `web/sme/` — public SME operating-model explainer (`npm run site`).

Private credentials, company profiles or eval suites, workspace state,
generated run artifacts, and live company data are excluded from this repo.
