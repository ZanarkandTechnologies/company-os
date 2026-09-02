---
template_id: company-os-documentation-request
template_version: "1.1.0"
---

Each generated artifact must begin with this routing frontmatter:

```text
---
artifact_type: documentation_request
work_id: "{{WORK_ID}}"
source_provider: "{{SOURCE_PROVIDER}}"
provider_record_id: "{{PROVIDER_RECORD_ID}}"
source_reference: "{{SOURCE_REFERENCE}}"
source_url: "{{SOURCE_URL_OR_EMPTY}}"
---
```

# Documentation request

<!-- PM Daily output: documentation request body

Write one concise comment for a completed Work item that is missing important
context. The comment must show what is already understood, identify exactly what
is missing, explain why it matters, and name where the owner should add it.

Writing rules:
- Ask only questions that affect understanding, reuse, accountability, or proof.
- Do not ask for cosmetic labels or generic "more detail".
- Do not repeat facts already present in the ticket.
- Ask in a direct, helpful tone.
- Refer to the exact ticket section to update.
- When the completed Work entry has no usable outcome or evidence, say so
  directly and ask the owner to add both.

Render the routing frontmatter followed by only the comment below. Do not include
template instructions or an application receipt. -->

I understand that {{KNOWN_OUTCOME_OR_DECISION}}.

What is still missing: {{IMPORTANT_MISSING_CONTEXT}}.

Please add this under {{EXACT_SECTION}}:
1. {{PRECISE_QUESTION}}

Why this matters: {{OPERATIONAL_REASON}}.

<!-- GOLDEN EXAMPLE — replace every fact below.
I understand that the reconciliation sheet became the release gate.

What is still missing: the ticket does not explain why this option was chosen.

Please add this under Notes > Decision:
1. Why was the reconciliation sheet selected over the other options considered?

Why this matters: we cannot safely reuse the release rule without its rationale.
END GOLDEN EXAMPLE -->

<!-- EMPTY COMPLETION VARIANT — render this body instead of the standard body
when no outcome or evidence is available. It requires only the source reference.
This Work item is complete, but its outcome and evidence are not recorded.
Please add both here: {{SOURCE_REFERENCE}}.
END EMPTY COMPLETION VARIANT -->
