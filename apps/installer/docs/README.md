---
title: Company OS setup model
status: active
owner: Company OS
updated_at: 2026-08-31
refs:
  - customer-setup.md
  - ../../../docs/prd.md
  - ../../../docs/operator-guide.md
  - ../../../workspace.hermes.template.md
---

# Company OS setup model

This directory documents what Company OS setup configures and supports. The operated installation procedure remains in [Install the Company OS on Hermes for Windows](customer-setup.md). The [PRD](../../../docs/prd.md) owns product boundaries and architecture; the [operator guide](../../../docs/operator-guide.md) owns day-to-day use.

Setup asks how the Company OS should operate, renders those answers directly
into self-contained automation contracts, installs them, and proves the
required connections without inventing authority. See
[the feature-first design](../design.md).

## Configuration model

```text
explained feature questions
          -> private config/setup-answers.json
          -> named automation template slots
          -> hardcoded Daily and Weekly prompts
```

| Configuration | Question it answers | Canonical owner |
| --- | --- | --- |
| Company | Whose context and timezone govern the run? | Workspace frontmatter |
| Sources | Where should each automation fetch its exact evidence? | Rendered automation nodes |
| Local state | Where do Project Memory, reports, and long-term memory live? | Private Hermes workspace structure |
| Artifact sync | Where may each completed artifact be copied? | Rendered Weekly nodes |
| Communications | How may each follow-up or report reach its recipient? | Rendered Daily/Weekly nodes |
| Credentials | Can this profile use the configured model/provider? | Private Hermes profile; never workspace Markdown |

Read [Sources](sources.md) for readable roles, supported providers, required feature content, and certification. Read [Sinks](sinks.md) for canonical local artifacts, provider copies, Work comments, messaging, authority, and receipts.

## What setup installs

After the operator reviews the plan, setup installs the allowlisted distribution into one private Hermes profile, applies the approved workspace context, enables required plugins, and reconciles three native jobs:

| Automation | Default schedule | Contract |
| --- | --- | --- |
| Company OS Daily Operating Update | `0 8 * * 1-5` | `automations/daily-operating-update.md` |
| Company OS Weekly Operating Review | `0 18 * * 5` | `automations/weekly-operating-review.md` |
| Company OS Weekly Meeting Ticket | `0 9 * * 1` | `automations/weekly-meeting-ticket.md` |

The job prompt tells Hermes to read the installed workspace and the complete automation contract. Missing jobs are created, drifted jobs are updated, paused matching jobs are resumed, and exact jobs remain unchanged. Duplicate accepted job names stop reconciliation.

## Connection, binding, and authority are separate

```text
Provider connection: "this profile can call Notion"
Role binding:        "this exact URL is Projects"
Action authority:    "this exact operation may read/comment/publish"
```

One Notion MCP connection may serve several role bindings. A successful OAuth connection does not choose company scope. A readable Projects or Work binding does not authorize comments or publication. A configured sink does not become usable until the provider connection, exact destination, automation authority, and relevant quality gates also pass.

## Setup and verification flow

```text
answer Workspace, Memory, Daily, and Weekly questions
  -> preview and render hardcoded automation prompts
  -> derive required providers from rendered behavior
  -> authorize model and unique provider connections
  -> install workspace, plugins, and jobs
  -> certify configured integrations
  -> report READY / PARTIAL / BLOCKED
```

Certification is binding-specific. Read-only tests inspect the configured source. Reversible tests require confirmation, create one isolated test object, read it back, and clean it up. Irreversible tests require confirmation and leave only their declared effect, such as one self-addressed email. Deferring certification keeps the installation but produces `PARTIAL` rather than a false pass.

## Doctor’s role

Doctor runs after setup as a thin analysis-only native Hermes invocation. It
reads the selected Daily or Weekly contract and configured workspace while
explicitly disabling provider mutations, messaging, and artifact sync. Missing
source data is reported by the automation itself rather than by a second
feature-readiness engine.

## Ownership boundaries

- Source repository: shipped workspace template, automation contracts, schemas, catalog, and setup code.
- Private setup answers: resumable nonsecret choices used only when rendering.
- Rendered automations: exact sources, destinations, and authority policy used at runtime.
- Private Hermes profile: credentials, OAuth, installed contracts, schedules, receipts, and generated operational state.
- Provider: account permissions and the records reachable at each exact binding.

Setup copies only distribution-owned files and preserves unknown profile files. It never treats repository files and generated runtime state as co-equal sources.

## Current support boundary

- Windows installation is documented and operated through [customer setup](customer-setup.md); this directory does not duplicate that runbook.
- Every feature question includes an explainer, two presets, Custom, and Back.
- Local artifacts are always supported; Weekly questions expose per-artifact destinations.
- Provider connections are derived from the selected automation behavior.
- Doctor is analysis-only. Scheduled Daily and Weekly jobs apply authorized effects directly through native skills and MCPs.
