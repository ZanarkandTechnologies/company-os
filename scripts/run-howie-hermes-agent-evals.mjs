/**
 * Real Hermes behavior runs for the Howie development proof.
 *
 * Unlike run-company-manager-evals.mjs, this launches the configured
 * `howie-ai` Hermes profile against disposable, isolated workspaces. It never
 * starts a gateway, contacts a phone number, calls a live Drive MCP, or runs
 * the controlled sender. Every input is a local mock file and every side
 * effect is preserved under the declared output directory.
 */
import { createHash } from "node:crypto";
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, readdirSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const defaultOutputRoot = resolve(projectRoot, "workspaces/howie-ai-poc/agent-runs");
const scenarioTime = "2026-08-17T18:01:00.000Z";
const profileSyncScript = resolve(projectRoot, "scripts/sync-howie-ai-profile.mjs");
const profileSource = resolve(projectRoot, "profiles/howie-ai");
const managerReplyStart = "<<<MANAGER_MESSAGE>>>";
const managerReplyEnd = "<<<END_MANAGER_MESSAGE>>>";
const managerReplyInstruction = `End with one concise Telegram-ready update from Manager to the company owner wrapped exactly between ${managerReplyStart} and ${managerReplyEnd}. Put no implementation prose inside those markers. Do not mention Hermes, model providers, tools, mock fixtures, test harnesses, worker IDs, filesystem implementation, ticket filenames or IDs, profile names, or internal fixture person IDs such as Kenji or Howie. Address the recipient as 'you' and refer to other people by their business role. State what you completed, what is happening next, and any review or missing input needed. Never claim a message was sent or a person was contacted in this no-send run; say a follow-up was prepared. The recipient is reading a chat, not a file-attachment view: do not say documents are attached or attached below. Say drafts are ready for review only when the corresponding workspace files exist. Use short paragraphs, plain language, and target no more than 80 words inside the markers.`;

function managerReplyFrom(output) {
  const text = String(output || "");
  const start = text.lastIndexOf(managerReplyStart);
  if (start < 0) return null;
  const contentStart = start + managerReplyStart.length;
  const end = text.indexOf(managerReplyEnd, contentStart);
  if (end < 0) return null;
  return text.slice(contentStart, end)
    .replace(/^🎉\s*Conversation completed after .*$/gmi, "")
    .trim();
}

function hermesSessionIdFrom(output) {
  return String(output || "").match(/^Session:\s+([A-Za-z0-9_-]{8,128})\s*$/m)?.[1] ?? null;
}

function invocationSucceeded(output) {
  const text = `${output?.stdout || ""}\n${output?.stderr || ""}`;
  return output?.status === 0
    && !/no api key found|could not authenticate|authentication (?:failed|required)|provider .* unavailable/i.test(text);
}

export function managerReplyChecks(reply) {
  const text = String(reply || "");
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const claimsAttachment = /\battach(?:ed|ment|ments)?\b/i.test(text);
  return {
    manager_reply_recorded: Boolean(text),
    manager_reply_concise: words > 0 && words <= 120,
    manager_reply_uses_business_language: !/(?:Hermes|provider|filesystem|mock fixture|test harness|worker ID|ticket\.md|progress\.md|artifacts? folder|\bTASK-\d+\b|Kenji|Howie|edits? succeeded)/i.test(text),
    manager_reply_makes_no_false_send_claim: !/\b(?:I|we|Manager)\s+(?:have\s+)?(?:sent|contacted|messaged)\b/i.test(text),
    manager_reply_makes_no_unavailable_attachment_claim: !claimsAttachment
  };
}

function visibleToolEvents(stdout, traceText = "") {
  const events = [];
  let pendingTool = null;
  const pushPending = () => {
    if (!pendingTool) return;
    events.push(pendingTool.path ? `${pendingTool.name} · ${pendingTool.path}` : pendingTool.name);
    pendingTool = null;
  };
  for (const rawLine of `${stdout || ""}\n${traceText || ""}`.split("\n")) {
    const line = rawLine.trim();
    const tool = line.match(/^📞 Tool \d+: ([a-z_]+)/i);
    if (tool) {
      pushPending();
      pendingTool = { name: tool[1], path: null };
      continue;
    }
    const path = line.match(/^"path":\s*"([^"]+)"/);
    if (path && pendingTool && !pendingTool.path) {
      pendingTool.path = path[1];
      continue;
    }
    if (/^✅ Tool \d+ completed/.test(line)) pushPending();
  }
  pushPending();
  return [...new Set(events)].slice(0, 18);
}

function usage() {
  return [
    "Usage: HOWIE_HERMES_PROFILE=<profile> HOWIE_HERMES_PROFILE_DIR=<profile-dir> HERMES_EVAL_PROVIDER=<provider> HERMES_EVAL_MODEL=<model> node scripts/run-howie-hermes-agent-evals.mjs [--output path] [--scenario id] [--dry-run]",
    "",
    "The invoking environment must already hold a development model credential.",
    "A real run opens a fresh Howie AI Hermes chat against a disposable workspace. It captures the visible verbose file-tool trace but never starts a gateway, invokes Drive MCP, or sends Telegram."
  ].join("\n");
}

