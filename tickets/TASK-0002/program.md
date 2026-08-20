---
ticket_id: TASK-0002
trigger: active_goal
approval: approved
compiled_from_ticket_updated_at: 2026-08-10T09:48:00Z
generated_prompt: tickets/TASK-0002/goal-prompt.md
---

# Goal Program: dependency-aware company plan

## Objective and mutable surface

Complete only TASK-0002’s Scope and Done conditions. Mutable source is limited
to the manager simulator, frozen fixtures, dashboard/server, focused tests,
ticket-scoped proof artifacts and project docs required by that ticket.

## Budget and stops

- **Window:** one continuous operator-authorized hour.
- **Tokens/spend:** no numeric token or spend budget was supplied; do not start
  a paid service, live transport or deployment.
- **Stop complete:** every Done condition and named proof gate passes.
- **Stop blocked:** a required live credential, human product decision or
  unresolvable source conflict is needed.
- **Stop report:** the time window expires with current evidence and one next
  action recorded.

## Metric / provider

Use a **hybrid** provider: frozen-scenario checks for correctness plus
independent visual/implementation review for usefulness. No numeric usability
threshold is invented. Guards are: no external send, no second task store, no
state transition before all declared requirements resolve.

## Decision backbone

`observe -> choose_next(objective, evidence, eligible_moves, remaining_budget) -> execute | diagnose | report_now | request_feedback | stop -> act -> verify -> write_back`

Prefer the smallest move that advances the critical path. Invoke no advisor
inside this Goal unless a material new decision appears; this program owns the
next-turn choice.

## First-load context gate

Initial read is full `ticket.md`, full `program.md`, and at most the latest 80
lines of `progress.md`. Target 300 lines; block and consolidate above 400.
Load `design.md`, `docs/prd.md`, source, fixtures and evidence only to resolve
a named implementation/proof gap.

## Logging and drift

Append a compact receipt to `progress.md` after each turn:

```yaml
observation:
evidence: []
learning:
decision: execute | diagnose | report_now | request_feedback | stop | blocked
remaining_budget:
next_action:
```

Run `goal-drift-reviewer` after the dependency contract and before completion
review; regenerate this packet if ticket scope, design, suite or proof policy
changes.

## Proof route

Run ordered engine checks first, then browser capture, visual QA, independent
review and a local narrated demo. Record strongest screenshot and all receipts
in ticket Links/progress. Do not self-certify a completion claim. `demo` is a
local proof artifact, never evidence of real Telegram or Drive activity.

## Delayed check-in

`mode: not_applicable` — this is an immediate implementation Goal, not an
experiment with delayed reward.
