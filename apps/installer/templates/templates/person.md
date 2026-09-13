---
{"output":"templates/person.md","runtime":{"template_id":"company-os-person","template_version":"0.6.0","name":"{{PERSON_NAME}}","person_id":"{{PERSON_ID}}","department":"{{DEPARTMENT}}","role":"{{ROLE}}","status":"{{STATUS}}","manager":"{{MANAGER}}","preferred_contact_channel":"{{PREFERRED_CONTACT_CHANNEL}}","approved_contact_channels":"{{APPROVED_CONTACT_CHANNELS}}","contact_endpoint":"{{APPROVED_ROUTE_ALIAS}}","contact_instructions":"{{CONTACT_INSTRUCTIONS}}","timezone":"{{TIMEZONE}}","expertise":"{{EXPERTISE}}"},"refs":["organization.grouping"]}
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

Use only supplied contact channels, approved route aliases, expertise and
escalation authority. A capability or example never establishes a person's
contact preference or grants permission to contact them. -->

{{OPERATING_NOTES}}

## Latest weekly evidence

<!-- Weekly replaces this section with accepted outputs and material blockers.
- Deduplicate by Work and artifact; preserve source links and acceptance scope.
- State the dependency, attempted remedy and smallest proposed unblocking action.
- Use a supplied decision owner and observable completion signal; do not invent authority.
- Keep open Work as interval context, not a durable claim about the person.
- Do not rank people or compare individual task speed against a baseline.
-->

{{LATEST_WEEKLY_EVIDENCE}}
