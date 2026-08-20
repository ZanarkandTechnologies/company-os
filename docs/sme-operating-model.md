---
title: Hermes SME operating model
status: active
owner: HermesCorp
updated_at: 2026-08-17
---

# Hermes SME operating model

Hermes does not treat an agent's private memory as company memory. Agents are
replaceable runtimes. Durable company state stays in systems with an explicit
owner, update path, provenance, and audit contract.

## The three durable systems

| System | Owns | Updated by | Queried by | Does not own |
| --- | --- | --- | --- | --- |
| Connected applications | Operational records and transactions in the apps people already use | Humans directly, or agents working through reviewed integrations | People, integrations, and bounded agents | Company-wide facts, decision rationale, reusable procedures |
| Company wiki | Sourced business facts, definitions, context, and current reference material | A separate knowledge workflow that ingests, checks, and refreshes facts | Humans and agents at task time | Approval authority, responsibility assignment, process execution |
| Decision ledger | Decisions, rationale, scope, approver, accountable owner, dates, review state, and supersession | Named decision owners and approvers | Auditors, operators, and the procedure compiler | Raw facts, application transactions, unapproved procedures |

Skills are a compiled runtime layer, not a fourth memory store. Only an approved
process or procedure may be dreamed into a skill. The skill carries source
decision references, version, inputs, outputs, guardrails, and evaluation proof.

## Change router

```text
route_company_change(kind, payload) -> owner + required_record

kind = app_change
  -> connected application / integration platform

kind = fact
  -> company wiki entry with source and freshness

kind = decision
  -> decision ledger entry with approval and responsibility

kind = procedure
  -> approved decision -> procedure compiler -> versioned skill + evals
```

## Record contracts

### Wiki fact

```yaml
fact_id:
statement:
source_refs: []
observed_at:
owner:
confidence:
review_at:
supersedes:
```

### Decision

```yaml
decision_id:
title:
context:
options_considered: []
decision:
rationale:
scope:
approved_by:
responsible_owner:
decided_at:
review_at:
supersedes:
status: proposed | approved | superseded | rejected
```

### Compiled skill

```yaml
skill_id:
version:
source_decision_refs: []
procedure_owner:
inputs: []
outputs: []
guardrails: []
approval_gates: []
eval_contract:
```

## Allowed flows

1. Humans keep updating their business applications as normal. An agent may
   help, but the application or integration platform remains the owner.
2. Facts enter the wiki with provenance and freshness. Agents query the wiki;
   they do not silently retain facts as durable private memory.
3. Decisions enter the ledger before they change responsibility, policy, or a
   procedure. The named approver and accountable owner remain visible.
4. Approved procedures compile into skills. Skill execution may query the wiki
   and act through integrations, but it cannot rewrite the originating decision.
5. A superseding decision can trigger a new skill version. Historical decisions
   and skill versions remain auditable.

## Non-goals

- A universal agent-memory database.
- Copying every application record into the wiki.
- Treating chat transcripts as approvals.
- Letting a generated skill become policy without a source decision.
- Hiding responsibility behind an autonomous-agent identity.
