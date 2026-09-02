# Shared entity templates

This directory owns provider-backed business entity shapes used outside a
single automation cadence. It is intentionally flat so every shared entity is
visible without navigating category folders.

```text
templates/
├── project.md
├── person.md
├── task.md
├── issue.md
├── meeting.md
├── feature.md
├── decision.md
└── sop.md
```

Frontmatter maps to provider database properties. Markdown below frontmatter
maps to the entity page body; do not duplicate either surface in the other.
Each template retains a stable `template_id`, `template_version`, complete body
shape, and realistic golden example where applicable.

Operational templates belong to their sole skill owner:

- PM Daily owns Project Memory, documentation-request, and progress-follow-up
  templates under `skills/pm-daily/templates/`.
- PM Weekly owns Project, Department, and Company reports plus executive
  distribution under `skills/pm-weekly/templates/`.

Setup installs these shared entity templates as `workspace/templates/` and the
cadence-owned templates inside their installed skill packages. Skills read the
Markdown directly; there is no generated catalog or template-to-schema sync.
