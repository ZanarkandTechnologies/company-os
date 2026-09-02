# Data readiness preflight

Use only the configured provider's read-only tools. Make no provider changes.

{{PROVIDER_INSTRUCTION}}

Use these canonical names when present: `id`, `name`, `status`, `project`,
`owner`, `due_date`, `type`, `department`, and `body_markdown`.

Return JSON only, with no record names, IDs, URLs, email addresses, excerpts,
or raw provider content. Use this shape:

{{OUTPUT_SCHEMA}}

Required fields for inspection: {{REQUIRED_FIELDS}}.
Required relations with at least one populated value: {{REQUIRED_RELATIONS}}.
Optional fields: {{OPTIONAL_FIELDS}}.
