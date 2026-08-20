import { existsSync, mkdirSync, readFileSync, renameSync, unlinkSync, writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { basename, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { assertValidManagerState } from "./manager-state.mjs";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const defaultOpsRoot = resolve(projectRoot, "workspaces/howie-ai/ops");
const taskIdPattern = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;

function copy(value) {
  return structuredClone(value);
}

function isoNow(value) {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) throw new TypeError("now must be an ISO timestamp.");
  return timestamp.toISOString();
}

function ticketIdFor(commitment) {
  const ticketId = commitment.taskLink.id;
  if (!taskIdPattern.test(ticketId)) throw new TypeError(`Task id ${JSON.stringify(ticketId)} is unsafe for the filesystem board.`);
  return ticketId;
}

function laneFor(commitment) {
  if (commitment.status === "resolved") return "done";
  if (commitment.owner === "unresolved" || commitment.deadline === null || commitment.requiredArtifact === null) return "blocked";
  if (commitment.owner === "howie") return "todo";
  return "waiting_signal";
}

function blockerFor(commitment) {
  const missing = [];
  if (commitment.owner === "unresolved") missing.push("owner");
  if (commitment.deadline === null) missing.push("deadline");
  if (commitment.requiredArtifact === null) missing.push("required artifact");
  return missing.length === 0 ? null : `Meeting commitment is incomplete: missing ${missing.join(", ")}.`;
}

function dueEntriesFor(commitment, now) {
  if (commitment.status === "resolved") return [];
  const ticketId = ticketIdFor(commitment);
  const entries = [];
  if (commitment.nextReminderAt !== null && commitment.nextReminderAt <= now) {
    entries.push({ ticketId, at: commitment.nextReminderAt, reason: "reminder due", owner: commitment.owner, title: commitment.title });
  }
  if (commitment.expectedMeetingNote && commitment.expectedMeetingNote.receivedAt === null && commitment.expectedMeetingNote.deadline <= now) {
    entries.push({ ticketId, at: commitment.expectedMeetingNote.deadline, reason: "meeting note overdue", owner: "howie", title: commitment.title });
  }
  if (commitment.escalation.status === "pending" && commitment.escalation.escalateAt !== null && commitment.escalation.escalateAt <= now) {
    entries.push({ ticketId, at: commitment.escalation.escalateAt, reason: "escalation due", owner: commitment.escalation.owner, title: commitment.title });
  }
  return entries;
}

function frontmatter(value) {
  return ["---", ...Object.entries(value).map(([key, item]) => `${key}: ${JSON.stringify(item)}`), "---", ""].join("\n");
}

function ticketMarkdown(commitment, lane, updatedAt) {
  const ticketId = ticketIdFor(commitment);
  const requirement = commitment.requiredArtifact
    ? `${commitment.requiredArtifact.name} (${commitment.requiredArtifact.id})`
    : "Not yet specified";
  const proof = commitment.artifactEvidence
    ? `[${commitment.artifactEvidence.name}](${commitment.artifactEvidence.url})`
    : "Not yet received";
  const nextAction = lane === "blocked"
    ? blockerFor(commitment)
    : lane === "done"
      ? "Artifact proof is recorded. This task is archived."
      : commitment.nextReminderAt
        ? `Check or chase at ${commitment.nextReminderAt}.`
        : "Review the task and set the next accountable action.";
  return `${frontmatter({
    ticket_id: ticketId,
    commitment_id: commitment.id,
    title: commitment.title,
    status: lane,
    owner: commitment.owner,
    created_at: commitment.startAt ?? updatedAt,
    updated_at: updatedAt,
    due_at: commitment.deadline,
    next_action_at: commitment.nextReminderAt,
    required_artifact: commitment.requiredArtifact,
    artifact_evidence: commitment.artifactEvidence,
    task_url: commitment.taskLink.url ?? null,
    escalation: commitment.escalation,
    expected_meeting_note: commitment.expectedMeetingNote,
    resolved_at: commitment.resolvedAt ?? null
  })}# ${ticketId}: ${commitment.title}

## Next action

${nextAction}

## Required artifact

${requirement}

## Evidence

${proof}
`;
}

function progressMarkdown(commitment, state) {
  const relevantEvents = state.events.filter((event) => event.commitmentId === commitment.id);
  const relevantActions = state.outbox.filter((action) => action.commitmentId === commitment.id);
  const entries = [
    ...relevantEvents.map((event) => ({ at: event.at, text: `**${event.type}** — ${event.source}` })),
    ...relevantActions.map((action) => ({ at: action.createdAt, text: `**${action.type}** message ${action.status} for ${action.recipient}` }))
  ].sort((left, right) => left.at.localeCompare(right.at) || left.text.localeCompare(right.text));
  const lines = entries.length === 0
    ? ["- No recorded progress yet."]
    : entries.map((entry) => `- ${entry.at} — ${entry.text}`);
  return `# Progress: ${ticketIdFor(commitment)}\n\n${lines.join("\n")}\n`;
}

function staleMarkdown(entries, generatedAt) {
  const lines = [
    "# Stale tickets",
    "",
    `Generated at ${generatedAt}. This is a read-only attention queue; use an event envelope to change work state.`,
    ""
  ];
  if (entries.length === 0) {
    lines.push("No due follow-up or escalation.");
  } else {
    for (const entry of entries) {
      lines.push(`- [${entry.ticketId}](tasks/${entry.ticketId}/ticket.md) — ${entry.reason} at ${entry.at}; owner: ${entry.owner}; ${entry.title}`);
    }
  }
  return `${lines.join("\n")}\n`;
}

function atomicWrite(path, content) {
  mkdirSync(dirname(path), { recursive: true });
  const temporaryPath = resolve(dirname(path), `.${basename(path)}.${process.pid}.${randomUUID()}.tmp`);
  try {
    writeFileSync(temporaryPath, content, { flag: "wx" });
    renameSync(temporaryPath, path);
  } finally {
    if (existsSync(temporaryPath)) unlinkSync(temporaryPath);
  }
}

function changed(path, content) {
  return !existsSync(path) || readFileSync(path, "utf8") !== content;
}

function describeCommitment(commitment, state, boardPath, write) {
  const ticketId = ticketIdFor(commitment);
  const lane = laneFor(commitment);
  const activePath = resolve(boardPath, "tasks", ticketId);
  const archivePath = resolve(boardPath, "archive", ticketId);
  let ticketPath = activePath;
  const changes = [];
  if (lane === "done") {
    ticketPath = archivePath;
    if (existsSync(activePath) && !existsSync(archivePath)) {
      changes.push({ type: "archived", ticketId });
      if (write) {
        mkdirSync(dirname(archivePath), { recursive: true });
        renameSync(activePath, archivePath);
      }
    } else if (existsSync(activePath) && existsSync(archivePath)) {
      throw new Error(`Cannot archive ${ticketId}: active and archived task directories both exist.`);
    }
  } else if (existsSync(archivePath)) {
    throw new Error(`Cannot reopen ${ticketId}: an archived task directory already exists.`);
  }
  const ticket = ticketMarkdown(commitment, lane, state.updatedAt);
  const progress = progressMarkdown(commitment, state);
  for (const [name, content] of [["ticket.md", ticket], ["progress.md", progress]]) {
    const path = resolve(ticketPath, name);
    if (changed(path, content)) {
      changes.push({ type: existsSync(path) ? "updated" : "created", ticketId, path });
      if (write) atomicWrite(path, content);
    }
  }
  if (write) mkdirSync(resolve(ticketPath, "artifacts"), { recursive: true });
  return changes;
}

/**
 * Project the deterministic manager ledger into inspectable task folders.
 * The task card and its progress file are safe to read from WhatsApp; state
 * mutation still enters through the event inbox and its deterministic guards.
 */
export function syncFilesystemKanban({
  state,
  boardPath = resolve(defaultOpsRoot, "board"),
  now = new Date().toISOString(),
  write = false
} = {}) {
  assertValidManagerState(state);
  const generatedAt = isoNow(now);
  const board = resolve(boardPath);
  const stale = state.commitments
    .flatMap((commitment) => dueEntriesFor(commitment, generatedAt))
    .sort((left, right) => left.at.localeCompare(right.at) || left.ticketId.localeCompare(right.ticketId) || left.reason.localeCompare(right.reason));
  const changes = state.commitments.flatMap((commitment) => describeCommitment(commitment, state, board, write));
  const stalePath = resolve(board, "STALE.md");
  const staleContent = staleMarkdown(stale, generatedAt);
  if (changed(stalePath, staleContent)) {
    changes.push({ type: existsSync(stalePath) ? "updated" : "created", path: stalePath, ticketId: null });
    if (write) atomicWrite(stalePath, staleContent);
  }
  return { boardPath: board, generatedAt, stale: copy(stale), changes };
}

function argumentValue(argumentsList, name) {
  const index = argumentsList.indexOf(name);
  return index === -1 ? undefined : argumentsList[index + 1];
}

function runCli() {
  const args = process.argv.slice(2);
  const statePath = argumentValue(args, "--state") ? resolve(argumentValue(args, "--state")) : resolve(defaultOpsRoot, "manager-state.json");
  const boardPath = argumentValue(args, "--board") ? resolve(argumentValue(args, "--board")) : resolve(defaultOpsRoot, "board");
  const state = JSON.parse(readFileSync(statePath, "utf8"));
  const result = syncFilesystemKanban({
    state,
    boardPath,
    now: argumentValue(args, "--now") ?? new Date().toISOString(),
    write: args.includes("--write")
  });
  console.log(JSON.stringify({ write: args.includes("--write"), boardPath: result.boardPath, stale: result.stale, changes: result.changes }, null, 2));
}

const invokedAsScript = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedAsScript) {
  try {
    runCli();
  } catch (error) {
    console.error(`Filesystem Kanban error: ${error.message}`);
    process.exitCode = 1;
  }
}
