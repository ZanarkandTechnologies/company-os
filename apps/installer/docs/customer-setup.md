---
title: Install the Company OS on Hermes for Windows
status: in_progress
owner: Company OS
created_at: 2026-08-29
updated_at: 2026-09-01
---

# Install the Company OS on Hermes for Windows

This is the customer runbook for the supported Windows deployment. Hermes and
the Company OS profile run on Windows. Hermes uses Docker as its terminal
backend, while only the optional ngrok ingress runs as a long-lived container.
The customer does not need a separate Python installation because setup uses
Hermes' bundled Python and Pydantic.

The screens below use the generic product labels. The current HermesCorp proving
build may still show legacy Company OS labels until the setup implementation is
renamed; the actions and expected states are the same.

## What the customer provides

- A Windows computer that remains on while host Hermes automations and comments
  should work.
- Hermes installed on Windows and available as `hermes`.
- Docker Desktop running and available as `docker`.
- This repository, obtained with Git or Download ZIP.
- A Hermes model login or API key.
- Notion authorization for the official hosted MCP.
- When Gmail or Google Drive is selected: one Composio project API key and the
  Google account login. Setup stores the API key in Hermes and opens hosted
  OAuth links; no Composio CLI is installed.
- For real-time comments only: a Notion internal connection token, an ngrok
  account authtoken, and the account's assigned HTTPS development domain.

