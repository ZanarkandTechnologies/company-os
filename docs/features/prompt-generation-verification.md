---
title: Template-driven installer verification
date: 2026-09-11
status: local-generator-passed
---

# Verification boundary

## Current questionnaire ownership — 2026-09-13

- User decision: edit `apps/installer/questions.json` directly; templates retain replacement tags. No inline question parser or template/question synchronization.
- Moved all 26 definitions unchanged out of template headers. Saved answer IDs/schema and generated behavior remain unchanged.
- Compared all eight Project/Department × none/Daily/Weekly/both bundles before and after: every generated file is byte-identical.
- In a scratch copy, edited one decision option's `render` text in JSON; only the Daily and Weekly skill files changed at their answer tags.
- CLI question export, Python compilation and `git diff --check` passed. Independent read-only review found no blocking issue; references resolve and distribution includes the question file.
- Proof ran in a temporary scratch directory. Live profile, saved answers and handwritten operating prompts were not modified by this change.
- Earlier blanket choice-first changes below were reversed: ordinary text fields remain text inputs; only configured choice questions have option menus.

- Grounding: local source, isolated scratch generation, operated CLI and two synthetic Hermes skill replays.
- No live installation, provider collection, provider writes, scheduling, commit or push was performed.
- Existing unrelated checkout changes were preserved. No code test suite was added.

## Generator and lifecycle

- Discovered 26 template-owned questions; rendered every declared option with synthetic inputs.
- Project × neither/Daily/Weekly/both propagation produced 16 files per bundle.
- Department × the same propagation selections produced 15 files; Project-only rollup support was omitted.
- Repeated generation was byte-identical; selected memory paths agreed across both cadences.
- Omitted integrations and propagation sections disappeared from generated instructions.
- Schema-4 prose survived migration; unreviewed structured choices blocked generation.
- Dormant destinations did not request credentials; selected custom Multica inventory produced its provider binding.
- Manual edits blocked replacement; explicit adoption retained backups.
- Grouping changes retired obsolete generated templates with backups, not historical memory.
- An injected write failure left an incomplete marker; installation refused it; regeneration recovered.
- Approved generated workspace context did not cause false drift; body edits were detected.
- Python compilation and `git diff --check` passed.
- Independent review: TAS-A for generator scope; not a live operating-system certification.

## Operated editor

- Ran `setup.py features --root <scratch-source>` in a real terminal.
- Changed company name from `Toy Shop` to `Toy Shop Edited`, interrupted at description and saved the draft.
- Relaunch prefilled `Toy Shop Edited`; the active answer document remained `Toy Shop` until application.
- Inline input probes covered custom typing, field navigation, selection toggling, Back, interrupt, EOF and non-TTY editing.

## Generated-skill replay

- Used existing evaluator with synthetic fixtures and file-only Hermes tools; live profile supplied model credentials only.
- Daily `documentation_quality_follow_up`: emitted one extraction JSON, eight memory categories and one consequential documentation request.
- Weekly `visible_people_and_department_coverage`: emitted one JSON containing four Project reports, two Department reports, one Company report, four next-week memories and executive distribution data.
- Inspection found named People progress, Department executive summaries, an explicit sparse-evidence gap and a decision-packet unblocking action.
- Both evaluator calls reported `passed`, no unauthorized file changes and verified tool safety; host paths were audited after execution, not OS-sandboxed.
- These results prove execution and the inspected coverage only. The full semantic judge suite, rendered automation reports and Department-mode semantic replay remain unverified.

## Local evidence

- Proof used an isolated temporary scratch root, not archival storage.
- Replay directory: `evidence/workspace/.company-os/eval-runs/generated-project-replay` beneath that root.
- Daily session: `20260911_012746_abe416`; Weekly session: `20260911_012844_cc5350`.
- Replay outputs and `file-deltas/` retain JSON and file-boundary evidence.

## Remaining gate

- Review real saved bindings through `setup.py features`; inspect `setup.py generate` before applying.
- Explicit installation and read-only provider preflight are separate from generation.
- Do not infer production readiness or permission to send from a selected option or these synthetic results.

## Follow-up parity and simplification

- 2026-09-13 matching correction: matching was incorrectly left as text. Restored two recommended policies and inline Custom. Only company name/context remain text; timezone has its selector and all policy questions use choices. Fixed grouping/propagation choices remain bounded to supported modes rather than accepting invented Custom modes.
- Operated the matching menu in a PTY: both recommendations and Custom displayed; arrow navigation, inline typing and Enter returned the exact Custom answer. Schema-4/5 matching prose is retained as Custom, not discarded. Blank schema-5 matching answers use the recommended default.
- Audited all 26 declarations; all three matching choices rendered 16 package files using comparison answers. Loader guards reject free-text policy questions and option lists hidden by a text/timezone kind. Independent review found a malformed-values migration crash; the boundary now raises the existing handled configuration error.

- Audited every installer Python module; removed six obsolete files and the dead slot-rendering helpers. See [script inventory](installer-script-inventory.md).
- Reconstructed current source bindings and matching/routing instructions into private temporary comparison answers.
- Generated 16 files in an isolated comparison directory using the real CLI with `--config`, `--output-dir` and `--apply`; handwritten source files and live profile were not replaced.
- Independent source comparison found no critical rule loss across the four prompts and supporting contracts. This is semantic review of text, not an agent-output equivalence claim.
- Accounted differences: parameterized identities/paths, selected policy detail, table layout, explicit source boundaries, configurable destinations, neutral examples and Area-to-Department report metadata alignment. Output is not byte-identical to handwritten prompts.
- Restored mandatory external read-back and made custom Telegram/WhatsApp routes inherit delivery safeguards.
- Added repeatable entries, explicit sync-section validation, open provider IDs and independent output-directory drift tracking. Unknown providers remain uncertified rather than silently passing setup.
- Question export parsed as 26 JSON declarations; installer modules compiled successfully.
- Repeat generation preserved answer bytes and produced no active source answer file; output was confined to the selected comparison directory.
- Operated inline entry add/remove/interruption/resume probes passed. Fallback probes passed retaining both entries, primary only, additional only and none; omitted entries no longer render.
- Direct probes passed repeated custom Calendar rows, custom Telegram chunk/idempotency rules and invalid-section rejection. Generated Markdown tables remain contiguous.
- Final independent bounded review cleared the fallback defect and found no remaining blocker in the reviewed scope. No new full agent semantic replay was run in this follow-up.
- Removed source remains recoverable from Git. Temporary evidence/backups are not permanent archival storage.
