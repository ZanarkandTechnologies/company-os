---
title: Company OS evaluation
status: active
owner: Company OS
created_at: 2026-09-03
updated_at: 2026-09-10
---

# Company OS evaluation

Company OS uses evals, not tests, while its product contracts are stabilizing.
Most reasoning coverage belongs to skills; a small end-to-end set checks wiring.
Collection and rendering cases diagnose a failed automation boundary.

```text
Daily(sources, latest Project memory, provenance)
  -> context + raw cache -> PM Daily JSON -> rolling Project memory + effects
Weekly(all reporting Project memories, coverage, provenance, prior baselines)
  -> frozen inventory -> PM Weekly JSON -> reports + next-week memory + effects
```

## File algebra and cache ownership

- Use one rolling weekly memory per Project, not a separate memory per day.
- Store it at `<HERMES_HOME>/workspace/weeks/<week>/project-memory/project--<id>.md`.
- Daily reads the latest valid memory, not necessarily yesterday's file.
- Collect the frozen 24-hour activity window plus unresolved Work and relevant
  linked context. A text diff alone loses unchanged obligations and provenance.
- PM Daily returns complete desired memory in JSON; Step 4 updates its Markdown.
- Weekly consumes the complete reporting set, including interval evidence for
  now-closed Projects. It composes Project, Department and Company reports in
  one skill call, then Step 4 renders them.
- Keep raw caches as evidence, extraction JSON as the proposed result, and
  rendered memory as the rolling readable state. These are not three competing
  memories. Retain referenced evidence while memory or reports depend on it.
- This deployment uses Project mode. Department report rollups are supported;
  Department-mode Daily caches are not configured or certified here.

| Eval boundary | Permitted result | Must remain unchanged |
| --- | --- | --- |
| PM Daily | One `daily/extractions/<run>/<id>.json` | Input snapshot/cache, prior extraction, every Markdown file |
| Daily end-to-end | Per-Project context/cache and extraction; affected `weeks/<week>/project-memory/` | Unrelated Projects, prior runs, reports, history; complete memory on no-op |
| PM Weekly | One `weekly/extractions/<run>.json` | Input memories/caches, reports, approved baselines |
| Weekly end-to-end | Frozen inventory, extraction, receipt and only validated declared artifact paths | Reporting-week input memories, unrelated files, prior runs; already-applied artifacts on repeat |

File judging rules:

- Capture the complete isolated workspace's path/type/content-hash inventory
  before each stage; keep evaluator receipts outside that workspace.
- Compare after execution: created, modified, deleted and unchanged paths.
- Fail undeclared writes, deletions, input edits, or missing required outputs.
- Validate JSON before deriving allowed destinations; an agent cannot authorize
  arbitrary writes by listing them in its output.
- Assert an update changes the intended memory; assert `no_change` preserves
  complete existing memory bytes. Initialization or structural repair is an update.
- Replay the same Step 4 input to check byte-identical rendered artifacts and
  no duplicate effects. A new run may create new context/JSON/receipt files.
- Assert facts as well as files: preserved history, grounded changes, coverage,
  and required report sections. A changed file can still be wrong.
- Grade effects from isolated provider-call/read-back evidence, never from a
  local file claiming success. No live providers are enabled by an eval.

## Execution readiness

- The catalogs below define the eval set; authored assertions are not a pass.
- Doctor runs selected skill cases in fresh sessions with JSON-only output.
- Candidate prompts contain fixture context and the request, not grading truth;
  the rubric is saved outside candidate inputs after generation finishes.
- Before/after file inventories and trace checks enforce the selected file
  boundary; source fixtures accompany artifacts during judging.
- Native file tools are not an OS sandbox. Out-of-scope access invalidates the
  run through trace checks; use synthetic fixtures and never expose secrets.
- End-to-end automation cases require fixture-backed provider reads and an
  isolated effect sink. Until wired and operated, report them as **not run**.
- Earlier isolated skill/render replays prove only their recorded boundaries;
  they do not prove scheduled production operation or complete source collection.
- September 10 authoring checks: `farplane lint evals --changed`,
  `check_eval_queries.py --root .`, and `git diff --check` pass. These validate
  the eval definitions, not execution of the two new end-to-end cases.

Operated runner smoke check, September 10:

- Run `20260910T133116Z-23756b19`: native Hermes, six minutes, two selected
  skill cases passed all 13 assertions with one source-backed judge call.
