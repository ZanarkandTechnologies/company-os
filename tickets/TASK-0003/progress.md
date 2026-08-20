---
ticket_id: TASK-0003
kind: goal-progress
---

# Progress: TASK-0003

```yaml
observation: "Kenji requested the actual Hermes WhatsApp gateway and actual Google Drive integration, while keeping all test-platform data fake and the customer VPS out of scope."
evidence:
  - ARCHITECTURE.md
  - HARNESS.md
  - profiles/howie-ai/config.template.yaml
  - docs/company-manager.md
learning: "The local simulator already proves canonical task state, but it has no authenticated Drive connection, paired gateway, model, or bounded inbound adapter. Hermes documents that Google's official Drive MCP requires a pre-registered OAuth client rather than automatic client registration."
decision: request_feedback
remaining_budget: "No numeric token or time budget supplied; native Goal is active, but external integration work remains held until the packet is approved."
next_action: "Obtain packet approval, implement source-safe adapter/configuration changes, then stop for Kenji at OAuth, model, and WhatsApp QR gates."
```

```yaml
observation: "System review confirmed that the direct simulator cannot prove Hermes behavior: no manager MCP exists, WhatsApp retains a generic file tool, manager logic is hard-wired to Drive mock files, and the three task rows have no Hermes session/file-content proof."
evidence:
  - tickets/TASK-0003/artifacts/system-gap-review.md
  - profiles/howie-ai/config.template.yaml
  - scripts/company-manager.mjs
  - scripts/run-company-manager-evals.mjs
  - .farplane/evals/tasks/harness_tasks.json
learning: "The smallest faithful route reuses the existing JSON scenarios and one source profile, but requires a bounded local manager MCP, a filtered real Drive MCP under a clean fake-data identity, and ephemeral per-session profile/workspace state. Gateway replies are normal same-thread responses, not a controllable `hermes send` receipt path."
decision: request_feedback
remaining_budget: "No numeric budget supplied. The revised plan is blocked for a renewed review before source changes or external configuration."
next_action: "Obtain review of the gap-driven revision, then implement the source-safe capability and eval layers before the OAuth/model/QR human gates."
```

```yaml
observation: "The reviewed packet remains pending operator approval across the Goal's review and two subsequent continuation checks."
evidence:
  - tickets/TASK-0003/artifacts/goal-packet-review.md
  - tickets/TASK-0003/program.md
learning: "Source-safe implementation is intentionally held by the approved Goal program until Kenji accepts the packet; OAuth, WhatsApp pairing, model setup, and any test receipt are not authorized before then."
decision: blocked
remaining_budget: "No numeric budget supplied. The native Goal is blocked rather than silently executing past the review gate."
next_action: "Kenji approves TASK-0003; resume source configuration and stop next at the OAuth/model/QR operator gates."
```

```yaml
observation: "Independent packet review found the original wording ambiguous about real WhatsApp replies: the existing source policy is preview/no-delivery while the private roster example permits outbound for an opted-in test contact."
evidence:
  - tickets/TASK-0003/ticket.md
  - tickets/TASK-0003/program.md
  - profiles/howie-ai/private-roster.example.json
  - profiles/howie-ai/schedule-policy.md
learning: "A useful real gateway proof needs a visible response, but it must be a single operator-started, same-thread receipt rather than an autonomous delivery/chase capability."
decision: request_feedback
remaining_budget: "No numeric token or time budget supplied; external integration work remains held until the revised packet passes review and Kenji approves it."
next_action: "Re-review the explicit one-run outbound boundary, then present the packet for Kenji's approval."
```

