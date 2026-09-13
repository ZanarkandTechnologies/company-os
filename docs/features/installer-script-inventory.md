---
title: Installer script inventory
date: 2026-09-13
status: audited
---

# Installer script inventory

The compiler loads `apps/installer/questions.json` for answer validation and fills the templates. Profile installation,
provider certification, health checks and CLI interaction still need their own
production modules; replacing generation does not replace those services.

Paths below are relative to `apps/installer/`. This covers every Python module
present during the audit, plus the removed Compose proof configuration.

| Modules | Decision | Caller or evidence |
| --- | --- | --- |
| `prompt_generation.py` | Retain | `cli/app.py`, feature wizard and lifecycle generate reviewed template bundles. |
| `feature_setup.py` | Retain shared services; prune dead renderer | Compiler uses `write_batch`; lifecycle uses `load_state` and `selected_bindings`; readiness/certification use `bindings_for_workspace`. Old slot rendering, answer-writing helpers and their private support have no external callers. |
| `cli/app.py` | Retain | Root `setup.py` dispatches customer commands here. |
| `cli/flows/features.py` | Retain | `features` and lifecycle ask questions from `questions.json` and edit saved answers. |
| `cli/flows/lifecycle.py` | Retain | Launch/install/update, source generation, profile setup and messaging configuration. |
| `cli/flows/workspace.py` | Remove | Superseded identity/source/messaging wizard writes generated workspace context directly, bypassing saved answers. Only old `init`/`configure` commands call it; active lifecycle uses the feature wizard and compiler. |
| `cli/flows/connections.py` | Retain | Lifecycle connection setup, `certify` and verification recovery. |
| `cli/flows/verification.py` | Retain | `verify` command. |
| `cli/flows/doctor.py` | Retain | Lazy dispatch for doctor preflight/eval/open/activate/analysis. |
| `cli/ui.py`, `cli/process.py`, `cli/paths.py` | Retain | Shared interaction, subprocess and profile-path services used by active flows. |
| `runtime.py` | Retain; prune obsolete messaging receipt readers | Active profile installation, credentials, MCP configuration, webhook operations and health checks. Removed receipt checks had no current writer. |
| `profile.py` | Retain | Lifecycle invokes this script; doctor uses schedule activation; reconciles plugins and schedules. |
| `workspace.py` | Retain | Profile setup invokes the allowlisted source-to-runtime installer. |
| `provider_catalog.py` | Retain; remove Markdown-table fallback | Provider definitions for lifecycle, certification and readiness. Saved answers are the binding authority. |
| `composio_session.py` | Retain | Connection flow imports it for OAuth sessions and connection links. |
| `connection_evals.py` | Retain | Explicit provider certification and receipt gates, not an orphan test suite. |
| `readiness_evals.py` | Retain | Doctor read-only preflight and activation evidence. |
| `model_output.py` | Retain | Shared JSON extraction used by readiness and certification. |
| `schemas/workspace.py`, `schemas/__init__.py` | Remove | Old context editor is gone; artifact models/renderers have no callers. Remaining messaging reader consumed receipts no current flow writes. |
| `dashboard.py` | Remove | Container-only executable and TCP proxy replaced in both launchers with native host `hermes dashboard`, bound to loopback. |
| `__init__.py`, `cli/__init__.py`, `cli/flows/__init__.py` | Retain | Package boundaries for active imports. |
| `design.md` | Remove | Superseded slots, schema and skill-output ownership conflict with the current generation contract. |
| `validate_context.py` | Remove | No caller or distribution entry; standalone validator hardcodes superseded context sections and policies. |
| `backend_e2e.py` | Remove | Unreferenced standalone Docker backend proof; no production command or distribution entry. |
| `cli/flows/messaging.py` | Remove | No imports or callers for its old messaging wizard. Active lifecycle configures messaging through runtime helpers. |
| `e2e.py`, `compose.e2e.yaml` | Remove | Proof invokes `setup`, `gateway`, `dashboard` and a named data volume removed from root Compose; current Compose defines only `ngrok`. |

Grounding: full candidate-file reads, repository-wide caller/reference searches,
CLI dispatch, distribution allowlist, `setup.sh` and current root `compose.yaml`.
No live installs, provider effects, Docker runs or test suites were performed.
Removed files were copied outside the repository before deletion and remain
recoverable from Git. This inventory establishes code reachability and stale
assumptions, not a behavioral certification of every retained module.

## Latest lean-check receipt

- Native-platform rung: Hermes already provides the dashboard; no custom server or relay is needed.
- Skip rung: remove unused managed tables, schema models, receipt readers and legacy workspace-generation fallback.
- Preserve: answer migration, inline editing, preview, conflict protection, profile installation and explicit connection certification.
- Remaining size: 22 Python files; this package still includes profile management, not just a questionnaire.
- Current format is not template-only: `questions.json` owns choices and templates own prompt text. A readable inline-choice syntax remains a separate design change; no new parser or configuration layer was added during this cleanup.
- Verification: 26 questions load; saved comparison answers render 16 files without legacy tables; Python syntax, shell syntax and diff whitespace checks pass.
- Dashboard flags checked against installed Hermes help. Windows execution and live profile installation were not exercised.
- Removed source remains recoverable from Git; local temporary backups are not permanent archives.

## Reusable-source promotion boundary

- Promoted installer, native dashboard launch, connectors, JSON-only PM skills,
  templates, eval runner/viewer, synthetic evals and their documentation together.
- Preserved the existing upstream test-suite removals and compatible documentation
  edits. Removed 13 additional obsolete installer and expected-output files.
- Compared 180 shared source files byte-for-byte with the sanitized deployment
  repository before adding this upstream-only receipt; all matched.
- Both generic Daily and Weekly contracts are rendered from the reusable
  templates. They require configuration before collection, use JSON-only skill
  handoffs, and have provider propagation disabled.
- No private setup answers, workspace context, authored deployment automations,
  client architecture note, credentials, provider IDs or runtime artifacts were
  copied. Examples use generic company/profile names; private scratch paths and
  demo seed identifiers were removed from shared documentation.

Allowed repository differences:

| Surface | Upstream treatment |
| --- | --- |
| `AGENTS.md` | Reusable Company OS ownership and host-independent locations |
| `workspace.hermes.md` | Existing generic draft, never the deployment context |
| `config/` | Deployment-owned answers and generated state excluded |
| Root Daily and Weekly automations | Generic configuration-required template renders |
| Root weekly meeting automation | Existing generic disabled contract preserved |
| Private client architecture note | Excluded entirely |
| This inventory | Upstream-only promotion receipt |

Proof: question export contains 26 declarations; shared Python syntax, shell
syntax and diff-whitespace checks pass. Generic automation contracts have no
unresolved template directives. This proves source transfer and static validity;
it does not certify a new customer installation or provider delivery.
