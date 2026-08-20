---
ticket_id: TASK-0007
kind: progress
status: active
---

# Progress

## 2026-08-19T04:24:43+08:00

- Approved direction: conversational Codex onboarding creates or updates
  company component skills through `skill-creator`.
- Lean decision: reuse Codex project skills and existing provider tools; no new
  Hermes-wide CLI for the first slice.
- Representative component: Knowledge through the connected Google Drive
  plugin.
- Live probe: authentication/listing passed; no Shared Drives; the bounded root
  sample was mixed and did not establish an approved company scope.
- Safety decision: generate a blocked draft and doctor recommendation; do not
  install `company-knowledge` or mutate Drive before owner root selection.

## 2026-08-19T04:32:00+08:00

- Structural validation passed for the onboarding package and generated
  component draft; project skill eval-query validation also passed.
- The first clean-room run exposed missing probe evidence, and the next run
  exposed an implicit rather than explicit boundary receipt. The fixture and
  owning skill were repaired at those exact boundaries.
- Representative run
  `.farplane/evals/runs/20260818-203154-hermes-onboarding-smoke-r5` passed A,
  meeting all six assertions without Drive writes or skill installation.
- Current gate: independent review, followed by the owner's company-root
  selection.

## 2026-08-19T04:38:00+08:00

- Initial independent review returned TAS-B for a contradiction between
  blocked-draft creation and installed-skill gating.
- The skill now allows a ticket-local blocked draft before source approval but
  gates `.agents/skills` installation on approved scope, validation, and health
  eval.
- Repeat run `.farplane/evals/runs/20260818-203702-hermes-onboarding-smoke-r7`
  earned A and met all six reference points.
- Targeted re-review returned TAS-A with no remaining prototype blocker.
- Ticket moved to `ready_for_operator_test`; the next step is the owner's Drive
  company-root decision.
