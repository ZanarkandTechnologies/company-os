---
skill: pm-daily
date: 2026-09-10
change_type: behavior
owner: skill-maintenance
status: pass
review_route: reviewer
eval_required: yes
---

# Lean extraction and memory

## Value decisions

| Unit | Decision | Value retained |
| --- | --- | --- |
| Full record/body copies | Delete from extraction | Frozen cache and source references retain original evidence. |
| Item metadata | Narrow | Exact Work/Person IDs, revisions, workflow and acceptance controls support Weekly attribution and comparison. |
| Repeated Project/week/provenance | Inherit | Keep item-level differences and mixed-evidence distinctions. |
| Empty section explanations | Delete | Explicit `none` still distinguishes no finding from insufficient evidence. |
| Empty/title-only record diagnostics | Keep only in Work reviews | Explain skipped actions without polluting Project memory. |
| Relative dates | Resolve from source | Durable commitments remain interpretable after the run date. |
| Memory self-links | Delete | Original evidence supports retained history. |
| `source_note_keys` initialization | Delete | Repository search found no runtime consumer; retain pre-existing unknown metadata. |
| Identity, version, time, extraction references | Keep | Routing, refresh visibility, provenance, and idempotent rendering. |
| Eight headings and `memory_action` | Keep | Explicit coverage and the existing render/no-change contract. |

## Proof plan

- Compare one frozen synthetic mixed-evidence replay with the previous JSON/memory.
- Check absence of raw-record copies, empty placeholders, repeated envelope fields,
  self-links, diagnostic-only memory, and relative dates.
- Preserve accepted result/scope, blocker/next action, consequential decision,
  prior sign-off, file-to-file SOP, exact Work/Person identity, and all headings.
- Replay empty evidence to verify material limitations still survive.
- Render supplied JSON only, then repeat without byte or metadata changes.
- Use a fresh Codex lane; no provider calls, live installation, or Hermes billing changes.
- Independent review must inspect artifacts, not infer success from shorter files.

## Results

- Codex offline replay passed mixed and empty-evidence cases; independent source
  and artifact review found no remaining issue in this bounded scope.
- Mixed compact JSON shrank from 8,039 to 4,618 bytes (43%); preserved all five
  substantive items, exact Work/Person IDs, scoped acceptance, and original sign-off.
- First replay lost local cache references and repeated non-blocking timezone
  uncertainty. Source rules were corrected; round 2 retained frozen evidence and
  qualified the time only beside the commitment.
- Both rendered memories retain nine required frontmatter fields and all eight
  headings. Empty sections render `None.`; empty-context evidence remains explicit.
- Renderer read-back verified local links and unchanged extraction JSON; its
  repeated application retained identical memory bytes and metadata in both cases.
- Private proof: `daily-lean.AW6blO/review.md` under the Hermes workspace.
- JSON state checks, `farplane lint evals --changed`, eval-query lint, and
  `git diff --check` passed. The source skill remains below 200 lines.
- Shared `check_skills.py --write` could not run: its installed package cannot
  locate a Farplane repository root. No registry validation is claimed.
- No live installation, provider reads/writes, Hermes rerun, or full Weekly
  execution. Existing artifacts and unrelated source edits were preserved.
