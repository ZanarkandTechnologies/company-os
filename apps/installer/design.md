---
title: Company OS feature-first installer design
status: accepted
updated: 2026-09-02
---

# Feature-first installer

## Outcome

Setup asks how the Company OS should operate, not which abstract source or sink
roles exist. Every question shows a short explanation, two useful presets, and
a custom answer. Every screen supports Back. The final screen previews changes
before writing them.

## Setup order

```text
Workspace identity
  -> Decision, Employee, and SOP memory
  -> Daily Review + Chase
     -> Projects, Work, Meetings, current memory, and People
     -> staleness, documentation quality, and contact routes
  -> Weekly Consolidate + Report
     -> reports and non-Project memory destinations
     -> report recipients
  -> Weekly Meeting Ticket
     -> disabled or exact Multica workspace/project
     -> title and agenda template
  -> Project Memory sync destination and sections
  -> review -> render -> connect -> install -> verify
```

## Screen contract

Each feature question has:

- a feature and progress label;
- one direct question;
- an explainer describing the effect and an example;
- at least two preset answers with consequence text;
- `Custom…`, which opens a free-text answer;
- `Back`, which preserves prior answers and returns one screen;
- the current saved answer as the default on reconfiguration.

The installer never asks for credentials inside a feature question. Provider
login remains a later human gate derived from the selected behavior.

Delivery questions use a checklist. Gmail, Telegram, and WhatsApp each open a
separate recipient or People-field prompt when selected. The compiled
automation names every allowed channel and target; runtime does not reinterpret
the setup JSON.

Workspace name, description, and timezone are direct text fields because they
have no meaningful presets. Each still has an explainer and Back; Back on the
first screen cancels without writing.

## Configuration architecture

```text
interactive answers
       |
       v
config/setup-answers.json        private, editable setup state
       |
       v
named <!-- setup:key --> slots   deterministic compile boundary
       |
       v
automations/*.md                 hardcoded, self-contained runtime prompts
       |
       v
Hermes jobs                      read no setup JSON at runtime
```

The JSON preserves each rendered answer, selected preset, explicit provider
requirement, and exact nonsecret connection target so setup can be resumed or changed. It is not a runtime
configuration dependency. Rendering replaces each named slot body with the
selected preset text or exact custom text. The renderer rejects missing or
duplicate slots and commits the workspace, automations, and JSON as one
rollback-safe batch. Secrets never enter the JSON or automation Markdown.

## Ownership

- The installer owns questions, answer persistence, rendering, preview, and
  provider-need derivation.
- Daily owns provider reads, Project snapshots, follow-up delivery, and its
  receipt.
- PM Daily owns Project Memory, entry-quality judgment, and message drafts.
- Weekly owns provider sync and distribution.
- PM Weekly owns reports, consolidation, and long-term memory artifacts.
- Hermes owns credentials, MCP connections, schedules, and execution.
- The Multica plugin owns the host CLI boundary so Docker automation prompts do
  not receive or copy the desktop profile token.
- The opt-in Company OS messaging MCP exposes only channel discovery,
  conversation lookup/read-back, and send tools required by configured
  Telegram or WhatsApp routes.

## Reruns and recovery

Setup loads the JSON, uses saved answers as defaults, and rerenders the same
named slots. Before writing, it displays a unified diff. A failed validation
changes neither automation. Writes use temporary files followed by atomic
replacement. Start-over archives the profile before clearing its answer state.

A legacy profile with the original Daily and Weekly jobs opens the normal
update menu instead of being forced into incomplete-install recovery. Software
update stops before replacing its distribution until feature setup has created
`config/setup-answers.json`. Full verification requires all current jobs,
including the weekly meeting-ticket job.

## Deliberate limits

- No second runtime config reader.
- No arbitrary search-and-replace outside named slots.
- No credentials or OAuth material in answer JSON.
- No provider, source, recipient, or destination inferred from rendered prose.
- No schedule activation while a required answer is incomplete.

Comparable research was skipped because the interaction model was explicitly
selected: a Codex-style guided question with presets, Custom, and Back.
