---
ticket_id: TASK-0010
artifact: progress
updated_at: 2026-08-20T12:40:00+08:00
---

# Progress

- 2026-08-20: Live read-only checks confirmed the supplied PKMS root, comments
  endpoint, and data-source Search endpoint return HTTP 200. Search exposes 18
  shared data sources; direct root-block traversal exposes only seven database
  blocks because linked views point at original databases elsewhere.
- 2026-08-20: Selected the `reuse_local` lean rung. Extend the current urllib
  adapter and Hermes platform registration; add no SDK, daemon, or service.
- 2026-08-20: Added paginated data-source discovery, recursive bounded ticket
  context, open page/inline comment retrieval, `@vishanai` filtering, bot-loop
  prevention, and same-discussion replies behind a dedicated write gate.
- 2026-08-20: Upgraded the Notion API binding from `2025-09-03` to
  `2026-03-11` after official docs showed Retrieve Comment is available only
  on the current version. Updated the Kamdar Doppler development binding.
- 2026-08-20: Live read-only proof found 18 shared data sources, located Tasks,
  queried a real Tasks row, and retrieved five content blocks plus open inline
  comments. That sampled ticket had no open comments, so exact comment-ID
  retrieval and reply routing remain synthetic until an operator posts the
  deliberate activation comment.
- 2026-08-20: Full suite passed 30/30, adapter tests passed 4/4, protocol tests
  passed 9/9, shell syntax/dry-run passed, and secret scan passed. Remaining
  activation inputs are a model-provider credential and permanent live webhook
  endpoint; the configured temporary tunnel no longer resolves.
- 2026-08-20: Persisted the 18-source catalog as
  `NOTION_ALLOWED_DATA_SOURCES` in Kamdar's Doppler development config and
  enforced each ticket page's parent data source against it. Live Tasks context
  passed the new scope check; protocol/API tests now pass 10/10.
- 2026-08-20: Independent QA and security/API review passed with no blocking
  findings. Ticket advanced to `ready_for_operator_test`; production activation
  remains gated on the model credential and permanent HTTPS webhook.
- 2026-08-20: Corrected the conversation boundary after operator feedback.
  Hermes now keys history by `ticket:<page_id>` instead of discussion ID and
  persists each triggering `comment_id -> discussion_id` delivery route. Two
  discussions on one ticket share history without crossing reply destinations.
- 2026-08-20: Bound the profile to Hermes-native `busy_input_mode: queue` and
  added an active-session lifecycle regression so concurrent same-ticket
  comments become ordered turns rather than interrupting the current answer.
  Crash-safe webhook job replay remains explicitly outside this ticket.
