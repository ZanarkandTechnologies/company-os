---
title: Company workspace setup QA
owner: skills/setup-company-workspace
status: active
kind: qa-checklist
updated_at: 2026-08-21
---

# Company workspace setup QA

- [ ] The runtime workspace and profile home are real, separate directories outside the source project.
- [ ] The reviewed context, automations, and skill packages are the only managed source surfaces; setup never deletes target files.
- [ ] `workspace.hermes.md` is `approved` or `active` before `--apply`; credentials and private runtime state stay out of source.
- [ ] Hermes `terminal.cwd` is set through its native config command, not a tracked profile overlay or symlink.
- [ ] Deterministic tests pass and the final receipt distinguishes preview, applied changes, and live-session proof.