function parseArgs(argv) {
  const options = { output: null, dryRun: false, scenario: null };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--dry-run") {
      options.dryRun = true;
      continue;
    }
    if (argument === "--output") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) throw new Error("--output requires a path.");
      options.output = resolve(value);
      index += 1;
      continue;
    }
    if (argument === "--scenario") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) throw new Error("--scenario requires a scenario ID.");
      options.scenario = value;
      index += 1;
      continue;
    }
    if (argument === "--help") {
      console.log(usage());
      process.exit(0);
    }
    throw new Error(`Unknown argument: ${argument}\n\n${usage()}`);
  }
  return options;
}

function timestampSlug() {
  return new Date().toISOString().replace(/[:.]/g, "-");
}

function write(path, text) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, text.endsWith("\n") ? text : `${text}\n`, "utf8");
}

function copyFile(source, target) {
  write(target, readFileSync(source, "utf8"));
}

function copyDirectory(source, target) {
  for (const entry of readdirSync(source, { withFileTypes: true })) {
    const from = resolve(source, entry.name);
    const to = resolve(target, entry.name);
    if (entry.isDirectory()) copyDirectory(from, to);
    else if (entry.isFile()) copyFile(from, to);
  }
}

function snapshot(root) {
  const files = [];
  function visit(directory) {
    if (!existsSync(directory)) return;
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) visit(path);
      else if (entry.isFile()) {
        const bytes = readFileSync(path);
        const relativePath = relative(root, path).replaceAll("\\", "/");
        const item = {
          path: relativePath,
          bytes: statSync(path).size,
          sha256: createHash("sha256").update(bytes).digest("hex")
        };
        if (relativePath === "SOUL.md"
          || /^profile\/(?:SOUL\.md|config\.template\.yaml)$/.test(relativePath)
          || /^meetings\/[^/]+\/[^/]+\.md$/.test(relativePath)
          || relativePath === "company-directory.md"
          || /^skills\/[^/]+\/(?:SKILL\.md|templates\/[^/]+\.md)$/.test(relativePath)
          || /^shared-drive\/.+\.(?:json|md)$/.test(relativePath)
          || /^tickets\/(?:archive\/)?TASK-\d+\/(?:ticket|progress)\.md$/.test(relativePath)
          || /^tickets\/(?:archive\/)?TASK-\d+\/artifacts\/[^/]+\.md$/.test(relativePath)) {
          const content = bytes.toString("utf8");
          item.content_preview = content.length > 4_000 ? `${content.slice(0, 4_000)}\n… [truncated]` : content;
        }
        files.push(item);
      }
    }
  }
  visit(root);
  return files.sort((left, right) => left.path.localeCompare(right.path));
}

function delta(before, after) {
  const beforeByPath = new Map(before.map((file) => [file.path, file]));
  const afterByPath = new Map(after.map((file) => [file.path, file]));
  return {
    created: after.filter((file) => !beforeByPath.has(file.path)),
    modified: after.filter((file) => beforeByPath.has(file.path) && beforeByPath.get(file.path).sha256 !== file.sha256)
      .map((file) => ({ ...file, previous_sha256: beforeByPath.get(file.path).sha256 })),
    deleted: before.filter((file) => !afterByPath.has(file.path))
  };
}

function sharedInputs(workspaceRoot, { includeDrive = true } = {}) {
  copyFile(resolve(profileSource, "SOUL.md"), resolve(workspaceRoot, "profile/SOUL.md"));
  copyFile(resolve(profileSource, "config.template.yaml"), resolve(workspaceRoot, "profile/config.template.yaml"));
  copyFile(resolve(profileSource, "workspace-context.hermes.md"), resolve(workspaceRoot, ".hermes.md"));
  write(resolve(workspaceRoot, "company-directory.md"), `# Aurora Lithium — internal directory\n\nUse this directory to identify the accountable lead for a missing decision, source, or review.\n\n| Directory ID | Team member | Role | Accountable for |\n| --- | --- | --- | --- |\n| owner | Marcus Hale | Company Owner | priorities, deadline decisions, and escalations |\n| principal-geologist | Dr Leila Noor | Principal Geologist | technical source data and technical review |\n| finance-lead | Mina Patel | Finance Lead | pricing scenarios, cash assumptions, and finance review |\n| growth-lead | Jonah Reed | Growth Lead | investor positioning and outreach review |\n| operations-lead | Rohan Davis | Operations Lead | compliance evidence and operating-risk review |\n`);
  copyDirectory(resolve(profileSource, "skills"), resolve(workspaceRoot, "skills"));
  if (includeDrive) {
    copyDirectory(resolve(projectRoot, "fixtures/company-manager/shared-drive"), resolve(workspaceRoot, "shared-drive"));
  }
}

