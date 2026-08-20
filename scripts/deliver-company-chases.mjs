/**
 * Controlled sender for canonical Company Manager ticket progress.
 *
 * This is the only code path that can invoke `hermes -p howie-ai send`.
 * It never creates an outbox or mutates a second task store: drafts and
 * receipts live beside their ticket in progress.md. Dry-run is the default.
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import {
  appendDeliveryReceipt,
  inspectBoard,
  loadEmployeeDirectory,
  readTicketProgressEvents
} from "./company-manager.mjs";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const terminalStatuses = new Set(["sent", "failed"]);

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function canonicalTime(value, label) {
  if (!isNonEmptyString(value) || !Number.isFinite(Date.parse(value))) {
    throw new TypeError(`${label} must be an ISO timestamp.`);
  }
  return new Date(value).toISOString();
}

function deliveryDrafts(events) {
  const terminal = new Set(events
    .filter((entry) => entry.type === "telegram_delivery_receipt" && terminalStatuses.has(entry.status))
    .map((entry) => entry.delivery_id));
  const latestDraft = new Map();
  for (const entry of events) {
    if (entry.type !== "telegram_delivery_draft" || entry.archived) continue;
    latestDraft.set(entry.delivery_id, entry);
  }
  return [...latestDraft.values()]
    .map((draft) => ({ draft, terminal: terminal.has(draft.delivery_id) }))
    .sort((left, right) => left.draft.at.localeCompare(right.draft.at) || left.draft.delivery_id.localeCompare(right.draft.delivery_id));
}

function latestOtherDeliveryEvent(events, employeeId, deliveryId) {
  return events
    .filter((entry) => entry.type === "telegram_delivery_receipt"
      && entry.status === "sent"
      && entry.employee_id === employeeId
      && entry.delivery_id !== deliveryId
      && !entry.archived)
    .sort((left, right) => right.at.localeCompare(left.at))[0] ?? null;
}

function deliveryPolicyError(draft, reason) {
  return {
    ticketId: draft.ticket_id,
    requirementId: draft.requirement_id,
    employeeId: draft.employee_id,
    deliveryId: draft.delivery_id,
    status: "rejected",
    reason
  };
}

function skippedDelivery(draft, reason) {
  return {
    ticketId: draft.ticket_id,
    requirementId: draft.requirement_id,
    employeeId: draft.employee_id,
    deliveryId: draft.delivery_id,
    status: "skipped",
    reason
  };
}

function defaultRunHermes({ target, message }) {
  return spawnSync("hermes", ["-p", "howie-ai", "send", "--json", "--to", `telegram:${target}`, message], {
    cwd: projectRoot,
    encoding: "utf8"
  });
}

function platformMessageIdFrom(result) {
  if (!result || result.status !== 0 || !isNonEmptyString(result.stdout)) return null;
  try {
    const payload = JSON.parse(result.stdout);
    return isNonEmptyString(payload?.message_id) ? payload.message_id : null;
  } catch {
    return null;
  }
}

function dueLabel(iso) {
  if (!isNonEmptyString(iso)) return "the task due date";
  return iso.replace(/\.\d{3}Z$/, " UTC").replace("T", " ");
}

function nonEmptyLines(lines) {
  return lines.filter((line) => isNonEmptyString(line));
}

function fallbackDecisionMessage({ task, question }) {
  return nonEmptyLines([
    "*Manager · decision needed*",
    "",
    task.description,
    "",
    `*Decision:* ${question}`,
    "*Reply:* Send your recommendation and one short reason.",
    "*After your reply:* I’ll apply it to the plan and return the resulting work for review."
  ]).join("\n");
}

/** Render a recipient brief: enough context to make a useful call from a phone. */
export function formatChaseMessage({ draft, task, employee = null }) {
  const requirement = task.requirements?.find((candidate) => candidate.id === draft.requirement_id);
  const brief = requirement?.human?.brief;
  if (!brief || !isNonEmptyString(brief.title) || !isNonEmptyString(brief.context)
    || !isNonEmptyString(brief.decision) || !isNonEmptyString(brief.outcome)) {
    return fallbackDecisionMessage({ task, question: draft.question });
  }
  const recommendation = isNonEmptyString(brief.recommendation)
    ? `*My recommendation:* ${brief.recommendation}`
    : null;
  const options = Array.isArray(brief.options) && brief.options.every(isNonEmptyString) && brief.options.length > 0
    ? `*Options:* ${brief.options.join(" · ")}`
    : null;
  const reply = isNonEmptyString(brief.reply)
    ? brief.reply
    : "Reply with your decision and one short reason.";
  return nonEmptyLines([
    `*Manager · ${brief.title}*`,
    "",
    brief.context,
    "",
    `*Decision:* ${brief.decision}`,
    recommendation,
    options,
    "",
    `*Reply:* ${reply}`,
    `*After your reply:* ${brief.outcome}`
  ]).join("\n");
}

/**
 * Discover ticket-local delivery drafts and either record dry runs or, only
 * behind both local gates, invoke Hermes once per permitted draft.
 */
