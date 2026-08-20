---
ticket_id: TASK-0002
kind: design-contract
status: accepted-by-operator-goal-request
---

# Dependency views design contract

## Design language

Continue the monochrome, database-first Company Plan. Views are different
projections, not different products: no new graph editor, colourful flowchart
or separate Kanban state.

## Declared screens

1. **Timeline:** date rows retain a compact `Blocked by` cue and use the
   existing inspector for the exact requirement chain.
2. **Table:** database properties include Status, Owner, Due, Blocked by and
   Unblocks; selecting a ticket opens its dependency details.
3. **Dependencies:** a dense, accessible dependency list grouped by producer:
   `TASK-1001 geo-report → TASK-1002 funding-brief, TASK-1003 model-input`.
   It may use connectors only where they clarify a real producer/consumer edge.
4. **Human request:** a labelled Telegram-preview card states the exact
   question, ticket and requirement. Development simulation controls are
   visually separated and explicitly local-only.

## Non-goals

No drag/drop graph authoring, inbox, unrestricted chat UI, contact editor or
claim that the POC delivered a Telegram message.
