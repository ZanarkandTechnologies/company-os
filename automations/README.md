# Company OS automation configuration

This directory is the source-controlled automation surface for the Company OS
harness. Treat these Markdown files like infrastructure configuration: each
file declares one active automation's cadence, inputs, procedure, authority,
and outputs.

| Automation | File |
| --- | --- |
| Daily operating update | `daily-operating-update.md` |
| Weekly operating review | `weekly-operating-review.md` |
| Weekly meeting ticket | `weekly-meeting-ticket.md` |

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
templates. The skill writes artifacts directly. The automation applies
authorized provider effects through configured skills and MCPs. Safety checks stay at the effect boundary:
exact destination, explicit authority, read-before-write, idempotency, and a
truthful receipt. There is no Python preparation, handoff, delivery-plan, or
provider-executor layer.

This layout cleanup changes repository source only. The workspace setup process
copies an allowlist and never deletes runtime files. Removing stale files from a
live Hermes workspace requires separately approved cleanup.
