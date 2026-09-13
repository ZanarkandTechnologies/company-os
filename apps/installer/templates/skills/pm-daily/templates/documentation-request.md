---
{"output":"skills/pm-daily/templates/documentation-request.md","runtime":{"template_id":"company-os-documentation-request","template_version":"2.0.0"},"refs":["organization.grouping"]}
---

# Documentation request body

- Write one `messages[]` object with `type: documentation_request` in extraction JSON.
- Put routing IDs in the object's fields; never create frontmatter or a separate file.

- Include source_url only when supplied. Keep IDs in object fields/link destinations;
  use readable Work titles in message links.
- State the understood outcome, ONE missing consequential fact, and why it matters.
- Ask one precise question; link the supplied provider URL or name the Work when absent. Name a destination
  section only if supplied; never invent a section.
- Judge the actual claimed outcome: meeting notes need not prove shipped work,
  and synthetic records need not prove a real client result.
- Do not request known facts, cosmetic completeness, optional owner/date fields,
  or generic outcome/evidence without a supported consequential claim.
- Example shape, replace with sourced facts:
  “Reconciliation is recorded as accepted, but its approving receiver is not
  identified. Who approved it? Record the approval on [reconciliation](source-url)
  so the acceptance can be verified.”
- Do not output these instructions, placeholders, or an application receipt.
