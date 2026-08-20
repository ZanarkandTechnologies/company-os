---
template_id: goal-loop-program
template_version: "0.1.7"
kind: goal-program
title: TASK-0004 Goal Program
status: active
owner: goal-advisor
ticket_ref: tickets/TASK-0004/ticket.md
progress_ref: tickets/TASK-0004/progress.md
---

# TASK-0004 Goal Program

## Goal Mode

```yaml
trigger: active_goal
files:
  - tickets/TASK-0004/ticket.md
  - tickets/TASK-0004/program.md
  - tickets/TASK-0004/progress.md
  - profiles/howie-ai/
  - scripts/sync-howie-ai-profile.mjs
  - scripts/company-manager.mjs
  - scripts/company-delivery.mjs
  - scripts/serve-dashboard.mjs
  - dashboard/index.html
compiled_from_ticket_updated_at: 2026-08-12T13:32:00+08:00
generated_prompt: tickets/TASK-0004/artifacts/native-goal-prompt.md
budget: unspecified
approval: approved
```

## Execution Contract

- Objective: make the exact `howie-ai` profile complete one real fake-data
  company-manager workflow through native Hermes, Google Drive and filesystem
  tickets, with inspectable proof.
- Mutable surface: TASK-0004 Scope: In files plus private `howie-ai` runtime,
  verified profile backups, fake-only Drive fixture and live POC workspace.
- Hard constraints: preserve `default`; export before duplicate-profile delete;
  never expose credentials/phone numbers; fake Drive data only; no arbitrary
  recipient, cron, ACL mutation, or unreviewed external commitment.
- Evidence owner: ticket QA Strategy and ticket-scoped artifacts.
- Hypothesis tree: none.

## Metric Provider

```yaml
provider: hybrid
primary: TASK-0004 Done checklist plus three native howie-ai acceptance cases
direction: pass
guards: [offline tests remain green, private values remain redacted, external actions stay explicitly gated]
anti_metrics: [canned replay, second client profile, unrelated Drive access, false send claim]
minimum: all available mechanical checks pass; live proof reports any operator-gated remainder honestly
```

## Decision Backbone

```text
choose_next(objective, evidence, eligible_moves, remaining_budget)
  -> execute | diagnose | report_now | request_feedback | stop
```

Apply `observe -> choose_next -> act -> verify -> write_back`. Execute the
mechanically implied safe move. Request feedback only for interactive Google
consent, unavailable private credentials, an unverified destructive target, or
another explicit external gate.

## Proof Policy

- Checks: ticket QA Strategy in order, cheapest local checks before live paths.
- Evidence paths: `tickets/TASK-0004/artifacts/` and private live receipts.
- Drift owner: `goal-drift-reviewer` before completion candidate.
- Final checkpoint: QA evidence review, browser proof, demo, completion review.

## After Each Turn

- Read full ticket/program and at most the latest 80 progress lines initially.
- Append observation, evidence, learning, decision, remaining budget, and next
  action before yielding.
- Continue while a safe move beats reporting, feedback, and stopping.

## Stop Conditions

- `complete`: Done/QA/review gates pass.
- `report_now`: useful verified partial result exists and the next move needs
  operator presence.
- `request_feedback`: interactive OAuth or missing private binding is required.
- `blocked`: a required authority or proof route is unavailable.
- `budget_limited`: no justified move fits the unspecified remaining budget.