ngrok's Free plan provides one assigned development domain without a forced
endpoint timeout, subject to its usage limits and without a production SLA.
See [ngrok's Free plan limits](https://ngrok.com/docs/pricing-limits/free-plan-limits/)
and [Docker Compose setup](https://ngrok.com/docs/using-ngrok-with/docker/compose/).

## Customer journey

```text
YOU                         SETUP                       RESULT
 |                            |                           |
 |-- open setup.cmd --------->|                           |
 |                            |-- asks for company info   |
 |<-- approve each service ---|                           |
 |                            |-- checks each connection  |
 |<-- fix or skip a problem --|                           |
 |                            |-- installs and verifies ->|
 |                                                        |
 |<---------------- dashboard, schedules, health ---------|
```

Real-time Notion comments add one optional ngrok step before setup. Daily
and Weekly scheduled reviews do not require it.

## Setup ownership and stage contract

The two entry points have deliberately different owners. `setup.cmd` is the
thin Windows host launcher; `setup.py launch` is the interactive product flow.
The Python flow requests a bounded launcher action by exit code rather than
starting persistent host processes itself.

| Owner | Responsibilities | Must not own |
| --- | --- | --- |
| `setup.cmd` on Windows | Check host Hermes, Hermes' bundled Python, Docker Desktop, and Compose; invoke the interactive CLI; start the selected host Hermes gateway; start or roll back the optional ngrok container; run the requested static/live verification or provider certification; open the local dashboard. | Company questions, provider selection, browser OAuth decisions, secret prompts, workspace rendering, certification policy, or eval judgment. |
| `setup.py launch` on Windows | Ask for company identity and operating context; select data sources and communication tools; configure Hermes model, MCPs, Composio, messaging, and optional webhook credentials; install the reviewed allowlist into the selected Hermes profile; write redacted receipts; choose which launcher action comes next. | Managing Docker Desktop, keeping host processes alive, or pretending that a container can edit the Windows Hermes profile. |

The intended first-install sequence and the current proving-build status are:

| Stage | Required behavior | Current status |
| --- | --- | --- |
| 1. Workspace | Ask for company name, description, timezone, data sources, tools, and communication choices; render and review the Hermes workspace before installation. | **Implemented.** |
| 2. Connections | Notion uses Hermes' hosted MCP login and test. Gmail and Drive share one restricted Composio MCP session; setup asks for the hidden project API key, opens OAuth for each selected Google toolkit, confirms both are connected, and runs `hermes mcp test`. Telegram uses Hermes' native gateway setup and an explicit test message/recipient confirmation when automatic sending is selected. | **Implemented.** Provider certification may perform isolated reversible writes after explicit approval; a failure can be retried or deferred. |
| 3. Optional Notion webhook | Ask for the agent trigger keyword, Notion integration token, ngrok authtoken, and assigned HTTPS domain; return the normalized `/notion/webhook` URL; start ingress; wait while the customer creates the subscription; display the one-time token received from Notion; then verify one real comment/reply. | **Implemented with a manual acceptance gate.** The launcher accepts a running gateway only when `hermes gateway status` succeeds under the selected profile; another profile on the same host cannot satisfy the check. Setup displays the saved trigger, the customer posts it on an isolated ticket, and setup waits for a new threaded reply. |
| 4. Data-readiness preflight | Fetch every selected source read-only, distinguish empty/unshared/inaccessible data, validate the minimum fields needed by Daily and Weekly, and report actionable failures before analysis. | **Implemented.** The preflight temporarily puts selected MCPs in Hermes' `untrusted` tier so tools without provider-declared `readOnlyHint=true` cannot execute, requires every observed tool to match the provider's positive read allowlist, batch-judges redacted evidence, and writes a private configuration-bound receipt. Missing Projects or Tasks, empty selected inputs, and missing required fields or relations return `needs_setup`. |
| 5. Full eval and dossier | Run the installed Daily and Weekly paths against an isolated eval scope, judge every owned case, write one eval receipt, build the private dossier, and open it. | **Implemented.** One isolated file-only Hermes session handles all mutually exclusive cases for each cadence, followed by one model-only batch judge. If the model returns prose instead of the strict receipt schema, one model-only formatting repair is allowed; every eval ID, assertion, evidence row, and output path must still validate before the receipt can pass. The dossier opens from the private run directory. |

A successful first-install wizard now proves installation, configured-provider
connectivity, selected-profile health, the optional live webhook path, real
source readiness, and the complete isolated PM eval before opening its dossier.
Daily and Weekly schedules are installed paused and are resumed only after live
health, readiness, and checksum-validated eval/dossier receipts all pass.
The eval proves the packaged PM behaviors against private fixtures; the
preflight separately proves that the configured customer sources are usable.

Current rerun surfaces are:

| Need | Supported rerun |
| --- | --- |
| Retest Gmail, Drive, Notion, and other configured provider cases | Rerun `setup.cmd`, then choose **Test integrations**. |
| Recheck installation, gateway, ingress, and the live comment path | Rerun `setup.cmd`, then choose **Run full health check**. |
| Recheck minimum source fields and content | Run `setup.py doctor preflight`, or choose **Check data readiness** in `setup.cmd`. |
| Regenerate and open a fully judged dossier | Run `setup.py doctor eval --open`, or choose **Run full eval and open dossier**. |
| Reopen the latest checksum-validated dossier | Run `setup.py doctor open`, or choose **Open latest eval dossier**. |
| Resume managed schedules after repairing a failed proof stage | Run `setup.py doctor activate`; it remains fail-closed unless live health, readiness, and eval/dossier receipts all pass. |
| Preview Daily and/or Weekly against installed company data without delivery | Run `setup.py doctor analysis --cadence daily` and/or `--cadence weekly`. |

## 1. Prepare ngrok for real-time comments

Skip this when scheduled operation is enough. The Notion plugin owns the
ngrok endpoint, token, webhook subscription, and safety instructions; follow
its [real-time comment setup](../../../plugins/platforms/notion/README.md#configure-real-time-comments)
before launching this installer.

## 2. Launch setup

Download and unzip the repository, or clone it with Git. Then double-click
`setup.cmd` from the repository folder. Git is optional.

The launcher checks host Hermes, Hermes' bundled Python, Docker, and Compose.
It runs the packaged `setup.py` entry point on Windows against the host
`company-os` profile. It never creates a second Hermes profile in Docker.
Setup configures `terminal.backend=docker`, points `terminal.cwd` at the
selected profile workspace, and enables Hermes' native
`terminal.docker_mount_cwd_to_workspace` setting. Therefore Docker tools see
that one workspace at `/workspace`, and generated artifacts survive container
teardown for host-side validation and dossier viewing.

The command window should show this sequence:

```text
Company OS Setup
Checking host Hermes and Docker Desktop...
Opening the guided setup in your Windows Hermes profile...
```

If setup stops before the image pull, the same window stays open and names the
failed prerequisite:

| Message | What to do |
| --- | --- |
| `Docker Desktop is required and was not found.` | Install Docker Desktop with its WSL2 backend, then rerun `setup.cmd`. |
| `Docker Desktop is installed but is not ready.` | Start Docker Desktop and wait until it reports **Ready**. |
| `Hermes must be installed on Windows before Company OS setup.` | Install or repair Hermes, then rerun setup. |
| `Hermes was found, but its bundled Python runtime is missing` | Repair or update Hermes, then rerun setup. |
| `Docker Compose is unavailable. Update Docker Desktop, then try again.` | Update Docker Desktop, then rerun setup. |

On a new profile, the interactive wizard asks for company details, data sources,
and communication choices. Projects, Tasks, People, SOPs, Reports, and Operator
Email are independent source roles: every selected role receives its own
provider and source URL or identifier. Choosing Notion for several roles does
not merge them into one database. The wizard also asks about optional owner
messages. Messaging asks ordinary questions only: completed
reports and/or owner alerts, the owner's name, Telegram/Slack/WhatsApp, and
**Prepare drafts in the private workspace** or **Send automatically**. Leaving
these choices empty is the lean default. Task-specific documentation and
progress questions use comments on the exact linked Work item; they need no
separate messaging setup.
Before setup changes runtime services or credentials, it shows a **Review setup
plan** table. An incomplete profile offers Resume. An
existing profile instead shows the maintenance menu documented below.

If owner messages are selected, setup opens Hermes' own messaging setup; tokens
remain in the private Hermes profile. A connection test is always a separate
opt-in send. Automatic delivery remains blocked until Hermes returns an exact
destination and the named owner confirms receiving that test. The private
receipt is tied to the current message choices, recipient, app, and exact
target, so changing any of them requires a new test.

Draft-first does not send. The automation writes the draft under the private
`weeks/<week>/outbound/` directory for review. An approved send uses the native
messaging skill or MCP and the exact confirmed route; there is no custom
messaging dispatcher or approval CLI.

> **What you should see:** Your chosen company values and data sources appear
> in the review table. If Notion is selected, setup offers browser
> authorization. If Gmail or Drive is selected, setup asks once for the hidden
> Composio project API key and shows a hosted OAuth link for each selected
> Google toolkit. If real-time comments are enabled, it asks for the two hidden
> tokens and the stable HTTPS hostname. Secret values do not appear afterward.

Candidate Composio and Notion keys are checked with their provider before they
replace any saved value. The ngrok authtoken is checked by starting the pinned
agent because ngrok agent tokens cannot authenticate its REST API; setup stops
before claiming readiness if the agent rejects the token or endpoint.

The setup creates one restricted Composio session containing only the selected
Gmail/Drive tools, disables Composio's remote workbench, and registers that
session in Hermes as `composio-google`. Gmail and Drive share the session but
retain separate Google OAuth connections. The Composio project key and hosted
MCP URL remain inside the private Hermes profile. Hermes authenticates every
hosted MCP request with the profile's `COMPOSIO_API_KEY`; the secret value is
never copied into the MCP configuration. A rejected saved key can be replaced
during interactive setup, and the old value remains saved until its replacement
has been accepted by Composio.
This follows Composio's current
[session MCP](https://docs.composio.dev/docs/sessions-via-mcp),
[session configuration](https://docs.composio.dev/docs/configuring-sessions),
and [hosted authentication](https://docs.composio.dev/docs/authentication)
contracts.

After authorization, setup certifies every configured provider. If a row
fails, its reason is shown and setup offers only:

```text
retry  - rerun the same certification immediately
defer  - keep the installation and test later
```

Deferring does not undo setup. Health reports `PARTIAL`, and the customer
reruns `setup.cmd` and chooses **Test integrations**. The underlying
container command is `setup.py certify`; customers do not need to type it.

When prompted for real-time comments, provide:

```text
Agent trigger keyword:              @youragent
Notion internal connection token: <hidden input>
ngrok agent authtoken:             <hidden input>
Assigned ngrok HTTPS domain:       https://example-name.ngrok-free.app
```

The setup rejects `trycloudflare.com`, localhost, non-HTTPS URLs, query
strings, fragments, and unrelated paths. It normalizes the accepted endpoint
to:

```text
https://example-name.ngrok-free.app/notion/webhook
```

No credential is written to the repository or printed in the receipt.

## 3. Verify the Notion webhook

After the gateway and ngrok agent start, complete the plugin's
[verification steps](../../../plugins/platforms/notion/README.md#configure-real-time-comments).

Expected checkpoints:

| After this action | What you should see |
| --- | --- |
| Create the subscription | Setup reports that it received Notion's verification request. |
| Paste the one-time token | Notion reports that the subscription is verified. |
| On an isolated ticket, post the exact trigger shown by setup, such as `@youragent setup healthcheck` | One new Hermes reply appears in the same Notion discussion. |

### Future automation: webhook acceptance test

The first production-safe version intentionally keeps the Notion write as a
visible customer action. A future setup release should ask for and remember an
isolated test-ticket URL, create the trigger comment through the Notion API,
record the created comment ID, and pass only after Hermes replies to that exact
comment. The write must remain limited to an explicitly selected ticket inside
the configured data-source allowlist, and the receipt must not expose page,
comment, or credential values. This is a setup convenience improvement, not a
prerequisite for today's manual webhook proof.

Troubleshooting and the external protocol references live with the plugin so
this customer journey does not duplicate its implementation contract.

## 4. Read the result

Setup returns `ready`, `partial`, or `blocked` and writes a redacted receipt in
the persistent Hermes profile. `ready` requires core profile, workspace,
model, schedules, official Notion MCP, gateway, and installed PM skill packages.
Messaging adds separate `messaging_configured` and `messaging_delivery` lanes;
a running gateway alone is not accepted as proof that the owner route works.
When comments are selected, the optional webhook lanes additionally check:

- local webhook health and captured verification state;
- stable public HTTPS reachability;
- one new reply in the exact Notion discussion.

A skipped comment integration remains visibly skipped. A deferred integration
certification or failed optional comment lane produces `partial`; neither
becomes a false pass.

The final panel should show one of these states:

| State | Meaning | Next action |
| --- | --- | --- |
| `READY` | Required setup and checks passed. | Open <http://127.0.0.1:9119>. |
| `PARTIAL` | Core setup works, but provider certification was deferred or an optional integration check needs attention. | Follow the named lane in the receipt, then rerun setup and choose **Test integrations** or **Run health check**. |
| `BLOCKED` | A required check failed. | Fix the named lane before relying on automations. |

> **What you should see:** An **Installation verification** table followed by
> the final state and a profile-relative support receipt. A successful launcher also prints
> `Company OS is ready` with the dashboard address.

The dashboard is still local-only in Docker. Current Hermes releases no longer
permit `--insecure` to bypass authentication on a container-wide bind, so the
Company OS starts Hermes on container loopback and uses its packaged bridge to
publish only `127.0.0.1:9119` on the host. If logs mention a refused
`0.0.0.0` dashboard bind, update the repository and rerun **Update Company OS
software**; do not add an unauthenticated public bind.

## Preflight and evaluate

`setup.py doctor preflight` fetches configured business inputs read-only and
reports `passed`, `needs_setup`, or `failed`. A selected input must contain
enough real structure and content to support PM Daily and Weekly; optional
destinations may be empty. Meetings are inspected inside the bounded Tasks
fetch and are never queried through a duplicate alias.

`setup.py doctor eval --open` stages private frozen cases, runs one PM Daily and
one PM Weekly evaluation session, batch-judges every case, writes the receipt,
and opens the dossier. It exposes no MCP, messaging, terminal, browser, or
provider tool to generation, and records `provider_mutations: 0`.

`setup.py doctor analysis` remains the installed-company preview. It disables
provider writes, messaging, and artifact sync. Scheduled jobs use the same
automation contracts but may apply only the exact effects authorized in the
workspace.

## 5. Restart and update

If setup stops before installation completes, rerunning it offers **Resume**,
**Start over**, or **Exit**. **Start over** moves the incomplete profile to a
timestamped sibling backup, creates a clean profile, and asks the workspace
questions again. It does not delete the saved credentials or draft in the
backup.

The host Hermes profile under `%USERPROFILE%\.hermes\profiles\company-os`
preserves credentials, OAuth state, schedules, receipts, and generated
workspace state. The assigned ngrok hostname remains stable when its container
or the computer restarts.

Rerunning `setup.cmd` on an existing installation shows:

```text
1. Update Company OS features
2. Update Company OS software
3. Test integrations
4. Check data readiness
5. Run full eval and open dossier
6. Run full health check
7. Repair setup
8. Open latest eval dossier
9. Open dashboard
10. Exit
```

Choose **Update Company OS features** to revisit the explained Memory, Daily,
and Weekly questions. Setup preserves the saved answers, previews the rendered
automation diff, reconciles any newly required provider connections, and runs a
static check. After downloading repository updates, choose **Update Company OS
software**; setup updates the distribution allowlist, preserves unknown runtime
files, reconciles schedules, and runs static verification. Use **Test
integrations** to retry the same provider certification without reinstalling
anything. Use **Run full
health check** when browser OAuth, webhook ingress, and the live Notion comment
path must be tested again. Use **Check data readiness** after changing source
schemas or sharing. Use **Run full eval and open dossier** to rebuild all PM
behavior proof, and **Open latest eval dossier** to reopen only a checksum-valid
existing run. Use **Repair setup** to replace a revoked ngrok
authtoken or assigned domain; the launcher recreates the ngrok container before
running live verification.

Moving to another computer requires installing Hermes there and moving the host
profile through Hermes' explicit backup/restore procedure. Compose moves only
the optional ngrok ingress configuration owned by that profile.

> **What you should see on rerun:** The maintenance menu appears before any
> update. Existing company values appear as defaults only when workspace update
> is selected. You should not receive duplicate schedules, repeated OAuth, or a
> new ngrok hostname.

## Acceptance test

The first customer-equivalent test is complete only when all of these are
observed on Windows:

- fresh `setup.cmd` run with host Hermes and Docker Desktop, but without a
  separate Python, Notion, or ngrok CLI;
- generated owner-only `ngrok.yml` accepted by `ngrok config check` inside the
  digest-pinned container;
- dashboard reachable only at `http://127.0.0.1:9119`;
- official Notion MCP connects;
- restricted Composio MCP connects to Gmail and Google Drive without a host CLI;
- one self-addressed Gmail test is sent and read back, and one isolated Drive
  test file is created, read back, and trashed;
- valid webhook verification is accepted and an invalid signature is rejected;
- one `@hermes` comment receives exactly one threaded reply;
- duplicate delivery produces no duplicate reply;
- host Hermes restart preserves the profile, credentials, schedules, and
  webhook state; ngrok restart preserves the assigned hostname;
- an unchanged `setup.cmd` rerun reaches the maintenance menu without mutating
  profile state or creating duplicates.

Until this operated Windows test passes, the implementation is locally
validated but not a completed clean-machine support claim.