- Cases: `resilience_history_and_repeated_followups` and
  `visible_people_and_department_coverage`.
- Each created one extraction JSON; zero input modifications, deletions or
  unauthorized changes. Daily preserved 55 files; Weekly preserved 58.
- Receipt, frozen catalog, traces, file deltas and viewer live under the
  profile's `workspace/.company-os/eval-runs/<run-id>/`.
- Browser inspection confirmed JSON, assertion evidence, file-change links and
  `NOT RUN` states. Independent review cleared the runner fixes and corroborated
  the initial replay's selected checks; the corrected rerun also passed.
- This is 2 of 19 catalog cases, not full certification. The remaining 11 skill
  cases were not selected; all six automation cases lack an operated adapter.
- No report Markdown or provider effects were produced by these skill-only runs.

## Automation-boundary evals

`automations/evals/evals.json` owns Daily and Weekly end-to-end cases plus
collection and JSON-to-render/application diagnostics. Collection starts from a synthetic seed
environment and ends at an inspectable expected snapshot. Collection cases establish
the contract for a runner that executes the corresponding automation only
through its fetch, normalization, completeness, and snapshot step.

The current Doctor eval runner does not consume this catalog yet. Until that
runner is wired and operated, these cases are design fixtures rather than proof
that automation collection passes.

The collection evaluator checks:

- every required source record is collected once;
- raw provider fields, stable IDs, relations, URLs, and revisions survive;
- normalized fields use the contract vocabulary;
- missing or ambiguous relations become named gaps rather than guesses;
- Discord collection freezes one 24-hour interval, paginates to its boundary,
  and retains only deduplicated stable message links for exactly matched
  Project channels or threads;
- the output matches the snapshot shape consumed by the PM skill; and
- no PM artifact, message, provider mutation, or semantic recommendation is
  produced in this layer.

- Grade collection only against completeness and context shape.
- Grade each Step 4 against supplied JSON, complete template fields/headings, exact
  message bodies/destinations, history preservation, no-op, and conflict handling.
- Do not regrade extraction decisions in Step 4 or rerun collection to test rendering.

## Skill evals

`skills/pm-daily/evals/` and `skills/pm-weekly/evals/` start from normalized
snapshot fixtures. They evaluate the main semantic process: decisions, no-ops,
blocked behavior, memory preservation, follow-ups, reports, carry-forward, and
long-term knowledge promotion. Daily ends at one JSON result per Project; Weekly
ends at one JSON artifact set for the complete frozen week. Neither skill writes
report/memory Markdown or individual message files; automation renders those outputs.

`python3 setup.py doctor eval --profile-home <profile> --open` stages these
skill-owned cases and builds a private dossier. Add repeatable `--case <id>`
arguments for a bounded replay. Prior Markdown-based results are not proof of
the JSON-only contract; the run receipt distinguishes selected coverage from
the full catalog. Unrun automation cases stay visible in the viewer.

- For a bounded Daily replay, run Hermes on frozen context with write ownership
  restricted to the extraction JSON; preserve existing memory bytes.
- Run a separate Hermes invocation on Step 4 with that JSON and the template.
- Allow local rendering only during an offline eval; prohibit all provider access
  and report provider application as unexecuted, never passed.
- For Weekly, run extraction against frozen Project memories, coverage evidence
  and approved baseline history; run local Step 4 separately on its JSON.
- Inspect JSON shape, exact message body/destination retention, all template
  fields/headings, local links, and the absence of individual message files.
- Repeat Step 4 to verify an unchanged complete memory remains byte-identical.

## Live evaluation

Live provider reads are a separate, explicitly authorized readiness lane. They
prove that configured sources are reachable and shaped as expected; they do not
replace the synthetic automation cases or skill evals. Provider writes,
messaging, and artifact synchronization require an exact account, destination,
and side-effect scope. A skipped live lane is never a pass.

Judge the collection run against both its saved files and actual tool results:

- Discover Project associations without supplying a per-Project answer map.
- Verify Discord active and archived thread reads honor the configured allowlist.
- Read Multica issue details and full comments through the host adapter.
- Require exactly `id`, `name`, and `context` in each Project manifest.
- Resolve every local context link and compare cached bodies, messages, and
  metadata with provider tool results; a readable summary is not raw evidence.
- Report pagination actually exercised, empty reads, and unsupported attachment
  reads separately. Small source inventories do not prove multipage behavior.
- Keep raw traces and client snapshots in the private runtime; record the
  baseline, fixes, rerun verdict, and artifact links in an ignored receipt.

