import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const statePath = process.argv[2]
  ? resolve(process.argv[2])
  : resolve(projectRoot, "workspaces/howiecompany/weekly/current.json");

const datePattern = /^\d{4}-\d{2}-\d{2}$/;
const validStatuses = new Set(["planned", "in_progress", "waiting", "blocked", "done"]);
const validOutboxStatuses = new Set(["draft", "approved_for_poc", "sent", "failed"]);

function issue(message) {
  console.error(`State error: ${message}`);
  process.exitCode = 1;
}

function assertObject(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    issue(`${label} must be an object.`);
    return false;
  }
  return true;
}

let state;
try {
  state = JSON.parse(readFileSync(statePath, "utf8"));
} catch (error) {
  issue(`could not read ${statePath}: ${error.message}`);
  process.exit();
}

if (!assertObject(state, "Root")) process.exit();
if (state.schemaVersion !== 1) issue("schemaVersion must be 1.");
if (!datePattern.test(state.weekOf ?? "")) issue("weekOf must be YYYY-MM-DD.");
if (!Array.isArray(state.tasks)) issue("tasks must be an array.");
if (!Array.isArray(state.artifacts)) issue("artifacts must be an array.");
if (!Array.isArray(state.outbox)) issue("outbox must be an array.");

const taskIds = new Set();
for (const [index, task] of (state.tasks ?? []).entries()) {
  if (!assertObject(task, `tasks[${index}]`)) continue;
  const label = `tasks[${index}]`;
  if (!task.id || typeof task.id !== "string") issue(`${label}.id is required.`);
  if (taskIds.has(task.id)) issue(`${label}.id duplicates ${task.id}.`);
  taskIds.add(task.id);
  if (!task.title || typeof task.title !== "string") issue(`${label}.title is required.`);
  if (!task.owner || typeof task.owner !== "string") issue(`${label}.owner is required; use "unresolved" when unknown.`);
  if (!validStatuses.has(task.status)) issue(`${label}.status is invalid.`);
  for (const field of ["start", "due"]) {
    if (task[field] !== null && task[field] !== undefined && !datePattern.test(task[field])) {
      issue(`${label}.${field} must be YYYY-MM-DD or null.`);
    }
  }
  if (task.start && task.due && task.start > task.due) {
    issue(`${label}.due must not precede start.`);
  }
  if (!task.source || typeof task.source !== "string") issue(`${label}.source is required.`);
}

for (const [index, artifact] of (state.artifacts ?? []).entries()) {
  if (!assertObject(artifact, `artifacts[${index}]`)) continue;
  const label = `artifacts[${index}]`;
  if (!artifact.id || !artifact.name || !artifact.type || !artifact.taskId || !artifact.status) {
    issue(`${label} requires id, name, type, taskId, and status.`);
  }
  if (!taskIds.has(artifact.taskId)) issue(`${label}.taskId must reference a task.`);
  if (artifact.url !== null && artifact.url !== undefined && typeof artifact.url !== "string") {
    issue(`${label}.url must be a string or null.`);
  }
}

const outboxIds = new Set();
for (const [index, item] of (state.outbox ?? []).entries()) {
  if (!assertObject(item, `outbox[${index}]`)) continue;
  const label = `outbox[${index}]`;
  if (!item.id || !item.taskId || !item.recipient || !item.message || !item.source) {
    issue(`${label} requires id, taskId, recipient, message, and source.`);
  }
  if (outboxIds.has(item.id)) issue(`${label}.id duplicates ${item.id}.`);
  outboxIds.add(item.id);
  if (!taskIds.has(item.taskId)) issue(`${label}.taskId must reference a task.`);
  if (!validOutboxStatuses.has(item.status)) issue(`${label}.status is invalid.`);
}

if (process.exitCode) process.exit();
console.log(`✓ Valid weekly state: ${state.tasks.length} task(s), ${state.artifacts.length} artifact(s), ${state.outbox.length} outbox item(s).`);
