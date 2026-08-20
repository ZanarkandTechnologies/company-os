# {{COMPANY_NAME}} source and runtime contract

This repository is the source-controlled development and evaluation harness for
the {{COMPANY_NAME}} Hermes manager. It is not the live Hermes workspace.

## Ownership

- This repository owns `workspace.hermes.md`, automation contracts,
  company-owned skills, evals, deterministic helpers, and tests.
- The separate Hermes workspace owns generated reports, memory, proposals,
  receipts, and other live company artifacts.
- The Hermes profile owns credentials, installed skill copies, sessions, logs,
  caches, gateway state, and local databases.
- HermesCorp owns reusable, company-agnostic templates and procedures.

## Layout

- `workspace.hermes.md`: reviewed source context installed as runtime
  `.hermes.md`.
- `automations/`: readable operating contracts.
- `skills/`: project-owned skill source, including explicit workspace setup.
- `evals/`: company cases plus the isolated filesystem-eval harness.
- `scripts/` and `tests/`: project-specific deterministic proof.

Do not add `configs/`, `plugins/`, `profile/`, `workspaces/`, or a nested
distribution tree unless a later accepted requirement establishes a distinct
owner. Do not use symlinks as synchronization.

## Development flow

1. Edit and test source here first.
2. Preview installation with `skills/setup-company-workspace`.
3. Apply only after `workspace.hermes.md` is owner-reviewed and marked
   `approved` or `active`.
4. Configure Hermes `terminal.cwd` natively and verify from a fresh session.
5. Upstream only generalized, company-agnostic improvements to HermesCorp.

Never commit credentials, private runtime state, generated operating output, or
unsanitized company data.
