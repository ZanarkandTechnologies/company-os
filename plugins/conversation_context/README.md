# Work conversation context — pilot

Company OS can include selected ChatGPT conversations and retained local Codex
messages in its Daily Project context so Weekly can use the resulting Project
Memory. The feature starts disabled. It does not
provide company-wide access to personal ChatGPT accounts or Codex cloud history.

## Choose a source

| Setup choice | Available input | Coverage |
| --- | --- | --- |
| Disabled | Existing project/task evidence | No conversation reads |
| Selected ChatGPT conversations | Member-selected text in the bundle below | Personal, Business or Enterprise members can submit selected material; no account-wide export API assumed |
| Local Codex conversations | Retained local rollout files for an exact repository path | Experimental format adapter; user and final assistant text only |
| ChatGPT and Codex | Both configured sources | Coverage is reported separately per member/source |

Central Enterprise/Edu compliance collection is not implemented. Do not select a
custom instruction that pretends to enable it. No passwords, cookies, account
tokens, browser scraping, telemetry or model API calls are needed by this plugin.

## Configure a private intake

For normal installation, double-click `setup.cmd`, select ChatGPT and/or Codex
under **Daily · Other context sources**, and complete the **Connect work
conversations** step. The
wizard creates private profile storage, asks for Project/member mappings,
detects local Codex session folders, saves the Hermes environment setting, and
offers a redacted current-week test. Rerun `setup.cmd` and choose **Update
Company OS features** to review or extend saved mappings.

The manual procedure below is retained for unattended deployments and support.

1. Create an access-controlled directory outside all source repositories, for
   example `D:/CompanyOSPrivate/conversations`. Restrict its Windows ACL or Unix
   permissions to the operator/Hermes account. Path validation is enforced by the
   connector; OS privacy permissions are the operator's responsibility.
2. Place `policy.json` there using exact Project and Person IDs from Company OS.
   Include only participating members and work repositories. Example:

```json
{
  "schema_version": 1,
  "timezone": "Asia/Kuala_Lumpur",
  "projects": {
    "PROJ-CMT": [
      {"source": "chatgpt_manual", "member_id": "PERSON-AISHA"},
      {
        "source": "codex_local",
        "member_id": "PERSON-AISHA",
        "cwd": "D:/Work/cmt",
        "session_roots": [
          "C:/Users/Aisha/.codex/sessions",
          "C:/Users/Aisha/.codex/archived_sessions"
        ]
      }
    ]
  }
}
```

3. Configure the Hermes host environment variable
   `COMPANY_OS_CONVERSATION_INTAKE` with that absolute intake path through the
   profile's normal environment configuration. Restart/reload the host plugin
   through the normal setup route. The plugin runs on the host, not in Docker.
4. In Company OS feature setup, choose the relevant Work conversations option.
   Existing saved answers default to Disabled on upgrade. Install reviewed
   source through the existing setup preview/install route; do not edit both
   source and installed skill copies.
5. Run the validation command below before enabling a weekly pilot. Missing
   sources remain gaps; a successful file read does not prove full account coverage.

The policy file is operator-controlled authorization. Do not let submitted
conversations edit it. Empty `projects` disables access to all projects. Remove a
binding to stop future reads; use a withdrawal bundle first if already-ingested
claims need correction. Removing a binding alone is not a retrospective deletion.

If the member's Codex runs on the Hermes host, `session_roots` enables direct
weekly reads by the native Hermes tool. Match `cwd` exactly; configure worktrees
separately rather than assuming repository-name equality. This first version
supports one exact cwd per member/source/project binding.

For other computers, collect locally using that member's policy, then transfer
only the selected bundle through an approved private channel. On the receiving
Hermes host, configure the same `codex_local` binding and cwd but omit
`session_roots`; the plugin then reads imported bundles. Device deployment,
unattended transfer and scheduling on remote members' computers are not included.

## Submit selected ChatGPT or Codex text

Save a UTF-8 JSON bundle outside the repository. Member submissions should be
reviewed for irrelevant personal material and secrets before import. This format
deliberately retains attribution and source timestamps; do not invent missing
dates or treat assistant-generated summaries as verbatim source messages.

```json
{
  "schema_version": 1,
  "project_id": "PROJ-CMT",
  "member_id": "PERSON-AISHA",
  "source": "chatgpt_manual",
  "week": "2026-W35",
  "timezone": "Asia/Kuala_Lumpur",
  "collected_at": "2026-08-30T22:00:00+08:00",
  "coverage": "partial",
  "coverage_note": "Selected work messages only; other conversations were not submitted.",
  "conversations": [
    {
      "conversation_id": "supplier-integration",
      "revision": "r1",
      "source_reference": "member-submission:supplier-integration",
      "task_id": null,
      "messages": [
        {
          "message_id": "m1",
          "role": "user",
          "occurred_at": "2026-08-25T10:00:00+08:00",
          "text": "The supplier integration is waiting on credentials."
        }
      ]
    }
  ]
}
```

