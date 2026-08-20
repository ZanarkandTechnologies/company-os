---
name: company-os-onboarding
description: "Onboard a company into Hermes by connecting its current tools, discovering its operating sources, and installing a reviewed .hermes.md company map."
tier: 2
group: operations
source: local
template_uses:
  skill-template: "0.3.2"
  skill-qa-checklist: "0.1.0"
  hermes-company-workspace: "0.2.0"
eval: evals/evals.json
qa_checklist: qa_checklist.md
---

# Company OS onboarding

## Context

Use when a company wants Hermes to work through its existing tools. Chat is the
setup interface. The durable output is one workspace-scoped `.hermes.md`;
provider skills, CLIs, and MCPs continue to own authentication and API
mechanics. Read `qa_checklist.md` before starting and apply it again before
completion.

The workspace file maps five stable company surfaces—Work, People, Knowledge,
Communications, and Decisions—to the real platforms, interaction routes, source
links, and plain-language structure the company already uses. It is an index,
not a copied database. Do not create intermediary company component skills
unless a later repeated procedure independently justifies one.

This file is durable operating context, not agent memory and not a second
database. Connection state and setup evidence are mutable, so keep them in a
separate onboarding receipt. Never put credentials or tokens in either file.

## Skill Signature

```text
onboard_company(company_name, company_description, company_timezone, current_stack, workspace)
  -> workspace/.hermes.md + connection_receipt + operating_gaps + next_action
state: reads(existing .hermes.md, available skills/CLIs/MCPs, bounded provider metadata);
       writes(ticket-local receipt and an owner-reviewed workspace context)
gates: inspect(owner consent); install(owner review); external write(explicit approval)
routes: scripts/onboard_company.py | provider-owned connectors | optional channel skills
fails: credential capture; broad account crawl; guessed authority; duplicated company configuration
```

<!-- BEGIN FARPLANE_IMPORTANT_CHECKLIST -->
## Todo List

- [ ] 1. Show `Stage 1/7 — Company`: ask for the company name and a short
      description only when they are not already known. Resolve one IANA
      company timezone before time-bounded automations are enabled.
- [ ] 2. Show `Stage 2/7 — Stack`: ask once, "What is your current stack?" Do
      not walk through a catalog of tools or ask what each tool is for yet.
- [ ] 3. Show `Stage 3/7 — Connections`: for every declared platform, find one
      installed skill, CLI, or MCP route and run its cheapest identity check
      plus one bounded read. Use the route that works; do not make connector
      type a product decision for the owner.
- [ ] 4. Show `Stage 4/7 — Discovery`: inspect shared roots, databases, labels,
      or folders narrowly enough to propose the operating map. Ask for exact
      links when automatic discovery is unavailable or the owner wants to
      constrain scope.
- [ ] 5. Show `Stage 5/7 — Operating map`: map sources into Work, People,
      Knowledge, Communications, and Decisions. Recommend missing projects and
      tasks, decision records, resources, or repeatable procedures as gaps; do
      not require the company to reorganize before the first useful install.
- [ ] 6. Show `Stage 6/7 — Review`: run `scripts/onboard_company.py init` to
      stage the template, fill its rows conversationally, run `check`, preview
      the complete file, and install it only after owner review.
- [ ] 7. Show `Stage 7/7 — Proof`: start a fresh Hermes session and run one
      representative lookup per configured platform. Return configured,
      blocked, and deferred routes plus one next action.
- [ ] 8. Only after core completion, offer optional operating channels. Route a
      Notion comment channel to the peer `notion-webhook-onboarding` skill and
      ask for its agent mention there, not during core Company OS onboarding.
<!-- END FARPLANE_IMPORTANT_CHECKLIST -->

## Template Rules

- Frontmatter follows the repository template convention. Hermes strips it
  before prompt injection; it remains useful for source ownership and versioning.
- `{{COMPANY_NAME}}`, `{{COMPANY_DESCRIPTION}}`, and `{{COMPANY_TIMEZONE}}` are
  the only required scalar placeholders. Source rows are filled conversationally
  rather than parsed into another configuration schema.
- In a Work row, keep the data-source link, applicable template link, covered
  record types, type property, and comment policy beside the route they govern.
- Duplicate a Markdown table row for additional platforms. Delete unused rows,
  onboarding comments, and empty optional sections before installation.
- Store stable platform names, route names, source links, structural guidance,
  and authority boundaries. Do not store connection health or secrets.
- Keep the rendered file comfortably below Hermes's context-file size limit;
  detailed procedures belong in skills and detailed content stays in its source.

## Gotchas

- `.hermes.md` wins over `AGENTS.md` in Hermes's first-match context loading;
  install it only in a dedicated company workspace whose required context it owns.
- Start a new session after editing `.hermes.md`; an existing session keeps its
  startup context snapshot.
- A reachable link proves access, not business authority. Keep unclear sources
  out of the rendered file and record them as blocked or deferred in the receipt.
- Automatic mapping is a proposal. The owner confirms authoritative sources and
  write boundaries before installation.
- Do not treat a failed optional webhook or chat channel as a failed Company OS
  installation.

## Proof

- Run `python3 -m unittest discover -s skills/company-os-onboarding/tests -v`.
- Validate both eval JSON files with `python3 -m json.tool`.
- Run `python3 skills/company-os-onboarding/scripts/onboard_company.py check --file <staged-file>`.
- For a customer installation, verify a fresh Hermes session loads the rendered
  file and completes one representative lookup per configured platform.

## Reference Map

- [Company workspace template](assets/templates/company-workspace.hermes.md) —
  copy and fill during onboarding; install the rendered result as `.hermes.md`.
- [Google Drive connector notes](references/google-drive.md) — read only when
  Drive is selected and bounded discovery is needed.
- [Operator guide](../../docs/hermes-company-os-onboarding.md) — current
  end-to-end setup and ownership contract.

## Output

```yaml
company_os_result:
  workspace_context_path:
  template_version: "0.2.0"
  tools:
    configured: []
    blocked: []
    deferred: []
  representative_checks: []
  writes_performed: []
  next_action:
```