The canonical Daily source-health probe is a Hermes read-only run of Steps 1–2 in
`automations/daily-operating-update.md`. It must verify the configured Notion
Projects source, Multica workspace and Projects, and Discord Project channels or
threads. Discord health means only that the complete frozen 24-hour interval can
be paginated and read; gateway delivery and send behavior are out of scope.

Use this prompt from the installed profile after its private source bindings are
rendered:

```text
Run only Steps 1–2 of automations/daily-operating-update.md as a read-only source
health probe. Freeze run_started_at once. Verify the configured Notion Projects
source and Multica workspace. Discover Discord channels and threads by the exact
configured Project rule, then paginate every matched source through the complete
half-open interval [run_started_at - 24 hours, run_started_at). Do not run PM
Daily and do not create, edit, sync, comment, send, pin, delete, or change roles.
Return provider health, Project match status, interval coverage, named gaps, and
READY, PARTIAL, or BLOCKED. Do not print credentials or private provider IDs.
```

## Change routing

### Explicit Daily demo invocation

Use an isolated demo workspace for context, weekly memory, and drafts; label all
outputs synthetic. A collection-only evaluation must explicitly stop after the
context stage. Do not run a prompt containing Step 4 against live providers
unless its configured effects are authorized. The eval invocation selects the
seeded records marked `[DEMO` or with the isolated run's declared demo seed prefix.
Keep exact seed identifiers in the private run receipt. Production prompts contain
no seed-specific filtering: before a normal run against these seeded providers,
exclude seeds in that invocation or remove/archive the exact seed records after
checking their current state. Removal has not been performed.

The Daily prompt discovers associations rather than storing per-Project IDs.
The configured Notion Project, Multica Project, and Discord thread now share
the exact canonical `<client> — <business type>` name. Require one unique
normalized exact match or an explicit source link; do not grade a guessed or
partial name match as correct. The private setup receipt retains provider IDs
for read-back and rollback, not as a second production configuration layer.
For a historical replay, specify the 24-hour interval that contains the seed's
actual timestamps. Fetch each record once and pass cached content to PM Daily.
Do not treat synthetic decisions or Done statuses as real delivery evidence.

Inspect blocked-input follow-ups, overdue approvals, meeting decisions, and
requests for missing completion evidence. Check that Project outputs stay
isolated and that coverage gaps remain visible. These are evaluation
expectations, not a claim that the automation has run or passed.

### Edit ownership

| Change | Required eval owner |
| --- | --- |
| Source query, relation discovery, normalization, completeness, snapshot shape | `automations/evals/` case and expected snapshot; operated verdict pending runner wiring |
| Daily extraction, decisions, intended memory facts, or message content | `skills/pm-daily/evals/`, ending at JSON |
| Daily memory rendering or JSON message application | `automations/evals/`, beginning with JSON |
| Weekly report reasoning and intended long-term memory | `skills/pm-weekly/evals/`, ending at JSON |
| Weekly Markdown rendering/application | `automations/evals/`, beginning with JSON |
| Provider connectivity or permissions | read-only readiness eval with explicit profile authority |
| Installer or deterministic production safeguard | operated proof of the real command and receipt; no test harness |

Keep fixtures synthetic and reusable. Never copy client records, credentials,
sessions, generated reports, or private workspace state into the repository.

## Feedback-derived regression backlog

- Audience: the operator and future eval maintainer.
- Purpose: preserve user-observed failures before choosing a runner or writing tests.
- These are future case specifications, not passing results or new runtime rules.
- Grounding: operator corrections in this migration, current source contracts,
  and the dated Daily/Weekly skill audits. Predictions below are hypotheses.
- Keep expectations anchored to user value. Matching an edited template is not
  sufficient when the edit removed required behavior.

### Likely next complaints

- **“This repeats itself; what actually changed?”** Repeated accepted-output and
  intervention detail remains in the latest Weekly replay. Check unique value
  across sections and changes versus the prior report, not just shorter bullets.
- **“What do I need to do now?”** Separate observed facts, unresolved decisions
  and proposed interventions; identify the supplied owner and completion signal.
- **“Why did it miss this person, Project or conversation?”** Sparse records,
  archived threads, pagination and incomplete identity coverage can silently
  shrink a convincing report. Compare against the actual expected inventory.
- **“Why is it asking again, or ignoring my correction?”** Repeated runs must
  retain accepted history, resolved issues and source revisions without duplicate
  reminders or resurrected work.