```yaml
observation: "The revised-packet reviewer found two remaining execution blockers: named MCP toolsets were not explicitly exposed to WhatsApp after removing generic file access, and the native Goal packet omitted the active legacy sender and Farplane scenario ownership files."
evidence:
  - tickets/TASK-0003/artifacts/revised-plan-review.md
  - https://hermes-agent.nousresearch.com/docs/reference/toolsets-reference
  - tickets/TASK-0003/ticket.md
  - tickets/TASK-0003/goal-prompt.md
learning: "Hermes creates dynamic mcp-<server> toolsets, so a least-privilege WhatsApp route needs an exact five-toolset allowlist. A plan that retires a legacy sender and reuses the existing eval catalog must name those files in the executable context packet."
decision: request_feedback
remaining_budget: "No numeric budget supplied. The repaired plan is awaiting an independent rerun review before operator approval."
next_action: "Rerun plan review for the exact MCP toolset contract and complete Goal Packet ownership list; then present the revised ticket to Kenji."
```

```yaml
observation: "The repaired TASK-0003 packet passed independent plan re-review at TAS-A with no hard-gate failures."
evidence:
  - tickets/TASK-0003/artifacts/revised-plan-rereview.md
  - tickets/TASK-0003/ticket.md
  - tickets/TASK-0003/program.md
  - tickets/TASK-0003/goal-prompt.md
learning: "The POC is now executable without reopening the connector/security design: WhatsApp has an exact dynamic-MCP allowlist, the legacy send route is an explicit retirement target, and the same three harness task IDs remain the only session-eval catalog."
decision: request_feedback
remaining_budget: "No numeric budget supplied. Source-safe work remains intentionally unstarted until Kenji approves the reviewed packet."
next_action: "Kenji approves TASK-0003; then implement local source/adapter/session-eval/dashboard changes and stop at OAuth, model, Drive login, and WhatsApp QR gates."
```

```yaml
observation: "A final source audit found that the existing simulator persists one ticket-global chase object even though a ticket can be blocked by multiple people and requirements."
evidence:
  - scripts/company-manager.mjs
  - docs/company-manager.md
  - tickets/TASK-0003/ticket.md
learning: "Progress.md is the right immutable audit history, but current next-chase/attempt/escalation state must live on each human requirement. A board summary and global employee cooldown can be derived from those events without creating a competing mutable memory store."
decision: request_feedback
remaining_budget: "No numeric budget supplied. The narrowed state-model amendment is awaiting independent re-review; no source work has started."
next_action: "Re-review requirement-local follow-up state, then present the final reviewed TASK-0003 packet to Kenji for approval."
```

```yaml
observation: "The requirement-local follow-up amendment passed scoped independent re-review at TAS-A with no hard-gate failures."
evidence:
  - tickets/TASK-0003/artifacts/requirement-followup-rereview.md
  - tickets/TASK-0003/ticket.md
learning: "The correct minimal state model is per-human-requirement schedule plus append-only progress events. A global employee cooldown and board next-chase are derivations, not writable duplicate memories."
decision: request_feedback
remaining_budget: "No numeric budget supplied. Source-safe execution remains held for Kenji's approval; all external integration gates remain untouched."
next_action: "Kenji approves TASK-0003; then implement local source/adapter/session-eval/dashboard changes and stop at OAuth, model, Drive login, and WhatsApp QR gates."
```

```yaml
observation: "Kenji approved a simpler POC: native filesystem tickets in a dedicated test workspace, a private employee directory, and a constrained delivery worker for proactive WhatsApp chases."
evidence:
  - tickets/TASK-0003/ticket.md
  - profiles/howie-ai/private-roster.example.json
  - scripts/deliver-manager-outbox.mjs
learning: "A manager MCP is unnecessary for this local development proof. The sensitive boundary is outbound delivery: a manual worker must resolve the private directory, require an explicit send gate, and write its receipt into canonical ticket progress."
decision: execute
remaining_budget: "No numeric budget supplied. Source-safe implementation is authorized; OAuth, model, Drive login, gateway start, QR pairing, and a real send remain later operator gates."
next_action: "Implement profile/file schema, requirement-local delivery drafts, the controlled sender, eval/dashboard proof, then stop for live integration setup."
```

