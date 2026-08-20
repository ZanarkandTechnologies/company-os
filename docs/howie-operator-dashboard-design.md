---
title: Howie operator dashboard visual brief
status: accepted-for-POC
updated_at: 2026-08-11
---

# Howie operator dashboard visual brief

## Register

Operational product UI with a field-operations character. The operator should
read the week and open the next piece of work without navigating a reporting
product.

## Scene sentence

An operator opens Howie before the weekly stand-up: a mine sits beyond the
application frame, a dark-paper sheet holds the operating context, and the
centred weekly Gantt gives the next decision its place.

## Taste dials

| Dial | Value | Direction |
| --- | ---: | --- |
| Density | 8/10 | A compact schedule is the primary object. |
| Variance | 6/10 | Editorial type and the mine perimeter distinguish it without obscuring work. |
| Motion | 3/10 | Small hover and drawer transitions only. |
| Colour commitment | 6/10 | Dark paper, warm-white type, muted green-grey metadata, and a restrained mine perimeter. |
| Materiality | 7/10 | The supplied mine image frames one dark-paper application sheet; the Gantt itself stays flat and legible. |

## Source synthesis

| Source | Adopt | Adapt | Reject |
| --- | --- | --- | --- |
| Aino | Sparse editorial hierarchy; restrained navigation; high-contrast dark atmosphere. | The feeling is rendered as a compact operational shell, not a brand site. | Large campaign imagery or decorative page sections. |
| Notion Timeline | A time-scaled, date-first grid where rows are canonical work items and selecting one opens details. | The central Gantt owns the week; requirement and dependency detail lives in a centred modal. | Multiple equal-weight views competing with the weekly plan. |
| Frappe Gantt | Native task bars, date rail and dependency arrows. | Local, read-only renderer using the canonical ticket projection; Howie owns the detail modal and state copy. | Editing dates, progress, or work from the chart. |
| Howie manager state | Ticket IDs, readiness, outputs, requirements, review and chase context remain the source of truth. | State is surfaced as compact signals rather than dashboard cards. | Any simulated action or developer copy in the normal operator view. |
| Eval trace | A readable event sequence plus concrete final files makes the harness inspectable. | A separate Evals tab stages and inspects an isolated local workspace. | Simulated chat presented as a live assistant conversation. |

## Visual system

- **Type:** neutral system grotesk for dense data; a tight serif accent only for
  the weekly title. No network font dependency.
- **Colour:** dark paper, warm-white text and muted green-grey metadata. State
  is written in text; a white mark supplements it.
- **Layout:** the mine photograph only lives beyond the outer margin. One
  centred dark-paper application sheet contains the header, week title and a
  centred, bounded Gantt. Ticket information appears in a centred modal so
  the schedule keeps its spatial context.
- **Surface:** the Gantt is not a card inside a page; it is the main panel's
  central native timeline. Its bars and arrows make the dependency order
  legible; Howie controls status and detail rather than exposing chart edits.
- **Motion:** 160--220ms opacity/translate transitions; reduced-motion disables
  them.

## Anti-slop constraints

- No website header, headline, or controls outside the inset application panel.
- No metric-card wall above the plan.
- No generic purple gradient, neon glow, or faux-terminal chrome.
- No developer-local wording in the `This week` view.
- Evals is visibly a proof view and explicitly states that it records local simulator events, not a live model chat.
- Status colour supplements an explicit text label; it never carries meaning by
  itself.
