---
title: Supported Company OS sources
status: active
owner: Company OS
updated_at: 2026-08-31
refs:
  - ../../workspace.hermes.template.md
  - ../providers/
  - ../provider_catalog.py
---

# Supported Company OS sources

A source is an exact provider location the Company OS may read under a semantic role. Automations ask for roles such as `projects`, `tasks`, `people`, `sops`, or `reports`; setup decides which provider and exact location fulfill that role.

A source binding does not grant account-wide access, choose an output destination, or authorize a write. Connections and sinks are separate setup decisions.

## Wizard-supported roles

These roles exist in the workspace template and are selectable today:

| Role | What it owns | Providers | Requirement |
| --- | --- | --- | --- |
| `projects` | Active Projects, status, current plan, and Department/Area relationships | Notion, Linear | Core setup and Doctor source |
| `tasks` | Current Work: Tasks, Features, Issues, and reviewable completed work | Notion, Linear | Core setup and Doctor source |
| `people` | Shared identity, role, and stable person references | Notion | Optional globally; required for employee performance reporting |
| `sops` | Approved source SOPs and operating procedures | Notion | Optional process evidence |
| `reports` | Historical company and department reports | Notion | Optional reporting evidence |
| `operator_email` | Isolated operator inbox used for connection certification | Gmail through Composio | Optional certification surface, not company memory |

The lean setup selects Projects and Work. Add People when Weekly employee reporting is expected. Skipped roles remain visibly unconfigured and can be added by rerunning workspace setup.

## Analysis input expectations

The automation contracts describe the preliminary content needed for useful analysis:

| User feature | Required provider data | Required local data |
| --- | --- | --- |
| Progress chasing | Project with ID, name, status; Work with ID, name, status, Project, owner, and due date | None |
| Documentation quality | Work with ID, name, status, type, and meaningful page body | None |
| Employee performance reporting | Projects; Work with Project and owner; People with ID and name | Frozen Project Memory |
| SOP extraction | Work with Project and meaningful page body | Frozen Project Memory |
| Department/company reporting | Project with status and Department/Area relation | Frozen Project Memory |

Doctor delegates the selected contract to native Hermes in analysis-only mode.
The agent reports missing or incomplete inputs alongside its local preview
files; setup does not maintain a parallel feature-readiness registry or
blocking engine.

## Canonical field mapping

Automation snapshots use provider-neutral field names:

| Canonical field | Accepted names/location |
| --- | --- |
| `id` | Provider record’s top-level stable ID |
| `name` | `Name` or `Title` |
| `status` | `Status` |
| `project` | `Project` or `Projects` |
| `owner` | `Owner`, `Assignee`, `Assigned To`, or `People` |
| `due_date` | `Task Due Date`, `Due Date`, or `Due` |
| `type` | `Type` |
| `department` | `Department`, `Departments`, `Area`, or `Areas` |
| `body_markdown` | Sanitized page body fetched for the selected record |

Missing fields remain explicit gaps in the validated automation result. They do
not authorize broader source scans or guessed values.

## Provider certification

Setup’s provider catalog defines how each selected binding is tested:

| Binding | Certification | Risk |
| --- | --- | --- |
| Projects → Notion | Fetch source; create, read back, and archive one isolated private page | Reversible; confirmation required |
| Projects → Linear | Fetch team/source; create, read back, and leave one isolated issue non-active | Reversible; confirmation required |
| Work → Notion or Linear | Fetch and describe configured structure and populated/empty state | Read-only |
| People → Notion | Fetch identity, visible properties, and populated/empty state | Read-only |
| SOPs → Notion | Fetch source and return one grounded process observation | Read-only |
| Reports → Notion | Fetch source and return one grounded report observation | Read-only |
| Operator email → Gmail | Confirm the exact isolated inbox; send and read back one self-addressed email | Irreversible; confirmation required |

Risky tests are listed before approval. Certification must not modify an existing provider record. A deferred test keeps the binding but makes setup health `PARTIAL` until certification is rerun.

## Catalogued roles not exposed by the wizard

The catalog also contains definitions for `meetings` and `decisions`. They are not current Data source rows in the workspace wizard:

| Catalog role | Provider tests present | Current use |
| --- | --- | --- |
| `meetings` | Notion read-only | Meeting evidence currently enters through Work/manual intake. |
| `decisions` | Notion destination inspection | Decision Memory remains locally canonical; copies use artifact sync. |

Catalog presence proves a validated connection-test definition, not complete wizard support or production authority.

## Data ownership and privacy

- Projects owns human-operated project truth, not private assessments or report history.
- Work owns progress, evidence, blockers, completion notes, and discussion.
- People owns shared identity and approved route references, not Employee Memory or inferred permissions.
- People, SOPs, and Reports own distinct provider evidence. Generated SOP/Decision/Issue Memory and generated reports stay private unless explicitly copied to a sink.
- Frozen Project Memory and long-term memory are runtime-local state, not setup sources.
- Bind exact URLs or provider identifiers. Never treat a connected account as an implied company boundary.
- Credentials and OAuth state remain in the private Hermes profile, never in workspace Markdown or Git.

## Failure behavior

Setup rejects unsupported role/provider combinations and incomplete configured rows. Connection failure may be retried or deferred. Doctor is stricter about content: a reachable but empty or structurally insufficient binding remains connected, while only the dependent user feature/cadence is marked `blocked_by_setup`.
