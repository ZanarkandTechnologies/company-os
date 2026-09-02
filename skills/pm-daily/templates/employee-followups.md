---
template_id: company-os-employee-followups
template_version: "1.1.0"
---

Each generated artifact must begin with this routing frontmatter:

```text
---
artifact_type: progress_followup
work_id: "{{WORK_ID}}"
source_provider: "{{SOURCE_PROVIDER}}"
provider_record_id: "{{PROVIDER_RECORD_ID}}"
source_reference: "{{SOURCE_REFERENCE}}"
source_url: "{{SOURCE_URL_OR_EMPTY}}"
---
```

# Employee progress follow-up

<!-- PM Daily output: progress follow-up body

Write one short progress question about a threatened weekly Project target.
By default it will be posted on each exact linked Work item; an explicitly
configured employee-follow-up channel may deliver the same text directly.

Writing rules:
- Begin with the Project target and due date, not a vague "checking in".
- State the observed progress and why the target appears at risk.
- Ask what changed, the current blocker, the recovery plan, and the date the
  owner can now commit to.
- Address the owner by name when it is known from the bounded source context.
- Do not ask documentation-quality questions already handled on the ticket.
- Do not exaggerate unknown causes, progress, or dates.
- When the active Work entry has no usable update, ask for its current status,
  next action, and blocker without inventing a risk explanation.

Render the routing frontmatter followed by only the message below. Do not include
template instructions or a delivery receipt. -->

{{OWNER}}, the Project target "{{TARGET}}" is due {{DUE_DATE}}.

Current evidence: {{PROGRESS_AND_RISK_BASIS}}.

Please reply with:
1. What changed since the last update?
2. What is blocking the remaining work?
3. What is the recovery plan and revised commitment date?

Update the linked Work item here: {{SOURCE_REFERENCE}}.

<!-- GOLDEN EXAMPLE — replace every fact below.
Jun, the Project target "Complete all three supplier comparisons" is due Friday.

Current evidence: only one comparison is complete, and the remaining two have
not changed since 21 August. The supplier normalisation rule is still unresolved.

Please reply with:
1. What changed since the last update?
2. What is blocking the remaining comparisons?
3. What is the recovery plan and revised commitment date?

Update the linked Work items here: TASK-103 and TASK-104.
END GOLDEN EXAMPLE -->

<!-- EMPTY ACTIVE WORK VARIANT — render this body instead of the standard body
when owner, target, due date, or progress is unavailable. It requires only the
source reference.
No usable update is recorded. Please add the current status, next action, and
blocker here: {{SOURCE_REFERENCE}}.
END EMPTY ACTIVE WORK VARIANT -->
