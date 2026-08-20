---
ticket_id: TASK-0002
approval: approved
compiled_from_ticket_updated_at: 2026-08-10T09:48:00Z
---

# Native Goal Prompt

```text
/goal Run the following files as one Goal Packet.
Files:
- tickets/TASK-0002/ticket.md
- tickets/TASK-0002/program.md
- tickets/TASK-0002/design.md
- tickets/TASK-0002/progress.md
- docs/prd.md
- HARNESS.md
- docs/company-manager.md
- scripts/company-manager.mjs
- scripts/serve-dashboard.mjs
- dashboard/index.html
- fixtures/company-manager/meetings/mock-weekly-meeting.json
- tests/company-manager.test.mjs
- tests/dashboard.test.mjs

Task: Complete only TASK-0002 Scope and Done. Preserve filesystem tickets as
the only task state. Build typed human/skill-output requirements and views as
projections; do not add Telegram sends, credentials, Drive/OAuth, cron, or a
second board.

Logging: Read program.md first, then the full ticket and only the latest 80
lines of progress.md. Load design/PRD only for a named UI or requirements gap.
Append the required compact receipt each turn.

Metric: Use the program’s hybrid frozen-scenario plus independent-review
provider. Follow the ticket QA Strategy’s ordered critical path. Do not
self-certify visual, QA, reviewer or demo proof.

After each turn: observe -> choose_next(objective, evidence, eligible_moves,
remaining_budget) -> execute | diagnose | report_now | request_feedback | stop
-> act -> verify -> write_back.

Context gate: ticket + program + latest 80 progress lines; target 300, hard
400. Drift reviewer: goal-drift-reviewer after the dependency contract and
before final review. Approval: approved by the operator’s explicit request to
run this Goal while away. If the ticket changes materially, regenerate this
packet before continuing.

Final checkpoint: engine checks -> browser proof -> visual QA -> local narrated
demo -> completion review -> ticket/progress writeback. The final response must
include Ticket, Verification, Artifacts, Grounding and Residual risk.
```
