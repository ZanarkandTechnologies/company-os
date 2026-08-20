---
name: company-onboard
description: "Onboard an SME by mapping its existing tools into one Hermes company workspace context and verifying each selected connection."
tier: 2
group: operations
source: local
template_uses:
  skill-template: "0.3.2"
  skill-qa-checklist: "0.1.0"
  hermes-company-workspace: "0.1.0"
eval: evals/evals.json
qa_checklist: qa_checklist.md
---

# Hermes Company OS

## Context

Use when an SME owner wants Hermes to understand and operate the company's
existing stack. Chat is the setup interface. The durable output is one
workspace-scoped `.hermes.md`; provider skills, CLIs, and MCPs continue to own
authentication and API mechanics.

The workspace file maps five stable company surfaces—Work, People, Knowledge,
Communications, and Decisions—to the real platforms, interaction routes, source
links, and plain-language structure the company already uses. It is an index,
not a copied database. Do not create intermediary company component skills
unless a later repeated procedure independently justifies one.

Connection state and setup evidence are mutable, so keep them in a separate
ticket-local onboarding receipt rather than `.hermes.md`. Never put credentials
or tokens in either artifact.

## Skill Signature

```text
onboard_company_workspace(company_name, company_description, current_stack)
  -> workspace_context + connection_receipt + unresolved_next_step
state: reads(existing .hermes.md, available skills/CLIs/MCPs, bounded provider metadata);
       writes(ticket-local receipt and an owner-reviewed workspace context)
gates: inspect(owner consent); install(owner review); external write(explicit approval)
routes: assets/templates/company-workspace.hermes.md | provider-owned connectors
fails: credential capture; broad account crawl; guessed authority; duplicated company configuration
```

<!-- BEGIN FARPLANE_IMPORTANT_CHECKLIST -->
## Todo List

- [ ] 1. Ask once: "What is your current stack?"
- [ ] 2. For every declared platform, find an installed skill, CLI, or MCP route
      and run its cheapest identity/status check plus one bounded read.
- [ ] 3. Ask only for business meaning that cannot be derived safely: authoritative
      sources, important links, structure, exclusions, and write authority.
- [ ] 4. Map every relevant source into Work, People, Knowledge, Communications,
      or Decisions. One platform may supply several surfaces; one surface may
      contain several platform rows.
- [ ] 5. Copy `assets/templates/company-workspace.hermes.md`, replace the company
      name and description, fill the source rows, and remove template comments
      and unused placeholders.
- [ ] 6. Preview the complete `.hermes.md` with the owner before installing it in
      the dedicated company workspace.
- [ ] 7. Start a fresh Hermes session from that workspace and run at least one
      representative lookup through every connected platform route.
- [ ] 8. Close with configured, blocked, and deferred tools plus the single next
      action. Keep dynamic health evidence in the receipt.
<!-- END FARPLANE_IMPORTANT_CHECKLIST -->

## Template Rules

- Frontmatter follows the repository template convention. Hermes strips it
  before prompt injection; it remains useful for source ownership and versioning.
- `{{COMPANY_NAME}}` and `{{COMPANY_DESCRIPTION}}` are the only required scalar
  placeholders. Source rows are filled conversationally rather than parsed into
  another configuration schema.
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

## Proof

- Run `python3 -m unittest discover -s skills/company-onboard/tests`.
- Validate both eval JSON files with `python3 -m json.tool`.
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
  template_version: "0.1.0"
  tools:
    configured: []
    blocked: []
    deferred: []
  representative_checks: []
  writes_performed: []
  next_action:
```
