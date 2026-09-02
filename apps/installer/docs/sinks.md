---
title: Supported Company OS sinks
status: active
owner: Company OS
updated_at: 2026-08-31
refs:
  - ../../workspace.hermes.template.md
  - ../schemas/workspace.py
  - ../../automations/README.md
  - ../../company_os/delivery.py
---

# Supported Company OS sinks

A sink is a destination where an already-produced Company OS effect may be stored, copied, commented, or sent. Sources answer where evidence is read; sinks answer where an authorized output may go. A provider connection may serve both, but a source binding never implies a sink.

## Sink model

```text
Analyze
  -> canonical private local artifacts
       -> optional provider copies
       -> exact Work-item comments
       -> optional reviewed messages
```

| Sink class | Canonical? | Configuration owner |
| --- | --- | --- |
| Private local workspace | Yes | Installed runtime structure; always present |
| Artifact sync | No, one-way secondary copy | Managed Artifact sync table |
| Work-item comments | No, exact action on source Work | Automation result, source binding, and write authority |
| Owner/employee messages | No, notification or draft | Managed Communications table and route receipt |

## Canonical local sinks

The private Hermes workspace is always the primary destination for generated operational state:

| Artifact | Location | Producer |
| --- | --- | --- |
| Short-term Project Memory | `weeks/<YYYY-Www>/project-memory/` | Daily |
| Project/Department/Company reports | `weeks/<YYYY-Www>/reports/` | Weekly |
| Employee Memory | `memory/employees/` | Weekly promotion |
| SOP Memory | `memory/sops/` | Weekly promotion |
| Decision Memory | `memory/decisions/` | Weekly promotion |
| Issue Memory | `memory/issues/` | Weekly promotion |
| Message drafts | `weeks/<YYYY-Www>/outbound/` | Authorized messaging guard |

Local writes validate and read back before completion. Reports are projections, Project Memory are short-term memory, and entity files are long-term memory. Provider copies never replace these owners.

## Optional artifact sync

Artifact sync copies completed local Markdown to one exact secondary provider destination. The runtime contract supports:

| Artifact | Providers | Destination rule |
| --- | --- | --- |
| `short-term memory` | Notion, Google Drive | One exact HTTPS private destination |
| `long-term memory` | Notion, Google Drive | One exact HTTPS private destination; never the public People source |
| `reports` | Notion, Google Drive | One exact HTTPS reporting destination |

Rules:

- each artifact type may have at most one destination;
- provider and destination must both be present;
- copying begins only after the local artifact reads back;
- the completed local artifact is copied without regenerating it;
- provider edits never flow back into local memory;
- no row means local-only, not failure;
- a configured but unavailable destination is blocked, never rerouted.

Current boundary: the workspace schema and runtime delivery path support these rows, but the interactive wizard does not currently create them. They must be added to the reviewed workspace configuration. A provider used only as an artifact sink also does not yet cause setup to provision its MCP connection automatically; that connection must already exist through another binding or managed setup step.

## Work-item comments

Progress and documentation questions return to the exact linked Work record by default. They are not artifact sync and require no general messaging destination.

A comment requires the exact provider record ID from the analyzed snapshot, a provider connection with comment capability, automation authority for that action, an idempotency key, and provider acceptance/read-back. Missing target or authority leaves the action blocked; the agent must not infer another page, channel, or person.

## Communications

The workspace contract supports:

| Message | Apps | Behavior | Recipient boundary |
| --- | --- | --- | --- |
| `owner report` | Telegram, Slack, WhatsApp | Draft for approval or automatic after a confirmed test | Named owner |
| `owner alert` | Telegram, Slack, WhatsApp | Draft for approval or automatic after a confirmed test | Same reviewed route as owner report |
| `employee follow-up` | Telegram, Slack, WhatsApp | Draft only | Employee-approved People-directory route |

The current wizard exposes owner report and owner alert. It does not expose employee follow-up. Owner report and alert must share one app, named recipient, and behavior.

Automatic sending remains locked until a setup test resolves an exact provider target and the named recipient confirms receipt. Changing the app, recipient, target, or behavior invalidates that proof. Draft mode sends nothing: it writes one private Markdown draft per stable action key. A changed body under the same key is a conflict instead of an overwrite, and explicit approval applies that exact reviewed file through the same typed guard.

## Analyze and Sync-to-provider

Native Daily and Weekly jobs receive the complete automation contract. They
review the skill-produced files and then apply only effects authorized by the
workspace, using configured skills or MCPs directly. Doctor disables provider
mutations, messaging, and artifact sync. There is no intermediate delivery plan,
handoff, or custom provider executor.

## Unsupported behavior

- No destination inferred from a connected account or source URL.
- No multiple destinations for one artifact type.
- No bidirectional or provider-to-local memory synchronization.
- No automatic employee follow-up sending.
- No fallback to another person, app, page, or folder after failure.
- No claim that a catalogued destination test proves configured production delivery.
- No end-to-end wizard provisioning for sink-only provider connections yet.

## Receipt meanings

| State | Meaning |
| --- | --- |
| `not_requested` | No applicable sink was configured. |
| `blocked` | Destination, target, authority, quality, or connection is unavailable. |
| applied/sent | Matching local/provider acceptance or read-back exists in the integration receipt. |

A preview or local Markdown file is not proof of external publication. Only matching provider acceptance may support that claim.