export function deliverCompanyChases({
  workspaceRoot,
  send = false,
  env = process.env,
  now = new Date().toISOString(),
  runHermes = defaultRunHermes
} = {}) {
  const at = canonicalTime(now, "now");
  const employees = loadEmployeeDirectory({ workspaceRoot });
  const events = readTicketProgressEvents({ workspaceRoot, includeArchived: true });
  const board = inspectBoard({ workspaceRoot, now: at });
  const tasksById = new Map(board.tasks.map((task) => [task.ticketId, task]));
  const followUps = new Map(board.tasks.flatMap((task) => task.outstandingPeople.map((person) => [
    `${task.ticketId}\u0000${person.requirementId}`,
    person.followUp
  ])));
  const attempts = [];
  const sentGate = send === true && env.HOWIE_POC_ENABLE_SEND === "1";
  const drafts = deliveryDrafts(events);
  const currentEvents = [...events];

  for (const { draft, terminal } of drafts) {
    if (terminal) {
      attempts.push(skippedDelivery(draft, "terminal_receipt_exists"));
      continue;
    }
    const currentFollowUp = followUps.get(`${draft.ticket_id}\u0000${draft.requirement_id}`);
    if (!currentFollowUp || currentFollowUp.deliveryId !== draft.delivery_id || currentFollowUp.status !== "pending") {
      attempts.push(deliveryPolicyError(draft, "stale_delivery_draft"));
      continue;
    }
    const employee = employees.get(draft.employee_id);
    if (!employee) {
      attempts.push(deliveryPolicyError(draft, "unknown_employee"));
      continue;
    }
    if (!employee.route_enabled || !employee.outbound_allowed || !employee.test_opt_in) {
      attempts.push(deliveryPolicyError(draft, "outbound_route_disabled"));
      continue;
    }
    if (!isNonEmptyString(employee.telegram_target)) {
      attempts.push(deliveryPolicyError(draft, "invalid_telegram_target"));
      continue;
    }
    const latest = latestOtherDeliveryEvent(currentEvents, employee.id, draft.delivery_id);
    if (latest) {
      const availableAt = new Date(Date.parse(latest.at) + employee.global_cooldown_minutes * 60_000).toISOString();
      if (Date.parse(availableAt) > Date.parse(at)) {
        attempts.push({ ...deliveryPolicyError(draft, "employee_global_cooldown"), availableAt });
        continue;
      }
    }
    if (!sentGate) {
      if (send === true) {
        attempts.push(deliveryPolicyError(draft, "explicit_send_gate_required"));
        continue;
      }
      const receipt = appendDeliveryReceipt({
        workspaceRoot,
        ticketId: draft.ticket_id,
        deliveryId: draft.delivery_id,
        requirementId: draft.requirement_id,
        employeeId: draft.employee_id,
        status: "dry_run",
        at,
        reason: "default_dry_run"
      });
      currentEvents.push({ ...receipt, type: "telegram_delivery_receipt", ticket_id: draft.ticket_id, archived: false });
      attempts.push({ ...receipt, status: "dry_run" });
      continue;
    }
    let result;
    try {
      const task = tasksById.get(draft.ticket_id);
      if (!task) throw new Error(`ticket ${draft.ticket_id} is missing from the board projection.`);
      result = runHermes({
        target: employee.telegram_target,
        message: formatChaseMessage({ draft, task, employee }),
        deliveryId: draft.delivery_id
      });
    } catch (error) {
      result = { status: 1, error };
    }
    const status = result?.status === 0 ? "sent" : "failed";
    const receipt = appendDeliveryReceipt({
      workspaceRoot,
      ticketId: draft.ticket_id,
      deliveryId: draft.delivery_id,
      requirementId: draft.requirement_id,
      employeeId: draft.employee_id,
      status,
      at,
      reason: status === "sent" ? null : "hermes_send_failed",
      platformMessageId: status === "sent" ? platformMessageIdFrom(result) : null
    });
    currentEvents.push({ ...receipt, type: "telegram_delivery_receipt", ticket_id: draft.ticket_id, archived: false });
    attempts.push(receipt);
  }

  return {
    workspaceRoot: resolve(workspaceRoot),
    mode: sentGate ? "send" : "dry_run",
    sendGate: sentGate,
    attempts,
    exitCode: attempts.some((attempt) => attempt.status === "failed" || attempt.status === "rejected") ? 1 : 0
  };
}

function parseArgs(argv) {
  const args = { workspaceRoot: null, send: false };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--send") {
      args.send = true;
      continue;
    }
    if (argument === "--workspace") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) throw new Error("--workspace requires a path.");
      args.workspaceRoot = resolve(value);
      index += 1;
      continue;
    }
    if (argument === "--help") {
      console.log("Usage: node scripts/deliver-company-chases.mjs --workspace path [--send]");
      process.exit(0);
    }
    throw new Error(`Unknown argument: ${argument}`);
  }
  if (!args.workspaceRoot) throw new Error("--workspace is required.");
  return args;
}

const invokedAsScript = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedAsScript) {
  try {
    const result = deliverCompanyChases(parseArgs(process.argv.slice(2)));
    console.log(JSON.stringify(result, null, 2));
    process.exitCode = result.exitCode;
  } catch (error) {
    console.error(`Company delivery error: ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 2;
  }
}