```yaml
observation: "Independent review found an unowned second Hermes sender route and two incompatible private roster shapes."
evidence:
  - tickets/TASK-0003/artifacts/filesystem-delivery-plan-review.md
  - package.json
  - scripts/deliver-manager-outbox.mjs
  - scripts/deliver-outbox.mjs
learning: "A safe active POC needs exactly one delivery command and one manager-owned directory validator. Legacy direct-send paths and parallel schema definitions are not harmless because they bypass the proof boundary."
decision: execute
remaining_budget: "No numeric budget supplied. Source-safe work remains authorized; all live integration gates remain untouched."
next_action: "Retire both legacy sender routes, align profile/fixture examples to the manager validator, re-review, and continue implementation."
```

```yaml
observation: "The delivery-route and directory-schema repairs passed independent plan re-review at TAS-A."
evidence:
  - tickets/TASK-0003/artifacts/filesystem-delivery-plan-rereview.md
learning: "The implementation boundary is now unambiguous: one manager-owned directory validator and one canonical ticket-progress delivery worker replace both old direct-send routes."
decision: execute
remaining_budget: "No numeric budget supplied. Local implementation continues; interactive OAuth, model, Drive, WhatsApp pairing, gateway, and real send gates remain deferred."
next_action: "Finish source implementation, run deterministic evals and dashboard proof, then stop at the live test setup gate."
```

```yaml
observation: "The local source POC is ready for operator testing: the new fake-only workspace is seeded, the public eval command and full test suite pass, and the dashboard exposes the Gantt plus three isolated proof traces."
evidence:
  - workspaces/howie-ai-poc/README.md
  - workspaces/howie-ai-poc/eval-runs/2026-08-12-local-proof-with-hashes/summary.json
  - .farplane/evals/runs/2026-08-11T17-49-28-284Z-company-manager/summary.json
  - tickets/TASK-0003/artifacts/implementation-completion-review.md
  - npm run eval:company-manager (3 pass, 0 gap, 0 error)
  - npm test (10 pass, 0 fail)
learning: "The system proof does not need a second AI-eval profile. The existing three-task catalog exercises isolated filesystem workflows, and each result now records meeting and workflow deltas, SHA-256 values, and bounded canonical ticket/progress/artifact content snapshots. A manual Drive/WhatsApp smoke remains the only honest claim about Hermes behavior."
decision: stop
remaining_budget: "No numeric budget supplied. Local implementation and evidence are complete; the remaining work requires private credentials, consent, QR pairing, and an opted-in test target."
next_action: "Kenji performs the operator-only Drive OAuth/model/WhatsApp self-chat test against workspaces/howie-ai-poc, then records the redacted smoke receipt."
```

```yaml
observation: "The final implementation review passed at TAS-A after the evaluator and Goal packet were reconciled around deterministic filesystem proof."
evidence:
  - tickets/TASK-0003/artifacts/implementation-completion-review.md
  - npm run eval:company-manager (3 pass, 0 gap, 0 error)
  - npm test (10 pass, 0 fail)
learning: "The dashboard can now show the operational trace and replayable filesystem evidence without overstating it as an agent session. The real boundary is crisp: only a manually observed self-chat, Drive OAuth root check, and explicit-gate test send can establish integration behavior."
decision: stop
remaining_budget: "No numeric budget supplied. External activation is operator-owned."
next_action: "Stop at the ready-for-operator-test gate; do not create credentials, pair a device, or send a WhatsApp message without Kenji at the consent and QR steps."
```