function ticketText({ id, title, workstream, startAt, dueAt, status, requirements = [], dependencies = [], artifact = null, reviewState = "pending_input" }) {
  return `---
ticket_id: "${id}"
title: "${title}"
description: "Operating task recorded from the current meeting plan."
workstream: "${workstream}"
owner_id: "manager"
reviewer_id: "company-owner"
start_at: "${startAt}"
due_at: "${dueAt}"
status: "${status}"
blocking_inputs: []
requirements: ${JSON.stringify(requirements)}
skill_dependencies: ${JSON.stringify(dependencies)}
artifact: ${artifact ? JSON.stringify(artifact) : "null"}
review: {"reviewer_id":"company-owner","state":"${reviewState}","decided_at":null,"decision":null}
source: {"meeting_id":"hermes-agent-eval","recorded_at":"${startAt}"}
created_at: "${startAt}"
updated_at: "${startAt}"
---
# ${id}: ${title}

## Current state

${status}

## Artifact

${artifact?.path ?? "No artifact drafted yet."}

## Reviewer

company owner
`;
}

function acquireProfileLock(profileDirectory) {
  const lockPath = resolve(profileDirectory, ".howie-agent-eval.lock");
  try {
    const descriptor = openSync(lockPath, "wx");
    writeFileSync(descriptor, JSON.stringify({ pid: process.pid, started_at: new Date().toISOString() }, null, 2), "utf8");
    closeSync(descriptor);
  } catch (error) {
    if (error && typeof error === "object" && error.code === "EEXIST") {
      throw new Error(`Another real Howie eval may be using ${profileDirectory}. Refusing to share a Hermes profile; use a fresh profile directory or remove the stale lock after inspecting it.`);
    }
    throw error;
  }
  return () => {
    if (existsSync(lockPath)) unlinkSync(lockPath);
  };
}

function syncProfileToWorkspace({ profileDirectory, workspaceRoot, env }) {
  const sync = spawnSync(process.execPath, [profileSyncScript, "--target", profileDirectory, "--workspace-root", workspaceRoot, "--apply"], {
    cwd: projectRoot,
    env,
    encoding: "utf8",
    timeout: 30_000,
    maxBuffer: 1_000_000
  });
  if (sync.status !== 0) {
    throw new Error(`Could not bind isolated Hermes profile to ${workspaceRoot}: ${sync.stderr || sync.stdout || "sync failed"}`);
  }
  return { stdout: sync.stdout || "", stderr: sync.stderr || "" };
}

function exportSessionTrace({ scenarioRoot, workspaceRoot, env }) {
  const tracePath = resolve(scenarioRoot, "session.jsonl");
  const output = spawnSync(env.HERMES_BIN || "hermes", [
    "-p", env.HOWIE_HERMES_PROFILE || "howie-ai",
    "sessions", "export", tracePath,
    "--format", "jsonl",
    "--source", "howie-eval",
    "--cwd", workspaceRoot,
    "--redact",
    "--yes"
  ], { cwd: projectRoot, env, encoding: "utf8", timeout: 30_000, maxBuffer: 2_000_000 });
  write(resolve(scenarioRoot, "session-export.txt"), `${output.stdout || ""}${output.stderr || ""}`);
  return existsSync(tracePath) ? readFileSync(tracePath, "utf8") : "";
}

function progressText(id, title, at, event) {
  return `# Progress: ${id} — ${title}

This log is append-only.

- ${at} — **${event.type}** — ${JSON.stringify(event)}
`;
}

