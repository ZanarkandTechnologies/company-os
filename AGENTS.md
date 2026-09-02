# HermesCorp source and runtime contract

HermesCorp is the source-controlled development and evaluation harness for the
Company OS Hermes manager. It is separate from the live Hermes workspace. Author
inputs here, review them, then install them into the runtime explicitly.

## Accessible locations and ownership

| Location | Owner | Purpose |
| --- | --- | --- |
| `/Users/kenjipcx/Zanarkand Technologies/projects/HermesCorp` | HermesCorp | Authoritative reusable Company OS contracts, installer, skills, plugins, templates, and tests. |
| `/Users/kenjipcx/.hermes/profiles/company-os/workspace` | Hermes runtime | Live reports, memory, proposals, receipts, and other agent-created company artifacts. |
| `/Users/kenjipcx/.hermes/profiles/company-os` | Hermes profile | Private credentials, installed skill copies, sessions, logs, caches, gateway state, and local databases. |

## Repository layout

- `workspace.hermes.md`: the reviewed, nonsecret workspace context installed as
  `.hermes.md` in the live runtime.
- `distribution.yaml`: the Hermes client-install allowlist. It packages runtime
  contracts without copying development evidence.
- `automations/`: readable automation contracts; scheduling and generated runs
  remain runtime concerns.
- `docs/`: the PRD, operator guide, and autonomous-testing runbook. Daily and
  Weekly behavior is documented only by its owning skill.
- `templates/`: shared provider-backed entity contracts. Cadence-owned memory,
  message, and report templates live inside the owning PM skill.
- `plugins/`: Hermes platform connector source. Installed profile
  copies are derived artifacts and update only through the setup route.
- `skills/pm-daily/` and `skills/pm-weekly/`: extraction instructions, owned
  eval cases, and frozen evidence. The skills write files directly.
- `apps/*/tests/`: tests
  owned by those packages. Root `tests/` contains only repository-wide
  contracts and the discovery bridge.

There is intentionally no tracked `profile/`, `context/`, `deploy/`, or nested
distribution tree. Do not add a profile overlay or mirror the live workspace
here.

## Development flow

1. Edit the workspace context, automations, templates, plugins, and eval cases here first.
2. Run the narrow deterministic tests and filesystem eval tests locally.
3. Preview source-to-runtime changes with
   `apps/installer/workspace.py`.
4. Apply only after `workspace.hermes.md` has owner-approved status.
   The setup command copies an allowlist and never deletes runtime files.
5. Set `terminal.cwd` with Hermes' native config command, then verify behavior
   from a fresh Hermes session. Do not use symlinks as synchronization.
6. Keep company deployments in their own repositories; promote only scrubbed,
   reusable behavior back into HermesCorp.

## Native automation boundary

- Hermes owns the Daily and Weekly runtime. Each automation fetches a bounded
  snapshot, runs its PM skill against local memory and templates, then uses
  configured skills or MCP tools for authorized provider effects.
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

## Verification

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 apps/installer/validate_context.py --context workspace.hermes.md
hermes config get terminal.cwd
```

Follow `docs/autonomous-testing.md`. Network and provider writes remain explicit
human gates; autonomous verification is offline by default.