```yaml
observation: "A source-synced disposable Hermes profile completed three real model-driven mock-only filesystem scenarios: meeting-to-ticket planning, chained local artifact drafting, and overdue missing-input escalation."
evidence:
  - workspaces/howie-ai-poc/agent-runs/2026-08-12-real-hermes-verified/summary.json
  - scripts/run-howie-hermes-agent-evals.mjs
  - npm run eval:howie-agent (3 pass, 0 fail)
  - npm test (11 pass, 0 fail)
learning: "A real agent proof needs profile-level working-root isolation. Rebinding the disposable clone before each scenario plus a profile lock prevents filesystem cross-talk, while preserving private credentials outside the repository."
decision: stop
remaining_budget: "No numeric budget supplied. The real local mock proof is complete; Drive OAuth, WhatsApp pairing, and a test send remain operator-owned integration gates."
next_action: "Use the Evidence tab to inspect the real Hermes prompt/reply/files, then perform the separately approved fake-Drive and self-chat smoke only with Kenji present."
```

```yaml
observation: "Independent completion review passed after the dashboard agent-proof reader was constrained to derived run-local paths."
evidence:
  - tickets/TASK-0003/artifacts/hermes-behavior-proof-review.md
  - tests/dashboard.test.mjs
  - npm test (11 pass, 0 fail)
learning: "Agent-eval artifacts are evidence, not authority: dashboards must derive read targets from the selected run and safe scenario ID, never from embedded absolute paths."
decision: stop
remaining_budget: "No numeric budget supplied. Local real-model proof is reviewed and ready to test; external connector activation remains intentionally unexecuted."
next_action: "Kenji can now test the displayed local Howie proof; perform only separately approved fake-Drive OAuth, self-chat pairing, and explicit send gates when ready."
```

```yaml
observation: "The Evidence page now presents the real model proof as a WhatsApp conversation with Manager and opens the four model-created reports as attachment cards; technical prompts and raw output are collapsed under Developer evidence."
evidence:
  - workspaces/howie-ai-poc/agent-runs/2026-08-12-whatsapp-verified-v5/summary.json
  - tickets/TASK-0003/artifacts/qa/whatsapp-evidence-qa.md
  - npm test (11 pass, 0 fail)
learning: "User-facing agent proof must separate the scored Manager reply from raw execution stdout. A dedicated manager_reply artifact makes message quality testable without hiding the underlying developer evidence."
decision: stop
remaining_budget: "No numeric budget supplied. The local WhatsApp-shaped real-agent proof is complete; live WhatsApp, Drive MCP, and outbound sends remain operator gates."
next_action: "Open Evidence, select Create reports, and expand any attachment; proceed to live integration only with the operator present."
```

```yaml
observation: "Independent re-review passed the WhatsApp Evidence correction at TAS-A after attachment-language consistency was added and the real v5 run passed."
evidence:
  - tickets/TASK-0003/artifacts/whatsapp-evidence-review.md
  - workspaces/howie-ai-poc/agent-runs/2026-08-12-whatsapp-verified-v5/summary.json
learning: "A user-facing attachment claim must be scored against the actual rendered artifact count; model fluency is not evidence consistency."
decision: stop
remaining_budget: "No numeric budget supplied. The local proof is complete and reviewed."
next_action: "Leave the Evidence tab on Create reports for operator inspection."
```

```yaml
observation: "The Evidence surface was simplified from a WhatsApp imitation into three neutral mock chat sessions with visible test assertions and expandable file/content proof immediately below each conversation."
evidence:
  - workspaces/howie-ai-poc/agent-runs/2026-08-12-simple-chat-v6/summary.json
  - tickets/TASK-0003/artifacts/qa/simple-chat-evidence-qa.md
  - npm test (11 pass, 0 fail)
learning: "The useful proof unit is behavior plus assertion: show the manager's short operational updates first, then prove ticket state, Drive use, artifact content, and escalation from the resulting files."
decision: stop
remaining_budget: "No numeric budget supplied. The three local mock sessions are complete and browser-proved."
next_action: "Inspect Evidence tabs 1–3; live integrations remain separate operator gates."
```

```yaml
observation: "Independent completion review passed the simplified chat and validation surface at TAS-A with no findings."
evidence:
  - tickets/TASK-0003/artifacts/simple-chat-evidence-review.md
  - tickets/TASK-0003/artifacts/qa/simple-chat-evidence-qa.md
learning: "The chat-plus-assertions presentation now matches both the user story and the underlying real-model filesystem evidence."
decision: stop
remaining_budget: "No numeric budget supplied. Local implementation is complete and independently reviewed."
next_action: "Keep the Evidence page open for operator inspection."
```

