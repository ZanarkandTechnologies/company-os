import { existsSync, renameSync, unlinkSync, writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { fileURLToPath } from "node:url";
import { basename, dirname, resolve } from "node:path";
import { pulseManagerState } from "./manager-state.mjs";
import { processManagerInbox } from "./process-manager-inbox.mjs";
import { syncFilesystemKanban } from "./sync-filesystem-kanban.mjs";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const defaultOpsRoot = resolve(projectRoot, "workspaces/howie-ai/ops");

function argumentValue(argumentsList, name) {
  const index = argumentsList.indexOf(name);
  return index === -1 ? undefined : argumentsList[index + 1];
}

function writeJsonAtomically(path, value) {
  const temporaryPath = resolve(dirname(path), `.${basename(path)}.${process.pid}.${randomUUID()}.tmp`);
  try {
    writeFileSync(temporaryPath, `${JSON.stringify(value, null, 2)}\n`, { flag: "wx" });
    renameSync(temporaryPath, path);
  } finally {
    if (existsSync(temporaryPath)) unlinkSync(temporaryPath);
  }
}

/**
 * Run the deterministic manager loop once. It first reconciles queued inbound
 * events, then derives due draft actions. It never sends a message or starts a
 * Hermes service.
 */
export function runManagerCycle({
  statePath = resolve(defaultOpsRoot, "manager-state.json"),
  inboxPath = resolve(defaultOpsRoot, "inbox"),
  processedPath = resolve(defaultOpsRoot, "processed"),
  boardPath = resolve(defaultOpsRoot, "board"),
  now = new Date().toISOString(),
  write = false
} = {}) {
  const inbox = processManagerInbox({ statePath, inboxPath, processedPath, write });
  if (inbox.failures.length > 0) {
    return { inbox, pulse: null, write, blocked: true };
  }
  const pulse = pulseManagerState(inbox.state, now);
  if (write) writeJsonAtomically(statePath, pulse.state);
  const board = syncFilesystemKanban({ state: pulse.state, boardPath, now, write });
  return { inbox, pulse, board, write, blocked: false };
}

function runCli() {
  const args = process.argv.slice(2);
  const statePath = argumentValue(args, "--state") ? resolve(argumentValue(args, "--state")) : resolve(defaultOpsRoot, "manager-state.json");
  const inboxPath = argumentValue(args, "--inbox") ? resolve(argumentValue(args, "--inbox")) : resolve(defaultOpsRoot, "inbox");
  const processedPath = argumentValue(args, "--processed") ? resolve(argumentValue(args, "--processed")) : resolve(defaultOpsRoot, "processed");
  const boardPath = argumentValue(args, "--board") ? resolve(argumentValue(args, "--board")) : resolve(defaultOpsRoot, "board");
  const result = runManagerCycle({
    statePath,
    inboxPath,
    processedPath,
    boardPath,
    now: argumentValue(args, "--now") ?? new Date().toISOString(),
    write: args.includes("--write")
  });

  const output = {
    write: result.write,
    blocked: result.blocked,
    inbox: {
      processed: result.inbox.outcomes.map((outcome) => ({ filename: outcome.filename, disposition: outcome.disposition })),
      failures: result.inbox.failures
    },
    draftsCreated: result.pulse?.actionsCreated.map((action) => action.id) ?? [],
    board: result.board ? { stale: result.board.stale, changes: result.board.changes } : null
  };
  console.log(JSON.stringify(output, null, 2));
  if (result.blocked) process.exitCode = 1;
}

const invokedAsScript = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedAsScript) {
  try {
    runCli();
  } catch (error) {
    console.error(`Manager cycle error: ${error.message}`);
    process.exitCode = 1;
  }
}
