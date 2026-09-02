---
template_id: company-os-person
template_version: "0.5.0"
name: "{{PERSON_NAME}}"
person_id: "{{PERSON_ID}}"
department: "{{DEPARTMENT}}"
role: "{{ROLE}}"
status: "{{STATUS}}"
manager: "{{MANAGER}}"
preferred_contact_channel: "{{PREFERRED_CONTACT_CHANNEL}}"
approved_contact_channels: "{{APPROVED_CONTACT_CHANNELS}}"
contact_endpoint: "{{APPROVED_ROUTE_ALIAS}}"
contact_instructions: "{{CONTACT_INSTRUCTIONS}}"
timezone: "{{TIMEZONE}}"
expertise: "{{EXPERTISE}}"
---

# {{PERSON_NAME}}

<!-- This is the canonical Person contract. Keep routing and expertise in
frontmatter so an agent can filter People rows before it reads operating context.
`contact_endpoint` stores a safe approved route alias resolved by workspace
configuration; it is not a guessed or seed-embedded email address, username, or
phone number. A route alias grants no send authority by itself.

The directory fields may project to a shared People database. The two memory
sections are private local context and must never sync back to a shared People
page or be used to infer personality, intent, effort, or a performance rating. -->

## Persistent operating memory

<!-- Long-term baseline. Keep only accepted cross-interval context: known
handoff boundaries, durable collaboration constraints, demonstrated expertise,
and deduplicated completed outcomes. Weekly consolidation appends accepted
observations; it never creates a rating or speculative profile.

GOLDEN EXAMPLE — replace every fact below; it demonstrates useful detail.
**Preferred contact channel:** Email
**Approved contact channels:** Email; Notion comment
**Contact endpoint:** email.eval-ops-lead
**Contact instructions:** Use email for owner follow-ups; do not use messaging
for urgent escalation. **Timezone:** Asia/Kuala_Lumpur
**Expertise:** replenishment variance; store-count controls; operational
decision briefs

Best for diagnosing replenishment variance and turning store-count evidence into
an operations decision. Escalate cross-department decisions to the Operations
Lead.
END GOLDEN EXAMPLE -->

{{OPERATING_NOTES}}

## Latest weekly evidence

<!-- Short-term interval context. Weekly replaces this section with every
accepted artifact-producing outcome for this Person plus material unresolved
actions, deduplicated by Work and artifact. Preserve source links, receiver
acceptance, workflow key, and sourced active/wait time for comparison against
persistent memory. Open, stale, or question-pending Work remains weekly context
rather than a durable claim. -->

{{LATEST_WEEKLY_EVIDENCE}}
