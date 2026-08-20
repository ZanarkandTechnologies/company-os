---
template_id: company-os-decision
template_version: "0.2.0"
kind: company-record-template
record_type: decision-precedent
status: active
owner: HermesCorp
promotion_gate: precedent-value
opens_with:
  - outcome
  - why
required_properties:
  - decision
  - projects
  - proposer
  - approver
  - decided_at
  - status
---

# {{DECISION}}

> **Outcome**
>
> _State the Decision now in force and the behavior it changes._
>
> **Why**
>
> _Explain why this deserves precedent status instead of staying in Task or Report context._

> **Promotion gate**
>
> Keep this only when the Decision is costly to reverse, affects several people,
> establishes precedent, resolves a recurring tradeoff, or explains an important
> constraint.

## Context

<!-- Problem, constraints, and affected projects. -->

## Rationale

<!-- Why this option won and which alternatives were rejected. -->

## Authority

<!-- Proposer, approver, decision date, and current status. -->

## Precedent

<!-- When future work should follow or reconsider this decision. -->

## Evidence and relationships

<!-- Related work items, reports, resources, people, and prior decisions. -->
