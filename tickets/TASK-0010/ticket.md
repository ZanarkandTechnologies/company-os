---
template_id: ticket-template
template_version: "0.2.6"
ticket_id: TASK-0010
title: Answer PKMS ticket questions from Notion comments
status: ready_for_operator_test
created_at: 2026-08-20T11:00:00+08:00
updated_at: 2026-08-20T12:40:00+08:00
claimed_by: codex-root
depends_on: [TASK-0009]
source_refs:
  - https://developers.notion.com/reference/post-search
  - https://developers.notion.com/reference/retrieve-a-page
  - https://developers.notion.com/reference/retrieve-a-comment
  - https://developers.notion.com/reference/list-comments
  - https://developers.notion.com/reference/create-a-comment
  - https://developers.notion.com/reference/webhooks/comment-created
---

# TASK-0010: Answer PKMS ticket questions from Notion comments

## Summary

Extend the existing Hermes-native Notion connector so a signed
`comment.created` event beginning with `@vishanai` loads the ticket page,
recursive block content, and open comments, then sends the agent result back to
the triggering Notion discussion. Every ticket page owns one persistent Hermes
session, so later `@vishanai` comments on that ticket retain its chat history.
Add a bounded data-source catalog using Notion Search for the tables shared
with the connection.

## Scope

- **In:** data-source discovery, triggering-comment retrieval, bounded ticket
  context, one session per ticket, exact triggering-discussion replies, loop
  prevention, root/trigger/reply configuration, tests, and live read-only
  verification against the supplied PKMS root.
- **Out:** retrieving resolved comments (unsupported by Notion), deploying the
  permanent VPS endpoint, and posting a live test reply before the operator
  leaves a deliberate `@vishanai` test comment. Durable replay of webhook jobs
  after a process crash is a future reliability layer, not part of this bridge.
- **Invariant:** webhook signatures and workspace authorization remain
  mandatory; external page/comment content remains untrusted; comment writes
  require a separate explicit gate.

## Delta

> **Before:** the connector reacts to page events, returns only page
> properties, and logs the model result.
>
> **After:** a signed `@vishanai` comment loads bounded ticket context and open
> discussions into that ticket's persistent Hermes session, while the model
> result is posted to the exact triggering discussion.
>
> **Example:** two `@vishanai` comments in different discussions on the same
> ticket share chat history; each answer still appears beneath its own question.

## Done / Proof

- [x] Shared Notion data sources are discoverable with pagination.
- [x] Ticket properties, recursive blocks, and open comments are returned with
      explicit bounds and no secret values.
- [x] Non-trigger comments are ignored and reply events do not loop.
- [x] Triggering comments resolve to their discussion and replies use that
      discussion ID behind a dedicated write gate.
- [x] Session identity is `ticket:<page_id>`; multiple comments on the same
      ticket reuse history while persistent reply anchors prevent cross-replies.
- [x] Busy input mode queues same-ticket comments as ordered follow-up turns
      instead of interrupting the active answer.
- [x] Canonical and Kamdar package copies remain synchronized.
- [x] Focused tests, full suite, live read-only PKMS probe, independent QA, and
      implementation review pass or name an exact blocker.

## State

- **Current:** implementation and read-only PKMS proof passed; independent QA
  and security/API review passed with no blockers.
- **Next:** add the model credential and permanent webhook endpoint, deploy the
  package, then post one deliberate `@vishanai` comment for the live smoke.

## Links

- Evidence and setup receipt: `artifacts/qa.md`
- Independent QA: `artifacts/qa-review.md`
- Security/API review: `artifacts/review.md`
