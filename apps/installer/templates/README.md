# Installer template packages

- Edit questions, recommended options, Custom fields and help in [../questions.json](../questions.json).
- These packages own prompt text, replacement tags and complete skill support files—not the questionnaire.
- Generated automation/skill files are outputs; edit questions or templates and regenerate. There is no synchronization between the two source files.
- Generation is local and deterministic; it does not connect providers, create profiles, install or schedule jobs.
- Credentials stay in the runtime profile, never answers or reusable templates.

## Metadata syntax

- Each template starts with `---`, one JSON object, then `---`; JSON is valid YAML.
- `output` names a workspace-relative destination. `runtime` becomes generated frontmatter.
- `refs` lists stable question IDs from `questions.json`. Do not put question definitions in template headers.
- Questions have `id`, `label`, `kind`, `order`, `default`, optional `help`, and `required`.
- Kinds: `text`, `timezone`, `select`, `multi`. Empty multi-selection means no source/destination.
- Text fields remain editable text; timezone uses its selector. Only declared option questions render choice menus. Do not invent presets or Custom modes for plain fields.
- Only company name and operating context are plain text. Policy questions require choices; matching includes recommendations and inline Custom. The loader rejects option lists attached to text/timezone fields instead of hiding them.
- Options have stable `id`, `label`, `render`, `fields`, and `providers`.
- Custom access options use required `provider` with `provider_id` validation and `providers_from: provider`; their rendered rows show that provider explicitly. IDs identify existing capabilities, not automatic integration installation.
- `target_kind: record_rule` marks exact cached-record routing rules rather than literal target URLs.
- Package metadata `when: {question: organization.grouping, options: [project]}` omits a whole package outside that selection.
- Fields have `id`, `label`, `required`, optional `default`, and optional validation (`positive_integer`, `memory_pattern`, `url`, `sync_sections`). Operating-memory sync requires explicit allowed section names.
- Option render text uses `{field_id}`; source/destination fields hold access, target and instructions.
- Body placeholders use `${answer__question_id}` with dots replaced by underscores.
- Shared variant maps select identity, names, paths and report hierarchy from `organization.grouping`.
- `${memory_current}` and `${memory_next}` are validated selected-mode memory patterns supplied by the compiler.
- Conditional blocks use `<!-- when:question.id=option1,option2 -->` and `<!-- endwhen -->`; nested blocks are permitted. Matching any selected ID includes the block.
- Unselected conditions disappear completely. Runtime placeholders such as `<week>` and `{{WEEK}}` remain for the operating agent.
- Custom text may specialize fixed evidence/safety rules but cannot grant access or silently replace them.

## Package boundary

- `automations/`: Daily collection and Weekly freezing, local rendering, optional provider propagation.
- `skills/pm-daily/`: JSON extraction plus complete memory/message templates.
- `skills/pm-weekly/`: JSON consolidation plus complete report templates.
- `templates/`: shared Person, SOP, issue and decision contracts.
- `workspace.hermes.md`: generated identity and context; automation prompts own provider bindings.
- Preserve exact headings, JSON contracts, provenance, coverage and closure rules in both modes.
- A selected connector name is a requirement, not proof the connector is installed or authorized.
- Existing memory is never migrated or deleted by changing grouping.
- Full design and acceptance boundaries: [generation spec](../../../docs/features/prompt-generation.md).

## Editing and applying

- Run `python3 setup.py features` to edit saved values or resume a draft.
- Run `python3 setup.py questions` to view the validated editable JSON question list.
- Run `python3 setup.py generate` to preview; add `--apply` to write source files.
- Add `--output-dir /path/to/package` to `features` or `generate` to choose another folder. Answers stay at the source; output hashes are tracked per destination.
- Multi-select input supports repeated options with distinct fields: Ctrl+N adds and Ctrl+X removes an entry. Saved `entries` supplements the first option's `inputs`.
- Import profile answers explicitly with `features --import-answers PATH`.
- Manual changes block regeneration; explicit `--adopt` backs up replaced files under private `config/generation-backups/`.
- An incomplete generation marker blocks installation until regeneration succeeds.
- Installation is separate; selecting a provider never certifies read/write access.
- Providers unknown to connection certification remain explicitly uncertified; generation can still describe their existing tools.
