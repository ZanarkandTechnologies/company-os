---
ticket_id: TASK-0003
title: Real-integration Howie dev POC (filesystem tickets + WhatsApp + Google Drive)
status: ready_for_operator_test
created_at: 2026-08-11T00:00:00Z
updated_at: 2026-08-12T12:22:00+08:00
goal_packet: true
source_refs:
  - https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp
  - https://hermes-agent.nousresearch.com/docs/reference/toolsets-reference
  - https://hermes-agent.nousresearch.com/docs/user-guide/features/tools/
  - https://hermes-agent.nousresearch.com/docs/user-guide/messaging/whatsapp
  - https://developers.google.com/workspace/drive/api/guides/configure-mcp-server
---

# TASK-0003: Real-integration Howie dev POC

## Summary

Turn the local Howie simulator into an honest developer proof: the `howie-ai`
Hermes profile receives a controlled WhatsApp self-chat event from Kenji's
paired phone, edits canonical filesystem tickets in a dedicated test workspace,
uses Google's official remote Drive MCP with a dedicated fake-data identity, and
creates a constrained WhatsApp delivery request when a follow-up is due. A
separate manual delivery worker resolves the approved employee directory and
calls `hermes send`. The dashboard shows ticket state, Drive references, and
the recorded trace. This is a single-owner development environment, not the
customer's VPS or a multi-user authorization product.

The source profile also has an **actual model-behavior** proof: a disposable
clone of a locally configured Hermes profile receives the source Howie
SOUL/config/skill, then runs three isolated filesystem fixtures with
`file,skills` only. Each run stores the visible scenario prompt, Hermes final
reply, model usage receipt, filesystem delta, hashes, and bounded file
snapshots. This proves local agent behavior with mock data; it does not claim a
gateway, Drive MCP, or outbound WhatsApp integration.

## Scope

- **In:** the existing `howie-ai` source profile; official Google Drive remote
  MCP configuration and tool filtering; a dedicated Drive development identity
  with one fake-data root; a private test-only WhatsApp allowlist; a bounded
  private employee directory; real WhatsApp self-chat QR pairing with Kenji's
  phone; a controlled `hermes send` delivery worker; three isolated
  deterministic filesystem evals using the existing scenario catalog; a
  source-synced disposable-profile real Hermes model suite against mock files;
  local dashboard/trace evidence; focused automated checks, human smoke test,
  review, and a customer-demo artifact.
- **Out:** customer data, employee phone numbers, production VPS deployment,
  a shared multi-user Hermes installation, company-wide Drive search, Drive
  ACL administration, employee self-service auth, cron, bulk messaging, or a
  customer-facing production deployment.
- **Constraint:** Hermes may use native file editing only inside the dedicated
  Howie test workspace; this is a development discipline, not a filesystem
  sandbox. A deterministic validator/dashboard reads those same files. Drive
  access is the filtered official MCP under a development identity with no
  non-fake shares. Only the standalone delivery worker can invoke `hermes send`;
  it resolves an employee ID from private runtime data, enforces idempotency,
  route permission, cooldown, and an explicit local send gate. All secrets,
  OAuth tokens, phone numbers, allowlists, model credentials, and pairing state
  stay outside the repository.

## Integration decision

Use Google's official remote Drive MCP endpoint
`https://drivemcp.googleapis.com/mcp/v1`, not the existing local Drive mock.
Hermes documents that Google Drive rejects dynamic client registration, so this
requires an operator-created OAuth client ID/secret in the private profile
configuration before `hermes -p howie-ai mcp login googledrive` can obtain a
token. The connection must expose only `search_files`, `read_file_content`,
`get_file_metadata`, and `create_file` through
`mcp_servers.googledrive.tools.include`. Google's Drive MCP inherits the
authenticated identity's permissions, so the development identity must have no
company content or shares outside the fake-data root. This POC proves a new
artifact creation only; it must not claim an existing-file update capability
that the advertised MCP tool set does not provide.

## Delta

> **Before:** the dashboard's simulator proves ticket transitions against a
> local mock Drive and records preview-only human requests.
>
> **After:** an allowlisted self-chat writes canonical ticket files in its
> dedicated workspace; Hermes can search/read/create only fake artifacts through
> the official Drive MCP, and a separate delivery worker sends only a validated,
> due WhatsApp chase to a directory-approved employee.
>
> **Example:** Kenji sends a weekly meeting summary to the paired Howie number.
> Howie creates missing `TASK-XXXX` folders directly in its dedicated workspace.
> A due requirement creates one delivery draft for a permitted employee; the
> manual worker sends it only under an explicit POC gate. Hermes creates the
> resulting fake geo-report draft in the dedicated Drive root. The dashboard
> trace links the files, Drive reference, and delivery receipt.

