---
title: "PRD: Hermes Company OS onboarding"
status: superseded
owner: HermesCorp
created_at: 2026-08-19
updated_at: 2026-08-20
superseded_by:
  - tickets/TASK-0012/ticket.md
  - docs/hermes-company-os-onboarding.md
source_refs:
  - skills/company-os-onboarding/SKILL.md
  - docs/sme-operating-model.md
  - tickets/TASK-0007/ticket.md
  - tickets/TASK-0008/ticket.md
---

# PRD: Hermes Company OS onboarding

> Superseded on 2026-08-20. This document preserves the earlier component-skill
> onboarding design and TASK-0011 proof contract. The accepted product direction
> now renders one workspace-scoped `.hermes.md` from the
> [company workspace template](../skills/company-os-onboarding/assets/templates/company-workspace.hermes.md)
> and stores transient connector health in a separate receipt. See
> [TASK-0012](../tickets/TASK-0012/ticket.md) and the
> [current operator guide](hermes-company-os-onboarding.md).

## Product Promise

An SME owner can start with the tools the company already uses, answer only the
questions Hermes cannot safely infer, and finish with a small set of verified
company skills that tell every Hermes agent where and how to find company Work,
People, Knowledge, Communications, and Decisions.

## Problem / Context

The retired `hermes-company-os` package proved three useful mechanics:

1. it can inventory, fetch, scaffold, and structurally validate company skills;
2. it contains five component templates; and
3. it can diagnose one Google Drive Knowledge boundary safely.

It does **not** yet implement the complete onboarding product. There is no
exhaustive question policy, resumable onboarding state machine, connector
catalog, provider-specific mapping playbook beyond Drive, deterministic
promotion step, or operated journey from first chat to an installed and healthy
component skill. Calling the narrow prototype generally ready concealed this
gap.

## First-Principles Basis

- **Objective:** turn an SME's existing software into dependable semantic
  entrypoints that Hermes can use without rediscovering the company stack on
  every request.
- **User or system need:** the owner needs a guided setup that cannot silently
  omit a tool, guess an authoritative source, over-scan private data, or claim a
  component works before a representative query passes.
- **Root cause:** connector availability, company meaning, source authority,
  permissions, and retrieval health are separate facts; the current skill
  describes parts of this reasoning but does not operate the complete sequence.
- **Key assumptions:** five company components cover the first SME operating
  layer; provider tools continue to own authentication/API mechanics; component
  `SKILL.md` files can remain the final configuration and operating contract.
- **Constraints:** no `STACK.md` or parallel tenant schema; no credential
  collection in chat; metadata-first discovery; no external writes without
  explicit approval; one component must be completed before scaling breadth.
- **First viable slice:** onboard Google Drive into `company-knowledge` from
  first chat through connection, source discovery, owner approval, generation,
  installation, and a real scoped health query.
- **Proof / falsification:** a new operator can complete the journey without
  hidden setup knowledge; the installed skill answers one natural company
  question inside the approved root and refuses the same query outside it.
- **Tradeoff accepted:** the first complete slice supports one provider and one
  component; it proves the whole lifecycle before connector breadth.
- **Non-goals:** replacing business applications, building agent memory, a
  setup console, automatic organization-wide ingestion, or a Palantir-style
  ontology.

## Audience

- **Primary:** owner or operations lead at a 1–20 person company who understands
  what the company tools are used for but may not know their exact IDs or schema.
- **Secondary:** implementation operator helping the owner connect accounts,
  resolve source boundaries, and review generated company skills.
- **Scale boundary:** above roughly 20 people—or earlier when permissions,
  departments, compliance, or delegated write authority become material—the
  onboarding must recommend a multi-workspace/proper-PM deployment rather than
  assume one simple company context.

## JTBD

When I want to make my existing company software usable by AI, I want Hermes to
ask me a clear sequence of questions, inspect what I cannot explain, and prove
each resulting company skill, so I can start using an assistant without first
designing an ontology or reorganizing every tool.

## Operated Story

Vishan opens Codex and asks Hermes Company OS to set up his company. Hermes
first inventories existing component skills and available connector tools. It
asks for the current company stack once, proposes tool-to-component mappings,
and asks only whether ambiguous workspace, folder, board, or database boundaries
and authority are correct.