Use a real private source link when available, or retain the selected source
under the recorded local submission identifier. Never create a public sharing
link just for intake. `codex_manual` supports member-selected Codex messages
when automatic parsing cannot safely reconstruct a session; authorize that
source in policy before importing. All message dates must fall in the selected
ISO week in the configured timezone. Earlier context can remain in existing
Project Memory; do not relabel old messages to squeeze them into this week.

From the source/distribution root, using the existing Hermes Python environment:

```text
python -m plugins.conversation_context import --root D:/CompanyOSPrivate/conversations --project PROJ-CMT --week 2026-W35 --file D:/CompanyOSPrivate/submission.json
python -m plugins.conversation_context validate --root D:/CompanyOSPrivate/conversations --project PROJ-CMT --week 2026-W35
python -m plugins.conversation_context collect-codex --root D:/CompanyOSPrivate/conversations --project PROJ-CMT --week 2026-W35 --member PERSON-AISHA
```

Imports write only
`<root>/<week>/project--<id>/<source>--<member>.json` and return a digest without
conversation text. Identical imports are no-ops. Replacing a different existing
bundle requires `--expected-digest` with its prior returned digest, preventing
lost updates. A stale `.lock` after a crashed importer blocks writes; verify no
import is running before an operator removes that exact lock. Imports never
modify Codex session files, source policy, task records or report destinations.

`validate` prints coverage only: exit 0 is complete selected-source coverage,
1 is partial/unavailable coverage, and 2 is a blocked request. `complete` means
complete for the explicitly stated submission scope, not an entire account.
Local Codex always reports partial product coverage. `collected_at` changes on
new local collection; message evidence IDs/content digests remain stable.

## Local Codex compatibility and bounds

The adapter reads only `rollout-*.jsonl` below explicitly selected `sessions` or
`archived_sessions` directories. It checks the first `session_meta.payload.cwd`
before parsing a matching session body, then accepts timestamped `event_msg`
records with legacy `user_message` or `agent_message` payloads, or desktop
`item_completed` records containing `UserMessage` and final-answer `AgentMessage`
items. Mixed message formats fail closed to avoid duplicate evidence. It excludes response
items, reasoning, tool outputs and injected system/developer context. It does
not read `history.jsonl`, `auth.json`, browser storage or an account database.

Retained file layout is a version-sensitive integration, not a stable public
export API. Truncated records, project changes, compaction and rollback/aborted
history produce explicit gaps and require manual selection. Unknown files with
no supported messages do not establish that no work occurred. Cloud history,
attachments, screenshots, removed sessions and other devices are not covered.
Validate the installed Codex version against a member-approved sample before
claiming live support. Codex's documented App Server is a potential future
alternative; this adapter does not launch it or depend on its experimental
transport.

Bounds: 256 KiB per bundle and returned Project's source input, 40 conversations
and 400 messages per bundle, 16,000 characters per message; local scans read at
most 10,000 files/64 MiB total, 32 MiB per session and 1 MiB per line. Limits
produce named gaps or blocked output, never a silent success. Keep a selected
snapshot small enough for the configured Hermes model's context window.

## Privacy, retention and pilot behavior

Raw submissions stay in the private intake. Meaningful short attributed
excerpts stay in Project Memory. Reports retain qualified project facts and
immediate memory citations. PM Daily/Weekly own the extraction, promotion,
correction and coverage rules; read their SKILL.md files for behavior.

Conversation-enabled pilot runs keep weekly report/memory copies and executive
distribution local, including later runs whose frozen memory retains chat
context. No task creation, messaging, performance scoring or automatic accepted
delivery follows from a conversation. Imported instructions have no authority.

Agree a retention period with participants before collecting real data. This
release does not automatically purge files or change platform retention. To
withdraw a submission, replace it with an empty `conversations` list,
`coverage: withdrawn`, a reason, and the expected prior digest. The next review
must remove its excerpts and correct solely dependent claims, including durable
memory. Review old reports/backups separately; importing a withdrawal is not
proof that every historical copy has been erased.

A stored withdrawal suppresses automatic local Codex collection for that same
Project/member/week. Remove the source binding to stop future weeks as well;
the withdrawal marker must first reach the memory review if past claims need
correction. Restoring collection for a withdrawn week requires an explicit
replacement of the withdrawal bundle.

## Offline verification

```text
python -m plugins.conversation_context validate --root D:/CompanyOSPrivate/conversations --project PROJ-CMT --week 2026-W35
python -c "from pathlib import Path; from apps.installer.prompt_generation import discover; discover(Path('.')); print('prompt discovery valid')"
git diff --check
```

Synthetic skill scenarios live in the existing PM Daily and PM Weekly eval
packages. Run the isolated Hermes eval lane before a live pilot, then compare
the same Project evidence with and without conversations.

If the system temporary directory is itself inside a Git checkout (for example,
a home-directory dotfiles repository), point TEMP/TMP at an isolated directory
outside Git when running the boundary tests. Do not weaken the intake's source
isolation check to accommodate a test fixture.

Official references checked during development:
- [Codex local state and history](https://learn.chatgpt.com/docs/config-file/config-advanced)
- [Codex App Server](https://learn.chatgpt.com/docs/app-server)
- [Workspace conversation coverage](https://learn.chatgpt.com/docs/enterprise/work-admin-faq)