## Contract

```text
receive_whatsapp(allowlisted_sender, text)
  -> normal_same_thread_reply + filesystem ticket/progress delta | reject

requirement_follow_up(ticket, requirement, employee, now)
  -> per-requirement next_chase state + append-only delivery draft | defer

deliver_pending_chases(workspace, private_directory, explicit_send_gate)
  -> hermes_send receipt in the owning progress.md | dry_run | reject

google_drive_mcp(filtered_tool, development_identity)
  -> fake-file search/read/metadata/create | provider error

record_drive_reference(ticket, DriveFileRef)
  -> pending artifact evidence | reject

show_proof(ticket_state, drive_receipts, trace)
  -> dashboard evidence + human smoke transcript
```

## Change Plan

### Change 1: Profile capability and activation boundary

Use native Hermes file editing for this development POC: the profile workspace
is the dedicated Howie test workspace and its WhatsApp platform configuration
must be exactly:

```yaml
platform_toolsets:
  whatsapp:
    - file
    - skills
    - mcp-googledrive
```

Keep terminal, browser, web, cron, delegation, messaging, Kanban, and all
other MCP toolsets unavailable to WhatsApp turns. Add a source-config test that
fails if the list differs. The skill must name the workspace-root-only file
discipline and the ticket/progress templates; this is not asserted as a sandbox.
Publish a private-runtime example that names `WHATSAPP_MODE=self-chat`, one
exact `WHATSAPP_ALLOWED_USERS` value, Drive client variables, and the private
employee-directory path without embedding their values. Verify source sync
cannot overwrite `.env`, auth, pairing, session data, or the employee directory.

### Change 2: Filesystem ticket, employee-directory, and follow-up semantics

Keep `tickets/TASK-XXXX/ticket.md` and sibling `progress.md` as the only task
state. The profile skill gives Hermes the meeting-to-ticket and reply-to-progress
templates; the deterministic manager validates/renders the same filesystem
contract for dashboard and evals, but is not an agent MCP. Replace
`telegram_preview` with `whatsapp_delivery_draft` across manager, fixtures,
dashboard, docs, and tests. Replace the persisted ticket-global `chase` object
with **requirement-local** follow-up state for each unresolved human
requirement: `employee_id`, `last_at`, `next_at`, `attempts`, optional
escalation, and a stable delivery ID. Append every draft, attempt, reply,
receipt, and escalation to the owning `progress.md`, keyed by both
`requirement_id` and `employee_id`.

Add a private runtime `people/employees.private.json` contract with employee
ID, display name, WhatsApp target, inbound/outbound permission, explicit test
opt-in, timezone, and cooldown policy. `scripts/company-manager.mjs` owns its
validator; both profile and fixture examples must conform to that one validator
rather than defining alternative roster schemas. The directory owns identity
and route policy only; it is never synced or committed. The board's “next
chase” is derived from unresolved requirements. A global employee cooldown is
derived from the newest matching progress event across active tickets; it delays
a draft without overwriting another requirement's own `next_at`.

### Change 3: Dedicated fake-data Drive and human gates

After source/config review, have the operator create a Google OAuth client,
approve its consent screen, create/select a dedicated Howie development
identity with no non-fake shares, add private profile configuration, complete
the Hermes MCP login, configure a model, and scan the WhatsApp self-chat QR
code. Do not copy secrets, select an account, or pair a device without the
operator at the consent/pairing step. Verify an actual search/read plus new
fake artifact creation; a manual inspector confirms every returned file is in
the approved Drive root.

### Change 4: Controlled delivery, deterministic filesystem evals, and proof

Replace both legacy outbox workers with a company-ticket delivery worker.
It discovers pending `whatsapp_delivery_draft` events from the canonical ticket
progress files, resolves the private employee directory, and supports dry-run
by default. It invokes `hermes -p howie-ai send` only when
`HOWIE_POC_ENABLE_SEND=1` and an explicit `--send` flag are both present; it
writes an idempotent sent/failed receipt back to that ticket's progress file.
It rejects unknown employee IDs, disabled routes, invalid targets, duplicate
delivery IDs, stale/terminal drafts, or a cooldown violation. No agent gains
terminal access and no cron is created.

