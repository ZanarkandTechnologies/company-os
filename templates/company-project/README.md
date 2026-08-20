# {{COMPANY_NAME}}

{{COMPANY_NAME}} is a source-controlled configuration and evaluation harness
for its Hermes company manager. The live agent runs from a separate Hermes
workspace.

```text
workspace.hermes.md  Reviewable, nonsecret company context
automations/          Daily and weekly operating contracts
skills/               Company-owned skills and workspace setup
evals/                Company cases and isolated filesystem evals
scripts/              Project-specific deterministic helpers
tests/                Project contract tests
```

Start by completing `workspace.hermes.md`, removing onboarding comments, and
keeping its status `proposed-owner-review` until the owner approves the full
map. Run the setup skill in preview mode before any source-to-runtime install.

Generated reports, memory, credentials, sessions, and logs belong in the
separate Hermes runtime and profile, never in this repository.
