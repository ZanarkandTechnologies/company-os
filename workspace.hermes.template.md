---
template_id: hermes-company-workspace
template_version: "1.1.0"
kind: hermes-project-context
company_name: REPLACE_ME
company_description: REPLACE_ME
company_timezone: REPLACE_ME
status: draft
production_write_mode: proposal-only
---

# Company Workspace

## Company

Replace this paragraph with the company context Hermes needs to do its work.

## Data sources

Choose a semantic role, provider, and source URL. Other instructions should
refer to the role instead of repeating the URL.

<!-- hermes:managed data-sources -->
| Role | Provider | Source | Access | Structure and scope |
| --- | --- | --- | --- | --- |
| `projects` | REPLACE_ME | REPLACE_ME | read-write | Human-operated project source records; private derived management state stays in the Hermes weekly workspace |
| `tasks` | REPLACE_ME | REPLACE_ME | read-write | Current work items linked to projects |
| `people` | REPLACE_ME | REPLACE_ME | read | People referenced by configured work only |
| `sops` | REPLACE_ME | REPLACE_ME | read | Approved source SOPs and operating procedures |
| `reports` | REPLACE_ME | REPLACE_ME | read | Historical company and department reports used as evidence |
| `operator_email` | REPLACE_ME | REPLACE_ME | isolated-eval | Operator-owned inbox used only for bounded connection certification |
<!-- /hermes:managed data-sources -->

Fill each provider independently. Roles may share one provider or use different
providers. The setup wizard leaves skipped roles as `—` so they remain available
for later configuration; automations must only use configured roles. Notion or
Drive owns permissions at a configured URL. Hermes records only its bounded
authority and never infers another destination.

The lean setup needs only Projects and Work. Add People for employee rollups,
SOPs for approved process evidence, and Reports for historical reporting
evidence. Operator email is optional. Generated Reports and
Employee/SOP/Decision/Issue Memory remain local artifacts, distinct from these
read-only provider sources.

## Optional artifact sync

Hermes always writes canonical Project Memory, long-term entity memory, and
Final reports inside its private runtime workspace. Add a row only when an
operator wants a one-way secondary copy after local read-back. An empty table
means local-only; provider edits never flow back into memory.

<!-- hermes:managed artifact-sync -->
| Artifact | Provider | Destination |
| --- | --- | --- |
<!-- /hermes:managed artifact-sync -->

Supported artifacts are `short-term memory`, `long-term memory`, and `reports`.
Each row needs an exact HTTPS destination. Memory destinations must be private;
the long-term-memory destination must never be the public People directory.

## Private weekly workspace

```text
weeks/
`-- YYYY-Www/
    |-- project-memory/
    |   `-- project--<stable-project-id>.md
    `-- reports/
        |-- projects/
        |-- areas/
        `-- company/
memory/
|-- employees/
|-- sops/
|-- decisions/
`-- issues/
```

PM Daily reviews its grounded local files before updating
Project Memory. Weekly freezes all Project Memory, writes versioned Project/Area/
Company reports, and updates the referenced long-term entity records. Optional
message drafts live under the week only when owner messaging is configured;
minimal delivery metadata stays in hidden run state.

## Outputs

| Output | Template | Local owner |
| --- | --- | --- |
| Project Memory | skills/pm-daily/templates/project-memory.md | weeks/&lt;week&gt;/project-memory |
| Employee Memory | templates/person.md | memory/employees |
| SOP Memory | templates/sop.md | memory/sops |
| Approved Final operating report | skills/pm-weekly/templates/weekly-report.md | weeks/&lt;week&gt;/reports |

## Communications

Choose what kind of message Hermes may prepare or send. Setup asks only for
the message, app, recipient, and whether Hermes should draft or send it:

- `owner report` is a completed company report for the owner or boss.
- `owner alert` is a short message about something that needs their attention.
- Task-specific documentation and progress questions use comments on the exact
  linked Work item by default.
- `employee follow-up` is an optional direct route that replaces progress
  comments only when explicitly configured.

One message type never substitutes for another.

<!-- hermes:managed communications -->
| Message | App | Send to | Behavior |
| --- | --- | --- | --- |
<!-- /hermes:managed communications -->

## Operating guidance

- Use the configured company timezone.
- Resolve sources and destinations through the Data sources roles above.
- Treat a reachable link as connectivity, not write authority.
- Report missing sources, properties, relations, or permissions as configuration gaps.

## Boundaries

- Never store credentials, tokens, passwords, or private keys in this document.
- Production writes remain proposal-only until explicitly authorized here.
- Never infer a source, destination, recipient, or fallback route.