Keep the three `harness_tasks.json` rows as the sole scenario catalog. The
deterministic filesystem evaluator stages each case in a fresh temporary
workspace and persists trace events plus SHA-256 and selected-content snapshots
of created, modified, and deleted ticket, progress, report, and artifact files.
Keep the direct delivery-worker dry run/send-receipt checks. Add a separate
**disposable clone** of a locally configured Hermes profile for actual model
behavior tests, but do not create a divergent Howie prompt, skills, or ticket
format: source-sync the same profile contract before each disposable workspace
run. Label the stored output as an actual local Hermes session and retain only
the visible prompt/final reply, tool-visible filesystem effects, usage receipt,
and hashes—not hidden reasoning. Keep
`.farplane/evals/tasks/harness_tasks.json` as the only scenario catalog and do
not change `.farplane/evals/run_evals.py` for this local simulator. Remove
`deliver:manager` and `deliver:outbox` from
`package.json` along with `scripts/deliver-manager-outbox.mjs`,
`scripts/deliver-outbox.mjs`, and their old tests; the only active sender path
must be the new company-ticket worker. Then execute the real self-chat-to-ticket-to-Drive-to-
one-allowlisted-chase smoke path, capture redacted dashboard evidence, obtain
independent review, and render a customer demo that labels this as development
proof, not business deployment.

## Done / Proof

- [x] Profile source gives WhatsApp exactly `file`, `skills`, and
  `mcp-googledrive`; it has no terminal, browser, web, cron, delegation,
  messaging, Kanban, or other MCP toolset. The skill binds native file edits to
  the dedicated Howie workspace and canonical ticket/progress templates.
- [x] A private employee-directory example and validator define employee ID,
  WhatsApp target, inbound/outbound permission, test opt-in, timezone, and
  cooldown policy. The profile and fixture examples conform to one manager-owned
  validator; source sync cannot write a real directory or private credential/session.
- [x] Every unresolved human requirement maintains its own follow-up schedule
  and append-only `progress.md` history keyed by requirement and employee;
  two blockers on one ticket can be chased independently, while any board-level
  next-chase display is derived rather than a competing writable field. A
  global employee cooldown is derived from progress history and can defer, but
  cannot overwrite, a different requirement's schedule.
- [ ] The real Drive MCP authenticated under a dedicated Howie development
  identity finds/reads a fake source and creates one new fake artifact. A
  manual record shows all files are in the approved root; no existing-file
  update is claimed.
- [ ] Kenji's paired WhatsApp self-chat sends one structured meeting event and
  one scoped reply; Hermes makes its ordinary same-thread response and each
  accepted event produces a canonical filesystem ticket delta plus trace
  receipt.
- [x] The delivery worker creates no send in dry-run mode, and tests its
  explicit-gate, replay, cooldown, unknown-recipient, and disabled-route
  rejections against canonical progress receipts. One actual permitted send
  remains an operator smoke gate.
- [x] Three isolated deterministic filesystem evals reuse the existing scenario
  catalog. Their proof records created/modified/deleted file deltas, SHA-256
  hashes, and bounded canonical content snapshots; the runner consumes the
  three existing task IDs rather than creating a second catalog.
- [x] The old `deliver:manager` and `deliver:outbox` routes are removed; the
  one active delivery command operates from canonical tickets/progress only.
- [x] The dashboard presents each actual model-behavior case as a simple mock
  chat followed by visible assertions and expandable file proof. Meeting,
  Drive-to-artifact, and end-of-week escalation behavior are independently
  readable; raw output, hashes, and manual-live proof stay under collapsed
  developer evidence.
- [x] A real Hermes model run uses an isolated cloned local profile plus the
  source-controlled Howie SOUL/config/skill. Its three mock-only scenarios
  pass: meeting-to-ticket DAG creation, chained local artifact drafting, and
  missing-source requirement-local escalation. Each run records a scored,
  bounded `manager_reply` separately from raw execution output; the dashboard
  shows that reply and the created file proof without exposing hidden reasoning.
- [x] Automated tests, deterministic proof evidence, browser/visual evidence,
  and independent source review distinguish local simulator coverage from a
  real integration.
- [ ] A redacted operator transcript, one Drive/WhatsApp/manual-send smoke,
  and a short customer-facing demo prove the real integration without claiming
  business deployment.

## QA Strategy

