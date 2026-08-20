---
skill: company-os-onboarding
date: 2026-08-20
status: pass_with_live_proof_deferred
review_scope:
  - skills/company-os-onboarding
  - skills/notion-webhook-onboarding
  - profiles/kamdar-ai/skills/notion-webhook-onboarding
  - docs/hermes-company-os-onboarding.md
  - README.md
---

# Company OS consolidation audit

## Delta

- Promoted Company OS onboarding from a hidden agent package to the canonical
  root `skills/company-os-onboarding` package.
- Promoted Notion webhook onboarding from one profile to the canonical root
  `skills/notion-webhook-onboarding` package and made the Kamdar profile a
  verified distribution copy.
- Added a deterministic, non-overwriting `.hermes.md` staging and validation
  helper.
- Made seven core onboarding stages visible and moved channel setup behind core
  completion.

## Skill QA

- Ownership: pass; company context and the optional Notion channel have separate
  reusable triggers and output receipts.
- First-load sufficiency: pass; both skills expose context, signature, todo
  path, gotchas, proof, and output without hidden chat context.
- Structure budget: pass; the Company OS and Notion skill files are 134 and 113
  lines respectively.
- Reuse: pass; the profile copy synchronizes from the root owner rather than
  creating a third onboarding abstraction.
- Security: pass; secrets stay in provider-owned secure configuration and local
  runtime state is excluded from version control.
- Behavior eval: deferred for live provider accounts; canonical eval cases are
  preserved and deterministic CLI and distribution behavior are tested.
- Self-improve route: not used because this consolidation has no stable live
  customer baseline yet.

## Proof

- `python3 -m unittest discover -s skills/company-os-onboarding/tests -v` — 8 pass.
- `python3 -m unittest discover -s skills/notion-webhook-onboarding/tests -v` — 12 pass.
- `node scripts/sync-kamdar-notion-webhook.mjs --target profiles/kamdar-ai --check` — clean.
- `npm test` — 32 pass.
- All three changed eval JSON files parse successfully.
- `git diff --cached --check` — pass after repository staging.

## Remaining live gate

Run one owner-reviewed Company OS installation against real company sources and
retain one representative read per configured platform. Optional Notion channel
readiness additionally requires its persisted live reply receipt.
