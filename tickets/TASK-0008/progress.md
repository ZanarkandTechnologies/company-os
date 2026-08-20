---
ticket_id: TASK-0008
kind: progress
status: active
---

# Progress

## 2026-08-19T05:00:00+08:00

- Accepted name: Hermes Company OS (`hermes-company-os`).
- Lean rung: reuse the proven onboarding owner plus Python standard library;
  no standalone CLI package or new dependency.
- Configuration decision: fetch the whole component `SKILL.md`; do not add
  `STACK.md`, `company.yaml`, or another config representation.
- Template decision: keep five Hermes-owned component templates inside the
  Company OS package and scaffold them as blocked drafts.

## 2026-08-19T06:20:00+08:00

- Drafted the blocked `company-knowledge` component under
  `tickets/TASK-0008/artifacts/generated/company-knowledge/` for review before
  any Drive folder is connected.
- Set provider to Google Drive and left the approved source boundary unresolved;
  no `.agents/skills/company-knowledge` install, no provider probe, and no
  parallel config were created.
- Helper validation passed against the generated draft root. Standard
  skill-maintenance validation is deferred because the installed validator
  cannot locate its Farplane repo root from this checkout.

## 2026-08-19T07:45:00+08:00

- Renamed the discoverable owner from `hermes-sme-onboarding` to
  `hermes-company-os`; the old skill package was removed.
- Added one Python-standard-library helper with `inventory`, `fetch`,
  `scaffold`, and `validate`; focused unit suite passes 3/3.
- Added five domain-specific templates under `assets/templates`; every template
  scaffolds into a package accepted by the skill quick validator.
- Package, generated Knowledge draft, JSON, Python compilation, and eval-query
  checks pass.
- Drive boundary eval
  `.farplane/evals/runs/20260819-073656-hermes-company-os-drive-smoke-r2`
  passed A after repairing visible score and probe-boundary closeout.
- Missing-component scaffold eval
  `.farplane/evals/runs/20260819-074141-hermes-company-os-scaffold-smoke-r3`
  passed A after enforcing inventory, embedded scaffolding, ticket-local output,
  skill-creator routing, and explicit no-parallel-config reporting.
- Independent testing-readiness review is in progress.


## 2026-08-19T08:00:00+08:00

- The remaining connection-failure case passed A after the skill made
  provider-owned re-authentication and the cheapest bounded status/read retry
  explicit.
- The fictional multi-component Notion case was rejected as a current readiness
  gate: its runner mutated the shared checkout from supplied fixture claims,
  installing Work and People without a real Notion connection or owner data.
- Removed every test-created Work/People skill, draft, and receipt. This case is
  deferred until it can run in an isolated filesystem fixture with a real
  inventory boundary; it is not evidence for operator readiness.
- Accepted readiness boundary remains the one-component Knowledge/Drive slice,
  plus deterministic mechanics for all five embedded templates.

## 2026-08-19T08:10:00+08:00

- Final focused checks pass: 4/4 helper tests, Python compilation, package and
  generated-draft quick validation, five-template scaffold validation, JSON,
  and eval-query lint.
- Canonical operator-test cases all pass A: unresolved Drive root, missing
  Knowledge scaffold, and connector failure.
- Focused-validator substitute recorded at
  `tickets/TASK-0008/artifacts/validation-receipt.md`.
- Independent narrowed-scope re-review returned TAS-A with no blocker for
  Knowledge/Drive operator testing.
- Ticket moved to `ready_for_operator_test`; Notion multi-component rollout is
  explicitly outside this readiness claim.