- **“Why does the real run differ from the demo?”** Source/profile drift,
  synthetic evidence, live permissions and unbound destinations are separate
  readiness checks. A successful local replay does not settle them.

### Cases to scope later

| ID / owner | Reproduce the failure | Observable acceptance condition |
| --- | --- | --- |
| F01 · Weekly | Multiple Departments; accepted, progressing, blocked and evidence-poor people | Every Department has a visible executive entry; every in-scope person has truthful progress, not only completed outputs. Preserve scope, supplied dates and roles without ratings. |
| F02 · Daily + Weekly | Same fact or intervention appears in several sections; identifiers and instructional boilerplate leak | Reader-facing names and source labels; each section adds distinct value; no template instructions, empty filler or repeated artifact lists. |
| F03 · Daily | Empty Work, no owner, routine status change, consequential meeting decision and one-off file conversion | No fabricated progress or generic message; explain insufficient evidence. Only substantive decisions qualify; SOP signals preserve input → output and acceptance, without premature promotion. |
| F04 · Weekly | Reminders failed because another person controls approval | Identify the actual dependency and an actionable proposal beyond another reminder; preserve known authority; do not blame or rate the worker. |
| F05 · Collection | Five active Projects; ambiguous or duplicate names across clients/platforms | Account for all five as eligible or explicitly blocked. Never silently omit, guess a match or mix clients; retain exact source identity. |
| F06 · Collection | Archived Discord thread, several message/issue pages, linked meeting content, empty source and denied source | Exhaust relevant pagination/recursion; distinguish empty success, denied access, truncation and unavailable attachments. Record what was actually read. |
| F07 · Collection | Messages on the 24-hour edges, unresolved older Work, duplicate links and recursive cycles | Freeze one half-open interval; retain unresolved Work and relevant linked history; fetch each record once and pass complete cached evidence without skill refetching. |
| F08 · PM/Step 4 boundary | Extraction has memory plus follow-up/documentation actions | Skill writes JSON only; Step 4 renders complete templates and executes only exact authorized JSON actions. No extra message Markdown or invented judgments during rendering. |
| F09 · Step 4 | Repeat a result; another user edits memory; a provider write times out after succeeding | No duplicate comments or memory updates; preserve unrelated edits/history; inspect uncertain writes before retry and require read-back. A skipped action is not a success. |
| F10 · Weekly | Sparse-but-present Project versus missing expected Project; approved baseline plus one new sample | Sparse evidence remains visible without blame; missing required input blocks final rollup/promotion. Preserve approved baseline and unresolved-only carry-forward. |
| F11 · Runtime | Repository changed but installed profile did not; provider credential/tool missing | Identify the actual executed source/version and named missing capability. Do not claim the live profile inherits a source-only fix. Notion OAuth MCP must not trigger an unrelated API-key flow. |
| F12 · Installer, deferred | Select Custom, type inline, edit prior answers, interrupt/save/resume; select timezone | Labels are readable; every custom selector supports inline text; saved partial answers reappear editable; cancellation preserves the requested draft and makes no unintended setup changes. |
| F13 · Configuration, deferred | Regenerate for Project versus Department mode and with/without propagation | Emit only the selected behavior; preserve saved answers and explicit bindings; no irrelevant mode instructions or contradictory runtime enable flags. |
| F14 · Provenance/privacy | Demo records mixed with real work; local cache links in an outbound message | Synthetic facts never become real progress or approved precedent; private paths/credentials do not escape; provider effects require explicit destination authority. |

### Proof already available versus still needed

- F01 has a bounded four-Project/two-Department/five-person Hermes replay:
  [coverage audit](../skills/pm-weekly/audits/2026-09-10-report-coverage.md).
- F04/F10 and local Weekly rendering/no-op have bounded evidence in the
  [unblocking audit](../skills/pm-weekly/audits/2026-09-10-unblocking-weekly.md).
- Daily readability, JSON separation and memory compaction have scoped evidence
  in [readability](../skills/pm-daily/audits/2026-09-09-readable-memory.md),
  [JSON handoff](../skills/pm-daily/audits/2026-09-09-json-handoff.md) and
  [lean memory](../skills/pm-daily/audits/2026-09-10-lean-memory.md) audits.
- These are partial coverage pointers, not passes for entire rows. F02 still
  has observed duplication; multi-run live collection/application remain separate.
