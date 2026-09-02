---
title: Notion platform plugin
status: in_progress
owner: Company OS
updated_at: 2026-08-31
---

# Notion platform plugin

This directory owns the Notion API adapter, webhook protocol, interactive
webhook onboarding, plugin manifest, and their focused tests. General Company
OS installation and lifecycle orchestration remain in `apps/installer/`.

## Runtime contract

- `adapter.py` receives `comment.created`, isolates conversations by Notion
  discussion, and sends replies back to that discussion.
- `api.py` owns bounded Notion reads and opt-in page-property writes.
- `protocol.py` verifies raw-body HMAC signatures and stores bounded private
  webhook state.
- `onboarding.py` collects the Notion and ngrok values and guides the
  browser-only verification gate.
- `plugin.yaml` declares tools and configuration.

Page-property writes remain disabled unless `NOTION_ENABLE_WRITES=true`.
Tokens and webhook state belong in the private Hermes profile, never this
repository.

## Configure real-time comments

Scheduled Daily and Weekly automations do not require this webhook.

1. Create an ngrok account and copy its agent authtoken and assigned stable
   HTTPS development domain. The free plan provides one assigned domain.
2. Do not run ngrok separately. The Company OS Compose stack owns the agent and
   forwards the assigned domain to `http://gateway:8645`.
3. Run Company OS setup and provide the hidden Notion integration token, hidden
   ngrok authtoken, and assigned URL such as
   `https://example-name.ngrok-free.app`. Localhost, non-HTTPS, query, fragment,
   unrelated path, and temporary `trycloudflare.com` values are rejected. Setup
   normalizes the endpoint to
   `https://example-name.ngrok-free.app/notion/webhook`.
4. In the same Notion internal connection, create a Webhooks subscription for
   that endpoint and the `comment.created` event. Enable Read content, Read
   comments, and Insert comments.
5. Paste the one-time verification token shown by setup into Notion. Share an
   isolated test page with the connection and manually post the trigger shown
   by setup, for example `@companyos setup healthcheck`.

Automatic creation of this isolated test comment is deferred. The current
acceptance gate keeps the Notion write visible to the operator; the planned
upgrade is scoped in the customer setup guide.

Do not place ngrok authentication or an interactive traffic policy in front of
the endpoint because Notion must reach it directly. If verification does not
arrive, check the ngrok container and public health endpoint before creating
another subscription.

## Verify locally

```bash
python3 -m unittest \
  plugins.platforms.notion.tests.test_comment_adapter \
  plugins.platforms.notion.tests.test_webhook_protocol -v
```

The repository-wide `tests/test_owned_packages.py` bridge keeps
these plugin-owned cases in the canonical root discovery run.

Notion references: [webhooks](https://developers.notion.com/reference/webhooks)
and [connection capabilities](https://developers.notion.com/reference/capabilities).
