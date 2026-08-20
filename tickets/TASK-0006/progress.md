---
ticket_id: TASK-0006
artifact: progress
updated_at: 2026-08-19T13:05:00+08:00
---

# Progress

- 2026-08-19: Confirmed Hermes v0.20.0 generic webhooks do not support
  `X-Notion-Signature` or Notion's unsigned verification-token handshake.
- 2026-08-19: Selected the native platform-plugin rung: one gateway process,
  source-owned plugin, no separate service.
- 2026-08-19: Implemented the plugin, scoped tools, handshake CLI, source sync,
  and persistent bounded deduplication; all repository tests pass.
- 2026-08-19: Installed into the real `howie-ai` profile. Hermes discovers the
  enabled plugin and toolset. An isolated gateway accepted a signed event,
  deduplicated its replay, rejected an unsigned event, and exposed the captured
  token through the local CLI. Live activation awaits private credentials and
  a public HTTPS URL.
- 2026-08-19: Added sync hygiene for generated Python cache files, applied the
  live profile sync, reran protocol/repository checks, and confirmed the
  operator CLI reports no captured token before Notion registration.
- 2026-08-19: Independent review caught and drove a repair to the model-facing
  tool schema wrapper. The real Hermes registry now validates both definitions;
  generated Python bytecode is excluded from source and profile sync.
- 2026-08-19: Final independent re-review passed at TAS-A with no blocking
  findings. Ticket advanced to `ready_for_operator_test`; live activation
  remains gated only by private credentials and a public HTTPS endpoint.
