---
automation_id: company-os-daily-operating-update
automation_version: "2.5.0"
kind: company-os-automation
cadence: daily
company_timezone: Asia/Kuala_Lumpur
skill: skills/pm-daily/SKILL.md
---

# Daily operating update

```text
[Daily parent] --fetch Projects--> [one Project snapshot each]
[Project] --discover explicit Work source(s)--> [schema + bounded Work]
[bounded Work] --normalize without overwriting raw fields--> [Project snapshot]
[Project packet] --isolated PM Daily subagent--> [Project Memory + action drafts]
[all results] --parent review and dedupe--> [authorized effects + receipt]
[unresolved relation] ---------------------> [named gap; no edit]
```

## Purpose

Build one snapshot per Project. Run PM Daily for each snapshot. Apply only its
authorized effects.

## Authority

Use only the source and delivery values declared at the node that consumes them.
Step 4 authorizes only the exact Notion comments and preference-routed direct
messages returned by PM Daily. Never infer another source, recipient, or
destination.

## Todo List

- [ ] **1 — Build the Daily Project snapshots.**

  Use `notion-fetch` and the hosted Notion MCP query tools for every Notion
  read. Use Multica tools for every Multica read. Do not call provider CLIs
  from the Docker terminal.

  1. Fetch Projects from this source:

     <!-- setup:daily.projects -->
     Fetch all active Projects from `<REPLACE_WITH_NOTION_PROJECTS_URL>`.
     <!-- /setup:daily.projects -->

     Read each complete Project page.
     Keep its provider ID, business ID, status, Department, URL, revision, and
     linked task sources.

  2. Inspect each Project's linked task sources.
     <!-- setup:daily.work -->
     Discover Work only from task databases explicitly linked inside that
     Project page.
     <!-- /setup:daily.work -->
     Read each source's schema and status options.
     Map its title, status, owner, due date, update, priority, and progress fields.
     Do not search for task sources outside the Project page.

     For Multica Work, map issues to a Project only through an exact configured
     project ID or an explicit Project reference in issue metadata. Record
     `work_project_relation_missing` when neither exists.

  3. Fetch the relevant Work from each source.
     Include active, blocked, overdue, Work changed during the last week, and
     completed Work awaiting documentation review.
     Keep every raw field, source provider, provider record ID, source reference,
     available source URL, source revision, and complete description or page body.

  4. Normalize each status.
     Keep the original value as `raw_status`.
     Set `normalized_status` to `not_started`, `in_progress`, `blocked`,
     `completed`, `cancelled`, or `unknown`.
     Use `unknown` when the meaning is unclear and record
     `status_mapping_ambiguous`.

  5. Fetch referenced People.
     <!-- setup:daily.people -->
     Fetch People from `<REPLACE_WITH_NOTION_PEOPLE_URL>`. Read preferred
     channel from `<REPLACE_WITH_FIELD_NAME_OR_NONE>` and its endpoint from
     `<REPLACE_WITH_FIELD_NAME_OR_NONE>`.
     <!-- /setup:daily.people -->
     Fetch only People linked to the selected Work.
     For Multica Work, require an explicit stable Person reference in the issue
     metadata or configured assignee mapping. Do not match People by guesswork.
     Keep their ID, name, preferred channel, and matching contact endpoint when
     available. Preserve the original field names and values.

  6. Record completeness facts for each selected Work item.
     Record whether its page body, progress, owner, due date, next action, and
     completion evidence are present. Preserve the source values without
     judging their quality. Do not edit the source record.

  7. Add relevant Meetings.
     <!-- setup:daily.meetings -->
     Read Meeting notes embedded in or explicitly linked from selected Work.
     <!-- /setup:daily.meetings -->

  8. Return one snapshot for every active Project.
     Write all Project snapshots to
     `daily/context/daily-snapshot-YYYY-MM-DD.json`.

  If a Project has no task source, return an empty snapshot with
  `project_work_source_missing`.

  If a task source lacks required fields, record `task_schema_gap` and list the
  missing fields.

  If Work lacks an exact Project relation, record
  `work_project_relation_missing`. Exclude it from packets and effects.

  If Work lacks a referenced Person relation, record
     `work_person_relation_missing`. Do not infer a Person. An exact Notion Work
     URL may still receive its comment; block only optional direct delivery.

  Use `templates/task.md` as the remediation template for both gaps.
  Do not create a follow-up or Notion comment for a setup gap.
  Do not scan unrelated history or widen a query for missing data.

