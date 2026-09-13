# Company OS automation configuration

This directory is the source-controlled automation surface for the Company OS
harness. Treat these Markdown files like infrastructure configuration: each
file declares one active automation's cadence, inputs, procedure, authority,
and outputs.

| Automation | File |
| --- | --- |
| Daily operating update | `daily-operating-update.md` |
| Weekly operating review | `weekly-operating-review.md` |

These are the only active Company OS prompts during stabilization. The former
weekly meeting-ticket job is deferred together with installer orchestration; it
is not part of the two-prompt control loop.

Extraction behavior and proof live with their owners:

- Daily: `skills/pm-daily/{SKILL.md,evals/}`
- Weekly: `skills/pm-weekly/{SKILL.md,evals/}`
- Cadence-owned artifact shapes: each skill's `templates/`
- Shared provider-backed entity shapes: repository `templates/`

Runtime receipts, proposals, and runs belong in ignored runtime directories.
They are generated state, not automation configuration, and must not be
committed here.

## Execution model

Hermes reads the cadence contract and configured workspace, fetches the bounded
snapshot, then runs the owning skill against the current local files and
templates. The skill writes JSON; the final stage renders reports and memory
before applying authorized provider effects. That final stage is
enabled by being present and disabled by being absent; there is no separate
runtime switch. A future installer-owned generator will persist answers
separately and emit only the stages, bindings, and destinations they enable.
There is no Python preparation, handoff, delivery plan, or provider-executor
layer.

This layout cleanup changes repository source only. The workspace setup process
copies an allowlist and never deletes runtime files. Removing stale files from a
live Hermes workspace requires separately approved cleanup.
