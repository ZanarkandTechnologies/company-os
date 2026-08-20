---
name: notion-webhook-onboarding
description: "Add Notion comments as an optional Company OS channel through ngrok after core onboarding, guiding secure login and proving one live reply."
tier: 3
group: operations
source: local
template_uses:
  skill-template: "0.4.3"
  skill-qa-checklist: "0.1.0"
eval: evals/evals.json
qa_checklist: qa_checklist.md
---

# Notion webhook onboarding

## Context

Use this skill only after core Company OS onboarding is complete and the
operator wants Notion comments to reach the current Hermes profile. This skill uses ngrok only;
it does not inspect or change Caddy, Nginx, Traefik, DNS, VPS users, or the
Hermes installation.

Chat owns the human handoffs. `scripts/notion_webhook_onboard.py` owns every
repeatable system action and returns JSON so the conversation can resume safely.
Never request a secret in chat. Notion comment replies are always enabled; only
page-property writes retain a separate disabled-by-default gate.

## Skill Signature

```text
onboard_notion_webhook(agent_mention, root_page_url)
  -> verified_webhook + discovered_tables + live_reply_receipt
reads: current profile, Doppler secret names, Notion webhook state, ngrok status
does: installs and runs ngrok, configures Notion scope, guides verification, proves one reply
writes: Doppler nonsecret settings, ngrok system service, connector state
returns: JSON phase receipts; only verification may surface the webhook token
```

<!-- BEGIN FARPLANE_IMPORTANT_CHECKLIST -->
## Todo List

- [ ] 1. Immediately run `python3 scripts/notion_webhook_onboard.py preflight`
      before asking for the root page; preflight does not need it. Require an
      already-installed Hermes profile, a configured Doppler scope, Linux with
      systemd, and the existing Notion connector. Do not merely describe this
      phase and do not offer proxy setup. The first receipt must say
      `ingress=ngrok`; absence of proxy work is part of the product boundary.
- [ ] 2. Ask what people should @mention to invoke the company agent, then ask
      for the Notion root-page URL. Comment
      replies are always true; never ask whether to enable them. When the
      operator asks about this boundary, state that page-property writes remain
      separately disabled by default, then continue the current onboarding
      phase without waiting for a reply preference.
- [ ] 3. Resolve missing credentials without chat exposure.
  - [ ] For a missing ngrok token, actually run
        `python3 scripts/notion_webhook_onboard.py open-login ngrok`, then run
        `python3 scripts/notion_webhook_onboard.py secure-set NGROK_AUTHTOKEN`
        in the operator terminal.
  - [ ] For a missing Notion token, actually run
        `python3 scripts/notion_webhook_onboard.py open-login notion`, then run
        `python3 scripts/notion_webhook_onboard.py secure-set NOTION_TOKEN` in
        the operator terminal.
  - [ ] If a graphical browser cannot open, render the returned URL as a
        clickable link and wait; do not call the setup blocked. Every auth
        handoff names the executed `open-login <target>` phase, its
        `browser_opened` result, the fallback URL, `secure-set <KEY>`, and the
        phase that resumes after authentication. Never invent the
        `browser_opened` result; use only the script receipt.
- [ ] 4. Run `configure --root-page-url <url> --mention <mention>`. Surface the
      returned webhook URL, open the returned Notion integrations URL, and ask
      the operator to create a `comment.created` subscription at that endpoint.
- [ ] 5. Poll `verification` until it returns `verification_token`. Give that
      one-time value to the operator for Notion's verification field, then run
      `discover` immediately after the operator verifies the subscription; do
      not answer “are we done?” with a plan. Discovery authorizes every data
      source currently shared with the connection and restarts the existing
      Hermes service so the catalog is active before the test comment.
- [ ] 6. Ask for exactly one harmless test comment using the chosen mention,
      such as `@hermes what is this ticket about?` Poll `finalize` until it reports
      both `workspace_locked=true` and `reply_observed=true`.
- [ ] 7. Return `status` as the completion receipt. Completion requires the
      ngrok endpoint, verified subscription, discovered-table count, locked
      workspace, and persisted reply receipt. Explicitly state that tunnel,
      transport, or process health alone is partial proof.
<!-- END FARPLANE_IMPORTANT_CHECKLIST -->

## Gotchas

- On a headless SSH session, a VPS cannot open the operator's local browser.
  Treat the script's clickable URL as the same human gate and continue polling.
- `secure-set` requires an interactive terminal so the credential never enters
  chat, shell history, logs, or process arguments.
- Do not install a reverse proxy as a fallback. A failed ngrok setup remains a
  precise ngrok/auth/systemd blocker.

## Proof

- `python3 -m unittest discover -s skills/notion-webhook-onboarding/tests -v`
- `python3 -m json.tool skills/notion-webhook-onboarding/evals/evals.json`
- `python3 scripts/notion_webhook_onboard.py configure --root-page-url https://notion.so/Test-725195b678ee475099946dfaedf086c0 --mention @hermes --dry-run`

## Output

```yaml
notion_webhook_onboarding:
  state: ready | human_required | blocked
  endpoint:
  verification_token_captured:
  discovered_table_count:
  workspace_locked:
  reply_observed:
  next_action:
```
