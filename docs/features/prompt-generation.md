---
title: Installer-driven Daily and Weekly generation
status: implemented-local-verification
updated_at: 2026-09-13
profile: standard
entry_mode: customer-first
context_type: brownfield
---

# Installer-driven prompt generation

See [all four annotated template packages](../../apps/installer/templates/README.md) for the
prompt text and replacement tags. The editable questionnaire now lives separately in `apps/installer/questions.json`.

## Decision and scope

- Let the operator edit saved answers and regenerate reviewed instructions.
- Generate the two automation prompts and two PM skills together, with their matching templates.
- Use deterministic text substitution and selected fragments, not an LLM rewrite.
- Keep questions/options/help in one editable JSON list; templates contain replacement tags. Do not derive questions from prose, angle tags or template headers, and do not synchronize two question definitions.
- Emit only the chosen grouping and configured integrations. No runtime mode switches.
- Keep collection/bindings/rendering/propagation in automations; keep interpretation and JSON output in skills.
- Generate source locally; installation, scheduling and provider operations remain separate.
- Exclude a new runtime, generic plugin framework, new test suite, and automatic upstream publication.

```text
questions.json → saved answers → reviewed templates/fragments
                                           ↓
                                  preview complete bundle
                                           ↓
                               save generated source files
                                           ↓ explicit existing install
                                     Hermes profile
```

## Grounding: pre-implementation baseline

These observations describe the replaced installer, not its current behavior.

- `apps/installer/cli/flows/features.py` declares 21 feature questions plus three company questions.
- `configure_features(root)` saves `root/config/setup-answers.json` and a resumable draft beside it.
- Launch can pass the profile root; other setup routes pass the checkout. Resolve this split before generation becomes authoritative.
- State schema 4 stores `answers`, `selections`, `provider_requirements`, and `provider_targets`.
- `apps/installer/feature_setup.py::render_text` replaces existing `setup:` slots only; it does not assemble selected sections.
- Current Daily and both skills contain no slots. Weekly contains seven destination/delivery slots.
- The current flow renders three automations and workspace identity, not either skill. It derives `weekly.projects` but the current Weekly prompt has no matching slot.
- `selected_bindings` handles Multica targets only under `daily.work`; Discord is not handled there.
- Existing source/destination presets contain stale Notion-only routes and employee/baseline wording; do not treat old presets as the behavior authority.

## Existing question → generated owner

`DA` = Daily automation; `DS` = Daily skill; `WA` = Weekly automation; `WS` = Weekly skill.
Selections choose reviewed sections; entered text fills the selected section. Preserve current keys unless explicitly replaced below.

| Existing key | Current choices | Proposed generated owner and use |
| --- | --- | --- |
| `company.name` | Text | Workspace identity; WA report identity |
| `company.description` | Text | Workspace context supplied to both skills; no repeated company boilerplate |
| `company.timezone` | IANA selection | DA/WA frozen window and week rules; skills consume supplied dates |
| `memory.decisions` | Standard / Lightweight / Custom | DS retained decision detail; WS promotion detail; consequential-choice evidence gate stays fixed |
| `memory.employees` | Growth review / Delivery only / Custom | DS attribution and WS People progress/person memory; replace Growth review with Contributions and unblocking; never enable ratings |
| `memory.sops` | Baseline comparison / Procedure capture / Custom | DS SOP signals and WS consolidation; use Procedure capture by default, preserve approved baselines without forced timing comparisons |
| `daily.projects` | Notion / Custom; multi-select | DA inventory table; WA inventory binding derived from the same answer, not a second question |
| `daily.work` | Project-local Notion / Shared Notion / Multica / Custom; multi-select | DA Work collection rows and exact membership rules |
| `daily.meetings` | Inside Work / Separate Notion / Custom | DA meeting context rows; make multi-select |
| `daily.existing_memory` | Local default / Explicit local path / Custom | DA/DS/WA/WS consistent memory paths; validate workspace-contained paths, not arbitrary prose paths |
| `daily.people` | Notion People / No direct contacts / Custom | DA identity, roster and optional contacts; separate roster coverage from delivery permission |
| `daily.staleness` | Standard / Age threshold / Custom | DS follow-up trigger; seven days default, positive integer for age preset |
| `daily.progress_route` | Notion Work comment / Gmail / Telegram / WhatsApp / Custom; multi-select or none | DA propagation routes; replace Notion-only option with exact Work provider; preserve inline details |
| `daily.documentation_quality` | Standard / Evidence only / Custom | DS review criteria; require only consequential missing evidence, not every optional field |
| `daily.documentation_route` | Notion Work comment / Gmail / Telegram / WhatsApp / Custom; multi-select or none | DA documentation propagation routes; same provider-neutral rule |
| `weekly.reports_destination` | Private local / Google Drive / Custom | WA optional report copies; local rendering always retained |
| `weekly.sops_destination` | Private local / Google Drive / Custom | WA approved SOP copies only |
| `weekly.employee_memory_destination` | Private local / Private Google Drive / Custom | WA private person-memory copies only |
| `weekly.decisions_destination` | Private local / Google Drive / Custom | WA promoted decision copies only |
| `weekly.other_memory_destination` | Private local / Private Google Drive / Custom | WA issue-memory destination in v1; do not promise undefined artifact types |
| `weekly.report_recipients` | Gmail / Telegram / WhatsApp / Custom; multi-select or none | WA delivery rows; preserve separate recipients and no-delivery selection |
| `weekly_meeting.destination` | Disabled / Multica / Custom | Existing separate meeting automation; preserve answers, exclude from this four-prompt generation boundary |
| `weekly_meeting.template` | Operating review / Short agenda / Custom | Existing separate meeting automation; no implicit activation or modification |
| `weekly.project_memory_destination` | Private local / Notion Project records / Custom | WA selected-section sync to exact bound records; validate section names against the generated template |