function meetingScenario(workspaceRoot) {
  sharedInputs(workspaceRoot);
  write(resolve(workspaceRoot, "inbox/meeting-summary.md"), `# Weekly operating meeting — Aurora Lithium\n\n**Meeting date:** 11 August 2026\n**Planning window:** 11–17 August 2026\n**Attendees:** Company Owner, Principal Geologist, Finance Lead\n\n## What must move this week\n\nAurora Lithium needs a reviewable technical picture before the investor conversation on Friday. The shared Drive source is the current approved source for the geo draft. The Principal Geologist will confirm technical interpretation before that draft can be used downstream.\n\n1. **Geo report — due Wednesday 17:00.** Create a concise technical draft from the shared Aurora Lithium source. It must be ready for Principal Geologist review by Tuesday afternoon.\n2. **Fundraising deck — due Thursday 17:00.** Build the investor narrative once the geo report is approved. Finance must provide the funding target, use of funds, and runway assumptions; ask the Finance Lead for this in parallel so the deck does not wait unnecessarily.\n3. **Financial model — due Thursday 17:00.** Refresh base, downside, and upside cases after the geo report is approved. The Finance Lead will review the assumptions.\n4. **Weekly operating report — due Friday 16:00.** Combine the reviewed fundraising deck and financial model. It should tell the owner what moved, what is blocked, and next week's decision points.\n\n## Operating decisions\n\n- The Manager owns coordination and initial drafts.\n- The Company Owner reviews business deliverables; the Principal Geologist reviews the technical report.\n- Any missing human input becomes one scoped follow-up. Prepare the first delivery only; do not send it in this test workspace.\n- For this proof, schedule the first technical-review follow-up for **12 August 12:00 UTC** and the first finance-input follow-up for **11 August 16:00 UTC**.\n`);
  return `This is a real Howie AI development chat at 2026-08-11T09:00:00.000Z. The company owner has sent the meeting summary in inbox/meeting-summary.md. Read that summary, company-directory.md, shared-drive/aurora-lithium/geo-source.json, skills/meeting-intake/SKILL.md, skills/company-ops-manager/SKILL.md, and the four relevant artifact skills. Use only the file tool. Do not call an external service, use MCP, or send a message.\n\nTurn the meeting into exactly TASK-2001 through TASK-2004, each with ticket.md and append-only progress.md using the canonical shape from the company-ops-manager skill. Append meeting_scanned for every ticket. Create dependency records so TASK-2002 and TASK-2003 require the approved geo-report output from TASK-2001, and TASK-2004 requires the approved fundraising-deck and financial-model outputs.\n\nMove the needle in this same turn: TASK-2001 has its source ready. Create tickets/TASK-2001/artifacts/geo-report-draft.md from the geo-report template, populated only from the shared source. Record work_started and artifact_drafted, set the task to awaiting_review, and add a technical-review human requirement for principal-geologist with a prepared draft follow-up: attempt 1, last_at 2026-08-11T09:00:00.000Z, next_at 2026-08-12T12:00:00.000Z, status draft.\n\nLeave TASK-2002, TASK-2003, and TASK-2004 blocked by their declared upstream outputs. TASK-2002 also needs one funding-terms human requirement owned by finance-lead. Prepare its attempt-1 draft follow-up at 2026-08-11T09:00:00.000Z with next_at 2026-08-11T16:00:00.000Z, and append matching telegram_delivery_draft events for both prepared follow-ups. Do not create downstream artifacts. In the final owner update name the completed geo draft, the two roles being chased, their next chase times, and the dependency that keeps each downstream deliverable blocked. ${managerReplyInstruction}`;
}

function meetingScenarioV2(workspaceRoot) {
  sharedInputs(workspaceRoot);
  const meetingId = "MEETING-2026-08-17-aurora-weekly";
  const transcript = resolve(projectRoot, "fixtures/company-manager/meetings/aurora-operator-weekly-transcript.md");
  copyFile(transcript, resolve(workspaceRoot, "meetings", meetingId, "transcript.md"));
  return `This is a Howie AI development chat at 2026-08-17T09:00:00.000Z. The company owner uploaded a weekly meeting transcript at meetings/${meetingId}/transcript.md and said: “Here are the weekly notes. Take the plan forward now.” Use only the file tool. Do not call an external service, use MCP, send a message, or change profile/runtime configuration.

Read these exact files before acting; do not browse directories or search unrelated files:
- .hermes.md
- meetings/${meetingId}/transcript.md
- company-directory.md
- shared-drive/aurora-lithium/sources/mining/technical-source.md
- shared-drive/aurora-lithium/sources/growth/investor-audience-research.md
- shared-drive/aurora-lithium/sources/operations/compliance-evidence.md
- shared-drive/aurora-lithium/sources/finance/operating-assumptions.md
- skills/meeting-intake/SKILL.md
- skills/company-ops-manager/SKILL.md
- skills/geo-report/SKILL.md and skills/geo-report/templates/geo-report.md
- skills/customer-research/SKILL.md and skills/customer-research/templates/customer-research-brief.md
- skills/compliance-report/SKILL.md and skills/compliance-report/templates/compliance-report.md

Create exactly six canonical tickets: TASK-3001 through TASK-3006. Each must have JSON-valued YAML front matter in ticket.md, append-only progress.md, clear title/description/workstream/owner/reviewer/start_at/due_at/status, requirements, mock_skill_dependencies, artifact/review state, and meeting source. Append meeting_received and meeting_scanned events. Use the meeting's deadlines exactly. Work through all six tickets rather than stopping to describe a plan.

Execution discipline: once the required files are read, begin creating the ticket and artifact files immediately. Do not restate the plan, debate the schema, or narrate your preparation. Use concise, complete content and batch independent file writes whenever the file tool permits.

Move the needle in this same turn. The technical source, investor audience research, and compliance evidence are ready. Create these three reviewable artifacts from their owned templates and only the named source evidence: tickets/TASK-3001/artifacts/geo-report-draft.md, tickets/TASK-3002/artifacts/customer-research-brief.md, and tickets/TASK-3003/artifacts/compliance-report-draft.md. Record work_started and artifact_drafted; put TASK-3001, TASK-3002, and TASK-3003 in awaiting_review. Prepare one requirement-local draft follow-up for principal-geologist to review TASK-3001, growth-lead to review TASK-3002, and operations-lead to review TASK-3003. Each must have a helpful phone-readable brief, attempt 1, last_at 2026-08-17T09:00:00.000Z, a next_at before its task deadline, status pending, delivery_id, and a matching telegram_delivery_draft progress event. Do not claim those messages were sent.

TASK-3004 is the 13-week cash forecast. It may read the finance baseline but must remain blocked until finance-lead chooses the pricing/revenue case. Prepare a contextual finance follow-up that recommends Base and asks for Base, Downside, or another stated case; set its first next_at to 2026-08-17T16:00:00.000Z. Do not draft the forecast yet. TASK-3005 is the fundraising deck and remains blocked until the approved geo report and approved cash forecast outputs exist. TASK-3006 is the weekly operating report and remains blocked until the approved geo report, customer research, compliance report, cash forecast, and fundraising deck outputs exist. Express those upstream dependencies as skill_output requirements; do not create their artifacts.

Finish with the concise owner update required below. It should say that you created the plan, started the ready work, named the drafts ready for review, explained the finance blocker and next follow-up, and explained what must be approved before the deck and weekly report begin. ${managerReplyInstruction}`;
}

