---
title: Notion Webhook Onboarding QA Checklist
owner: notion-webhook-onboarding
status: active
kind: qa-checklist
---

# Notion Webhook Onboarding QA Checklist

```text
notion_webhook_onboarding_check(skill, cli, receipt) -> pass | revise | blocked
```

- [ ] The workflow assumes Hermes already exists and never configures a reverse
      proxy, DNS, VPS account, or model choice.
- [ ] Account credentials enter only through an interactive terminal or
      existing Doppler scope; logs, arguments, and chat contain none. Only the
      explicit verification phase may surface the webhook verification token.
- [ ] Comment replies are unconditionally enabled while page-property writes
      remain disabled unless separately authorized outside this onboarding.
- [ ] Every phase is resumable and returns structured `ready`,
      `human_required`, or `blocked` state with one exact next action.
- [ ] Completion includes a captured verification token, discovered source
      count, locked workspace, and persisted successful reply receipt.
