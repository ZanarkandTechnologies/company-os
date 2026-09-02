---
artifact_type: company-os-project-memory
artifact_version: "1.1.0"
project_id: "{{PROJECT_ID}}"
project_name: "{{PROJECT_NAME}}"
week: "{{WEEK}}"
note_version: 0
last_appended_at: null
source_note_keys: []
---

# {{PROJECT_NAME}} — Project Memory — {{WEEK}}

Private working memory for this Project and week. PM Daily updates the current
operating picture from source-linked evidence while preserving useful history
and unresolved attention. PM Weekly freezes all Projects together before
producing reports or persistent entity updates.

## Work and employee updates

<!--
One complete latest-state snapshot for open, active, blocked, stale, or
Done-but-unresolved Work whenever its source revision changes.

Capture:
- work_id, title, project_id, employee_ids, exact source status;
- assigned/started/due/completed and last meaningful update timestamps;
- derived stale duration and its source basis;
- blocker, next action, and next-action owner;
- documentation state; expected artifact; observed artifact evidence;
- source IDs and source revision.

Do not infer effort, intent, personality, or a performance rating.

Golden shape:
### TASK-103 — confirm the supplier normalisation rule
- **Owner / state:** PERSON-JUN · Blocked.
- **Timing:** Due 2026-09-02; last meaningful update 2026-08-29; stale 4 days.
- **Blocker / next action:** Approved column map missing; PERSON-JUN supplies it.
- **Documentation / artifact:** needs_information; signed column map expected; none linked.
- **Evidence:** TASK-103, COMMENT-318.
-->

## Completed outcomes and artifacts

<!--
Capture every Done Work that produced or materially changed an artifact. Add it
here only when the claimed outcome and artifact acceptance are sufficiently
documented; otherwise retain it above and open one documentation question.

Capture:
- work_id, project_id, employee_ids, title, accepted business outcome;
- workflow_key when supplied or reconstructable, output receiver, expected
  artifact, and accepted artifact IDs/links/types;
- started, completed, and accepted timestamps;
- elapsed, active, and waiting hours when sourced, otherwise explicit gaps;
- handoffs, exceptions, rework, and control failures when evidenced;
- comparison with an existing SOP baseline and the reason for a material
  variance; do not demand narrative for routine execution;
- documentation state and closed question IDs;
- optional explicit workflow_key; source and approval evidence.

Golden shape:
### TASK-105 — normalise the supplier count package
- **Outcome:** Five stores can now be compared from one approved column shape.
- **Owner / output / receiver:** PERSON-NUR · FILE-105 · Operations lead.
- **Acceptance:** Approval COMMENT-318.
- **Timing:** 5.5 active hours; accepted next day after 18 waiting hours.
- **Variance / rework:** No approved baseline; no rework evidenced.
- **Documentation:** sufficient; no open questions.
- **Workflow:** supplier-count-normalisation; one sample, not a baseline.
- **Evidence:** TASK-105, FILE-105, COMMENT-318.
-->

## Documentation questions

<!--
One precise open question for Done Work whose page or artifact does not yet
prove an important fact. Do not repeat information already present.

Capture:
- question_key, work_id, employee_ids, open/answered state;
- the exact missing fact and why it matters;
- where the answer belongs and the evidence already checked;
- asked_at, answered_at when available, and source IDs.

Golden shape:
### TASK-108 — acceptance evidence missing
- **Question:** Which receiver approved FILE-108, and where is that approval recorded?
- **Why it matters:** The outcome cannot enter Employee Memory without acceptance proof.
- **Add to:** TASK-108 Notes or linked approval comment.
- **Evidence checked:** TASK-108, FILE-108.
-->

## Problems and inefficiencies

<!--
Describe the operating problem, not the employee. Combine related blockers,
risks, rework, waits, and sourced cost consequences.

Capture:
- affected workflow and step; observed condition and operating impact;
- dated measurement window, recurrence/volume, active/wait time loss;
- sourced cost formula only when its inputs exist;
- confidence, measurement gaps and owner;
- narrow intervention, next proof, and evidence IDs.

Golden shape:
### Supplier formats prevent one reliable replenishment comparison
- **Workflow / step:** Replenishment / normalise incoming count file.
- **Observed baseline:** Six files/week; 35 rework minutes per affected file.
- **Impact / cost:** Rollout blocked; 6 × 35/60 × MYR 42 = MYR 147/week.
- **Confidence / gap:** Medium; time the next two files.
- **Next proof / evidence:** Apply the signed map; TASK-101, TASK-105.
-->

## Decisions

<!--
Record a choice another person will need later. Routine execution updates stay
in Work. Mark an unapproved candidate as Proposed.

Capture:
- choice; context and rationale; two or three real options/tradeoffs when known;
- authority and decision time; accepted consequence;
- review trigger; source evidence.

Golden shape:
### Hold rollout until counts are normalised — Proposed
- **Choice:** Do not approve rollout until every supplier count uses the signed format.
- **Tradeoff:** Accept a two-day delay instead of approving incomparable counts.
- **Authority:** Missing; weekly review must confirm.
- **Review trigger / evidence:** Final two comparisons attached; MEETING-042, TASK-105.
-->

## Workflow and SOP signals

<!--
Capture an observed artifact-producing workflow. Daily records samples; it does
not create or replace a baseline.

Capture:
- explicit workflow_key, name, trigger, actors, systems, ordered steps;
- handoffs, output_artifact_type, exceptions, and controls;
- sample work IDs, elapsed/active/wait hours, acceptance time;
- existing canonical baseline when supplied, variance note, confidence, gaps;
- promotion state and evidence IDs.

Golden shape:
### Normalise supplier counts before rollout review — Observed
- **Workflow key / output:** supplier-count-normalisation · comparison-ready-file.
- **Method:** Retain original; map columns; validate totals; attach; request review.
- **Sample:** TASK-105 · 5.5 elapsed hours · accepted FILE-105.
- **Baseline:** Not established; capture two more accepted samples across Projects.
- **Evidence:** TASK-105, FILE-105, COMMENT-318.
-->

## Carry-forward items

<!--
Weekly initializes this section in the next week from the newest unresolved Work
and documentation-question snapshots. Daily may later append newer source state
under the original Work ID. Accepted completed outcomes do not carry forward.

Capture:
- original work_id and source note keys;
- unresolved state or question; accountable owner and next action;
- source week and evidence IDs.
-->