When Vishan knows the location, Hermes spot-checks it. When he does not, Hermes
asks permission for a bounded, metadata-only, read-only discovery pass and maps
observed structures to the five company components. It returns one component
doctor at a time, explains what is workable, and asks whether to use the current
structure, tidy it first, or skip it.

After Vishan accepts a component boundary, Hermes fetches the existing company
skill or copies the matching embedded template, asks only the remaining policy
questions, calls `skill-creator`, validates the result, shows the exact install
delta, and obtains installation approval. A representative health question
must succeed before the component becomes ready. The final component skills,
not the onboarding transcript, become Hermes' durable company operating layer.

## System View

```text
owner chat
  |
  v
Hermes Company OS
  |-- inventory existing company skills
  |-- detect/select available connector tools
  |-- ask only unresolved company questions
  |-- declared spot-check OR bounded discovery
  |-- per-component doctor + owner decision
  |-- fetch existing OR scaffold embedded template
  |-- skill-creator customization
  |-- validate -> approve install -> health query
  v
installed company skills
  |-- company-work ----------> project/task providers
  |-- company-people --------> directory providers
  |-- company-knowledge -----> file/wiki providers
  |-- company-comms ---------> mail/calendar/chat providers
  `-- company-decisions -----> approved decision source

Provider tools own authentication and API calls.
Component SKILL.md files own company meaning and source instructions.
Ticket-local onboarding receipts own temporary setup progress and proof.
```

## SLC Slice (Next Release)

Complete one Google Drive → Knowledge onboarding lifecycle:

1. Start or resume an onboarding receipt.
2. Inventory existing company skills and detect the Drive connector.
3. Ask the minimum company, outcome, tool-use, exclusion, and authority questions.
4. Connect through the provider-owned route when needed.
5. Follow declared-folder or bounded-discovery branches.
6. Score the Knowledge boundary and ask use-current/tidy-first/skip.
7. Scaffold or update `company-knowledge` through `skill-creator`.
8. Validate the draft and show its source/policy delta.
9. Obtain explicit installation approval and promote the skill safely.
10. Run one representative scoped retrieval and one outside-boundary refusal.
11. Return the installed component, proof, unresolved components, and exact next
    onboarding step.

## Goals

- A first-time operator completes the slice without editing files manually.
- Every asked question changes a source boundary, policy, generated skill, or
  proof obligation; safely derivable facts are not asked again.
- No component reaches `ready` without connection, approved source scope,
  validated skill, install approval, and health proof.
- The final installation contains no second company-stack configuration.

## Metric Candidates

- **Primary candidate:** pass/fail completion of the full Drive → Knowledge
  lifecycle in an isolated test workspace.
- **Direction:** pass/fail.
- **Verification idea:** assert the ordered state transitions, required human
  gates, installed skill content, inside-root success, and outside-root refusal.
- **Guard idea:** assert no secret persistence, broad Drive crawl, unapproved
  provider write, direct template install, or parallel config file.
- **Conversation candidate:** number of questions whose answers were already
  available from inventory or approved metadata; target zero redundant asks.

## Non-Goals

- Supporting every connector in the first release.
- Creating or replacing a project manager, wiki, mail client, calendar, Drive,
  directory, or decision application.
- Copying source content into an agent-memory database.
- Automatically tidying, moving, sharing, deleting, or rewriting provider data.
- Installing all five company skills by default.
- Multi-department authorization or 20–100 person deployment architecture.

## User Stories

### US-001: Guided company intake

**Description:** As an SME owner, I want Hermes to ask one understandable setup
question at a time so that I can configure the company without knowing connector
IDs or skill internals.

**Acceptance Criteria:**

- [ ] The flow starts by reading existing state and never asks for a fact it can
      safely derive from inventory or an approved connector probe.
- [ ] Every unresolved required field has an explicit question and skip/defer path.
- [ ] The user can stop and resume from a ticket-local receipt without repeating
      accepted answers.

### US-002: Tool-to-component mapping

**Description:** As an owner, I want to explain what each tool contains in my
own words so Hermes can map it to stable company entrypoints.

**Acceptance Criteria:**

- [ ] One tool may map to several components, but each receives an independent
      source boundary, doctor verdict, and acceptance decision.
- [ ] When the owner does not know the layout, discovery stays bounded,
      metadata-only, read-only, and visibly consented.
- [ ] Hermes distinguishes authoritative sources from supporting/reference sources.

### US-003: Safe connection recovery

**Description:** As an owner, I want connection problems handled through the
provider's normal authentication so I never paste credentials into chat.

**Acceptance Criteria:**

- [ ] A listed connector is not treated as healthy until status and one bounded
      read succeed.
- [ ] Failed authentication routes to provider-owned reconnect and retries only
      the cheapest status/read sequence.
- [ ] Continued failure records `blocked` without generating a ready skill.

### US-004: Reviewable component generation

**Description:** As an owner, I want to see what Hermes will believe about a
component before it becomes active.

**Acceptance Criteria:**

- [ ] Existing skills are fetched and updated; missing selected components use
      their embedded template.
- [ ] The draft states provider, approved boundary, authority, exclusions,
      read/write rules, failure behavior, and health query.
- [ ] Unresolved placeholders or source gates prevent installation.

### US-005: Proven installation

**Description:** As an owner, I want a company skill activated only after the
real workflow works.

**Acceptance Criteria:**

- [ ] The exact draft-to-installed delta is shown before approval.
- [ ] Promotion is deterministic, refuses accidental overwrite, and preserves a
      review receipt.
- [ ] One inside-boundary query succeeds and one outside-boundary query refuses
      before readiness.

## Functional Requirements

- **FR-1 — Session state:** maintain a ticket-local onboarding receipt with the
  current phase, answered questions, selected tools/components, connector
  health, proposed boundaries, approvals, draft paths, and proof status. It is
  workflow state, not a parallel runtime config.
- **FR-2 — Question engine:** derive the next question from missing required
  state; include why it matters, allowed answers, and the effect of skipping it.
- **FR-3 — Connector inventory:** show only connector tools actually available
  in the current Codex environment, plus an explicit unsupported-tool route.
- **FR-4 — Mapping catalog:** map common tool functions to Work, People,
  Knowledge, Communications, and Decisions without forcing one provider per
  component or one component per provider.
- **FR-5 — Provider playbooks:** each supported provider defines connection
  proof, boundary unit, declared spot-check, discovery limits, doctor evidence,
  exclusions, health query, and write-risk gates.
- **FR-6 — Question coverage:** collect company identity/scale, desired outcome,
  current stack in one answer, exact locations when known, source authority,
  exclusions, inspection consent, write policy, approver, and representative
  health question only when not already known.
- **FR-7 — Per-component decisions:** never combine doctor scores or approval
  decisions across components even when one provider supplies several.
- **FR-8 — Generation:** inventory/fetch before create; scaffold exactly one
  selected missing component; call `skill-creator` for semantic customization.
- **FR-9 — Validation:** run helper validation, skill validation, unresolved
  placeholder checks, natural eval, and privacy scan before promotion.
- **FR-10 — Promotion:** add a deterministic approval-gated draft-to-installed
  operation with collision detection, backup/review receipt, and post-install
  re-inventory.
- **FR-11 — Health:** each installed component owns at least one natural success
  query and one scope/failure case.
- **FR-12 — Closeout:** report configured, blocked, deferred, and skipped
  components; never describe missing components as failures or generate them
  automatically.

## Constraints

- **Security/privacy:** never request or persist credentials, account emails,
  private IDs, unrelated filenames, message bodies, or document content in
  onboarding receipts unless explicitly necessary and approved.
- **Performance:** discovery calls must have explicit limits and avoid recursive
  account-wide scans.
- **Platform:** Codex chat plus project-local skills and standard-library helper
  scripts for the first slice.
- **Budget/time:** do not add a setup UI or custom connector runtime until the
  conversational lifecycle proves insufficient.

## Autonomy Readiness

- **Human inputs/assets needed:** selected business outcome, tool selection,
  source authority, exclusions, inspection consent, boundary decision, install
  approval, and representative health question.
- **Credentials / external services:** existing provider plugins own auth; the
  first slice requires a connected Google Drive identity.
- **Compute or runtime needs:** isolated filesystem fixture for eval writes and
  a live connected-provider test for final health proof.
- **Remaining tooling gaps:** no provider catalog beyond Drive, existing-skill
  update/rollback path, or isolated multi-component eval harness exists today.
- **Hard-to-QA surfaces:** natural-language source mapping, permission visibility,
  connector rate/error behavior, and proving that an outside-boundary query was
  truly refused.
- **Human gates:** approve discovery, source boundary, provider cleanup, write
  authority, generated instructions, installation, and consequential actions.
- **Agent decision boundaries:** may inventory, ask, inspect approved metadata,
  diagnose, and draft; may not infer authority, broaden scope, collect secrets,
  mutate provider data, or promote a skill without explicit gates.

## Risks / Unknowns

- Some connectors expose too little metadata to infer structure safely; the flow
  must ask rather than compensate with content crawling.
- A tool can contain several components and a component can span several tools;
  the state machine must preserve independent source roles and approvals.
- Provider plugins vary in available status, list, and scoped-search calls.
- A generated `SKILL.md` is human-readable but not automatically safe to parse
  as arbitrary structured configuration; helpers should fetch it whole and
  validate stable markers only.
- Without isolated eval writes, fictional setup cases can contaminate the real
  checkout; such runs are invalid evidence.

## Backpressure / Evidence to Ship

- Unit tests for next-question selection, resume behavior, skip/defer, inventory,
  scaffold, promotion collision, and rollback/receipt behavior.
- Isolated integration test of every Drive → Knowledge state transition.
- Live read-only Drive proof inside one approved test folder using fake/nonprivate
  data.
- Natural success and outside-boundary refusal evals for installed
  `company-knowledge`.
- Privacy scan of receipts and generated skills.
- Independent product-contract, skill-contract, and evidence review.

## Current Gap Summary

| Product capability | Current state | Needed next |
| --- | --- | --- |
| Five stable component entrypoints | Templates exist | Keep; prove installed behavior one at a time |
| Skill inventory/fetch/scaffold/validate | Implemented and unit tested | Add existing-skill update support after MVP |
| Conversational question flow | Implemented for Drive → Knowledge | Prove with a live operator session |
| Connector selection | Drive is explicit; other providers block | Add providers only after the live Drive slice passes |
| Provider mapping | Drive Knowledge reference only | Complete Drive lifecycle, then add provider playbooks incrementally |
| Declared/discovered branches | Persisted and isolated-tested | Prove both against a live connector |
| Multi-component provider | Described; unsafe eval deferred | Build isolated fixture before claiming support |
| Installation | Preview, reviewed-hash approval, promotion, and collision refusal implemented | Add existing-skill update/rollback later |
| Health proof | Inside success/provenance and outside refusal gate implemented | Run against one approved live Drive root |
| Full onboarding proof | Isolated lifecycle passes | Complete the live owner-approved Drive operator test |

## Handoff

After this PRD is accepted, the next implementation ticket should own only the
complete Drive → Knowledge lifecycle, including the onboarding receipt,
next-question resolver, promotion command, and isolated end-to-end proof. Do not
start connector breadth until that lifecycle passes.

## Confirmed Decisions, Assumptions, and Conflict

### Confirmed from the product discussion

- Setup happens through chat with one meta onboarding skill.
- Provider plugins/MCPs/CLIs own authentication and API mechanics.
- Company behavior is exposed through five stable component skills.
- Templates live inside Hermes Company OS and seed missing component drafts.
- Each component `SKILL.md` carries its own company instructions; no `STACK.md`
  or central company schema is required.
- Hermes asks the owner when business meaning or authority is missing and maps
  the tools itself when the owner cannot provide structure.

### Assumptions to confirm before ticketing

1. A ticket-local JSON onboarding receipt is temporary, resumable workflow
   state, not a second runtime configuration.
2. Google Drive → Knowledge should be the first completely installed lifecycle
   before implementing Notion, Linear, mail, calendar, or chat breadth.
3. Work, People, Knowledge, Communications, and Decisions remain the stable
   Hermes product terms for the initial template set.

### Conflict this PRD resolves

TASK-0008 is correctly ready only for its narrow template/Drive prototype test.
The full onboarding product described here is not implemented and must not be
called ready until the SLC lifecycle and proof above pass.

## MVP Implementation Receipt

TASK-0011 implements the complete isolated Google Drive → Knowledge lifecycle
through the former `.agents/skills/hermes-company-os/scripts/onboarding.py`. It inventories
on start, derives one next step, records bounded provider and doctor evidence,
renders the accepted Knowledge template, records `skill-creator` review, binds
owner approval to the reviewed hash, refuses install collisions, and requires
inside-scope success with provenance plus outside-scope refusal before healthy.

The provider calls remain agent-operated through the Google Drive connector.
The isolated lifecycle is implemented; a live customer installation still
requires an owner-approved Drive boundary and representative health question.
