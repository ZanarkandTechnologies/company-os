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
- [Onboarding guide](docs/hermes-company-os-onboarding.md) — product flow,
  ownership, completion, and safety boundaries.
- [Company architecture](ARCHITECTURE.md) — isolated company workspace model.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/company-os-onboarding/tests -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/notion-webhook-onboarding/tests -p 'test_*.py' -v
npm test
```

## Product experiments

This repository also contains the earlier Howie company-manager POC, Kamdar
Notion distribution, SME explainer site, and their evaluation fixtures. They
are implementation evidence for Company OS, not separate product centers.

- [Manager harness](HARNESS.md) — file-first company-manager runtime.
- [POC guide](POC.md) — controlled activation path.
- [Manager API](docs/company-manager.md) — deterministic local commands.
- `profiles/kamdar-ai/` — transferable Hermes profile with the Notion channel.
- `web/sme/` — public SME operating-model explainer (`npm run site`).

Private credentials, customer workspace state, generated run artifacts, and
live company data are intentionally excluded from version control.