- [ ] **2 — Run PM Daily.**

  1. Read `skills/pm-daily/SKILL.md` completely.

  2. Build one packet from each Project snapshot.
     <!-- setup:daily.existing_memory -->
     Read that Project's current-week Project Memory from the local weekly
     filesystem and update that same file.
     <!-- /setup:daily.existing_memory -->
     Add the PM Daily templates.
     Never add context from another Project.

  3. Run PM Daily once per packet in a native subagent.
     Require each subagent to read the skill before editing.
     Give each subagent only that Project's Memory file and Work drafts.
     Require each subagent to return changed paths and named gaps.

  4. Run independent packets concurrently when safe.
     A packet failure blocks only its Project unless it exposes a cross-Project
     safety or completeness failure.

  PM Daily writes Project Memory and message drafts directly. Do not add an
  extraction object, generated template catalog, or Pydantic representation.

- [ ] **3 — Review local changes.**

  1. Collect every subagent result.
     Reject overlapping write paths.

  2. Deduplicate actions by Work item and question condition.

     <!-- setup:daily.staleness -->
     Treat Work as stale when it is overdue, blocked, or has no meaningful
     update for seven days.
     <!-- /setup:daily.staleness -->

     <!-- setup:daily.documentation_quality -->
     Treat completed Work as poorly documented when its outcome, evidence,
     rationale, or next action is missing.
     <!-- /setup:daily.documentation_quality -->

  3. Read every changed file.
     Require source citations, preserved memory, complete template headings,
     precise questions, and no changes outside the owning Project packet.

  4. Repair unclear prose with `unslop` without changing facts.

  If any artifact fails review, stop before calling a provider.

- [ ] **4 — Apply authorized effects.**

  1. Keep every `project_memory` file local.

  2. Apply each `documentation_request` and `progress_followup` with a Notion
     `source_provider` and nonempty `source_url` to that exact Work item with the
     Notion MCP. A Multica source reference is not a Notion comment target.
     Use the Markdown body after the routing frontmatter as the message.
     Read the page comments with `notion-get-comments`.
     If the exact message exists, record `duplicate` and stop that effect.
     Otherwise create it with `notion-create-comment`.
     Read the comments again and require an exact match.

     <!-- setup:daily.documentation_route -->
     Deliver documentation requests only as comments on the exact Notion Work
     item.
     <!-- /setup:daily.documentation_route -->

     <!-- setup:daily.progress_route -->
     Post every progress follow-up on the exact Notion Work item, then also use
     the linked Person's preferred Gmail or Telegram endpoint when present.
     <!-- /setup:daily.progress_route -->

  3. Follow the configured route for each artifact. When it authorizes direct
     delivery, read the linked Person's preferred channel and endpoint from the
     Project snapshot. Send the same question plus the exact Work source
     reference through Gmail, Telegram, or WhatsApp. Direct delivery does not
     require a Notion comment first.
     For Telegram or WhatsApp, use the configured Company OS messaging MCP.
     Resolve the exact target with `channels_list`. Use `conversations_list`
     for that platform and `conversation_get` to find the unique session whose
     `chat_id` matches the target. If a session exists, use `messages_read` and
     record `duplicate` when the exact message already exists. Otherwise send
     with `messages_send`. Resolve the session again, read the message back,
     and record the returned message ID. Block that effect when a target or
     session cannot be resolved uniquely after sending.

     If direct delivery is disabled, record `skipped_disabled` without creating
     an attempt. If an enabled preference or endpoint is missing or invalid,
     preserve any source-record result and record `contact_route_missing`. Do
     not choose a fallback.

  4. Record one attempt for each `notion_comment`, `gmail`, `telegram`, or
     `whatsapp` effect. Give each attempt its own `applied`, `duplicate`, `blocked`, or
     `failed` status and returned provider ID.

  Use native skills and MCP tools directly. Do not add a dispatcher, delivery
  plan, or provider executor. Never substitute another Work record, channel,
  destination, or person.

  If an integration or route is missing, block only that effect.

## Integration outputs

- `daily/context/daily-snapshot-YYYY-MM-DD.json`
- `daily/receipts/daily-YYYY-MM-DD.json`

PM Daily returns every Project Memory and message-draft path. The receipt stores
attempted effects, exact targets, provider confirmations, and blockers. It does
not copy artifact bodies. It also records `records_scanned`, `empty_entries`,
`sparse_entries`, `reviewable_entries`, `completed_without_evidence`,
`documentation_requests_created`, `progress_followups_created`, and
`records_skipped_with_reason`.
