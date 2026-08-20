---
document_id: company-os-automations
document_version: "0.5.0"
kind: automation-index
status: draft
owner: HermesCorp
opens_with:
  - outcome
  - why
---

# Company OS automations

> **Outcome**
>
> Keep company records useful with one shared evidence pass each day and one
> weekly review that promotes only future-useful records.
>
> **Why**
>
> Reduce follow-up work, surface recurring problems, preserve important context,
> and improve documentation without turning every note or choice into permanent
> company knowledge.

Company OS uses one incremental Daily automation and one Weekly finalization
automation. Daily ingests changed evidence once and updates the current weekly
draft. Weekly reviews those accumulated candidates, promotes approved durable
records, freezes the report, and opens the next reporting window.

```text
changed Tasks + embedded Meeting notes + changed documents
  -> one deduplicated evidence bundle
  -> progress, problem, decision, SOP, and resource candidates
  -> same-day records checked against their matching Notion templates
  -> source comments asking only for missing documentation
  -> current weekly report draft
  -> weekly review and selective promotion
  -> immutable weekly report
```

## Automation files

| Automation | Cadence | Owns | Does not own |
| --- | --- | --- | --- |
| [Daily operating update](automations/daily-operating-update.md) | Daily | Incremental evidence, candidate extraction, same-day template checks, source comments, draft updates, stale-work proposals | Promoting Issues, Decisions, Resources, or Skills; sending unapproved messages |
| [Weekly operating review](automations/weekly-operating-review.md) | Weekly | Plan comparison, candidate review, approved promotion, report finalization | Deleting canonical work items; inventing approvals or decision rationale |

## Process model

An automation owns the schedule, evidence window, process order, and final
receipt. A process owns one kind of judgment or write inside that automation.
Processes may share the same evidence bundle without sharing responsibilities.

> **Automation**
>
> `schedule + evidence bundle + ordered processes + receipt`
>
> **Process**
>
> `owned input + one decision + owned output + boundary`

This distinction keeps extraction, promotion, quality review, and external
follow-up independently testable even when they run from the same Markdown file.

## Shared rules

- Tasks are the single work-item database with `Task`, `Issue`, and `Meeting`
  types.
- Problems remain report candidates during the week. Weekly review may promote
  an accepted problem into a Task row with `Type = Issue`.
- Meeting notes remain in their Task row unless they pass the Resource
  future-value gate.
- Small choices remain task or report context. Only future-useful precedents
  become Decision records.
- Candidate sections are upserted by stable source fingerprint; reruns must not
  append duplicates.
- Daily checks records created or edited that day against the matching Notion
  template. A source comment lists only missing required information and is not
  projected into the weekly Report or processed by Weekly. Without an approved
  source-comment policy, Daily saves the exact comment as a proposal.
- Runtime watermarks, logs, credentials, and provider state stay outside these
  tracked specifications.
- External comments and chase messages require an explicit company policy or
  owner approval.

These files define desired behavior only. A deployment chooses the exact local
schedule and connector routes during Company OS onboarding.