## Missing questions and revised controls

| Proposed key | Question / shape | Affects |
| --- | --- | --- |
| `organization.grouping` | Project or Department; single choice | Both automations, both skills, paths and report templates |
| `organization.matching` | Describe canonical identity, exact relations and cross-platform matching; editable text | DA matching and WA hierarchy/identity resolution |
| `daily.context_sources` | Additional context: Discord, CRM, calendar, chats, Custom; multi-select, each with binding and fetch instructions | DA Step 1 rows; only installed/read-capable integrations selectable as ready |
| `automation.propagation` | Which cadences may propagate? Daily / Weekly / neither | Include provider subsections for selected cadences; no runtime flag |

- All source and destination questions support multiple selections, each with editable inline details.
- Identity and mutually exclusive policies remain single-select; they cannot simultaneously be Project and Department.
- Local-only is an empty external destination list, not another destination alongside Drive.
- Every source entry records provider/access method, exact target, and fetch instructions. Instructions include filters, relevant recursion, relation fields and scope exclusions.
- Matching text names the canonical source and Department relation/inventory when Department rollups are required. Stable IDs remain in caches, not invented from names.
- Custom entry text does not install an integration or grant write access. Missing capabilities remain setup blockers.
- Preserve inline editing, prefill, timezone selection and interrupted-draft recovery.
- Keep the 24-hour activity window, ISO week semantics, and evidence safeguards fixed in v1; do not add knobs without an operator need.

## Grouping contract

| Generated behavior | Project mode | Department mode |
| --- | --- | --- |
| Daily isolation | One packet and skill call per Project | One packet and skill call per Department |
| Packet | `{id, name, context}` | Same three fields; Department identity |
| Work attribution | Exact Project membership | Exact Department membership, direct or via an explicitly resolved Project relation |
| Extraction identity | `project_id`, `project_name` | `department_id`, `department_name` |
| Daily memory | `weeks/<week>/project-memory/project--<id>.md` | `weeks/<week>/department-memory/department--<id>.md` |
| Weekly input | Complete reporting Project set | Complete reporting Department set |
| Weekly reports | Project → Department → Company | Department → Company; no required Project reports |
| Next week | Active Project memory | Active Department memory |

