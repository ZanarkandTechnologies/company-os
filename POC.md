---
title: "Howie File-First Manager POC"
status: test_ready
owner: HermesCorp
created_at: 2026-08-10
updated_at: 2026-08-12
source_refs:
  - https://github.com/NousResearch/hermes-agent/security
  - https://developers.google.com/workspace/drive/api/guides/about-files
---

# Howie File-First Manager POC

## Objective

Prove the company-manager work loop first with deterministic local filesystem
evidence, then make one tightly controlled live-development test possible:

```text
weekly meeting note -> canonical ticket folders -> scheduled pulse
  -> bounded staff chase -> reply + scoped shared artifact
  -> artifact draft -> review -> archive -> weekly report + Gantt
```

The default proof uses fake names, a mock Drive scope, and mock artifact
templates. It does not authenticate to Google, search a real Drive, pair
WhatsApp, start a gateway, register cron, or send a real message. TASK-0003
adds the source profile and manual gates for one developer-owned self-chat,
one opted-in test recipient, and one dedicated fake-data Drive identity.

## What the local proof shows

| Requested behavior | POC proof |
| --- | --- |
| Weekly meeting creates work/timeline | Meeting scan creates `TASK-1001` through `TASK-1004`, each with dates, owner, Kenji review, dependencies, and a skill template |
| Blocked work gets chased | Pulse finds due blocked work, records one task-local chase, and observes employee global + task-local cooldown |
| Reply changes the board | Authorized Kenji reply accepts only a matching file in the `howie-ai/shared` mock Drive scope and creates a draft |
| Artifact reaches shared storage | Publication records a mock native Workspace file reference and moves to `awaiting_review` |
| Review closes work | Kenji approval archives the complete ticket folder and the weekly report/Gantt update |
| Admin controls access | Dashboard has a clearly marked mock route-policy control; it is not a real Drive ACL editor |

## Test workspace

Use `workspaces/howie-ai-poc/`, seeded by the manager, for all current
dashboard and source-profile tests. It contains only synthetic employee policy,
mock Drive files, and derived ticket state. Leave `workspaces/howie-ai/`
untouched: it is a prior runtime shape and deliberately fails the current
manager validator rather than being silently migrated.

## Production adapter rule

The real Howie agent needs its **own** company-managed Google identity or
service credential, granted only the required Shared Drive/project folder. It
must not reuse Howie's personal Drive credential. The ticket records the
Drive file ID/URL and review state; it does not mirror every task update to
Drive. Blob artifacts can use a local work copy and an ID-targeted Drive update;
native Docs/Sheets/Slides use their native Workspace/API path.

## Deliberately gated activation

1. Create a private Howie profile and use the source sync only after reviewing
   its rendered configuration.
2. Configure a model plus a pre-registered Google OAuth client outside this
   repository; authenticate a dedicated identity with no non-fake shares.
3. Confirm one fake Drive source can be searched/read and one new fake
   artifact can be created. Do not claim existing-file update support.
4. Pair the private WhatsApp self-chat and test one inbound meeting/reply in
   `workspaces/howie-ai-poc/`.
5. Test one employee-directory-approved chase only with both explicit local
   send gates. No cron is in scope.

Profiles/toolsets are not authorization boundaries; production staff access
still needs distinct persistent workspaces, scoped credentials, and gateway
policy as described in [ARCHITECTURE.md](ARCHITECTURE.md).
