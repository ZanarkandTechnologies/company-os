---
skill: pm-daily
date: 2026-09-09
change_type: behavior
owner: skill-maintenance
status: bounded_pass
review_route: reviewer
eval_required: yes
---

# JSON-only Daily handoff

## Accepted boundary

- Before: Daily wrote extraction JSON, memory Markdown, and individual message files.
- After: Daily writes one JSON containing complete desired memory, section states,
  exact message bodies/destinations, and Work review reasons.
- Step 4 renders every memory template field/heading and applies JSON messages.
- Keep Daily rules as short bullets; complete sections do not require invented facts.
- Preserve evidence gates, history, exact provenance, provider authority, conflict
  checks, read-back, and repeated-render no-op behavior.
- Message templates remain skill guidance, not generated Markdown artifacts.

## Proof

- Three Hermes extraction cases produced JSON only: mixed evidence/history,
  insufficient context, and cached Project data with actionable messages.
- All three JSON results passed required-field and section-state checks.
- Existing mixed memory remained byte-identical during extraction.
- Hermes completed the insufficient-context Step 4 rendering with all fields/headings.
- Mixed Hermes rendering stopped on OpenRouter's out-of-credits error; the other
  pending renderer was stopped. Provider settings and credits were not changed.
- Codex-operated local Step 4 rendered the three supplied JSON results faithfully;
  repeated rendering preserved bytes. This is not a full Hermes runtime verdict.
- Faithful rendering exposed duplicate extracted facts and private cache links
  inside message bodies. Source selection was tightened; Step 4 blocks those links.
- Fresh final Codex extraction passed eight-section state checks; accepted outcomes
  and blockers appear once, unsupported scope decisions are excluded, and message
  bodies contain no private cache paths.
- Final Codex rendering retained ten frontmatter fields and all eight headings
  in both corrected cases; fourteen local references resolved. Repeated rendering
  preserved bytes and metadata without editing extraction JSON.
- Independent review passed the bounded skill contract, prompt quality,
  integration readiness, and evidence quality; full runtime readiness is excluded.
- JSON parsing, eval-contract lint, and `git diff --check` passed.

## Scope and limitations

- No provider access, sends, scheduling, live skill installation, or generated
  client artifacts committed to source.
- Replaced obsolete message Markdown expectations with JSON; moved rendered
  memory expectations to the automation eval owner. Tracked prior versions remain
  recoverable in Git; no live output files were removed.
- The existing Doctor adapter is not certified for the changed contract.
- Full Hermes handoff requires restored provider credits; live propagation and
  Weekly execution remain unverified.
- The cached-client extraction retains verbose raw-record metadata and repeated
  synthetic labels for mixed provenance; this replay does not certify minimality.