- Department mode may retain Project labels as evidence; it never runs a hidden second Project pipeline.
- The table shows default memory paths. A custom memory location supplies one workspace-relative pattern containing week and unit identity; use it for both cadences, current and next week. Reject collisions, traversal and patterns missing either identity dimension.
- Generate one matching identity/path/type contract and selected memory template, not runtime union branches.
- Retain eight memory categories in either mode. Memory preferences change evidence/detail, not arbitrary JSON keys or required headings.
- Generate WS artifact allowlist and WA render ordering together. Department mode uses `next_week_department_memory` and removes `project_report` and `next_week_project_memory` types.
- Both modes retain visible People progress and Company Department summaries, including sparse/quiet known units.
- Missing hierarchy is an explicit gap, not an invented Department. Resolve the required hierarchy before accepting a complete generated setup.
- Changing grouping does not migrate or delete existing memory. Preview names the historical-input discontinuity; start a new selected-mode boundary or separately approve migration.

## Rendering versus propagation

- Always keep local rendering after skill JSON validation, including exact template headings, history preservation and read-back.
- Daily: fetch → cache → skill → render; append configured provider actions only when Daily propagation is selected.
- Weekly: freeze → skill → validate → render; append configured provider actions only when Weekly propagation is selected.
- Include freshness, duplicate, authority, conflict and uncertain-write checks with every generated propagation section.
- With propagation omitted, local extraction JSON can still contain proposed messages; no tool route executes them.
- Preserve the full executive Company report embedding and Department links even without delivery.
- Do not emit `external_effects`, `skipped_disabled`, or instructions evaluating saved configuration during a run.

## Ownership and files

```text
apps/installer/templates/
  automations/
    daily-operating-update.md
    weekly-operating-review.md
  skills/
    pm-daily/SKILL.md             # plus owned templates/
    pm-weekly/SKILL.md            # plus owned templates/
  templates/                     # shared Person/SOP/issue/decision contracts
config/setup-answers.json         # private deployment source of truth, nonsecret
config/setup-answers.draft.json   # unfinished edits; never generation input by default
automations/{daily-operating-update,weekly-operating-review}.md
skills/{pm-daily,pm-weekly}/SKILL.md
skills/{pm-daily,pm-weekly}/templates/  # selected derived templates; no parallel live contract
```

- `apps/installer/questions.json` is the sole editable question list. The installer loads it directly; template headers contain only rendering metadata.
- Questions use stable IDs, option IDs, input shapes and defaults. Prompt tags reference their rendered answers. No automatic synchronization or reverse parser exists.
- Reuse the existing answer document with an explicit schema migration: stable semantic option IDs and per-selection input text replace positional preset IDs and flattened prose as authoritative input; retain existing semantic channel IDs where valid.
- Derive provider requirements, rendered text and targets from those selections; do not maintain independently editable duplicates.
- Import schema 4 without guessing: preserve custom text; require review where flattened multi-source answers cannot be separated safely.
- Adopt checkout-owned answers for this private deployment. Import profile answers only explicitly; differing checkout/profile values require operator resolution.
- Hermes keeps credentials and an installed derived copy, never a second editable answer authority. Generated prompts contain profile references, not secrets.
- Consolidate overlapping workspace role/communications controls into these answers; derive workspace managed sections instead of asking the same destination twice.
- Do not copy private bindings into reusable templates or upstream. Public examples use synthetic targets.
- Package owned supporting templates inside each skill folder and shared contracts alongside them. Current copies preserve the existing contracts; generation must select matching scope variants before installation. Do not copy evals, audits or runtime state into the install package.

## Generation interface and reliability

- CLI: `python3 setup.py generate --config config/setup-answers.json` previews; `--apply` saves the source bundle. `features` uses the same compiler after interactive review.
- Installer and CLI call the same local functions; neither invokes an LLM, provider, scheduler or hidden job.
- `load_config(path) -> SavedAnswers`: load/migrate input; reject unknown keys or unresolved choices.
- `render_bundle(answers, template_root) -> {relative_path: text}`: deterministic full bundle, including workspace managed sections.
- `validate_bundle(bundle) -> errors`: unresolved slots, path escapes, missing references, mismatched artifact/template contracts and unsupported selected capabilities.
- `preview_bundle(bundle, checkout) -> diff`: show all changed files and newly enabled external routes.
- `apply_bundle(bundle, expected_originals) -> changed_paths`: reject concurrent edits; reuse existing atomic file writes and rollback for caught failures.
- Existing batch writes are not crash-atomic. Keep an interrupted apply visibly incomplete and require full regeneration/validation before installation; do not claim multi-file transactional safety.
- Compare generated outputs with their last generated versions before replacing manual edits; block and show the conflict, never silently discard edits.
- Save generation provenance with saved answers: template version and per-output content hashes for drift detection only, not an execution handoff framework.
- Repeating generation with identical inputs produces identical bytes; no generation timestamps inside outputs.
- Generation is synchronous local work, no queue/fan-out/retries/network rate limits. Retry only after resolving an input or write error.
- Runtime Daily fan-out and Weekly single-call behavior remain owned by generated prompts; generation does not orchestrate them.
- Installation stays a separate existing operation. No profile creation or activation merely from regeneration.