```yaml
observation: "The real-model evidence suite now matches the three final manager stories: meeting notes create and start the plan, a blocked requirement finds and chases the right expert, and an end-of-week pulse escalates after two prior follow-ups."
evidence:
  - workspaces/howie-ai-poc/agent-runs/2026-08-12-pulse-tests-v7/summary.json
  - tickets/TASK-0003/artifacts/qa/pulse-loop-evidence-qa.md
  - npm test (11 pass, 0 fail)
learning: "The customer-facing trace should render the real Manager reply, while deterministic file assertions immediately below prove the behavior. A separate Drive-to-artifact story obscured the manager loop and was removed from the three primary evals."
decision: stop
remaining_budget: "No numeric budget supplied. The three local real-model stories are complete and browser-proved."
next_action: "Inspect Evidence tabs 1–3; live WhatsApp delivery and Drive OAuth remain separate operator gates."
```

```yaml
observation: "The Evidence page was redesigned as one minimal operator workflow: fixture workspace and capabilities first, then the real Manager session, then the exact filesystem delta and proof checks. Raw evaluator telemetry is retained in the run folder but removed from the customer-facing page."
evidence:
  - tickets/TASK-0003/artifacts/evidence-surface-design-brief.md
  - tickets/TASK-0003/artifacts/qa/evidence-surface-redesign-qa.md
  - workspaces/howie-ai-poc/agent-runs/2026-08-12-evidence-surface-v9/summary.json
  - npm test (11 pass, 0 fail)
learning: "The proof surface reads best when its spatial order mirrors the harness lifecycle. A complete visible fixture tree and explicit capability boundary explain the run more effectively than raw prompts, stdout, or a separate developer-evidence panel."
decision: stop
remaining_budget: "No numeric budget supplied. The local proof surface and its real-model evidence are complete."
next_action: "Use Evidence tabs 1–3 for the customer demo; live WhatsApp delivery and Drive OAuth remain separate operator gates."
```

```yaml
observation: "The real Hermes proof now stages the actual Howie AI SOUL and six native skill packages with their own templates, then renders only the customer-readable Manager message, actual file-tool events, and filesystem result. The meeting case produces a geo draft and two scheduled role-specific follow-ups in the same turn."
evidence:
  - workspaces/howie-ai-poc/agent-runs/2026-08-12-native-profile-live-v4/summary.json
  - tickets/TASK-0003/artifacts/qa/native-profile-real-session-qa.md
  - npm test (11 pass, 0 fail)
learning: "The real behavior assertion should judge the required business state and evidence, not one model-chosen internal requirement label. Visible tool events are useful proof; raw model deliberation is not a customer-facing artifact."
decision: stop
remaining_budget: "No numeric budget supplied. The local no-send real-session proof is passing and browser-proved."
next_action: "For direct howie-ai-profile testing, add its development model credential privately; WhatsApp pairing and fake-Drive OAuth remain separate explicit operator gates."
```

```yaml
observation: "Each Evidence scenario now exposes a direct local link to the exact native Hermes chat session that produced its captured manager update and filesystem proof."
evidence:
  - "http://127.0.0.1:9119/chat?profile=howieaieva&resume=20260812_120557_48a879"
  - "workspaces/howie-ai-poc/agent-runs/2026-08-12-native-profile-live-v4/summary.json"
  - "npm test (11 pass, 0 fail)"
learning: "The dashboard replay stays readable, while the native Hermes chat remains the audit source for the full recorded conversation."
decision: stop
remaining_budget: "No numeric budget supplied. The link is a local development-only bridge and depends on the native Hermes dashboard being started."
next_action: "Open an Evidence case and select Open Hermes chat to inspect its exact native session."
```
