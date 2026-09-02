---
automation_id: company-os-weekly-operating-review
automation_version: "2.4.0"
kind: company-os-automation
cadence: weekly
company_timezone: Asia/Kuala_Lumpur
skill: skills/pm-weekly/SKILL.md
---

# Weekly operating review

```text
[Weekly parent] --freeze--> [every Project Memory]
[Project Memory] ----------> [finalized Project evidence summaries]
[Project summaries] --by Department--> [Department reports] --> [Company report]
[Project summaries] --by Person ID----> [Employee Memory]
[Project summaries] --by workflow_key-> [SOP samples + baseline proposal]
[Project summaries] --decisions/issues> [durable memory]
```

## Purpose

Freeze the complete week. Run PM Weekly once. Sync only authorized outputs.

## Authority

Use only the source and destination declared at the node that consumes it.
Local files remain canonical. Never infer another source, recipient, or
destination.

## Todo List

- [ ] **1 — Freeze the weekly input.**

  Use `notion-fetch` and the hosted Notion MCP query tools for every Notion read.

  1. Fetch Projects from this source:

     <!-- setup:weekly.projects -->
     Fetch all active Projects from `<REPLACE_WITH_NOTION_PROJECTS_URL>`.
     <!-- /setup:weekly.projects -->

     Keep each provider page ID, business ID, exact Department relation,
     status, URL, and source revision.
     Exclude inactive Projects.

  2. Find one current-week Project Memory file for every active Project.
     Read only `weeks/<current-week>/project-memory/`.

  3. Validate the complete Project set.
     Reject mixed weeks, duplicate Projects, unreadable files, and missing
     Project Memory.

  4. Freeze the inventory and file hashes.
     Write `weekly/context/weekly-snapshot-YYYY-Www.json`.

- [ ] **2 — Run PM Weekly.**

  1. Read `skills/pm-weekly/SKILL.md` completely.

  2. Give PM Weekly every frozen Project Memory file.
     Add the prior reports and long-term memory needed for comparison.
     Add the report, record, and message templates named by the skill.

     <!-- setup:memory.decisions -->
     Extract decisions with their context, options, rationale, and outcome.
     <!-- /setup:memory.decisions -->

     <!-- setup:memory.employees -->
     Aggregate each employee's contributions, blockers, ownership, and growth
     evidence across Projects.
     <!-- /setup:memory.employees -->

     <!-- setup:memory.sops -->
     Compare repeated Work against its workflow baseline and retain reusable
     process lessons.
     <!-- /setup:memory.sops -->

  3. Run PM Weekly once.
     Let the skill write finalized Project summaries, Department and Company
     reports, memory updates, next-week Project Memory, and the executive draft.

  Treat Project summaries as intermediate evidence. Treat Department and
  Company reports as management outputs. Do not add an extraction object,
  generated template catalog, or Pydantic representation.

- [ ] **3 — Review local artifacts.**

  1. Read every changed file.

  2. Verify complete Project coverage and matching templates.
     Require immediate-source links, conservative promotion, preserved prior
     memory, and no changes outside the skill's declared paths.

  3. Propagate blocked coverage.
     A blocked Project blocks its Department and the Company report.

  If any artifact fails review, stop before calling a provider.

