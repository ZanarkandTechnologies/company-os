# HermesCorp source and runtime contract

HermesCorp is the source-controlled development and evaluation harness for the
Company OS Hermes manager. It is separate from the live Hermes workspace. Author
inputs here, review them, then install them into the runtime explicitly.

## Accessible locations and ownership

| Location | Owner | Purpose |
| --- | --- | --- |
| Repository checkout | HermesCorp | Authoritative reusable Company OS contracts, installer, skills, plugins, templates, and evals. |
| Selected Hermes profile's `workspace/` | Hermes runtime | Live reports, memory, proposals, receipts, and other agent-created company artifacts. |
| Selected Hermes profile | Hermes profile | Private credentials, installed skill copies, sessions, logs, caches, gateway state, and local databases. |

## Repository layout

- `workspace.hermes.md`: the reviewed, nonsecret workspace context installed as
  `.hermes.md` in the live runtime.
- `distribution.yaml`: the Hermes client-install allowlist. It packages runtime
  contracts without copying development evidence.
- `automations/`: readable automation contracts; scheduling and generated runs
  remain runtime concerns.
- `docs/`: the PRD, operator guide, and evaluation runbook. Daily and
  Weekly behavior is documented only by its owning skill.
- `templates/`: shared provider-backed entity contracts. Cadence-owned memory,
  message, and report templates live inside the owning PM skill.
- `plugins/`: Hermes platform connector source. Installed profile
  copies are derived artifacts and update only through the setup route.
- `automations/evals/`: synthetic source records, expected snapshots, and
  boundary case definitions for Daily and Weekly collection. They are not proof
  until an operated runner consumes them.
- `skills/pm-daily/` and `skills/pm-weekly/`: PM instructions, owned semantic
  eval cases, and frozen evidence. Each skill writes JSON; its automation renders
  the intended memory/reports and applies authorized provider effects.

## Skill writing

- Use short bullets for skill rules: one action and its related conditions.
- Keep JSON contracts and examples in compact tables or code blocks.
- Avoid paragraph-sized checklist items; put qualifications beside their rule.

## Code test suites are temporarily banned

- Do not add repository unit, integration, snapshot, contract, end-to-end, or
  live test suites.
- Do not add `tests/` directories, `test_*.py` files, test frameworks, test-only
  wrappers, or CI steps that invoke a test runner.
- Verification belongs in evals. Automation evals must cover source collection,
  normalization, completeness facts, and the snapshot boundary using synthetic
  seed data. Skill evals cover analysis, decisions, memory updates, reports,
  messages, no-ops, and blocked behavior.
- Put most semantic cases in skill evals, which end at JSON. Keep a small
  end-to-end automation set for source-to-file transitions and authorized
  effects; use collection and Step 4 cases to diagnose failed boundaries.
- Judge created, modified, deleted and unchanged files against a before-run
  inventory. File changes prove execution, not factual correctness; retain
  source-grounded semantic assertions in the owning skill cases.
- Keep deterministic validators only when they are production safeguards for a
  named non-semantic invariant. Do not disguise tests as validators or scripts.
- Provider connection certification and explicitly authorized acceptance probes
  are product operations, not repository test suites; keep their existing
  authority, isolation, read-back, cleanup, and receipt gates.
- This ban remains until the product contracts stabilize and this project-level
  policy is deliberately revised.

There is intentionally no tracked `profile/`, `context/`, `deploy/`, or nested
distribution tree. Do not add a profile overlay or mirror the live workspace
here.

## Development flow

1. Edit the workspace context, automations, templates, plugins, and eval cases here first.
2. Inspect the automation case and expected snapshot; run the owning skill eval.
   Do not claim an automation verdict until its runner exists and is operated.
3. Preview source-to-runtime changes with
   `apps/installer/workspace.py`.
4. Apply only after `workspace.hermes.md` has owner-approved status.
   The setup command copies an allowlist and never deletes runtime files.
5. Set `terminal.cwd` with Hermes' native config command, then verify behavior
   from a fresh Hermes session. Do not use symlinks as synchronization.
6. Keep company deployments in their own repositories; promote only scrubbed,
   reusable behavior back into HermesCorp.

## Native automation boundary

- Automations own integrations; skills own operating logic. Before changing
  that boundary, read `automations/AGENTS.md`.
- Hermes owns the Daily and Weekly runtime. Each automation fetches a bounded
  snapshot and runs its PM skill against local memory and templates. Prompt
  shape is the authority: a propagation stage is active whenever present and
  is omitted when disabled. Do not add a second runtime enablement flag.
- Do not build another runtime around it. This includes Python preparation,
  delivery plans, hashed handoffs, action graphs, semantic reducers, provider
  executors, and wrappers that duplicate a skill or MCP.
- Keep semantic work out of Python. Analysis, prioritization, progress chasing,
  documentation review, memory consolidation, report writing, and tool choice
  belong in automation contracts, templates, skills, or MCP tools.
- Use deterministic code only to enforce a named non-semantic invariant, such
  as Pydantic validation, destination and permission checks, draft-versus-send
  authority, stable idempotency keys, atomic writes, conflict detection, or
  compact receipts. Put the check beside the boundary it protects.
- Add a separate prepare/review/apply handoff only when an accepted product
  requirement calls for human approval between analysis and an external side
  effect. Testing convenience, symmetry, and hypothetical retries are not
  sufficient reasons.
- Any new deterministic automation code must name the invariant it protects and
  explain why the contract, schema, existing skill or MCP, or provider receipt
  cannot enforce it. If it cannot, do not add the code.

The source repository is authoritative for intended behavior. The live
workspace is authoritative for generated operational state. Never edit both
copies and treat them as co-equal sources.

## Safety

- Never commit credentials, OAuth material, sessions, logs, databases, caches,
  generated reports, project memory, or unsanitized company data.
- `.gitignore` is cleanup protection, not the runtime isolation boundary.
- External Notion, Drive, Gmail, messaging, scheduling, and webhook writes
  require their own bounded integration checks and the authority stated in the
  automation or setup contract.
- Preserve unknown live-workspace files. Archive or delete them only through a
  separately approved cleanup.

## Evaluation

Follow `docs/evaluation.md`. Network and provider writes remain explicit human
gates; autonomous evaluation is offline and synthetic by default.
