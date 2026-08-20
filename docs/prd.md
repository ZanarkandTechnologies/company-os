---
title: "Howie Dependency-Aware Company Plan"
status: active
owner: HermesCorp
updated_at: 2026-08-10T09:48:00Z
---

# PRD: Dependency-aware company plan

## Problem / Context

The manager POC shows every ticket’s own human input and skill template, but
cannot answer the operational question that matters: **which skill output is
needed next, which ticket does it unblock, and who should Howie ask?** The
current dashboard also treats its scenario buttons as product controls rather
than distinguishing a production human-request entrypoint from development
simulation.

## First-Principles Basis

- **Objective:** let Howie turn a meeting or PRD into accountable, dependency-aware work without inventing a second task system.
- **User or system need:** Howie needs to see readiness, blockers, downstream impact and the one human input that will unblock the most work.
- **Root cause:** task-local `blocking_inputs` and `mock_skill_dependencies` are untyped lists; no canonical producer/consumer edge exists.
- **Key assumptions:** a finite directed acyclic graph of ticket outputs and human inputs is sufficient for the POC; Telegram can be represented safely before a real adapter exists.
- **Constraints:** filesystem tickets remain canonical; no real Telegram send, Google Drive access, OAuth, cron, or employee ACL mutation.
- **First viable slice:** typed human and skill-output requirements, declared skill outputs, deterministic readiness projection, and Timeline/Table/Dependencies views over the same tickets.
- **Proof / falsification:** a frozen meeting creates a chain where publishing/reviewing one artifact automatically resolves a named downstream skill-output requirement; tests and browser evidence show the graph and a mock human reply.
- **Tradeoff accepted:** model only explicit DAG dependencies and one request type (`human_input` via `telegram_preview`); defer a generic workflow engine, editable graph, and live delivery.
- **Non-goals:** multi-user authorization, production Telegram credentials, arbitrary PRD parsing, or automatic execution of all skills.

## Audience

- **Primary:** Howie, reviewing a company plan after a meeting or PRD.
- **Secondary:** Kenji, who receives a bounded Telegram request, answers it, and reviews the resulting artifact.

## JTBD

When a meeting or PRD produces several dependent deliverables, I want to see
what is blocked by a person versus another skill output, so I can ask one
useful question and keep the company moving.

## SLC Slice (Next Release)

1. A ticket declares `requirements` (human input or another ticket’s approved
   skill output) and `skill_outputs`.
2. The manager validates a DAG, derives `blocked_by`, `unblocks`, and the next
   eligible human request from ticket folders.
3. The frozen scenario chains geo report → fundraising deck / Excel model →
   weekly report.
4. One dashboard state has three views of the same projection: Timeline,
   Table, and Dependencies. No view owns separate state.
5. Human requests are **Telegram previews** in ticket progress; development
   controls may simulate Kenji’s input/reply, but no transport sends.

## Prototype / PoC Gates

- **Highest-risk assumption:** explicit producer/consumer fields remain more
  useful and inspectable than a generic graph-memory layer.
- **Prototype artifact:** deterministic dependency fixture plus browser flow.
- **Pass signal:** the dependency view names a concrete producer/output and a
  mock reply or approved output changes the dependent ticket’s readiness.
- **Ticket before full production build:** yes.

## Metric Candidates

- **Primary candidate:** pass/fail frozen-scenario evaluation of dependency
  resolution and human-request eligibility.
- **Direction:** pass/fail.
- **Verification idea:** unit tests assert cycle rejection, no premature
  skill execution, one Telegram-preview request, and downstream unblocking.
- **Guard idea:** tests assert no Telegram/Drive/OAuth/cron side effect exists.
- **Human quality provider:** independent reviewer judgment of the views; no
  honest numeric usability threshold has been supplied.

## Non-Goals

- Live Telegram notifications or inbound webhook handling.
- Google Drive file search, permissions or writes.
- Dragging dates, editing graph edges, or creating a general workflow editor.
- Automatic skill execution without declared required inputs and review rules.

## User Stories

### US-001: Diagnose a blocked deliverable

As Howie, I want a ticket to state the exact upstream ticket, output and skill
that it needs, so that I know whether to wait, request an input, or escalate.

**Acceptance Criteria:**

- [ ] A dependency view identifies `TASK-1002` as blocked by `TASK-1001`’s
  approved `geo-report` output rather than showing an opaque blocker.
- [ ] A cycle or unknown producer/output is rejected before any state write.
- [ ] The dashboard exposes the same dependency data in Timeline, Table and
  Dependencies views.

### US-002: Request the next human input

As Kenji, I want Howie to create a concise Telegram-ready question only when
my answer can make work eligible, so that I am not spammed with generic chases.

**Acceptance Criteria:**

- [ ] A due human requirement produces a ticket-local `telegram_preview`
  request record, never an actual send.
- [ ] The development-only simulation records Kenji’s reply against that
  requirement and recomputes readiness.
- [ ] No generic dashboard action claims to contact a real person.

## Functional Requirements

- **FR-1:** Requirements have stable IDs, a type, resolution state, and either
  a human-request contract or an upstream ticket/output reference.
- **FR-2:** Every mock skill declares stable input IDs and output IDs.
- **FR-3:** Readiness is derived from declared requirements; a ticket remains
  blocked until all required inputs are resolved.
- **FR-4:** Human requests name the intended channel and are persisted only as
  preview/intent records until a separately approved transport adapter exists.
- **FR-5:** Views are read-only projections over canonical ticket folders.

## Constraints

- **Security/privacy:** no personal Telegram target, token, Drive credential or
  employee contact data in source fixtures or browser state.
- **Platform:** Node standard library and the existing dependency-free local UI.
- **Budget/time:** one operator-authorized continuous improvement window; do
  not infer a token, spend or live-service budget.

## Autonomy Readiness

- **Human inputs/assets needed:** Telegram chat identity and consent before a
  real adapter; PRD/meeting source and artifact-review rules per workstream.
- **Credentials / external services:** none in this POC; real Telegram and
  Google Workspace adapters require separate approval and isolation design.
- **Tooling gaps:** no production parser, delivery receipt, or real inbound
  message gateway.
- **Human gates:** plan/PRD acceptance before live adapter; human review before
  artifact completion; explicit approval before any send, publish or spend.
- **Agent decision boundaries:** may derive and preview the next request; may
  not send it, alter permissions, or claim an input is satisfied without a
  bounded reply/artifact record.

## Risks / Unknowns

- Real PRDs may contain ambiguous or cyclic dependencies; the POC must reject
  rather than guess.
- Telegram delivery and identity binding are intentionally unproven.
- Some artifacts require iterative human judgment that a simple satisfied flag
  cannot capture; model them as explicit review requirements rather than hide
  them in prompts.

## Backpressure / Evidence to Ship

- Unit/integration tests for graph validation, upstream-output resolution and
  Telegram-preview request/reply.
- Browser capture of all three views and the unblocked transition.
- Independent implementation + visual review and a narrated POC demo.