- [ ] **4 — Sync authorized artifacts.**

  Apply only the exact artifact types and paths returned by PM Weekly.

  1. Configure report storage at this node.
     <!-- setup:weekly.reports_destination -->
     Keep reports in the private local workspace.
     <!-- /setup:weekly.reports_destination -->
     Sync each `project_report`, `department_report`, and `company_report`
     returned under `weeks/<week>/reports/` only as configured above.
     For an external destination, upload the exact file without rewriting it,
     read it back, and record the returned URL. Otherwise call no provider.

  2. Configure SOP storage at this node.
     <!-- setup:weekly.sops_destination -->
     Keep SOP Memory in the private local workspace.
     <!-- /setup:weekly.sops_destination -->
     Sync each approved, finalized `sop_memory` returned under `memory/sops/`
     only as configured above.
     Use the integration selected by that destination.
     Read back the created record or file.
     Keep proposals and unapproved baselines local.

  3. Configure decision storage at this node.
     <!-- setup:weekly.decisions_destination -->
     Keep Decision Memory in the private local workspace.
     <!-- /setup:weekly.decisions_destination -->
     Sync each promoted, final `decision_memory` returned under
     `memory/decisions/` only as configured above.
     Use the integration selected by that destination.
     Read back the created record or file.
     Keep unapproved proposals local.

  4. Configure executive delivery at this node.
     <!-- setup:weekly.report_recipients -->
     Keep the executive distribution draft local and send nothing.
     <!-- /setup:weekly.report_recipients -->
     Send `executive_distribution` returned under `weeks/<week>/outbound/`
     only as configured above.
     For Telegram or WhatsApp, resolve each exact target with `channels_list`.
     Use `conversations_list` for that platform and `conversation_get` to find
     the unique session whose `chat_id` matches the target.

     Compute a SHA-256 delivery token from the exact draft bytes and exact
     target. Split the draft into ordered messages of at most 1,900 characters,
     including a header of
     `[company-os:<token>:part <number>/<count>]`. Before sending, use
     the current weekly receipt plus `messages_read` to find every expected
     header and exact chunk. Send only missing chunks with `messages_send`.
     After each successful send, immediately store its token, part number, and
     provider message ID in the receipt before sending the next part. Resolve
     the session again and require every unreceipted exact chunk in message
     history. This keeps verification within the MCP's 2,000-character read
     limit and makes a partial retry idempotent.
     Limit one recipient delivery to 50 chunks; record `message_too_long` and
     send nothing when the draft exceeds that bound.
     Block only that recipient when the target or post-send session cannot be
     resolved uniquely. Record the token, part count, and each returned message
     ID. When delivery is disabled, call no provider and keep the draft local.

  5. Configure Project Memory sync at this node.
     <!-- setup:weekly.project_memory_destination -->
     Keep Project Memory in the private local workspace.
     <!-- /setup:weekly.project_memory_destination -->

     Apply that rule to each `next_week_project_memory` path returned under
     `weeks/<next-week>/project-memory/`. For Notion sync, use the exact source
     Project URL, update only the named sections, then read those sections back.
     Otherwise call no provider.

  6. Configure Employee Memory storage at this node.
     <!-- setup:weekly.employee_memory_destination -->
     Keep Employee Memory in the private local workspace.
     <!-- /setup:weekly.employee_memory_destination -->

     Apply that rule to each `employee_memory` path returned under
     `memory/employees/`. For external storage, upload the exact file, read it
     back, and record the returned URL. Never sync Employee Memory to the public
     People database.

  7. Configure additional Memory storage at this node.
     <!-- setup:weekly.other_memory_destination -->
     Keep every additional extracted memory type in the private local workspace.
     <!-- /setup:weekly.other_memory_destination -->

     Apply that rule only to additional memory paths explicitly returned by PM
     Weekly. For external storage, upload the exact file, read it back, and
     record the returned URL. Keep `issue_memory` local unless this rule names it.

  8. Record each provider effect.
     Store only URLs and message IDs returned by the provider.

  Use native skills and MCP tools directly. Do not add a dispatcher, delivery
  plan, or provider executor.

  If a destination is missing, incomplete, or unauthorized, block only that
  effect. Keep its artifact local. Never use a fallback destination.

## Integration outputs

- `weekly/context/weekly-snapshot-YYYY-Www.json`
- `weekly/receipts/weekly-YYYY-Www.json`

PM Weekly returns every report, memory, next-week Project Memory, and draft
path. The receipt stores frozen input hashes, validated paths, provider
outcomes, returned provider IDs, and blockers. It does not copy artifact bodies.
