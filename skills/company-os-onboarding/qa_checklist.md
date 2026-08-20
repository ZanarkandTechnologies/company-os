---
template_id: skill-qa-checklist
template_version: "0.1.1"
title: Company OS Onboarding QA Checklist
owner: company-os-onboarding
status: active
kind: qa-checklist
---

# Hermes Company OS QA Checklist

```text
company_os_qa(stack, routes, workspace_context, receipt)
  -> pass | violation | deferred
```

- [ ] The seven onboarding stages were made visible and the owner was asked for the current stack once, before platform-specific questions.
- [ ] Every configured platform has a named skill, CLI, or MCP route with a successful status check and bounded read.
- [ ] `.hermes.md` contains the company name, description, and the five company surfaces.
- [ ] Every populated source row names its platform, interaction route, real source or link, and structural description.
- [ ] Additional rows are used for additional platforms; no second stack schema or intermediary component skill was created.
- [ ] Template placeholders, onboarding comments, and unused example rows were removed from the rendered file.
- [ ] Credentials, tokens, private keys, transient health state, and broad source dumps are absent.
- [ ] Consequential writes remain approval-gated and company-specific boundaries are explicit.
- [ ] A fresh Hermes session loads the file and completes one representative lookup per connected platform.
- [ ] The separate receipt names configured, blocked, and deferred routes without becoming runtime configuration.
- [ ] Operating gaps were offered as recommendations, not prerequisites for the first useful install.
- [ ] Optional channel setup began only after core proof and cannot invalidate core readiness.

## Reviewer Prompt

```text
Review the rendered company workspace and connection receipt against this
checklist. Treat secrets, unresolved template instructions, invented source
authority, untested routes, or duplicated configuration as blockers.
```
