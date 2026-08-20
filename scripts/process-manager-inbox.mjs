import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  unlinkSync,
  writeFileSync
} from "node:fs";
import { randomUUID } from "node:crypto";
import { fileURLToPath } from "node:url";
import { basename, dirname, resolve } from "node:path";
import {
  assertValidManagerState,
  recordMeetingEvent,
  reconcileManagerInbound
} from "./manager-state.mjs";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const defaultOpsRoot = resolve(projectRoot, "workspaces/howie-ai/ops");

function isObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function readJson(path, label) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    throw new Error(`could not read ${label} ${path}: ${error.message}`);
  }
}

function writeJsonAtomically(path, value) {
  const temporaryPath = resolve(dirname(path), `.${basename(path)}.${process.pid}.${randomUUID()}.tmp`);
  try {
    writeFileSync(temporaryPath, `${JSON.stringify(value, null, 2)}\n`, { flag: "wx" });
    renameSync(temporaryPath, path);
  } catch (error) {
    if (existsSync(temporaryPath)) unlinkSync(temporaryPath);
    throw new Error(`could not write manager state atomically: ${error.message}`);
  }
}

function prepareProcessedDestination(sourcePath, processedPath) {
  mkdirSync(processedPath, { recursive: true });
  const destinationPath = resolve(processedPath, basename(sourcePath));
  if (existsSync(destinationPath)) {
    throw new Error(`processed event already exists: ${destinationPath}`);
  }
  return destinationPath;
}

function moveEventAtomically(sourcePath, destinationPath) {
  try {
    renameSync(sourcePath, destinationPath);
  } catch (error) {
    throw new Error(`could not move ${sourcePath} to processed inbox: ${error.message}`);
  }
  return destinationPath;
}

/** Validate the file-level envelope before dispatching its event payload. */
export function validateManagerInboxEnvelope(envelope) {
  const errors = [];
  if (!isObject(envelope)) return { valid: false, errors: ["Inbox envelope must be an object."] };
  if (envelope.kind !== "meeting" && envelope.kind !== "inbound") {
    errors.push('Inbox envelope kind must be "meeting" or "inbound".');
  }
  if (!isObject(envelope.event)) errors.push("Inbox envelope event must be an object.");
  return { valid: errors.length === 0, errors };
}

function applyEnvelope(state, envelope) {
  const validation = validateManagerInboxEnvelope(envelope);
  if (!validation.valid) throw new Error(validation.errors.join(" "));
  const result = envelope.kind === "meeting"
    ? recordMeetingEvent(state, envelope.event)
    : reconcileManagerInbound(state, envelope.event);
  assertValidManagerState(result.state);
  return result;
}

function inboxEventFiles(inboxPath) {
  if (!existsSync(inboxPath)) throw new Error(`manager inbox does not exist: ${inboxPath}`);
  return readdirSync(inboxPath, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .map((entry) => resolve(inboxPath, entry.name))
    .sort();
}

/**
 * Reconcile inbox files in deterministic filename order. A dry run only
 * returns previews; `write` atomically updates state then moves each accepted
 * source file into processed storage. Failed files always remain in the inbox.
 */
export function processManagerInbox({
  statePath = resolve(defaultOpsRoot, "manager-state.json"),
  inboxPath = resolve(defaultOpsRoot, "inbox"),
  processedPath = resolve(defaultOpsRoot, "processed"),
  write = false
} = {}) {
  let state = readJson(statePath, "manager state");
  assertValidManagerState(state);
  const outcomes = [];
  const failures = [];

  for (const eventPath of inboxEventFiles(inboxPath)) {
    const filename = basename(eventPath);
    try {
      const envelope = readJson(eventPath, "inbox event");
      const result = applyEnvelope(state, envelope);
      if (write) {
        const destinationPath = prepareProcessedDestination(eventPath, processedPath);
        writeJsonAtomically(statePath, result.state);
        moveEventAtomically(eventPath, destinationPath);
      }
      state = result.state;
      outcomes.push({
        filename,
        kind: envelope.kind,
        disposition: result.disposition ?? "recorded",
        commitmentsCreated: result.commitmentsCreated ?? [],
        commitmentId: result.commitmentId ?? null,
        eventsAdded: result.eventsAdded.map((event) => event.id)
      });
    } catch (error) {
      failures.push({ filename, error: error.message });
    }
  }

  return { state, outcomes, failures, write };
}

function argumentValue(argumentsList, name) {
  const index = argumentsList.indexOf(name);
  return index === -1 ? undefined : argumentsList[index + 1];
}

function runCli() {
  const argumentsList = process.argv.slice(2);
  const statePath = argumentValue(argumentsList, "--state")
    ? resolve(argumentValue(argumentsList, "--state"))
    : resolve(defaultOpsRoot, "manager-state.json");
  const inboxPath = argumentValue(argumentsList, "--inbox")
    ? resolve(argumentValue(argumentsList, "--inbox"))
    : resolve(defaultOpsRoot, "inbox");
  const processedPath = argumentValue(argumentsList, "--processed")
    ? resolve(argumentValue(argumentsList, "--processed"))
    : resolve(defaultOpsRoot, "processed");
  const result = processManagerInbox({
    statePath,
    inboxPath,
    processedPath,
    write: argumentsList.includes("--write")
  });

  for (const outcome of result.outcomes) {
    console.log(`${result.write ? "processed" : "preview"} ${outcome.filename}: ${outcome.kind} ${outcome.disposition}`);
  }
  for (const failure of result.failures) {
    console.error(`Manager inbox error in ${failure.filename}: ${failure.error}`);
  }
  if (result.outcomes.length === 0 && result.failures.length === 0) console.log("No manager inbox event files.");
  if (result.failures.length > 0) process.exitCode = 1;
}

const invokedAsScript = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedAsScript) {
  try {
    runCli();
  } catch (error) {
    console.error(`Manager inbox error: ${error.message}`);
    process.exitCode = 1;
  }
}
