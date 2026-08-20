# Kamdar AI Hermes Distribution

This directory is a standalone Hermes profile distribution. Publish this
directory as the root of a private Git repository, or install it directly for
development.

## Local install

```bash
hermes profile install ./profiles/kamdar-ai --name kamdar-ai --alias --yes
```

## Notion webhook onboarding MVP

When Hermes is already running on the target Linux VPS, invoke the bundled
`notion-webhook-onboarding` skill in Hermes and provide the Notion root-page
URL. The skill installs ngrok, stores configuration in the profile's existing
Doppler scope, opens or links the ngrok and Notion login pages, discovers every
data source shared with the Notion connection, and finishes only after one live
`@vishanai` comment receives a persisted reply.

This path does not inspect or change Caddy, Nginx, Traefik, DNS, VPS users, or
the Hermes installation. On a headless SSH session the skill returns a
clickable browser URL instead of pretending the remote VPS can open a browser
on the operator's computer. Credentials are entered only through the bundled
CLI's masked `secure-set` phase or an existing Doppler configuration.

The older Caddy bootstrap below remains available for deployments that already
use it; it is not part of the MVP onboarding skill.

## VPS install

Clone the private distribution repository on a Debian 11+ or Ubuntu 22.04+ VPS,
then run the bootstrap as root. It installs Hermes, Doppler, and Caddy; creates
the unprivileged runtime user; installs the profile; persists a scoped Doppler
service token; and starts the gateway behind HTTPS.

```bash
read -rsp "Doppler service token: " DOPPLER_SERVICE_TOKEN; echo
printf '%s\n' "$DOPPLER_SERVICE_TOKEN" | \
  sudo ./deploy/bootstrap-vps.sh \
    --hostname notion.example.com \
    --doppler-token-stdin
unset DOPPLER_SERVICE_TOKEN
```

The hostname must already resolve to the VPS. Use a dedicated hostname so the
generated Caddy site does not collide with another application.

Only `POST /notion/webhook` is publicly routed. Hermes remains bound to
`127.0.0.1:8645`, its health endpoint stays local to the VPS, and every other
public path returns `404`.

## Doppler contract

The onboarding skill needs a write-capable Doppler session while it records
the discovered endpoint, root page, tables, and workspace. After onboarding,
the long-running Hermes and ngrok services should use a read-only service token
scoped to the intended production config. That config contains:

- `OPENROUTER_API_KEY`
- `NOTION_TOKEN`
- `NGROK_AUTHTOKEN` when using the bundled ngrok onboarding skill
- `NOTION_WEBHOOK_PUBLIC_URL=https://<hostname>/notion/webhook`
- `NOTION_ROOT_PAGE_ID=<the PKMS root page UUID>`
- `NOTION_ALLOWED_DATA_SOURCES=<comma-separated IDs discovered during onboarding>`
- `NOTION_COMMENT_TRIGGER=@vishanai`
- `NOTION_ALLOW_ALL_WORKSPACES=false`
- `NOTION_ENABLE_WRITES=false`
- `NOTION_API_VERSION=2026-03-11`

The Notion connection must have Read content, Read comments, and Insert
comments capabilities. Comment replies are intrinsic to this connector and are
always enabled; the separate page-property write tool remains disabled by
default. The PKMS root must be shared with the connection and the
webhook subscription must include `comment.created`. Comments that do not begin
with the configured trigger are acknowledged and ignored. Replies created by
the connection are also ignored, preventing a webhook loop.

The connector catalogs tables through Notion Search filtered to
`data_source`, because linked database views can point to original databases
outside the literal root block tree. Access remains bounded by the pages shared
with the Notion connection and the stored data-source allowlist. Refresh that
allowlist deliberately when adding a new PKMS table. Ticket context includes properties, recursive
blocks, and open page/inline comments. Notion does not expose resolved comments
through its public API.

Keep allow-all disabled. The first signed event records its workspace ID before
Hermes applies the allowlist, but it is not dispatched to the agent. Read the ID
with the redacted status command, set `NOTION_ALLOWED_WORKSPACES` in Doppler,
restart the service, and trigger a second event for the end-to-end test.

## Notion verification

Create the subscription in the target Notion connection using the permanent
public webhook URL. The gateway captures the one-time verification token.

```bash
sudo -u kamdar -H doppler run \
  --scope /home/kamdar/.hermes/profiles/kamdar-ai -- \
  hermes -p kamdar-ai notion-webhook token
```

Paste the returned value into Notion, then run:

```bash
sudo ./deploy/verify-vps.sh --hostname notion.example.com
```

After sending the first test event, inspect the captured workspace ID without
printing any credential:

```bash
sudo -u kamdar -H doppler run \
  --scope /home/kamdar/.hermes/profiles/kamdar-ai -- \
  hermes -p kamdar-ai notion-webhook status
```

Store that ID as `NOTION_ALLOWED_WORKSPACES` in Doppler, restart
`kamdar-hermes.service`, and send a second event. The second event is the first
one expected to reach the agent.

The verification script reports readiness only; it never prints credentials or
the captured token.

## Transfer to another Notion workspace

1. Replace `NOTION_TOKEN` in Doppler.
2. Share the target pages with the new Notion connection.
3. Reset the stored verification state with `hermes -p kamdar-ai notion-webhook reset-token` under the Doppler-scoped runtime user.
4. Delete and recreate the Notion webhook subscription at the same public URL.
5. Paste the newly captured verification token and repeat the smoke test.

No profile or plugin code changes are required.
