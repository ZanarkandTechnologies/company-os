---
template_id: company-os-weekly-report
template_version: "0.3.0"
kind: company-record-template
record_type: weekly-report
status: active
owner: HermesCorp
lifecycle: draft-then-immutable
opens_with:
  - executive-summary
required_properties:
  - name
  - project
  - week
  - report_status
  - previous_report
---

# {{PROJECT_NAME}} — Week of {{WEEK_START}}

## Executive summary

{{EXECUTIVE_SUMMARY — Write exactly three sentences: what materially changed,
the main problem or risk, and the next priority.}}

## Plan versus actual

| Planned result | Actual result | Evidence | Variance and implication |
| --- | --- | --- | --- |
| {{What the team expected to complete}} | {{What happened}} | {{Linked Tasks, Meetings, or documents}} | {{Why the difference matters}} |

## What went well

- {{A useful result or repeatable success, with evidence and why it mattered}}

## Problems observed

| Problem | Evidence and recurrence | Impact | Disposition |
| --- | --- | --- | --- |
| {{Observed problem}} | {{Source links and whether it recurred}} | {{Cost, delay, risk, or affected work}} | {{Promote to Issue \| Duplicate \| Monitor \| Dismiss}} |

## Promotion candidates

### Decisions with future precedent

- {{Decision candidate, future precedent, authority gap, and weekly disposition}}

### Resources with future reuse

- {{Resource candidate, future use, source, and weekly disposition}}

### SOPs with repeatability evidence

- {{SOP candidate, repeated workflow evidence, owner, and weekly disposition}}

## Follow-ups

- {{Owner, stale commitment, chase status, response, and unresolved dependency}}

## Next week

- {{Owner-approved commitment or carried-forward Issue, owner, and evidence of priority}}

## Automation receipt

- `evidence_window:` {{START_TIMESTAMP}}..{{END_TIMESTAMP}}
- `sources_checked:` {{Stable source names or locators}}
- `source_gaps:` {{Missing or stale sources, or none}}
- `last_successful_daily_receipt:` {{Receipt locator}}
