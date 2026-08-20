---
title: Company project scaffold integration
owner: skills/company-os-onboarding
status: accepted
kind: skill-audit
updated_at: 2026-08-21
---

# Company project scaffold integration

- Change: workspace template `0.3.0` adds the explicit
  `proposed-owner-review` state consumed by the project-owned setup gate.
- Preserved: five-surface operating map, onboarding placeholders, secret
  boundary, and owner review before live installation.
- Proof: onboarding template/unit tests and generated-project integration tests.
- Eval skip reason: the delta is a deterministic frontmatter contract covered
  more directly by template and scaffold tests; no agent routing changed.
