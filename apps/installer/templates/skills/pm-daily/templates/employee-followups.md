---
{"output":"skills/pm-daily/templates/employee-followups.md","runtime":{"template_id":"company-os-employee-followups","template_version":"2.0.0"},"refs":["organization.grouping"]}
---

# Progress follow-up body

- Write one `messages[]` object with `type: progress_followup` in extraction JSON.
- Put routing IDs in the object's fields; never create frontmatter or a separate file.

- Include source_url only when supplied. Keep IDs in object fields/link destinations;
  use readable Work titles in message links.
- State the known context needed to explain ONE precise actionable question.
- Ask only for the missing answer affecting a supported next action/outcome.
- Never ask again for known status, blocker, next action, or owner.
- No generic checklist or empty-Work fallback; missing optional fields alone
  produce no message. Never invent a target, risk, date, or recipient.
- Example shape, replace with sourced facts:
  “The supplier comparison is waiting on column-map approval. Who can approve
  the attached map so comparison can proceed? Update [supplier comparison](source-url).”
- Do not output these instructions, placeholders, or a delivery receipt.
