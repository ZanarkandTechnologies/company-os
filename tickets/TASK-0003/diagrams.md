---
status: companion
source: ticket.md
blocks_approval: false
canonical_contract: ticket.md
generated_by: diagramming
---

# Howie real-integration POC — alignment diagram

**Approval question:** are we building one real, personal development loop —
Kenji's phone and a fake-data Drive folder — without mistaking it for the
customer's production workspace?

## Before — what we have now

```mermaid
flowchart LR
  classDef keep fill:#e7e5e4,stroke:#78716c,color:#1c1917
  classDef problem fill:#fee2e2,stroke:#b91c1c,color:#7f1d1d

  meeting["Meeting fixture"]:::keep
  drive["Local Drive mock"]:::problem
  manager["Deterministic manager\nfilesystem tickets"]:::keep
  dashboard["Dashboard + eval trace"]:::keep
  phone["WhatsApp / real Drive\nnot connected"]:::problem

  meeting --> manager
  drive --> manager
  manager --> dashboard
  phone -. no real route .-> manager
```

## After — the POC we are proposing

```mermaid
flowchart LR
  classDef keep fill:#e7e5e4,stroke:#78716c,color:#1c1917
  classDef changed fill:#fef3c7,stroke:#b45309,color:#1c1917
  classDef added fill:#dcfce7,stroke:#15803d,color:#14532d
  classDef guard fill:#dbeafe,stroke:#2563eb,color:#172554
  classDef outside fill:#fee2e2,stroke:#b91c1c,color:#7f1d1d

  phone["Kenji's own WhatsApp\npaired self-chat"]:::added
  gate["1. Exact WhatsApp allowlist\nfile · skills · filtered Drive"]:::guard
  hermes["Howie / Hermes\nsame source profile\ndedicated test workspace"]:::changed
  tickets["Canonical filesystem tickets\n+ ticket-local progress"]:::keep
  mcp["2. Official Google Drive MCP\nminimum tool allowlist"]:::added
  root["Dedicated Drive dev identity\none fake-data root"]:::guard
  directory["Private employee directory\ncontact + route policy"]:::guard
  sender["3. Manual delivery worker\nexplicit send gate"]:::changed
  proof["4. Dashboard\nactual receipts + trace"]:::keep
  production["Customer VPS, customer Drive,\nemployees, cron, broad search"]:::outside

  phone -->|"1 inbound"| gate --> hermes
  tools["file · skills\nmcp-googledrive"]:::guard
  tools -. "only available toolsets" .-> hermes
  hermes -->|"2 writes ticket/progress files"| tickets
  hermes -->|"3 search/read/create"| mcp --> root
  tickets -->|"4 due draft"| sender
  directory -->|"5 resolve allowed target"| sender
  sender -->|"6 hermes send with explicit gate"| phone
  tickets --> proof
  root --> proof
  sender --> proof
  hermes -. "ordinary same-thread response" .-> phone
  production -. "not connected" .-> tickets
```

## Critical-path trace

```mermaid
sequenceDiagram
  participant K as Kenji's phone
  participant H as Howie / Hermes
  participant T as Ticket filesystem
  participant E as Employee directory
  participant S as Delivery worker
  participant D as Fake-data Drive root
  participant V as Dashboard proof

  K->>H: 1. Structured meeting summary
  H->>T: 2. Create/update canonical tickets
  H->>D: 3. Read source or create fake artifact
  T->>S: 4. Due delivery draft
  S->>E: 5. Resolve permitted target
  S-->>K: 6. Explicit-gate chase
  T-->>V: 7. Ticket + progress receipt
  D-->>V: 8. Drive reference
  S-->>V: 9. Delivery receipt
  H-->>K: 10. Ordinary same-thread status response
```

## Legend

- **Gray:** existing, canonical component.
- **Amber:** changed ownership/behavior.
- **Green:** real integration added for the development POC.
- **Blue:** hard guard that keeps the proof bounded.
- **Red:** explicitly outside this POC.

## Short notes

1. The **ticket filesystem remains the task board**; Drive keeps shared fake
   artifacts, not a second task system.
2. The **Google Drive connector is real**, but it runs under a development
   identity that has only the fake-data root shared with it.
3. This proves a one-person integration loop. It does **not** prove the
   enterprise permission model; that needs isolated production workspaces.