function expertChaseScenario(workspaceRoot) {
  sharedInputs(workspaceRoot, { includeDrive: false });
  const now = "2026-08-14T10:00:00.000Z";
  const requirement = {
    id: "geo-source-refresh",
    type: "human_input",
    description: "The missing geo source workbook must be refreshed before the report can continue.",
    state: "unresolved",
    human: { employee_id: null, role: "Principal Geologist", channel: "telegram_delivery", question: "Please refresh the Aurora Lithium source workbook for this week's report." },
    follow_up: { employee_id: null, attempts: 0, last_at: null, next_at: now, cooldown_minutes: 120, delivery_id: null, status: "pending", escalation: null }
  };
  write(resolve(workspaceRoot, "tickets/TASK-2101/ticket.md"), ticketText({ id: "TASK-2101", title: "Prepare the geo report", workstream: "Geology", startAt: "2026-08-11T09:00:00.000Z", dueAt: "2026-08-15T17:00:00.000Z", status: "blocked", requirements: [requirement] }));
  write(resolve(workspaceRoot, "tickets/TASK-2101/progress.md"), progressText("TASK-2101", "Prepare the geo report", "2026-08-14T09:55:00.000Z", { at: "2026-08-14T09:55:00.000Z", type: "requirement_blocked", requirement_id: "geo-source-refresh", reason: "geo source workbook missing" }));
  return `This is a real Howie AI development chat at ${now}. The company owner says: “The geo report is blocked on a missing source workbook. Run pulse.” Read company-directory.md, skills/company-ops-manager/SKILL.md, and tickets/TASK-2101. The required shared source is deliberately absent. Use only the file tool. Match the missing geology input to principal-geologist. Update that one human requirement and its follow_up with employee_id principal-geologist, attempt 1, last_at ${now}, next_at 2026-08-14T12:00:00.000Z, status draft, and delivery_id TASK-2101:geo-source-refresh:1. Append exactly one matching telegram_delivery_draft event to progress.md. Keep the ticket blocked. Do not create an artifact, use MCP, call an external service, or send a message. In the final owner update say which role owns the missing source, that the first follow-up is prepared, and exactly when the next chase is due. ${managerReplyInstruction}`;
}

function escalationScenario(workspaceRoot) {
  sharedInputs(workspaceRoot, { includeDrive: false });
  const startAt = "2026-08-11T09:00:00.000Z";
  const requirement = {
    id: "geo-source-file",
    type: "human_input",
    description: "The Principal Geologist must refresh the missing geo source workbook.",
    state: "unresolved",
    human: { employee_id: "principal-geologist", channel: "telegram_delivery", question: "Please refresh the scoped geo source workbook." },
    follow_up: { employee_id: "principal-geologist", attempts: 2, last_at: "2026-08-17T16:00:00.000Z", next_at: "2026-08-17T18:00:00.000Z", cooldown_minutes: 120, delivery_id: "TASK-2201:geo-source-file:2", status: "pending", escalation: null }
  };
  write(resolve(workspaceRoot, "tickets/TASK-2201/ticket.md"), ticketText({ id: "TASK-2201", title: "Prepare the geo report", workstream: "Geology", startAt, dueAt: "2026-08-13T09:00:00.000Z", status: "blocked", requirements: [requirement] }));
  write(resolve(workspaceRoot, "tickets/TASK-2201/progress.md"), `# Progress: TASK-2201 — Prepare the geo report\n\nThis log is append-only.\n\n- 2026-08-15T09:00:00.000Z — **telegram_delivery_draft** — {"at":"2026-08-15T09:00:00.000Z","type":"telegram_delivery_draft","requirement_id":"geo-source-file","employee_id":"principal-geologist","delivery_id":"TASK-2201:geo-source-file:1","attempt":1,"delivery":"draft_only"}\n- 2026-08-17T16:00:00.000Z — **telegram_delivery_draft** — {"at":"2026-08-17T16:00:00.000Z","type":"telegram_delivery_draft","requirement_id":"geo-source-file","employee_id":"principal-geologist","delivery_id":"TASK-2201:geo-source-file:2","attempt":2,"delivery":"draft_only"}\n`);
  return `This is a real Howie AI development chat at ${scenarioTime}. The company owner says: “It’s the end of the week. Run pulse.” Read company-directory.md, skills/company-ops-manager/SKILL.md, and tickets/TASK-2201. The source workbook is deliberately absent. The geo report is four days overdue and two scoped follow-ups have already been prepared. Use only the file tool to record the required escalation. Keep TASK-2201 blocked; do not create an artifact, append another follow-up, use MCP, call an external service, or send a message. Append exactly one ticket_escalated progress event with next_owner_id owner and the overdue-after-two-follow-ups reason. Update only the requirement-local follow_up state: preserve attempts 2 and last_at, set next_at null, set status escalated, and add escalation metadata. In the final owner update say what is complete, what is blocked, who has already been followed up with, and that the owner escalation is prepared. ${managerReplyInstruction}`;
}

