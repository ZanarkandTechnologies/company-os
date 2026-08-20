---
name: daily-documentation-check
description: Check Notion work records edited today against the company’s configured template and post or propose one focused, deduplicated source comment for missing documentation.
---

# Daily Documentation Check

## Context

Use `.hermes.md` as the routing index and the official `ntn` CLI for Notion.
The script owns bounded reads, local-day boundaries, deduplication, and writes;
the agent judges whether each template requirement is meaningfully answered.

```text
daily_documentation_check(company_context, local_day?, write_policy)
  -> checked_records + comments_or_proposals + configuration_gaps + receipt
reads: .hermes.md Work rows, Notion records, template pages, source comments
writes: source comments only when the Work row approves internal comments
```

## Todo List

- [ ] 1. Read `.hermes.md` and bind one Work source.
  - [ ] Require an IANA `company_timezone`, Notion data-source link or ID,
    template page link or ID, covered record types, and comment policy.
  - [ ] Return `configuration_gap: unmapped_template` rather than inventing a
    rubric when a record type has no template.
- [ ] 2. Run the bounded fetch for the company-local day.
  - [ ] Write a temporary JSON map from each configured record type to its
    template page ID, then pass it with the source ID, type property, timezone,
    and optional `--date` to `scripts/notion_documentation_check.py fetch`.
  - [ ] Stop with a source gap if the query, template, comments, or record read
    fails. Never replace a failed read with model memory.
- [ ] 3. Compare each record with the configured template.
  - [ ] Name only required information that is absent or unusably vague.
    Treat non-applicable prompts as non-applicable; do not police style.
  - [ ] Ask for the smallest useful addition. “Add the next action and due
    date” passes; “Add more detail” fails because it is not actionable.
- [ ] 4. Build one comment request per incomplete record.
  - [ ] Include `page_id`, `template_ref`, `missing_items`, and a concise
    question in a JSON file outside the repository.
  - [ ] Run `comment --input <file>` for a proposal. Add both `--apply` and
    `--comment-policy approved` only when `.hermes.md` explicitly approves
    internal comments; the script rejects every other write attempt.
  - [ ] Accept `duplicate` as a successful no-write result.
- [ ] 5. Return one receipt with the UTC window, checked/complete/incomplete
  counts, posts, proposals, duplicates, configuration gaps, source gaps, and
  whether the bounded query was partial.

## Commands

Create the temporary map from the Work row. Several types may point to the
same template:

```json
{"templates":{"Task":"WORK_ITEM_TEMPLATE_ID","Issue":"WORK_ITEM_TEMPLATE_ID","Meeting":"WORK_ITEM_TEMPLATE_ID"}}
```

```bash
python3 skills/daily-documentation-check/scripts/notion_documentation_check.py fetch \
  --data-source-id "$DATA_SOURCE_ID" --template-map /tmp/hermes-template-map.json \
  --type-property Type --timezone "$COMPANY_TIMEZONE"

python3 skills/daily-documentation-check/scripts/notion_documentation_check.py comment \
  --input /tmp/hermes-documentation-comment.json --comment-policy approved --apply
```

`NOTION_TOKEN` is canonical. The script exposes it as `NOTION_API_TOKEN` only
inside the `ntn` subprocess. Never track IDs, tokens, content, or drafts.

## Gotchas

- Do not infer company timezone from the machine timezone.
- Task, Issue, and Meeting can share one Work Item template.
- Comments can change edit time. Deduplication uses page ID + template +
  normalized missing items, not edit time.
- `has_more: true` means `partial`; do not claim full coverage.
- Do not edit records or route documentation comments into Weekly.

## Proof

Run the script tests and skill validator. Verify proposal, duplicate,
timezone-boundary, and partial-query behavior before scheduling writes.

## Output

Return source/template locators, local date and UTC window, one result per
record, comments/proposals, and explicit gaps and `partial` fields.