## Fixed safeguards: never installer switches

- Frozen windows, complete pagination within authorized scope, bounded recursion and explicit incomplete-versus-empty coverage.
- Source text is evidence, not instructions; cache once and preserve provenance.
- Exact grouping, no guessed membership or invented identity, all expected reporting units accounted for.
- JSON-only skills, no fabricated facts, names in readable prose, strict decision/SOP evidence criteria.
- Preserve valid history, approved baselines, closed-unit reporting and supported next-week carry-forward.
- People progress and unblocking, not employee performance ratings; lean material usefulness/gap footer.
- Exact headings/contracts, workspace-contained output paths, local rendering before effects, conflict/read-back checks.
- Custom instructions may specialize these rules, never weaken them. Structural conflicts block generation; operator review must resolve semantic conflicts in custom prose before application. Do not build semantic policy analysis into Python.

## Acceptance and pressure pass

- Map every in-scope saved question to an output or explicit retirement; no silently ignored answers.
- Generate Project/local-only, Project/selected-provider, and Department/local-only bundles from synthetic configurations.
- Verify selected text/IDs appear only in their owners; omitted providers/mode instructions and enablement flags do not appear.
- Rerun the existing Daily/Weekly semantic evals on the generated Project pair; compare JSON, rendered headings, People coverage and gaps against current reviewed behavior.
- Operate a Department fixture with two Projects contributing to one Department and another Department sharing a person; verify isolation and cross-unit People consolidation.
- Exercise resume, custom multi-source text, schema-4 migration, manual edit conflict, interrupted write, repeat generation and invalid destination cases through eval evidence, not a new test suite.
- Keep provider writes out of generator acceptance; live readiness remains a separately authorized operation.
- Pressure pass: dropping all Step 4 would lose local rendering. Revised design omits only propagation.
- Pressure pass: replacing Project with Department mechanically would duplicate Department rollups. Revised design generates a different hierarchy and matching artifact contract.
- Pressure pass: retaining old presets would reintroduce baseline ratings and Notion-only routing. Revise preset content before extracting reusable templates.
- Pressure pass: unrestricted LLM regeneration could erase hardening. Use reviewed fragments and deterministic compilation.

## Implementation and verification

### Parity repair and simplification — 2026-09-11

- Accepted scope: audit every installer script, remove proven obsolete owners, repair option/behavior gaps and support a chosen output directory.
- Preserve the handwritten automation/skill files as the comparison baseline; do not overwrite the live profile.
- Flow: template metadata → exported question JSON → editable saved answers → preview → selected output directory.
- Reuse the compiler and editor; retain separate profile/authentication operations with live callers. Remove only traced orphan scripts, retaining recovery copies.
- Repair repeatable entries, custom provider declarations, destination validation and mandatory provider read-back without moving semantic reasoning into Python.
- Proof: actual deployment configuration rendered in isolation; inspect every four-prompt difference; exercise repeat sources, custom routes, target-folder drift and CLI import/resume. No new code test suite.
- Review the implementation independently before declaring parity; report unresolved semantic or live-provider limits explicitly.

- Implemented in `apps/installer/prompt_generation.py` and the existing feature/install flows.
- Schema 5 stores selected option IDs and per-option inputs under `values`; generation hashes track drift. Schema-4 prose is retained for explicit review, not guessed into authorizations.
- Workspace context is generated from `templates/workspace.hermes.md`; provider bindings stay in automation prompts.
- Plan executed: template declarations → compiler/migration → inline editor → source/profile boundary → isolated verification and independent review.
- Local matrix, draft recovery, conflict/backup and interrupted-write checks passed; independent review passed the generator scope.
- Full live collection, provider effects and Department semantic acceptance are not certified by these checks.
- See [verification evidence and limits](prompt-generation-verification.md). No live installation was applied.