const scenarios = [
  {
    id: "real_meeting_to_tickets",
    title: "Real Hermes turns a weekly meeting into a six-ticket operating plan",
    channelMessage: "Here are the weekly Aurora Lithium meeting notes. Take the plan forward now.",
    setup: meetingScenarioV2,
    score: ({ workspaceRoot, output }) => {
      const ids = ["TASK-3001", "TASK-3002", "TASK-3003", "TASK-3004", "TASK-3005", "TASK-3006"];
      const ticketTextById = Object.fromEntries(ids.map((id) => [id, existsSync(resolve(workspaceRoot, "tickets", id, "ticket.md")) ? readFileSync(resolve(workspaceRoot, "tickets", id, "ticket.md"), "utf8") : ""]));
      const progressTextById = Object.fromEntries(ids.map((id) => [id, existsSync(resolve(workspaceRoot, "tickets", id, "progress.md")) ? readFileSync(resolve(workspaceRoot, "tickets", id, "progress.md"), "utf8") : ""]));
      const ticketsCreated = ids.every((id) => new RegExp(`^ticket_id:\\s*[\"']?${id}[\"']?\\s*$`, "m").test(ticketTextById[id]) && progressTextById[id].includes("meeting_scanned"));
      const readyArtifacts = [
        ["TASK-3001", "geo-report-draft.md", "principal-geologist"],
        ["TASK-3002", "customer-research-brief.md", "growth-lead"],
        ["TASK-3003", "compliance-report-draft.md", "operations-lead"]
      ];
      const readyWorkDrafted = readyArtifacts.every(([ticketId, artifact, reviewer]) => {
        const path = resolve(workspaceRoot, "tickets", ticketId, "artifacts", artifact);
        return /^status:\s*[\"']?awaiting_review[\"']?\s*$/m.test(ticketTextById[ticketId])
          && progressTextById[ticketId].includes("work_started")
          && progressTextById[ticketId].includes("artifact_drafted")
          && progressTextById[ticketId].includes("telegram_delivery_draft")
          && ticketTextById[ticketId].includes(reviewer)
          && existsSync(path);
      });
      const blockedDownstream = ["TASK-3004", "TASK-3005", "TASK-3006"].every((id) => /^status:\s*[\"']?blocked[\"']?\s*$/m.test(ticketTextById[id]));
      const financeChasePrepared = ticketTextById["TASK-3004"].includes("finance-lead")
        && ticketTextById["TASK-3004"].includes("Base")
        && ticketTextById["TASK-3004"].includes("2026-08-17T16:00:00.000Z")
        && progressTextById["TASK-3004"].includes("telegram_delivery_draft");
      const dependencyMapRecorded = ticketTextById["TASK-3005"].includes("TASK-3001")
        && ticketTextById["TASK-3005"].includes("TASK-3004")
        && ["TASK-3001", "TASK-3002", "TASK-3003", "TASK-3004", "TASK-3005"].every((id) => ticketTextById["TASK-3006"].includes(id));
      return {
        pass: invocationSucceeded(output) && ticketsCreated && readyWorkDrafted && blockedDownstream && financeChasePrepared && dependencyMapRecorded,
        checks: {
          hermes_session_completed: invocationSucceeded(output),
          six_tickets_created: ticketsCreated,
          three_ready_artifacts_drafted_for_review: readyWorkDrafted,
          three_downstream_tickets_blocked_by_dependencies: blockedDownstream,
          finance_follow_up_prepared: financeChasePrepared,
          deck_and_weekly_dependencies_recorded: dependencyMapRecorded
        }
      };
    }
  },
  {
    id: "real_blocked_ticket_expert_chase",
    title: "Real Hermes finds the right expert for blocked work",
    channelMessage: "The geo report is blocked on a missing source workbook. Run pulse.",
    setup: expertChaseScenario,
    score: ({ workspaceRoot, output }) => {
      const ticket = readFileSync(resolve(workspaceRoot, "tickets/TASK-2101/ticket.md"), "utf8");
      const progress = readFileSync(resolve(workspaceRoot, "tickets/TASK-2101/progress.md"), "utf8");
      const blocked = /^status:\s*["']?blocked["']?\s*$/m.test(ticket);
      const expertSelected = ticket.includes("principal-geologist") && progress.includes('"employee_id":"principal-geologist"');
      const firstFollowUp = ticket.includes('"attempts":1') && progress.includes("telegram_delivery_draft")
        && progress.includes('"delivery_id":"TASK-2101:geo-source-refresh:1"');
      const nextChase = ticket.includes("2026-08-14T12:00:00.000Z");
      const noArtifact = !existsSync(resolve(workspaceRoot, "tickets/TASK-2101/artifacts"));
      return {
        pass: invocationSucceeded(output) && blocked && expertSelected && firstFollowUp && nextChase && noArtifact,
        checks: {
          hermes_session_completed: invocationSucceeded(output),
          blocked_requirement_detected: blocked,
          geology_expert_selected: expertSelected,
          first_follow_up_prepared: firstFollowUp,
          next_chase_scheduled: nextChase,
          no_artifact_created_for_missing_input: noArtifact
        }
      };
    }
  },
  {
    id: "real_missing_drive_escalation",
    title: "Real Hermes keeps missing Drive work blocked and escalates",
    channelMessage: "It's the end of the week. Run pulse.",
    setup: escalationScenario,
    score: ({ workspaceRoot, output }) => {
      const ticket = readFileSync(resolve(workspaceRoot, "tickets/TASK-2201/ticket.md"), "utf8");
      const progress = readFileSync(resolve(workspaceRoot, "tickets/TASK-2201/progress.md"), "utf8");
      const priorFollowUps = (progress.match(/\*\*telegram_delivery_draft\*\*/g) || []).length === 2;
      return {
        pass: invocationSucceeded(output) && ticket.includes('status: "blocked"') && ticket.includes("attempts\":2")
          && ticket.includes("status\":\"escalated\"") && priorFollowUps && progress.includes("ticket_escalated")
          && !existsSync(resolve(workspaceRoot, "tickets/TASK-2201/artifacts")),
        checks: {
          hermes_session_completed: invocationSucceeded(output),
          ticket_stays_blocked: ticket.includes('status: "blocked"'),
          two_prior_follow_ups_found: priorFollowUps,
          requirement_local_escalation_recorded: ticket.includes("attempts\":2") && ticket.includes("status\":\"escalated\"") && progress.includes("ticket_escalated"),
          no_artifact_created_for_missing_input: !existsSync(resolve(workspaceRoot, "tickets/TASK-2201/artifacts"))
        }
      };
    }
  }
];

function runScenario(scenario, outputRoot, env, dryRun, profileDirectory) {
  const scenarioRoot = resolve(outputRoot, "runs", scenario.id);
  const workspaceRoot = resolve(scenarioRoot, "workspace");
  mkdirSync(workspaceRoot, { recursive: true });
  const prompt = scenario.setup(workspaceRoot);
  write(resolve(scenarioRoot, "prompt.md"), prompt);
  const before = snapshot(workspaceRoot);
  let output = { status: 0, stdout: "DRY RUN — Hermes not invoked.", stderr: "" };
  let sessionTrace = "";
  if (!dryRun) {
    const provider = env.HERMES_EVAL_PROVIDER;
    const model = env.HERMES_EVAL_MODEL;
    if (!provider || !model) throw new Error("HERMES_EVAL_PROVIDER and HERMES_EVAL_MODEL are required for a real agent run.\n\n" + usage());
    const profileSync = syncProfileToWorkspace({ profileDirectory, workspaceRoot, env });
    write(resolve(scenarioRoot, "profile-sync.txt"), `${profileSync.stdout}${profileSync.stderr}`);
    output = spawnSync(env.HERMES_BIN || "hermes", [
      "-p", env.HOWIE_HERMES_PROFILE || "howie-ai",
      "chat",
      "--query", prompt,
      "--verbose",
      "--source", "howie-eval",
      "--provider", provider,
      "-m", model,
      "--in", workspaceRoot,
      "-t", "file,skills",
      "--max-turns", "80"
    ], { cwd: projectRoot, env, encoding: "utf8", timeout: 300_000, maxBuffer: 2_000_000 });
    sessionTrace = exportSessionTrace({ scenarioRoot, workspaceRoot, env });
  }
  write(resolve(scenarioRoot, "stdout.txt"), output.stdout || "");
  write(resolve(scenarioRoot, "stderr.txt"), output.stderr || "");
  const after = snapshot(workspaceRoot);
  const managerReply = dryRun ? null : managerReplyFrom(output.stdout);
  const toolTrace = dryRun ? [] : visibleToolEvents(output.stdout, sessionTrace);
  const behaviorScore = dryRun ? { pass: null, checks: {}, reason: "Fixture prepared; Hermes intentionally not invoked." } : scenario.score({ workspaceRoot, output });
  const replyChecks = dryRun ? {} : managerReplyChecks(managerReply);
  const score = dryRun ? behaviorScore : {
    ...behaviorScore,
    pass: behaviorScore.pass && Object.values(replyChecks).every(Boolean),
    checks: { ...behaviorScore.checks, ...replyChecks }
  };
  const result = {
    id: scenario.id,
    title: scenario.title,
    real_agent: !dryRun,
    profile: env.HOWIE_HERMES_PROFILE || "howie-ai",
    provider: env.HERMES_EVAL_PROVIDER ?? null,
    model: env.HERMES_EVAL_MODEL ?? null,
    hermes_session_id: dryRun ? null : hermesSessionIdFrom(output.stdout),
    channel_message: scenario.channelMessage,
    manager_reply: managerReply,
    tool_trace: toolTrace,
    tool_trace_source: dryRun ? null : "Hermes verbose chat output plus a redacted session export",
    exit_code: output.status ?? 1,
    timed_out: Boolean(output.error?.code === "ETIMEDOUT"),
    pass: score.pass,
    checks: score.checks,
    reason: score.reason ?? null,
    files: { setup: before, delta: delta(before, after), final: after },
    artifact_paths: {
      prompt: resolve(scenarioRoot, "prompt.md"),
      stdout: resolve(scenarioRoot, "stdout.txt"),
      stderr: resolve(scenarioRoot, "stderr.txt"),
      session_trace: resolve(scenarioRoot, "session.jsonl"),
      workspace: workspaceRoot
    }
  };
  write(resolve(scenarioRoot, "result.json"), JSON.stringify(result, null, 2));
  return result;
}

export function runHowieHermesAgentEvals({ output, dryRun = false, scenario = null, env = process.env } = {}) {
  const outputRoot = resolve(output ?? defaultOutputRoot, output ? "" : `${timestampSlug()}-real-hermes`);
  if (existsSync(outputRoot)) throw new Error(`Refusing to overwrite agent-eval output: ${outputRoot}`);
  mkdirSync(outputRoot, { recursive: true });
  const profileDirectory = env.HOWIE_HERMES_PROFILE_DIR ? resolve(env.HOWIE_HERMES_PROFILE_DIR) : null;
  if (!dryRun && !profileDirectory) throw new Error("HOWIE_HERMES_PROFILE_DIR is required for a real agent run so every scenario can bind an isolated filesystem root.\n\n" + usage());
  const releaseProfileLock = dryRun ? null : acquireProfileLock(profileDirectory);
  const startedAt = new Date().toISOString();
  const selectedScenarios = scenario === null
    ? scenarios
    : scenarios.filter((candidate) => candidate.id === scenario);
  if (selectedScenarios.length === 0) {
    releaseProfileLock?.();
    throw new Error(`Unknown scenario: ${scenario}. Available: ${scenarios.map((candidate) => candidate.id).join(", ")}`);
  }
  let results;
  try {
    results = selectedScenarios.map((candidate) => runScenario(candidate, outputRoot, env, dryRun, profileDirectory));
  } finally {
    releaseProfileLock?.();
  }
  const summary = {
    schema_version: 1,
    suite: "howie-real-hermes-agent",
    started_at: startedAt,
    completed_at: new Date().toISOString(),
    real_agent: !dryRun,
    profile: env.HOWIE_HERMES_PROFILE || "howie-ai",
    provider: env.HERMES_EVAL_PROVIDER ?? null,
    model: env.HERMES_EVAL_MODEL ?? null,
    counts: {
      pass: results.filter((result) => result.pass === true).length,
      fail: results.filter((result) => result.pass === false).length,
      skipped: results.filter((result) => result.pass === null).length
    },
    pass: dryRun ? null : results.every((result) => result.pass === true),
    scenarios: results.map((result) => ({ id: result.id, title: result.title, pass: result.pass, exit_code: result.exit_code, result_path: resolve(outputRoot, "runs", result.id, "result.json") })),
    safety: {
      gateway_started: false,
      telegram_sent: false,
      live_drive_mcp_used: false,
      credentials_written: false
    }
  };
  write(resolve(outputRoot, "summary.json"), JSON.stringify(summary, null, 2));
  return { outputRoot, summary, exitCode: summary.pass === false ? 1 : 0 };
}

const invokedAsScript = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedAsScript) {
  try {
    const result = runHowieHermesAgentEvals(parseArgs(process.argv.slice(2)));
    console.log(JSON.stringify({ outputRoot: result.outputRoot, ...result.summary }, null, 2));
    process.exitCode = result.exitCode;
  } catch (error) {
    console.error(`Howie Hermes agent eval error: ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 2;
  }
}