- Prioritize omission/isolation, truthful extraction, preservation and safe
  effects before installer polish. Do not expand the installer before its
  underlying operating behavior stabilizes.

### Readiness snapshot — 2026-09-10

- Normal human use of Notion, Multica and Discord can supply real evidence;
  that is different from certifying Company OS to act unattended.
- Source declares Notion OAuth reads, Multica reads and Discord history reads.
  Installed connector directories exist; their presence does not prove current
  access, complete pagination or correct Project matching.
- A byte comparison found installed Daily/Weekly prompts, both PM skills and
  the Company template differ from the evaluated repository source. No install
  or synchronization was performed during these replays or this assessment.
- Daily currently leaves Multica comment/update actions blocked and Project
  Memory provider sync unbound. Weekly destinations are local and delivery is
  no-send. Do not describe those effects as operational.
- Doctor's collection catalog and current JSON adapter remain uncertified as
  described above. No fresh live connectivity probe was run for this assessment.
- Before relying on scheduled output: reconcile the intended installed source,
  run the read-only Steps 1–2 probe, account for every active Project, then inspect
  a real Daily and Weekly result with provider effects excluded from that pilot.
- Provider propagation needs its own bounded destination/write/read-back proof.
  Discord history health does not require sending or gateway testing.

### Feedback tracking later

- Group corrections by the case IDs above, not by individual wording.
- Record: date, case ID, source version, run/output link, expected versus observed,
  user correction, root cause, repair and rerun evidence.
- Count distinct observed episodes; exclude repeated quotes, compression hooks
  and restatements of one incident. Mark recurrence after a claimed fix separately.
- Do not invent historical counts from this partial conversation. Capture new
  episodes prospectively; automate counting only if manual review becomes costly.
- Use real operation to discover whether reports change a decision, remove a
  dependency or save source-checking effort. Another correct-looking report alone
  is not proof of usefulness.

## Pre-production hardening — 2026-09-10

- Scope: repository connectors, Daily/Weekly contracts and owned eval cases;
  no live deployment, provider reads/writes, new test suite or runtime framework.
- Grounding: source/native-handler inspection, synthetic connector probes and
  Hermes replays. Prompt-level guarantees are not atomic runtime enforcement.

| Failure | Repair | Evidence boundary |
| --- | --- | --- |
| Discord embed/reply content silently becomes empty | Preserve raw messages inside the bounded read-only envelope, retaining allowlist checks | 21 offline connector checks include embeds, replies, attachments and denied actions |
| CLI error output leaks private text; timeout escapes | Static Multica errors; structured transport failures; uncertain creates require read-back before retry | Same isolated connector probes; no real create attempted |
| Failed reads erase facts or revive stale approval blockers | Preserve last supported facts; explicit newer corrections supersede current state; missing coverage is not resolution | Fresh Daily resilience replay passed targeted semantics |
| Repeated or stale questions get sent | Suppress existing questions; Step 4 checks fresh Work/comments and blocks changed or unreadable evidence | Supplied read-back decision replay, not live provider certification |
| Memory conflict still permits messaging | Require that Project's successful render/read-back before effects | Render-conflict decision replay passed; no provider write attempted |
| Weekly drops Projects closed during the week | Include interval Daily Projects; report closure without creating new next-week memory for closed Projects | Archived-Project replay and final independent targeted review passed |
| Rerun overwrites snapshot/receipt evidence | Run-scoped immutable snapshots and retained receipt attempt history | Source contract reviewed; crash/concurrent execution still unproven |
| Missing Daily intervals look like a complete week | Compare supplied coverage against requested interval; recover real evidence or propose bounded backfill, never invent success receipts | Missing-interval detection and corrected recovery wording passed targeted review |

- Private evidence: `preprod-hardening.VRGLcA/` and
  `connector-hardening.1pg1fp/` under the Hermes workspace; their `review.md`
  records carry generated outputs and exact commands, not source-controlled data.
- Deployment remains gated on reconciling installed source, live read-only
  collection proof and separately authorized provider-effect proof.
- Known residuals: a Project created and closed between Daily runs may never
  enter the captured inventory; recovering all such history needs a supported
  historical discovery/backfill route, not a claim of exhaustive coverage.
- Compare-before-write prompts do not provide atomic cross-process locking or
  provider transactions. Concurrent/crash recovery and uncertain writes require
  operated proof before unattended provider propagation.
- Remaining repeated report detail and representative real-world usefulness
  still need tuning; passing these cases is not a whole-system production pass.
