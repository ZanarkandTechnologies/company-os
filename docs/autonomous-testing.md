---
title: Autonomous testing
status: active
owner: Company OS
created_at: 2026-08-29
updated_at: 2026-08-31
---

# Autonomous testing

This runbook is the default verification contract for coding agents and CI.
The autonomous lane is deterministic, network-free, and safe to rerun. Live
provider tests require an explicitly selected profile and separate authority.

## Safe default lane

Run these commands from the repository root:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 apps/installer/validate_context.py --context workspace.hermes.md
farplane lint evals --changed
python3 ../Farplane/skills/eval/scripts/check_eval_queries.py --root .
```

The lane passes only when every command exits zero, context validation prints
`context_valid=true`, and both eval checks accept the changed skill manifests.
Do not update expected files merely to turn a failure green.

Tests live beside their behavioral owners in `apps/*/tests/`,
`seed/tests/`, and plugin packages. Root `tests/contracts/`
holds repository-wide invariants; `tests/test_owned_packages.py` provides one
standard discovery bridge. Installer E2E and live-provider cases remain
explicit gated lanes in `apps/installer/tests/`.

## Targeted setup lane

Use this smaller loop while changing setup, distribution, or webhook code:

```bash
python3 -m unittest \
  apps.installer.tests.test_architecture \
  apps.installer.tests.test_init \
  apps.installer.tests.test_launch \
  apps.installer.tests.test_connections \
  apps.installer.tests.test_runtime \
  apps.installer.tests.test_profile \
  apps.installer.tests.test_workspace \
  apps.installer.tests.test_provider_catalog \
  apps.installer.tests.test_connection_evals \
  apps.installer.tests.test_composio_session \
  tests.contracts.test_distribution \
  plugins.platforms.notion.tests.test_comment_adapter \
  plugins.platforms.notion.tests.test_webhook_protocol -v
python3 -m py_compile \
  setup.py apps/installer/cli/*.py apps/installer/cli/flows/*.py \
  apps/installer/runtime.py apps/installer/profile.py apps/installer/workspace.py
```

After the targeted lane passes, run the complete safe default lane before
claiming completion.

## Host Hermes Docker-backend lane

Claims about the configured terminal backend require host Hermes to execute a
real isolated container through Hermes' own backend implementation:

```bash
"$HOME/.hermes/hermes-agent/venv/bin/python" apps/installer/backend_e2e.py \
  --receipt /absolute/private-or-ticket-artifact-path/docker-receipt.json
```

The runner imports Hermes' `DockerEnvironment`, starts a digest-pinned sandbox
with networking disabled, verifies `/workspace` execution, removes the exact
container, and writes an owner-only receipt. It does not create another Hermes
profile or run the gateway inside Docker.

## Real data-readiness Doctor lane

When the task explicitly authorizes reads and model spend against one named
profile, run:

```bash
python3 setup.py doctor preflight --profile-home "$COMPANY_OS_PROFILE"
```

Preflight temporarily sets selected MCPs to Hermes' `untrusted` tier, so any
tool without provider-declared `readOnlyHint=true` is blocked before its RPC.
Every observed tool must also match that provider's positive read allowlist.
It requires exported tool evidence and writes a redacted private receipt. It
must return nonzero for missing core sources, empty selected inputs, missing
required fields or relations, a non-allowlisted tool, or judge failure.

## Isolated full-eval Doctor lane

```bash
python3 setup.py doctor eval --profile-home "$COMPANY_OS_PROFILE" --open
```

This runs one file-only Hermes session per PM cadence against private packaged
fixtures, then one model-only batch judge. It must cover every current eval and
assertion, record zero provider mutations, build the private dossier, and fail
closed on missing output or evidence.

Managed schedules remain paused until live health, readiness, and the complete
checksum-validated eval dossier pass. After repairing a failure, rerun the
proof stages and then:

```bash
python3 setup.py doctor activate --profile-home "$COMPANY_OS_PROFILE"
```

For an installed-company analysis preview without delivery, use:

```bash
python3 setup.py doctor analysis --profile-home "$COMPANY_OS_PROFILE"
```

## Installed and live lanes

Installed-profile verification is allowed only against the profile named by
the task. Use a task-specific variable rather than relying on ambient profile
selection:

```bash
COMPANY_OS_PROFILE=/absolute/path/to/profile
python3 setup.py verify --profile-home "$COMPANY_OS_PROFILE" --skip-connections
```

`--live`, connection tests, Notion comments, email, Drive writes, and
`--allow-side-effects` are not part of autonomous default testing. Run them only
when the task explicitly authorizes the provider, account, destination, and
write scope. Preserve the redacted receipt and report `ready`, `partial`, or
`blocked`; never convert a skipped live lane into a pass.

### Global Telegram delivery test

The global Python discovery includes one provider-backed Telegram acceptance
test, skipped by default. When the task explicitly authorizes one message to the
configured owner route, run:

```bash
COMPANY_OS_RUN_TELEGRAM_LIVE=1 \
COMPANY_OS_PROFILE=/absolute/path/to/the/named/profile \
python3 -m unittest apps.installer.tests.test_messaging_live -v
```

This sends exactly one labeled connection-test message. It asserts provider
success, an exact target, a target hash, and a provider message ID without
printing the destination ID. Human receipt confirmation remains a separate
acceptance fact; provider success alone must not enable automatic messaging.

## Failure handling

1. Stop at the first failed required lane and keep its output.
2. Reproduce with the narrowest owning test.
3. Repair the source owner; do not patch installed profile copies or generated
   receipts.
4. Rerun the narrow test, then the complete safe default lane.
5. Report the failed check, repair, final command results, and any live lane
   that remained intentionally unrun.
