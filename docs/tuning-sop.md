---
title: Company OS maintenance and tuning SOP
status: active
owner: Company OS
created_at: 2026-09-01
updated_at: 2026-09-01
system_id: SYS-0001
refs:
  - operator-guide.md
  - autonomous-testing.md
  - ../README.md
  - ../templates/README.md
  - ../skills/pm-daily/SKILL.md
  - ../skills/pm-weekly/SKILL.md
---

# Company OS maintenance and tuning SOP

## Who this is for

This SOP is for a semi-technical maintainer changing how the Company OS writes,
summarizes, or evaluates Daily and Weekly outputs. It assumes the system is
already installed. For installation, credentials, connection testing, or
recovery, use the [customer setup guide](../apps/installer/docs/customer-setup.md).

Always edit this repository first. Do not edit installed copies under the live
Hermes profile: setup replaces those copies from this repository. Generated
reports, memory, receipts, credentials, and provider data belong to the live
profile and must not be copied into Git.

## Choose the file that owns the change

Start with the output you want to change. Most wording and report-layout tuning
belongs in a Markdown template, not in a skill.

| Desired change | Edit | Examples |
| --- | --- | --- |
| Change the wording, headings, order, or required content of a Daily output | `skills/pm-daily/templates/` | Project Memory, documentation request, progress follow-up |
| Change the wording, headings, order, or required content of a Weekly output | `skills/pm-weekly/templates/` | Project report, Department rollup, Company rollup, executive distribution |
| Change what the agent selects, rejects, infers, promotes, or preserves | `skills/pm-daily/SKILL.md` or `skills/pm-weekly/SKILL.md` | What counts as stale Work; when an observation may become an SOP |
| Change a shared business-record shape | `templates/` | Task, Project, Person, Meeting, Issue, Decision, SOP |
| Change company identity, source/destination bindings, authority, or operating policy | `workspace.hermes.md` through the setup workflow | Company name, Notion source, report destination, allowed delivery |
| Change schedule boundaries or automation orchestration | `automations/` | Daily window, Weekly invocation and review sequence |
| Change installer, integration, or provider behavior | `apps/` or `plugins/` | Setup screens, connection validation, Notion webhook behavior |

If a template can express the change, stop there. Change a skill only when the
agent's decision rules must change. Changes under `apps/`, `plugins/`, or
`automations/` are engineering changes and should not be treated as ordinary
content tuning.

## The tuning loop

### 1. Write down the expected Before and After

Use one real but sanitized example. State what the current output does, what the
new output should do, and what must remain unchanged.

```text
Before: The executive summary lists every open item in one paragraph.
After: It shows the three decisions or risks that require owner attention,
each with an owner, date, and source-report link.
Keep: Missing owners or dates remain explicit gaps; the agent must not invent them.
```

Do not use private employee, customer, credential, or production data in the
repository. Add a synthetic fixture when the existing packaged example cannot
represent the change.

### 2. Edit the smallest owner

For a template change:

1. Preserve the YAML frontmatter and stable `template_id`.
2. Keep placeholders visually distinct, normally as `{{PLACEHOLDER_NAME}}`.
3. Put instructions in HTML comments when they guide the agent but should not
   appear in the final output.
4. Keep every required heading represented in the corresponding expected file
   and eval assertions.
5. Increase `template_version` when the installed output contract changes.

For a skill change, update its Rule and Assert together. A rule says what the
agent should do; its Assert states the observable condition that proves it. Do
not add provider writes to a PM skill: both PM skills edit local artifacts only.

### 3. Update the owned example and eval only when behavior intentionally changed

Each PM skill owns its evidence:

```text
skills/pm-daily/evals/
skills/pm-weekly/evals/
```

- `fixtures/` contains synthetic input.
- `expected/` contains the intended resultant files.
- `evals.json` describes the observable assertions.

Update expected output only when it represents the accepted After behavior.
Never weaken an assertion or overwrite an expected file merely to make a failed
check pass. If the new behavior cannot be distinguished from the old behavior
by an assertion or expected artifact, the tuning change is not yet proven.

### 4. Run safe local checks