```yaml
proof_weight: hybrid
critical_path:
  - source sync preserves private OAuth/pairing/model data and enforces the exact bounded WhatsApp toolset list
  - native Hermes file edits create only the canonical ticket/progress shape in the dedicated test workspace
  - source-synced disposable Hermes profile executes the same Howie skill against three mock-only workspaces and stores visible reply plus filesystem proof
  - one manager-owned employee-directory validator rejects malformed, unknown, disabled, unopted-in, and invalid-target routes
  - two human requirements on one ticket retain independent follow-up/cooldown/escalation state and append distinct progress events
  - two tickets assigned to one employee respect one derived global cooldown without erasing either requirement's next-chase timestamp
  - Drive MCP OAuth -> dedicated fake identity -> source search/read -> new fake artifact create
  - allowlisted WhatsApp self-chat -> filesystem ticket/progress -> normal same-thread reply
  - delivery worker dry run -> exactly one fake-Hermes send -> terminal receipt/replay rejection
  - deterministic filesystem evals -> created/modified/deleted deltas +
    hashes/content snapshots -> dashboard evidence
checks:
  - automated: source sync, profile/employee-directory schemas, ticket/progress validation, delivery policy, Drive reference, and no-write-on-rejection
  - filesystem eval: three isolated scenario workspaces with trace, delta,
    SHA-256, and selected-content assertions
  - integration: Hermes MCP connection with authenticated Drive token, minimum tool list, and dedicated fake-data identity
  - human smoke: Kenji's own self-chat and fake Drive root only; ordinary same-thread replies plus one allowlisted test chase are permitted under the explicit local send gate
  - negative: unknown sender, malformed event, wrong ticket/requirement, invalid ticket file, unknown/disabled/unopted-in employee, invalid target, duplicate delivery, cooldown violation, non-root Drive reference, missing source, unapproved WhatsApp toolset, and either old legacy delivery command all fail closed
  - browser: dashboard labels deterministic/local/live evidence correctly and reports zero console/page errors
  - reviewer: independent source, boundary, and proof review
  - demo: redacted local recording; no customer/VPS/multi-user claim
residual_risk: Native Hermes file access is not path-sandboxed; the POC relies on a dedicated test workspace and must not run against a customer machine. Google OAuth client setup and WhatsApp QR pairing require Kenji. Hermes's Baileys WhatsApp bridge is a local development path, not business-grade production transport; this POC does not prove enterprise caller authorization or client VPS operations.
```

## State

- **Current:** local source is ready: the fake-only
  `workspaces/howie-ai-poc/` has four seeded canonical tickets, the dashboard
  serves its Gantt plus deterministic and actual-Hermes proof traces, and both
  three deterministic evals and the three-scenario real-model mock suite pass
  with replayable file evidence.
- **Next:** operator-run source-profile check/apply, model configuration,
  dedicated fake-data Drive OAuth/login, private self-chat QR pairing, then
  one allowlisted meeting/reply and one explicit-gate test send.
- **Blockers:** the required private OAuth client, dedicated fake-data identity,
  model, exact self-chat allowlist, one opted-in test target, and interactive
  pairing/consent steps.

## Links

- Architecture boundary: `ARCHITECTURE.md`
- Existing harness: `HARNESS.md`, `docs/company-manager.md`
- Existing profile source: `profiles/howie-ai/`
- Private directory shape: `profiles/howie-ai/private-roster.example.json`,
  `fixtures/company-manager/people/employees.private.example.json`
- Existing eval proof: `scripts/run-company-manager-evals.mjs`
- Actual Hermes behavior proof: `scripts/run-howie-hermes-agent-evals.mjs`,
  `workspaces/howie-ai-poc/agent-runs/2026-08-12-real-hermes-verified/summary.json`
- System gap review: `tickets/TASK-0003/artifacts/system-gap-review.md`
- Plan re-review: `tickets/TASK-0003/artifacts/revised-plan-rereview.md`
- Follow-up state re-review:
  `tickets/TASK-0003/artifacts/requirement-followup-rereview.md`
- Filesystem/delivery plan re-review:
  `tickets/TASK-0003/artifacts/filesystem-delivery-plan-rereview.md`
- Completion review:
  `tickets/TASK-0003/artifacts/implementation-completion-review.md`
- Actual Hermes behavior proof review:
  `tickets/TASK-0003/artifacts/hermes-behavior-proof-review.md`
- Seeded fake-only workspace: `workspaces/howie-ai-poc/`
- Native Goal: `tickets/TASK-0003/program.md`,
  `tickets/TASK-0003/progress.md`, `tickets/TASK-0003/goal-prompt.md`
- Grounding: [Hermes tools](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools/), [Hermes MCP documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp), [Hermes toolsets reference](https://hermes-agent.nousresearch.com/docs/reference/toolsets-reference), [Google Drive MCP configuration](https://developers.google.com/workspace/drive/api/guides/configure-mcp-server)