From the repository root, run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 apps/installer/validate_context.py --context workspace.hermes.md
```

Both commands must exit successfully, and context validation must print
`context_valid=true`. These checks are offline and make no provider writes.

If an authorized private test profile is available, a maintainer may also run
Daily or Weekly in analysis-only mode:

```bash
python3 setup.py doctor analysis --profile-home "/absolute/path/to/profile" --cadence daily
python3 setup.py doctor analysis --profile-home "/absolute/path/to/profile" --cadence weekly
```

Doctor can use model capacity and read the named profile, but it disables
provider mutations, messaging, and artifact synchronization. Review the full
generated output, not only whether the command exited successfully.

### 5. Review the output before installation

Check the representative output against the Before and After statement:

- All requested headings and wording are present.
- Instructions and placeholders do not leak into reader-facing prose.
- Claims retain source links and distinguish facts, estimates, and gaps.
- Missing evidence stays missing rather than becoming an invented answer.
- Unrelated output and decision rules remain unchanged.
- Daily or Weekly changed only the files declared by its skill.

For a report change, read it as the manager who receives it. The result should
make the required decision or next action clear without requiring knowledge of
Hermes or this repository.

### 6. Install the reviewed source

Commit or otherwise save a recoverable copy of the reviewed repository change.
Then rerun `setup.cmd` on Windows or `./setup.sh` on macOS and choose **Update
Company OS software**. Setup copies only the distribution allowlist, preserves
unknown runtime files, reconciles schedules, and runs static verification.

Do not copy files into the live profile by hand. Do not treat a successful
installation as proof that a scheduled output is good; inspect the next
analysis-only or scheduled result.

### 7. Observe one Daily and one Weekly boundary

After a Daily-related change, inspect one representative Daily result. After a
Weekly or shared-template change, inspect both a representative Daily result
and the next Weekly result because Weekly consumes Daily-owned Project Memory.

Record:

```text
Change:
Source files and versions:
Representative input:
Observed output:
Checks passed:
Unexpected behavior or remaining risk:
Decision: keep, revise, or revert
```

## Worked example: tune the executive distribution

1. Describe the Before and After using a sanitized Company report.
2. Edit `skills/pm-weekly/templates/executive-distribution.md`.
3. Preserve its `template_id`; increase `template_version` because the output
   contract changed.
4. If the headings or required content changed, update the matching Weekly
   expected artifact and `skills/pm-weekly/evals/evals.json` assertion.
5. Run the safe local checks.
6. Run Weekly Doctor against an explicitly authorized private profile, when
   available, and inspect the rendered executive draft.
7. Save the reviewed repository change and use **Update Company OS software**.
8. Inspect the next Weekly draft before enabling or relying on delivery.

Do not edit `skills/pm-weekly/SKILL.md` for this example unless the selection
rule itself changes—for example, changing which risks qualify for executive
attention rather than changing how qualifying risks are presented.

## Revert and recovery

If the output is worse, restore the last reviewed repository version of every
file changed by the tuning attempt, rerun the safe local checks, then run
**Update Company OS software** again. The installer preserves generated runtime
files; reverting source does not delete previous reports or memory.

If the problem is credentials, provider access, schedules, webhook ingress, or
installation health, stop tuning content and use the maintenance menu in the
[customer setup guide](../apps/installer/docs/customer-setup.md#5-restart-and-update).

## Maintenance checklist

### Routine operator work

- Keep source Work records, owners, dates, blockers, evidence, and next actions current.
- Review Daily questions and Weekly reports using the [operator guide](operator-guide.md).
- Use setup's health and integration checks for runtime problems.

### When tuning behavior

- Start with one representative Before and After.
- Edit the smallest owning template or skill.
- Update the owned expected artifact and assertion only for intentional changes.
- Run the offline checks and inspect the complete output.
- Save a recoverable source version before installation.
- Install through setup and observe the affected cadence boundary.

### Escalate to a developer

- A change requires Python, provider code, credentials, or a new external write.
- The desired behavior crosses Daily, Weekly, workspace authority, and provider routing.
- Tests fail outside the files intentionally changed.
- A safe synthetic example cannot reproduce the problem.
- Reverting and reinstalling the reviewed source does not restore behavior.

Grounding: current repository ownership, PM skill boundaries, template layout,
distribution allowlist, installer update path, and autonomous-testing contract.
No external source is required for this SOP.
