/**
 * File-first Howie company-manager POC.
 *
 * Canonical task state lives only in `tickets/TASK-XXXX/ticket.md`; progress is
 * append-only in the sibling `progress.md`. The mock employee directory and
 * mock Drive records supply bounded policy/evidence, never a second task list.
 *
 * Dashboard API:
 *   inspectBoard({ workspaceRoot }) -> { tasks, gantt, counts }
 *   scanMeeting({ workspaceRoot, write }) -> { createdTicketIds, ... }
 *   runPulse({ workspaceRoot, now, maxWorkers, write }) -> worker dispatches + chases + escalations
 *   recordReply({ workspaceRoot, ticketId, employeeId, text, write })
 *   publishArtifact({ workspaceRoot, ticketId, write })
 *   reviewArtifact({ workspaceRoot, ticketId, reviewerId, decision, write })
 *   seedDemo({ workspaceRoot, write })
 *   generateWeeklyReport({ workspaceRoot, now, write })
 *
 * No function here contacts Hermes, Telegram, Google Drive, starts a schedule,
 * or creates a Kanban card. `write: false` is an in-memory preview.
 */
import {
  appendFileSync,
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

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const fixtureRoot = resolve(projectRoot, "fixtures/company-manager");
const defaultWorkspaceRoot = resolve(projectRoot, "workspaces/howie-ai");
const ticketIdPattern = /^TASK-\d{4}$/;
const statuses = new Set(["blocked", "in_progress", "awaiting_review", "done"]);
const requirementTypes = new Set(["human_input", "skill_output"]);
const requirementStates = new Set(["unresolved", "resolved"]);
const humanRequestChannels = new Set(["telegram_delivery"]);
const followUpStatuses = new Set(["pending", "resolved", "escalated"]);
const driveScope = "howie-ai/shared";
const defaultMaxWorkers = 2;
const escalationAttemptThreshold = 2;
const escalationOwnerId = "howie-ai";

function copy(value) {
  return structuredClone(value);
}

function isObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function canonicalTime(value, label) {
  if (!isNonEmptyString(value) || !Number.isFinite(Date.parse(value))) {
    throw new TypeError(`${label} must be an ISO timestamp.`);
  }
  return new Date(value).toISOString();
}

function runtimePaths(workspaceRoot) {
  const root = resolve(workspaceRoot ?? defaultWorkspaceRoot);
  const ticketsRoot = resolve(root, "tickets");
  return {
    root,
    ticketsRoot,
    archiveRoot: resolve(ticketsRoot, "archive"),
    peoplePath: resolve(root, "people/employees.private.json"),
    sharedDriveRoot: resolve(root, "drive-mock/howie-ai-shared"),
    reportsRoot: resolve(root, "reports")
  };
}

function assertTicketId(ticketId) {
  if (!ticketIdPattern.test(ticketId ?? "")) throw new TypeError(`ticketId must match ${ticketIdPattern}.`);
  return ticketId;
}

function ticketDirectory(paths, ticketId, archived = false) {
  assertTicketId(ticketId);
  return resolve(archived ? paths.archiveRoot : paths.ticketsRoot, ticketId);
}

function readText(path, label) {
  try {
    return readFileSync(path, "utf8");
  } catch (error) {
    throw new Error(`could not read ${label} at ${path}: ${error.message}`);
  }
}

function readJson(path, label) {
  try {
    return JSON.parse(readText(path, label));
  } catch (error) {
    throw new Error(`could not parse ${label} at ${path}: ${error.message}`);
  }
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

function jsonFrontmatter(metadata) {
  return ["---", ...Object.entries(metadata).map(([key, value]) => `${key}: ${JSON.stringify(value)}`), "---", ""].join("\n");
}

function parseFrontmatter(markdown, label) {
  const match = markdown.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!match) throw new Error(`${label} needs JSON-valued YAML frontmatter.`);
  const metadata = {};
  for (const line of match[1].split("\n")) {
    if (!line) continue;
    const separator = line.indexOf(": ");
    if (separator < 1) throw new Error(`${label} has invalid frontmatter line ${JSON.stringify(line)}.`);
    const key = line.slice(0, separator);
    const source = line.slice(separator + 2);
    try {
      metadata[key] = JSON.parse(source);
    } catch {
      throw new Error(`${label} frontmatter field ${key} is not JSON-valued.`);
    }
  }
  return { metadata, body: markdown.slice(match[0].length) };
}

function assertTicket(ticket, label) {
  if (!isObject(ticket)) throw new Error(`${label} metadata must be an object.`);
  assertTicketId(ticket.ticket_id);
  if (!isNonEmptyString(ticket.title)) throw new Error(`${label}.title is required.`);
  if (!isNonEmptyString(ticket.description)) throw new Error(`${label}.description is required.`);
  if (!isNonEmptyString(ticket.workstream)) throw new Error(`${label}.workstream is required.`);
  if (!isNonEmptyString(ticket.owner_id)) throw new Error(`${label}.owner_id is required.`);
  if (!isNonEmptyString(ticket.reviewer_id)) throw new Error(`${label}.reviewer_id is required.`);
  if (!statuses.has(ticket.status)) throw new Error(`${label}.status is invalid.`);
  canonicalTime(ticket.start_at, `${label}.start_at`);
  canonicalTime(ticket.due_at, `${label}.due_at`);
  canonicalTime(ticket.created_at, `${label}.created_at`);
  canonicalTime(ticket.updated_at, `${label}.updated_at`);
  if (!Array.isArray(ticket.blocking_inputs)) throw new Error(`${label}.blocking_inputs must be an array.`);
  if (!Array.isArray(ticket.mock_skill_dependencies) || ticket.mock_skill_dependencies.length === 0) {
    throw new Error(`${label}.mock_skill_dependencies must be a non-empty array.`);
  }
  if (!Array.isArray(ticket.requirements)) throw new Error(`${label}.requirements must be an array.`);
  assertDependencyDeclaration(ticket, label);
  if (!isObject(ticket.review) || !isNonEmptyString(ticket.review.state)) throw new Error(`${label}.review is invalid.`);
  if (ticket.artifact !== null && !isObject(ticket.artifact)) throw new Error(`${label}.artifact must be an object or null.`);
  return ticket;
}

function assertDependencyDeclaration(ticket, label) {
  if (!Array.isArray(ticket.requirements)) throw new Error(`${label}.requirements must be an array.`);
  const requirementIds = new Set();
  for (const requirement of ticket.requirements) {
    if (!isObject(requirement) || !isNonEmptyString(requirement.id)) {
      throw new Error(`${label}.requirements entries need stable IDs.`);
    }
    if (requirementIds.has(requirement.id)) throw new Error(`${label} duplicates requirement ${requirement.id}.`);
    requirementIds.add(requirement.id);
    if (!requirementTypes.has(requirement.type)) throw new Error(`${label} requirement ${requirement.id} has an invalid type.`);
    if (!isNonEmptyString(requirement.description)) throw new Error(`${label} requirement ${requirement.id} needs a description.`);
    if (!requirementStates.has(requirement.state)) throw new Error(`${label} requirement ${requirement.id} has an invalid state.`);
    if (requirement.state === "resolved") {
      if (!isObject(requirement.resolution) || !isNonEmptyString(requirement.resolution.source)) {
        throw new Error(`${label} resolved requirement ${requirement.id} needs a resolution record.`);
      }
      canonicalTime(requirement.resolution.at, `${label} requirement ${requirement.id} resolution.at`);
    }
    if (requirement.type === "human_input") {
      if (!isObject(requirement.human) || !isNonEmptyString(requirement.human.employee_id)
        || !humanRequestChannels.has(requirement.human.channel) || !isNonEmptyString(requirement.human.question)) {
        throw new Error(`${label} human requirement ${requirement.id} needs employee_id, telegram_delivery channel, and question.`);
      }
      if (requirement.upstream !== undefined) throw new Error(`${label} human requirement ${requirement.id} cannot name an upstream output.`);
      assertFollowUp(requirement.follow_up, `${label} human requirement ${requirement.id}`, requirement.human.employee_id);
    } else {
      if (!isObject(requirement.upstream) || !isNonEmptyString(requirement.upstream.ticket_id)
        || !isNonEmptyString(requirement.upstream.skill_id) || !isNonEmptyString(requirement.upstream.output_id)) {
        throw new Error(`${label} output requirement ${requirement.id} needs ticket_id, skill_id, and output_id.`);
      }
      if (requirement.human !== undefined) throw new Error(`${label} output requirement ${requirement.id} cannot name a human contract.`);
    }
  }

  const skillIds = new Set();
  const outputIds = new Set();
  for (const skill of ticket.mock_skill_dependencies) {
    if (!isObject(skill) || !isNonEmptyString(skill.id) || !isNonEmptyString(skill.template)) {
      throw new Error(`${label}.mock_skill_dependencies entries need IDs and templates.`);
    }
    if (skillIds.has(skill.id)) throw new Error(`${label} duplicates skill ${skill.id}.`);
    skillIds.add(skill.id);
    if (!Array.isArray(skill.input_ids) || !Array.isArray(skill.outputs) || skill.outputs.length === 0) {
      throw new Error(`${label} skill ${skill.id} needs input_ids and at least one output.`);
    }
    for (const inputId of skill.input_ids) {
      if (!isNonEmptyString(inputId) || !requirementIds.has(inputId)) {
        throw new Error(`${label} skill ${skill.id} names unknown input ${inputId}.`);
      }
    }
    for (const output of skill.outputs) {
      if (!isObject(output) || !isNonEmptyString(output.id) || !isNonEmptyString(output.description)) {
        throw new Error(`${label} skill ${skill.id} has an invalid output.`);
      }
      if (outputIds.has(output.id)) throw new Error(`${label} duplicates output ${output.id}.`);
      outputIds.add(output.id);
    }
  }
}

function assertFollowUp(followUp, label, expectedEmployeeId) {
  if (!isObject(followUp) || !isNonEmptyString(followUp.employee_id)) {
    throw new Error(`${label}.follow_up must name an employee.`);
  }
  if (followUp.employee_id !== expectedEmployeeId) {
    throw new Error(`${label}.follow_up.employee_id must match the human employee.`);
  }
  if (!Number.isInteger(followUp.attempts) || followUp.attempts < 0) {
    throw new Error(`${label}.follow_up.attempts must be a non-negative integer.`);
  }
  if (!Number.isInteger(followUp.cooldown_minutes) || followUp.cooldown_minutes < 0) {
    throw new Error(`${label}.follow_up.cooldown_minutes must be a non-negative integer.`);
  }
  if (!followUpStatuses.has(followUp.status)) throw new Error(`${label}.follow_up.status is invalid.`);
  if (followUp.last_at !== null) canonicalTime(followUp.last_at, `${label}.follow_up.last_at`);
  if (followUp.next_at !== null) canonicalTime(followUp.next_at, `${label}.follow_up.next_at`);
  if (followUp.delivery_id !== null && !isNonEmptyString(followUp.delivery_id)) {
    throw new Error(`${label}.follow_up.delivery_id must be a stable ID or null.`);
  }
  if (followUp.escalation !== null && followUp.escalation !== undefined) {
    if (!isObject(followUp.escalation) || !isNonEmptyString(followUp.escalation.next_owner_id)
      || !isNonEmptyString(followUp.escalation.reason)) {
      throw new Error(`${label}.follow_up.escalation must name a next owner and reason.`);
    }
    canonicalTime(followUp.escalation.at, `${label}.follow_up.escalation.at`);
  }
  if (followUp.status === "resolved" && followUp.next_at !== null) {
    throw new Error(`${label}.follow_up.next_at must be null once resolved.`);
  }
}

function template(name) {
  return readText(resolve(fixtureRoot, "templates", name), `source template ${name}`);
}

function interpolate(source, values) {
  return source.replace(/{{([a-z_]+)}}/g, (_match, key) => String(values[key] ?? ""));
}

function ticketMarkdown(ticket) {
  const blockers = ticket.blocking_inputs.length === 0
    ? "None"
    : ticket.blocking_inputs.map((input) => `- ${input.id}: ${input.description}`).join("\n");
  const artifact = ticket.artifact
    ? `${ticket.artifact.name} (${ticket.artifact.storage_kind}; ${ticket.artifact.native_workspace_format ?? ticket.artifact.local_edit_format})`
    : "No published artifact.";
  return `${jsonFrontmatter(ticket)}${interpolate(template("ticket.md"), {
    ticket_id: ticket.ticket_id,
    title: ticket.title,
    status: ticket.status,
    blockers,
    artifact,
    reviewer_id: ticket.reviewer_id
  })}`;
}

function progressHeader(ticket) {
  return interpolate(template("progress.md"), { ticket_id: ticket.ticket_id, title: ticket.title });
}

function progressLine(event) {
  return `- ${event.at} — **${event.type}** — ${JSON.stringify(event)}\n`;
}

function ticketPaths(paths, ticketId, archived = false) {
  const directory = ticketDirectory(paths, ticketId, archived);
  return {
    directory,
    ticketPath: resolve(directory, "ticket.md"),
    progressPath: resolve(directory, "progress.md"),
    artifactsPath: resolve(directory, "artifacts")
  };
}

function readTicketAt(paths, ticketId, archived = false) {
  const pathsForTicket = ticketPaths(paths, ticketId, archived);
  if (!existsSync(pathsForTicket.ticketPath)) return null;
  const { metadata } = parseFrontmatter(readText(pathsForTicket.ticketPath, `ticket ${ticketId}`), `ticket ${ticketId}`);
  assertTicket(metadata, `ticket ${ticketId}`);
  return { ticket: metadata, archived, ...pathsForTicket };
}

function getTicket(paths, ticketId, { allowArchived = false } = {}) {
  const active = readTicketAt(paths, ticketId, false);
  if (active) return active;
  if (allowArchived) {
    const archived = readTicketAt(paths, ticketId, true);
    if (archived) return archived;
  }
  throw new Error(`ticket ${ticketId} does not exist in the active board.`);
}

function ticketDirectories(root) {
  if (!existsSync(root)) return [];
  return readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && ticketIdPattern.test(entry.name))
    .map((entry) => entry.name)
    .sort();
}

function listTickets(paths, { includeArchived = true } = {}) {
  const active = ticketDirectories(paths.ticketsRoot).map((ticketId) => readTicketAt(paths, ticketId, false));
  const archived = includeArchived
    ? ticketDirectories(paths.archiveRoot).map((ticketId) => readTicketAt(paths, ticketId, true))
    : [];
  return [...active, ...archived].filter(Boolean).sort((left, right) => left.ticket.ticket_id.localeCompare(right.ticket.ticket_id));
}

function parseProgressLine(line) {
  const marker = " — ";
  const first = line.indexOf(marker);
  const last = line.lastIndexOf(marker);
  if (!line.startsWith("- ") || first < 2 || last === first) return null;
  const at = line.slice(2, first);
  const payload = line.slice(last + marker.length);
  try {
    const parsed = JSON.parse(payload);
    return isObject(parsed) && isNonEmptyString(parsed.type) && parsed.at === at ? parsed : null;
  } catch {
    return null;
  }
}

/** Read immutable ticket events without creating a second delivery store. */
export function readTicketProgressEvents({ workspaceRoot, includeArchived = true } = {}) {
  const paths = runtimePaths(workspaceRoot);
  return listTickets(paths, { includeArchived }).flatMap((record) => {
    if (!existsSync(record.progressPath)) return [];
    return readText(record.progressPath, `progress for ${record.ticket.ticket_id}`)
      .split("\n")
      .map(parseProgressLine)
      .filter(Boolean)
      .map((entry) => ({ ...entry, ticket_id: record.ticket.ticket_id, archived: record.archived }));
  });
}

function deliveryEventsFor(records) {
  return records.flatMap((record) => {
    if (!existsSync(record.progressPath)) return [];
    return readText(record.progressPath, `progress for ${record.ticket.ticket_id}`)
      .split("\n")
      .map(parseProgressLine)
      .filter((entry) => entry && typeof entry.delivery_id === "string")
      .map((entry) => ({ ...entry, ticket_id: record.ticket.ticket_id, archived: record.archived }));
  });
}

function terminalDeliveryIds(events) {
  return new Set(events
    .filter((entry) => entry.type === "telegram_delivery_receipt" && new Set(["sent", "failed"]).has(entry.status))
    .map((entry) => entry.delivery_id));
}

function pendingDeliveriesFor(records) {
  const events = deliveryEventsFor(records);
  const terminal = terminalDeliveryIds(events);
  const latestDraftById = new Map();
  for (const entry of events) {
    if (entry.type === "telegram_delivery_draft") latestDraftById.set(entry.delivery_id, entry);
  }
  return [...latestDraftById.values()]
    .filter((entry) => !terminal.has(entry.delivery_id) && !entry.archived)
    .sort((left, right) => left.at.localeCompare(right.at) || left.delivery_id.localeCompare(right.delivery_id));
}

function requirementsFor(ticket) {
  return ticket.requirements;
}

function outputKey(ticketId, skillId, outputId) {
  return `${ticketId}\u0000${skillId}\u0000${outputId}`;
}

function ticketFromRecord(value) {
  return value?.ticket ?? value;
}

function approvedOutput(ticket) {
  return ticket.status === "done" && ticket.review?.state === "approved" && ticket.artifact !== null;
}

function outputRegistry(tickets) {
  const outputs = new Map();
  for (const ticket of tickets) {
    for (const skill of ticket.mock_skill_dependencies) {
      for (const output of skill.outputs ?? []) {
        outputs.set(outputKey(ticket.ticket_id, skill.id, output.id), {
          ticket,
          skill,
          output,
          approved: approvedOutput(ticket)
        });
      }
    }
  }
  return outputs;
}

/**
 * Reject malformed producer/consumer declarations before a mutation can write
 * ticket state. Legacy TASK-0001 tickets remain readable but do not synthesize
 * producer edges until their source metadata declares them.
 */
export function validateDependencyGraph(records) {
  if (!Array.isArray(records)) throw new TypeError("tickets must be an array.");
  const tickets = records.map(ticketFromRecord);
  const byId = new Map();
  for (const ticket of tickets) {
    assertTicket(ticket, `ticket ${ticket?.ticket_id ?? "unknown"}`);
    if (byId.has(ticket.ticket_id)) throw new Error(`dependency graph duplicates ticket ${ticket.ticket_id}.`);
    byId.set(ticket.ticket_id, ticket);
  }
  const outputs = outputRegistry(tickets);
  const edges = new Map(tickets.map((ticket) => [ticket.ticket_id, new Set()]));
  const references = [];
  for (const ticket of tickets) {
    for (const requirement of requirementsFor(ticket)) {
      if (requirement.type !== "skill_output") continue;
      const upstream = requirement.upstream;
      const producer = byId.get(upstream.ticket_id);
      if (!producer) {
        throw new Error(`ticket ${ticket.ticket_id} requirement ${requirement.id} names unknown producer ${upstream.ticket_id}.`);
      }
      const key = outputKey(upstream.ticket_id, upstream.skill_id, upstream.output_id);
      if (!outputs.has(key)) {
        throw new Error(`ticket ${ticket.ticket_id} requirement ${requirement.id} names unknown output ${upstream.ticket_id}.${upstream.skill_id}.${upstream.output_id}.`);
      }
      edges.get(ticket.ticket_id).add(upstream.ticket_id);
      references.push({
        consumerTicketId: ticket.ticket_id,
        requirementId: requirement.id,
        producerTicketId: upstream.ticket_id,
        producerSkillId: upstream.skill_id,
        producerOutputId: upstream.output_id
      });
    }
  }
  const visiting = new Set();
  const visited = new Set();
  function visit(ticketId, trail) {
    if (visiting.has(ticketId)) throw new Error(`dependency graph cycle: ${[...trail, ticketId].join(" -> ")}.`);
    if (visited.has(ticketId)) return;
    visiting.add(ticketId);
    for (const producerId of edges.get(ticketId)) visit(producerId, [...trail, ticketId]);
    visiting.delete(ticketId);
    visited.add(ticketId);
  }
  for (const ticketId of [...edges.keys()].sort()) visit(ticketId, []);
  return {
    producerOutputKeys: [...outputs.keys()].sort(),
    references: references.sort((left, right) => (
      left.consumerTicketId.localeCompare(right.consumerTicketId)
      || left.requirementId.localeCompare(right.requirementId)
    ))
  };
}

function requirementIsResolved(requirement, outputs) {
  if (requirement.type === "human_input") return requirement.state === "resolved";
  const upstream = requirement.upstream;
  const output = outputs.get(outputKey(upstream.ticket_id, upstream.skill_id, upstream.output_id));
  return requirement.state === "resolved" || output?.approved === true;
}

function publicRequirement(requirement, outputs) {
  const resolved = requirementIsResolved(requirement, outputs);
  const base = {
    id: requirement.id,
    type: requirement.type,
    description: requirement.description,
    state: resolved ? "resolved" : "unresolved",
    resolution: requirement.resolution ? copy(requirement.resolution) : null
  };
  if (requirement.type === "human_input") {
    return {
      ...base,
      human: {
        employeeId: requirement.human.employee_id,
        channel: requirement.human.channel,
        question: requirement.human.question,
        brief: requirement.human.brief ? copy(requirement.human.brief) : null
      },
      followUp: {
        employeeId: requirement.follow_up.employee_id,
        attempts: requirement.follow_up.attempts,
        lastAt: requirement.follow_up.last_at,
        nextAt: requirement.follow_up.next_at,
        deliveryId: requirement.follow_up.delivery_id,
        status: requirement.follow_up.status,
        escalation: requirement.follow_up.escalation ? copy(requirement.follow_up.escalation) : null
      }
    };
  }
  return {
    ...base,
    upstream: {
      ticketId: requirement.upstream.ticket_id,
      skillId: requirement.upstream.skill_id,
      outputId: requirement.upstream.output_id
    }
  };
}

function publicBlocker(requirement) {
  if (requirement.type === "human_input") {
    return {
      requirementId: requirement.id,
      type: requirement.type,
      description: requirement.description,
      employeeId: requirement.human.employeeId,
      channel: requirement.human.channel
    };
  }
  return {
    requirementId: requirement.id,
    type: requirement.type,
    description: requirement.description,
    ticketId: requirement.upstream.ticketId,
    skillId: requirement.upstream.skillId,
    outputId: requirement.upstream.outputId
  };
}

function dependencyProjection(records, now) {
  const graph = validateDependencyGraph(records);
  const tickets = records.map(ticketFromRecord);
  const outputs = outputRegistry(tickets);
  const unblocksByProducer = new Map(tickets.map((ticket) => [ticket.ticket_id, []]));
  for (const reference of graph.references) {
    unblocksByProducer.get(reference.producerTicketId).push({
      ticketId: reference.consumerTicketId,
      requirementId: reference.requirementId,
      skillId: reference.producerSkillId,
      outputId: reference.producerOutputId
    });
  }
  const currentTime = canonicalTime(now, "now");
  const publicByTicketId = new Map();
  for (const ticket of tickets) {
    const requirements = requirementsFor(ticket).map((requirement) => publicRequirement(requirement, outputs));
    const blockedBy = requirements.filter((requirement) => requirement.state === "unresolved").map(publicBlocker);
    const eligibleHumanRequirements = ticket.status === "blocked"
      ? requirements.filter((requirement) => requirement.type === "human_input" && requirement.state === "unresolved"
        && !blockedBy.some((blocker) => blocker.type === "skill_output"))
        .sort((left, right) => (left.followUp.nextAt ?? "9999").localeCompare(right.followUp.nextAt ?? "9999") || left.id.localeCompare(right.id))
      : [];
    const isEligible = ticket.status === "blocked" && blockedBy.length === 0;
    const eligibleSkillIds = isEligible
      ? ticket.mock_skill_dependencies
        .filter((skill) => skill.input_ids === undefined || skill.input_ids.every((inputId) => requirements.find((requirement) => requirement.id === inputId)?.state === "resolved"))
        .map((skill) => skill.id)
      : [];
    const readinessState = ticket.status === "blocked" ? (isEligible ? "eligible" : "blocked") : ticket.status;
    publicByTicketId.set(ticket.ticket_id, {
      requirements,
      blockedBy,
      unblocks: (unblocksByProducer.get(ticket.ticket_id) ?? []).sort((left, right) => (
        left.ticketId.localeCompare(right.ticketId) || left.requirementId.localeCompare(right.requirementId)
      )),
      skillOutputs: ticket.mock_skill_dependencies.flatMap((skill) => (skill.outputs ?? []).map((output) => ({
        skillId: skill.id,
        outputId: output.id,
        description: output.description,
        approved: approvedOutput(ticket),
        approvedAt: approvedOutput(ticket) ? ticket.review.decided_at : null
      }))),
      readiness: {
        state: readinessState,
        unresolvedRequirementIds: blockedBy.map((blocker) => blocker.requirementId),
        eligibleSkillIds
      },
      eligibleHumanRequests: eligibleHumanRequirements.map((eligibleHumanRequirement) => ({
        requirementId: eligibleHumanRequirement.id,
        employeeId: eligibleHumanRequirement.human.employeeId,
        channel: eligibleHumanRequirement.human.channel,
        question: eligibleHumanRequirement.human.question,
        dueAt: eligibleHumanRequirement.followUp.nextAt,
        due: eligibleHumanRequirement.followUp.nextAt !== null && Date.parse(eligibleHumanRequirement.followUp.nextAt) <= Date.parse(currentTime)
      })),
      eligibleHumanRequest: eligibleHumanRequirements.length > 0 ? {
        requirementId: eligibleHumanRequirements[0].id,
        employeeId: eligibleHumanRequirements[0].human.employeeId,
        channel: eligibleHumanRequirements[0].human.channel,
        question: eligibleHumanRequirements[0].human.question,
        dueAt: eligibleHumanRequirements[0].followUp.nextAt,
        due: eligibleHumanRequirements[0].followUp.nextAt !== null && Date.parse(eligibleHumanRequirements[0].followUp.nextAt) <= Date.parse(currentTime)
      } : null
    });
  }
  return { graph, publicByTicketId };
}

function writeTicket(record, ticket, events, write) {
  assertTicket(ticket, `ticket ${ticket.ticket_id}`);
  if (!write) return;
  atomicWrite(record.ticketPath, ticketMarkdown(ticket));
  if (!existsSync(record.progressPath)) atomicWrite(record.progressPath, progressHeader(ticket));
  mkdirSync(record.artifactsPath, { recursive: true });
  for (const event of events) appendFileSync(record.progressPath, progressLine(event));
}

function writeNewTicket(paths, ticket, events, write) {
  const record = ticketPaths(paths, ticket.ticket_id, false);
  if (existsSync(record.directory) || existsSync(ticketPaths(paths, ticket.ticket_id, true).directory)) {
    throw new Error(`ticket ${ticket.ticket_id} already exists in active or archive.`);
  }
  if (write) {
    mkdirSync(record.artifactsPath, { recursive: true });
    atomicWrite(record.ticketPath, ticketMarkdown(ticket));
    atomicWrite(record.progressPath, `${progressHeader(ticket)}${events.map(progressLine).join("")}`);
  }
  return record;
}

function loadRoster(paths) {
  const roster = readJson(paths.peoplePath, "employee directory");
  if (roster.schema_version !== 1 || !Array.isArray(roster.employees)) {
    throw new Error("employee directory must be schema_version 1 with an employees array.");
  }
  const employees = new Map();
  for (const employee of roster.employees) {
    if (!isObject(employee) || !isNonEmptyString(employee.id) || !isNonEmptyString(employee.display_name)) {
      throw new Error("employee directory contains an invalid employee.");
    }
    if (!isNonEmptyString(employee.timezone)) throw new Error(`employee ${employee.id} needs a timezone.`);
    if (!/^-?\d{5,20}$/.test(employee.telegram_target ?? "")) {
      throw new Error(`employee ${employee.id} needs a numeric Telegram chat ID.`);
    }
    for (const field of ["inbound_allowed", "outbound_allowed", "test_opt_in", "route_enabled"]) {
      if (typeof employee[field] !== "boolean") throw new Error(`employee ${employee.id} needs boolean ${field}.`);
    }
    if (!Number.isInteger(employee.global_cooldown_minutes) || employee.global_cooldown_minutes < 0) {
      throw new Error(`employee ${employee.id} needs a non-negative global_cooldown_minutes.`);
    }
    if (!Number.isInteger(employee.requirement_cooldown_minutes) || employee.requirement_cooldown_minutes < 0) {
      throw new Error(`employee ${employee.id} needs a non-negative requirement_cooldown_minutes.`);
    }
    if (!Array.isArray(employee.allowed_mock_drive_scopes)) throw new Error(`employee ${employee.id} needs allowed_mock_drive_scopes.`);
    if (employees.has(employee.id)) throw new Error(`employee directory duplicates ${employee.id}.`);
    employees.set(employee.id, employee);
  }
  return employees;
}

/** Validate and return the private employee directory without exposing targets to board projections. */
export function loadEmployeeDirectory({ workspaceRoot } = {}) {
  return new Map(loadRoster(runtimePaths(workspaceRoot)));
}

/** Append one delivery receipt to the draft's owning canonical progress file. */
export function appendDeliveryReceipt({
  workspaceRoot,
  ticketId,
  deliveryId,
  requirementId,
  employeeId,
  status,
  at = new Date().toISOString(),
  reason = null,
  platformMessageId = null
} = {}) {
  const paths = runtimePaths(workspaceRoot);
  assertTicketId(ticketId);
  if (!isNonEmptyString(deliveryId) || !isNonEmptyString(requirementId) || !isNonEmptyString(employeeId)) {
    throw new TypeError("deliveryId, requirementId, and employeeId are required.");
  }
  if (!new Set(["dry_run", "sent", "failed"]).has(status)) {
    throw new TypeError("delivery receipt status must be dry_run, sent, or failed.");
  }
  if (platformMessageId !== null && !isNonEmptyString(platformMessageId)) {
    throw new TypeError("platformMessageId must be a non-empty message ID or null.");
  }
  const record = getTicket(paths, ticketId);
  const requirement = record.ticket.requirements.find((candidate) => candidate.id === requirementId);
  if (!requirement || requirement.type !== "human_input" || requirement.follow_up.employee_id !== employeeId) {
    throw new Error(`delivery ${deliveryId} does not match ${ticketId}.${requirementId} for ${employeeId}.`);
  }
  const timestamp = canonicalTime(at, "delivery receipt at");
  const receipt = event(timestamp, "telegram_delivery_receipt", {
    delivery_id: deliveryId,
    requirement_id: requirementId,
    employee_id: employeeId,
    status,
    reason,
    delivery: "local_receipt",
    ...(platformMessageId ? { platform_message_id: platformMessageId } : {})
  });
  if (!existsSync(record.progressPath)) atomicWrite(record.progressPath, progressHeader(record.ticket));
  appendFileSync(record.progressPath, progressLine(receipt));
  return { ticketId, deliveryId, requirementId, employeeId, status, at: timestamp, reason, platformMessageId };
}

function readMeetingFixture(meetingOverride) {
  const source = meetingOverride ?? readJson(resolve(fixtureRoot, "meetings/mock-weekly-meeting.json"), "mock weekly meeting");
  const meeting = source?.kind === "pre_extracted_weekly_meeting" ? source.meeting : source;
  if (!isObject(meeting) || !isNonEmptyString(meeting.id) || !isNonEmptyString(meeting.at) || !Array.isArray(meeting.tasks)) {
    throw new Error("weekly meeting input is invalid.");
  }
  canonicalTime(meeting.at, "weekly meeting.at");
  return meeting;
}

function initialTicketFromMeetingTask(task, meetingAt) {
  const ticket = {
    ticket_id: task.ticket_id,
    title: task.title,
    description: task.description,
    workstream: task.workstream,
    owner_id: task.owner_id,
    reviewer_id: task.reviewer_id,
    start_at: task.start_at,
    due_at: task.due_at,
    status: "blocked",
    blocking_inputs: copy(task.blocking_inputs),
    requirements: copy(task.requirements),
    mock_skill_dependencies: copy(task.mock_skill_dependencies),
    artifact: null,
    review: { reviewer_id: task.reviewer_id, state: "pending_input", decided_at: null, decision: null },
    source: { meeting_id: task.meeting_id, recorded_at: meetingAt },
    created_at: meetingAt,
    updated_at: meetingAt
  };
  assertTicket(ticket, `mock ticket ${task.ticket_id}`);
  return ticket;
}

function event(at, type, data = {}) {
  return { at, type, ...data };
}

function addMinutes(timestamp, minutes) {
  return new Date(Date.parse(timestamp) + minutes * 60 * 1000).toISOString();
}

function workerLimit(value) {
  const candidate = value ?? defaultMaxWorkers;
  if (!Number.isInteger(candidate) || candidate < 1 || candidate > 16) {
    throw new TypeError("maxWorkers must be an integer from 1 to 16.");
  }
  return candidate;
}

function requiresDriveInput(ticket) {
  return ticket.blocking_inputs.find((input) => input.kind === "mock_drive_file") ?? null;
}

function sharedDriveEntries(paths) {
  if (!existsSync(paths.sharedDriveRoot)) return [];
  return readdirSync(paths.sharedDriveRoot, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .map((entry) => ({ path: resolve(paths.sharedDriveRoot, entry.name), value: readJson(resolve(paths.sharedDriveRoot, entry.name), "mock Drive file") }));
}

function findScopedDriveInput(paths, employee, ticket) {
  const input = requiresDriveInput(ticket);
  if (!input) throw new Error(`ticket ${ticket.ticket_id} has no scoped mock Drive input to reconcile.`);
  if (!employee.allowed_mock_drive_scopes.includes(driveScope)) {
    throw new Error(`employee ${employee.id} is not allowed to use mock Drive scope ${driveScope}.`);
  }
  const entry = sharedDriveEntries(paths).find(({ value }) =>
    value.input_id === input.id
    && value.scope === driveScope
    && Array.isArray(value.shared_with) && value.shared_with.includes("howie-ai")
    && value.storage_kind === "binary_local_edit"
    && value.native_workspace_format === null
    && isNonEmptyString(value.local_edit_format)
  );
  if (!entry) throw new Error(`no accessible howie-ai shared mock Drive file satisfies ${input.id}.`);
  return entry.value;
}

function draftArtifactPath(record) {
  return resolve(record.artifactsPath, "mock-skill-draft.md");
}

function sourceSkillTemplate(ticket) {
  const dependency = ticket.mock_skill_dependencies[0];
  if (!isNonEmptyString(dependency?.template)) throw new Error(`ticket ${ticket.ticket_id} has no mock skill template dependency.`);
  const sourcePath = resolve(fixtureRoot, "mock-skills", dependency.template);
  return { dependency, sourcePath, content: readText(sourcePath, `mock skill template ${dependency.id}`) };
}

function renderDraft(ticket, driveFile) {
  const { content } = sourceSkillTemplate(ticket);
  return interpolate(content, {
    ticket_id: ticket.ticket_id,
    title: ticket.title,
    drive_name: driveFile.name,
    drive_reference: driveFile.drive_url
  });
}

function publicDelivery(entry) {
  return {
    at: entry.at,
    type: entry.type,
    ticketId: entry.ticket_id,
    requirementId: entry.requirement_id,
    employeeId: entry.employee_id,
    deliveryId: entry.delivery_id,
    status: entry.status ?? "draft",
    delivery: entry.delivery ?? null,
    reason: entry.reason ?? null
  };
}

function outstandingPeopleFor(dependency) {
  return dependency.requirements
    .filter((requirement) => requirement.type === "human_input" && requirement.state === "unresolved")
    .map((requirement) => ({
      requirementId: requirement.id,
      description: requirement.description,
      employeeId: requirement.human.employeeId,
      followUp: copy(requirement.followUp)
    }));
}

function nextFollowUpAt(outstandingPeople) {
  return outstandingPeople
    .map((item) => item.followUp.nextAt)
    .filter(Boolean)
    .sort()[0] ?? null;
}

function publicTask(record, dependency, pendingDeliveries) {
  const ticket = record.ticket;
  const outstandingPeople = outstandingPeopleFor(dependency);
  return {
    ticketId: ticket.ticket_id,
    title: ticket.title,
    description: ticket.description,
    workstream: ticket.workstream,
    ownerId: ticket.owner_id,
    reviewerId: ticket.reviewer_id,
    status: ticket.status,
    startAt: ticket.start_at,
    dueAt: ticket.due_at,
    nextChaseAt: nextFollowUpAt(outstandingPeople),
    chaseAttempts: outstandingPeople.reduce((total, item) => total + item.followUp.attempts, 0),
    blockingInputs: copy(ticket.blocking_inputs),
    mockSkillDependencies: copy(ticket.mock_skill_dependencies),
    requirements: dependency.requirements,
    blockedBy: dependency.blockedBy,
    unblocks: dependency.unblocks,
    skillOutputs: dependency.skillOutputs,
    readiness: dependency.readiness,
    eligibleHumanRequest: dependency.eligibleHumanRequest,
    eligibleHumanRequests: dependency.eligibleHumanRequests,
    outstandingPeople,
    pendingDeliveries: pendingDeliveries.filter((delivery) => delivery.ticket_id === ticket.ticket_id).map(publicDelivery),
    artifact: copy(ticket.artifact),
    review: copy(ticket.review),
    archived: record.archived
  };
}

/** Read-only dashboard projection derived solely from ticket folders. */
export function inspectBoard({ workspaceRoot, now = new Date().toISOString() } = {}) {
  const paths = runtimePaths(workspaceRoot);
  const records = listTickets(paths);
  const dependencies = dependencyProjection(records, now);
  const pendingDeliveries = pendingDeliveriesFor(records);
  const tasks = records.map((record) => publicTask(record, dependencies.publicByTicketId.get(record.ticket.ticket_id), pendingDeliveries));
  const counts = Object.fromEntries([...statuses].map((status) => [status, tasks.filter((task) => task.status === status).length]));
  return {
    workspaceRoot: paths.root,
    tasks,
    gantt: tasks.map((task) => ({ ticketId: task.ticketId, title: task.title, startAt: task.startAt, dueAt: task.dueAt, status: task.status })),
    counts
  };
}

function recentProgress(record, limit = 4) {
  if (!existsSync(record.progressPath)) return [];
  return readText(record.progressPath, `progress for ${record.ticket.ticket_id}`)
    .split("\n")
    .filter((line) => line.startsWith("- "))
    .slice(-limit);
}

/**
 * Serializable dashboard state. It exposes only fake employee policy and
 * howie-ai shared mock Drive files; it never reads an external Drive or a
 * private contact target.
 */
export function dashboardState({ workspaceRoot, now = new Date().toISOString() } = {}) {
  const paths = runtimePaths(workspaceRoot);
  const board = inspectBoard({ workspaceRoot: paths.root, now });
  const employees = existsSync(paths.peoplePath)
    ? [...loadRoster(paths).values()].map((employee) => ({
      id: employee.id,
      displayName: employee.display_name,
      timezone: employee.timezone,
      globalCooldownMinutes: employee.global_cooldown_minutes,
      requirementCooldownMinutes: employee.requirement_cooldown_minutes,
      routeEnabled: employee.route_enabled,
      allowedMockDriveScopes: copy(employee.allowed_mock_drive_scopes)
    }))
    : [];
  const records = listTickets(paths);
  const deliveryEvents = deliveryEventsFor(records).map(publicDelivery);
  return {
    board,
    employees,
    driveFiles: sharedDriveEntries(paths).map(({ value }) => copy(value)),
    weeklyReport: generateWeeklyReport({ workspaceRoot: paths.root, now, write: false }).markdown,
    lastActions: records.flatMap((record) => recentProgress(record).map((line) => ({ ticketId: record.ticket.ticket_id, line }))),
    deliveryEvents,
    deliveryTimeline: deliveryEvents
  };
}

/** Create only missing canonical ticket folders from the four-task mock meeting. */
export function scanMeeting({ workspaceRoot, write = false, meeting: meetingOverride } = {}) {
  const paths = runtimePaths(workspaceRoot);
  const meeting = readMeetingFixture(meetingOverride);
  const existingRecords = listTickets(paths);
  const existing = new Set(existingRecords.map((record) => record.ticket.ticket_id));
  const meetingAt = canonicalTime(meeting.at, "meeting.at");
  const pendingTickets = meeting.tasks
    .filter((task) => !existing.has(task.ticket_id))
    .map((task) => initialTicketFromMeetingTask({ ...task, meeting_id: meeting.id }, meetingAt));
  validateDependencyGraph([...existingRecords, ...pendingTickets]);
  const createdTicketIds = [];
  const skippedTicketIds = [];
  for (const task of meeting.tasks) {
    assertTicketId(task.ticket_id);
    if (existing.has(task.ticket_id)) {
      skippedTicketIds.push(task.ticket_id);
      continue;
    }
    const ticket = pendingTickets.find((candidate) => candidate.ticket_id === task.ticket_id);
    writeNewTicket(paths, ticket, [event(ticket.created_at, "meeting_scanned", { meeting_id: meeting.id })], write);
    createdTicketIds.push(ticket.ticket_id);
    existing.add(ticket.ticket_id);
  }
  return { workspaceRoot: paths.root, meetingId: meeting.id, write, createdTicketIds, skippedTicketIds };
}

function latestDeliveryEventByEmployee(records) {
  const latest = new Map();
  for (const entry of deliveryEventsFor(records)) {
    if (!entry.employee_id || !["telegram_delivery_draft", "telegram_delivery_receipt"].includes(entry.type)) continue;
    const previous = latest.get(entry.employee_id);
    if (!previous || Date.parse(entry.at) > Date.parse(previous)) latest.set(entry.employee_id, entry.at);
  }
  return latest;
}

function requestAvailability({ requirement, employee, runAt, latestAt }) {
  if (!employee) return { reason: "unknown_employee" };
  if (!employee.route_enabled) return { reason: "employee_route_disabled" };
  if (!employee.outbound_allowed) return { reason: "employee_outbound_disabled" };
  if (!employee.test_opt_in) return { reason: "employee_missing_test_opt_in" };
  const globalAvailableAt = latestAt ? addMinutes(latestAt, employee.global_cooldown_minutes) : null;
  if (globalAvailableAt && Date.parse(globalAvailableAt) > Date.parse(runAt)) {
    return { reason: "employee_global_cooldown", availableAt: globalAvailableAt };
  }
  const followUp = requirement.followUp;
  if (followUp.status !== "pending") return { reason: "follow_up_terminal" };
  if (followUp.nextAt && Date.parse(followUp.nextAt) > Date.parse(runAt)) {
    return { reason: "requirement_cooldown", availableAt: followUp.nextAt };
  }
  return null;
}

function recordEscalationIfDue(ticket, requirement, at, trigger) {
  const followUp = requirement.follow_up;
  const alreadyEscalated = followUp.escalation !== undefined && followUp.escalation !== null;
  const pastDue = Date.parse(at) >= Date.parse(ticket.due_at);
  if (alreadyEscalated || !pastDue || followUp.attempts < escalationAttemptThreshold) return null;
  const escalation = {
    at,
    next_owner_id: escalationOwnerId,
    reason: `Blocked after ${followUp.attempts} bounded follow-ups; ${ticket.ticket_id} is past its due date.`,
    requirement_id: requirement.id,
    employee_id: followUp.employee_id,
    trigger
  };
  followUp.escalation = escalation;
  followUp.status = "escalated";
  followUp.next_at = null;
  return escalation;
}

function workerSource(ticket, skillId) {
  return {
    name: "all declared inputs resolved",
    drive_url: `drive://aurora-lithium/working/${ticket.ticket_id}/${skillId}`
  };
}

function startEligibleWorker({ record, ticket, skillId, at, workerId, trigger, write }) {
  const skill = ticket.mock_skill_dependencies.find((candidate) => candidate.id === skillId);
  if (!skill) throw new Error(`ticket ${ticket.ticket_id} has no eligible mock skill ${skillId}.`);
  ticket.status = "in_progress";
  ticket.review = { ...ticket.review, state: "pending_artifact" };
  ticket.updated_at = at;
  const draftPath = draftArtifactPath(record);
  const source = workerSource(ticket, skillId);
  if (write) atomicWrite(draftPath, renderDraft(ticket, source));
  const worker = {
    ticketId: ticket.ticket_id,
    skillId,
    workerId,
    trigger,
    at,
    execution: "local_mock"
  };
  const events = [
    event(at, "mock_worker_dispatched", {
      ticket_id: ticket.ticket_id,
      skill_id: skillId,
      worker_id: workerId,
      trigger,
      execution: "local_mock"
    }),
    event(at, "mock_skill_draft_ready", { template: skill.template, skill_id: skillId, worker_id: workerId })
  ];
  writeTicket(record, ticket, events, write);
  return { ticket, worker, draftPath, events };
}

/**
 * Starts only skills whose declared human and producer-output requirements are
 * all resolved. The workers are deterministic local mock slots, not Hermes
 * processes or external side effects.
 */
export function dispatchEligibleWorkers({ workspaceRoot, now, maxWorkers = defaultMaxWorkers, write = false } = {}) {
  const paths = runtimePaths(workspaceRoot);
  const at = canonicalTime(now, "now");
  const limit = workerLimit(maxWorkers);
  const records = listTickets(paths);
  const projection = dependencyProjection(records, at);
  const candidates = records
    .filter((record) => !record.archived && record.ticket.status === "blocked")
    .map((record) => ({ record, state: projection.publicByTicketId.get(record.ticket.ticket_id) }))
    .filter(({ state }) => state.readiness.state === "eligible" && state.readiness.eligibleSkillIds.length > 0)
    .sort((left, right) => (
      left.record.ticket.start_at.localeCompare(right.record.ticket.start_at)
      || left.record.ticket.ticket_id.localeCompare(right.record.ticket.ticket_id)
    ))
    .slice(0, limit);
  const workerDispatches = candidates.map(({ record, state }, index) => {
    const ticket = copy(record.ticket);
    const skillId = state.readiness.eligibleSkillIds[0];
    const started = startEligibleWorker({
      record,
      ticket,
      skillId,
      at,
      workerId: `howie-worker-${index + 1}`,
      trigger: "requirements_resolved",
      write
    });
    return { ...started.worker, draftArtifactPath: started.draftPath };
  });
  return { workspaceRoot: paths.root, write, runAt: at, maxWorkers: limit, workerDispatches };
}

function draftDeliveryId(ticket, requirement) {
  return `${ticket.ticket_id}:${requirement.id}:${requirement.follow_up.attempts + 1}`;
}

function recordTelegramDeliveryDraft({ record, requirementId, employee, at, write, action = "follow_up", reason = null }) {
  const ticket = copy(record.ticket);
  const requirement = ticket.requirements.find((candidate) => candidate.id === requirementId);
  if (!requirement || requirement.type !== "human_input") throw new Error(`ticket ${ticket.ticket_id} has no human requirement ${requirementId}.`);
  const followUp = requirement.follow_up;
  const deliveryId = draftDeliveryId(ticket, requirement);
  followUp.attempts += 1;
  followUp.last_at = at;
  followUp.next_at = addMinutes(at, followUp.cooldown_minutes ?? employee.requirement_cooldown_minutes);
  followUp.delivery_id = deliveryId;
  followUp.status = "pending";
  ticket.updated_at = at;
  const draft = {
    ticketId: ticket.ticket_id,
    requirementId: requirement.id,
    employeeId: employee.id,
    deliveryId,
    channel: "telegram_delivery",
    question: requirement.human.question,
    action,
    reason,
    at,
    nextAt: followUp.next_at,
    attempt: followUp.attempts,
    delivery: "draft_only"
  };
  const escalation = recordEscalationIfDue(ticket, requirement, at, action === "follow_up" ? "repeated_follow_up" : action);
  if (escalation) {
    draft.escalation = copy(escalation);
    draft.nextAt = null;
  }
  const events = [event(at, "telegram_delivery_draft", {
    delivery_id: deliveryId,
    requirement_id: requirement.id,
    employee_id: employee.id,
    channel: "telegram_delivery",
    question: requirement.human.question,
    action,
    reason,
    attempt: followUp.attempts,
    next_at: followUp.next_at,
    delivery: "draft_only"
  })];
  if (escalation) events.push(event(at, "ticket_escalated", escalation));
  writeTicket(record, ticket, events, write);
  return draft;
}

function recordExpertChase({ record, requirement, employee, at, reason, write }) {
  const draft = recordTelegramDeliveryDraft({
    record,
    requirementId: requirement.id,
    employee,
    at,
    write,
    action: "request_scoped_source_refresh",
    reason
  });
  return { expertChase: draft, escalation: draft.escalation ?? null };
}

function dependencyStateFor(records, ticketId, now) {
  const projection = dependencyProjection(records, now);
  const state = projection.publicByTicketId.get(ticketId);
  if (!state) throw new Error(`ticket ${ticketId} does not exist in the dependency graph.`);
  return { projection, state };
}

/**
 * Determine due, dependency-eligible human requests. It creates only a
 * ticket-local Telegram delivery draft; no transport or outbox exists.
 */
export function runPulse({ workspaceRoot, now, maxWorkers = defaultMaxWorkers, write = false } = {}) {
  const paths = runtimePaths(workspaceRoot);
  const runAt = canonicalTime(now, "now");
  const workerRun = dispatchEligibleWorkers({ workspaceRoot: paths.root, now: runAt, maxWorkers, write });
  const employees = loadRoster(paths);
  const records = listTickets(paths);
  const activeTickets = records.filter((record) => !record.archived);
  const projection = dependencyProjection(records, runAt);
  const latestByEmployee = latestDeliveryEventByEmployee(activeTickets);
  const deliveryDrafts = [];
  const escalations = [];
  const cooldowns = [];
  const staleTicketIds = [];
  for (const record of activeTickets) {
    const task = projection.publicByTicketId.get(record.ticket.ticket_id);
    const dueRequests = task.eligibleHumanRequests.filter((request) => request.due);
    if (dueRequests.length > 0) staleTicketIds.push(record.ticket.ticket_id);
    for (const request of dueRequests) {
      const employee = employees.get(request.employeeId);
      const requirement = task.requirements.find((candidate) => candidate.id === request.requirementId);
      const unavailable = requestAvailability({ requirement, employee, runAt, latestAt: latestByEmployee.get(request.employeeId) });
      if (unavailable) {
        cooldowns.push({ ticketId: record.ticket.ticket_id, requirementId: request.requirementId, ...unavailable });
        continue;
      }
      const writableRecord = write ? getTicket(paths, record.ticket.ticket_id) : record;
      const draft = recordTelegramDeliveryDraft({ record: writableRecord, requirementId: request.requirementId, employee, at: runAt, write });
      latestByEmployee.set(employee.id, runAt);
      deliveryDrafts.push(draft);
      if (draft.escalation) escalations.push({ ticketId: record.ticket.ticket_id, ...draft.escalation });
    }
  }
  return {
    workspaceRoot: paths.root,
    write,
    runAt,
    maxWorkers: workerRun.maxWorkers,
    workerDispatches: workerRun.workerDispatches,
    deliveryDrafts,
    chases: deliveryDrafts,
    escalations,
    cooldowns,
    staleTicketIds
  };
}

/** Record exactly one due human request as a local Telegram delivery draft, never a send. */
export function previewHumanRequest({ workspaceRoot, ticketId, requirementId, now, write = false } = {}) {
  const paths = runtimePaths(workspaceRoot);
  assertTicketId(ticketId);
  if (!isNonEmptyString(requirementId)) throw new TypeError("requirementId is required.");
  const at = canonicalTime(now, "now");
  const records = listTickets(paths);
  const record = records.find((candidate) => candidate.ticket.ticket_id === ticketId && !candidate.archived);
  if (!record) throw new Error(`ticket ${ticketId} does not exist in the active board.`);
  const { state } = dependencyStateFor(records, ticketId, at);
  const request = state.eligibleHumanRequests.find((candidate) => candidate.requirementId === requirementId);
  if (!request || !request.due) {
    throw new Error(`human requirement ${ticketId}.${requirementId} is not due and dependency-eligible.`);
  }
  const employee = loadRoster(paths).get(request.employeeId);
  const requirement = state.requirements.find((candidate) => candidate.id === requirementId);
  const unavailable = requestAvailability({ requirement, employee, runAt: at, latestAt: latestDeliveryEventByEmployee(records.filter((candidate) => !candidate.archived)).get(request.employeeId) });
  if (unavailable) throw new Error(`human requirement ${ticketId}.${requirementId} cannot be drafted: ${unavailable.reason}.`);
  const deliveryDraft = recordTelegramDeliveryDraft({ record, requirementId, employee, at, write });
  return { workspaceRoot: paths.root, write, ticketId, requirementId, deliveryDraft };
}

function boundedResponse(text) {
  if (!isNonEmptyString(text) || text.trim().length > 500) {
    throw new TypeError("text must be a non-empty response of at most 500 characters.");
  }
  return text.trim();
}

function replaceRecordTicket(records, ticketId, ticket) {
  return records.map((record) => record.ticket.ticket_id === ticketId ? { ...record, ticket } : record);
}

/**
 * Development-only bounded reply simulation. It resolves one named human
 * requirement and never accepts a transport payload. The next pulse stages a
 * declared mock skill only after all requirements are resolved.
 */
export function recordHumanResponse({ workspaceRoot, ticketId, requirementId, employeeId, text, now = new Date().toISOString(), write = false } = {}) {
  const paths = runtimePaths(workspaceRoot);
  assertTicketId(ticketId);
  if (!isNonEmptyString(requirementId) || !isNonEmptyString(employeeId)) throw new TypeError("requirementId and employeeId are required.");
  const response = boundedResponse(text);
  const at = canonicalTime(now, "now");
  const employees = loadRoster(paths);
  const employee = employees.get(employeeId);
  if (!employee) throw new Error(`employee ${employeeId} is not in the private employee directory.`);
  if (!employee.route_enabled || !employee.inbound_allowed) {
    throw new Error(`employee ${employeeId} has its inbound Telegram route disabled.`);
  }
  const records = listTickets(paths);
  const record = records.find((candidate) => candidate.ticket.ticket_id === ticketId && !candidate.archived);
  if (!record) throw new Error(`ticket ${ticketId} does not exist in the active board.`);
  const { state } = dependencyStateFor(records, ticketId, at);
  const request = state.eligibleHumanRequests.find((candidate) => candidate.requirementId === requirementId);
  if (!request) {
    throw new Error(`human requirement ${ticketId}.${requirementId} is not dependency-eligible.`);
  }
  if (request.employeeId !== employeeId) throw new Error(`employee ${employeeId} cannot resolve ${ticketId}.${requirementId}.`);
  const ticket = copy(record.ticket);
  const sourceRequirement = requirementsFor(ticket).find((requirement) => requirement.id === requirementId);
  let acceptedDriveInput = null;
  if (sourceRequirement?.human?.requires_mock_drive_input) {
    try {
      acceptedDriveInput = findScopedDriveInput(paths, employee, ticket);
    } catch (error) {
      recordExpertChase({
        record,
        requirement: sourceRequirement,
        employee,
        at,
        reason: error instanceof Error ? error.message : String(error),
        write
      });
      throw error;
    }
  }
  if (Array.isArray(ticket.requirements)) {
    ticket.requirements = ticket.requirements.map((requirement) => requirement.id === requirementId ? {
      ...requirement,
      state: "resolved",
      resolution: { at, source: "simulated_human_response", employee_id: employeeId },
      follow_up: {
        ...requirement.follow_up,
        status: "resolved",
        next_at: null
      }
    } : requirement);
  }
  ticket.blocking_inputs = ticket.blocking_inputs.filter((input) => input.id !== requirementId);
  ticket.updated_at = at;
  const events = [event(at, "simulated_human_response", {
    requirement_id: requirementId,
    employee_id: employeeId,
    text: response,
    development_only: true
  })];
  if (acceptedDriveInput) {
    events.push(event(at, "mock_drive_input_accepted", {
      input_id: acceptedDriveInput.input_id,
      name: acceptedDriveInput.name,
      storage_kind: acceptedDriveInput.storage_kind,
      local_edit_format: acceptedDriveInput.local_edit_format,
      native_workspace_format: acceptedDriveInput.native_workspace_format
    }));
  }
  writeTicket(record, ticket, events, write);
  const finalState = dependencyStateFor(replaceRecordTicket(records, ticketId, ticket), ticketId, at).state;
  return {
    workspaceRoot: paths.root,
    write,
    ticketId,
    requirementId,
    status: ticket.status,
    acceptedDriveInput: acceptedDriveInput ? copy(acceptedDriveInput) : null,
    draftArtifactPath: null,
    readiness: finalState.readiness,
    events
  };
}

/** Preserve the original geo/Drive demo API as a named human response wrapper. */
export function recordReply({ workspaceRoot, ticketId, employeeId, text, now, write = false } = {}) {
  const paths = runtimePaths(workspaceRoot);
  assertTicketId(ticketId);
  const record = getTicket(paths, ticketId);
  const driveInput = requiresDriveInput(record.ticket);
  if (!driveInput) throw new Error(`ticket ${ticketId} has no scoped mock Drive input to reconcile.`);
  return recordHumanResponse({ workspaceRoot: paths.root, ticketId, requirementId: driveInput.id, employeeId, text, now, write });
}

function resolveDependentOutputRequirements(records, producerTicket, at) {
  const resolved = [];
  for (const record of records) {
    if (record.archived || record.ticket.ticket_id === producerTicket.ticket_id || !Array.isArray(record.ticket.requirements)) continue;
    const ticket = copy(record.ticket);
    const changedRequirementIds = [];
    ticket.requirements = ticket.requirements.map((requirement) => {
      if (requirement.type !== "skill_output" || requirement.state === "resolved") return requirement;
      const upstream = requirement.upstream;
      const matchesProducer = upstream.ticket_id === producerTicket.ticket_id
        && producerTicket.mock_skill_dependencies.some((skill) => skill.id === upstream.skill_id
          && (skill.outputs ?? []).some((output) => output.id === upstream.output_id));
      if (!matchesProducer) return requirement;
      changedRequirementIds.push(requirement.id);
      return {
        ...requirement,
        state: "resolved",
        resolution: {
          at,
          source: "approved_upstream_output",
          producer_ticket_id: upstream.ticket_id,
          producer_skill_id: upstream.skill_id,
          producer_output_id: upstream.output_id
        }
      };
    });
    if (changedRequirementIds.length === 0) continue;
    ticket.updated_at = at;
    resolved.push({
      record,
      ticket,
      requirementIds: changedRequirementIds,
      events: changedRequirementIds.map((requirementId) => event(at, "upstream_output_resolved", {
        requirement_id: requirementId,
        producer_ticket_id: producerTicket.ticket_id,
        source: "approved_upstream_output"
      }))
    });
  }
  return resolved;
}

/** Publish an existing mock skill draft into the howie-ai scoped Drive mock and await review. */
export function publishArtifact({ workspaceRoot, ticketId, write = false } = {}) {
  const paths = runtimePaths(workspaceRoot);
  assertTicketId(ticketId);
  const records = listTickets(paths);
  validateDependencyGraph(records);
  const record = records.find((candidate) => candidate.ticket.ticket_id === ticketId && !candidate.archived);
  if (!record) throw new Error(`ticket ${ticketId} does not exist in the active board.`);
  const ticket = copy(record.ticket);
  if (ticket.status !== "in_progress") throw new Error(`ticket ${ticketId} must be in_progress before publication.`);
  const draftPath = draftArtifactPath(record);
  if (write && !existsSync(draftPath)) throw new Error(`ticket ${ticketId} has no generated mock skill draft to publish.`);
  const at = new Date().toISOString();
  const artifact = {
    id: `${ticketId.toLowerCase()}-artifact`,
    name: `${ticket.title} — mock Workspace document`,
    source_ticket_id: ticketId,
    scope: driveScope,
    shared_with: ["howie-ai"],
    storage_kind: "native_workspace",
    local_edit_format: null,
    native_workspace_format: "application/vnd.google-apps.document",
    drive_url: `drive://aurora-lithium/published/${ticketId.toLowerCase()}-artifact`,
    published_at: at
  };
  ticket.status = "awaiting_review";
  ticket.artifact = artifact;
  ticket.review = { ...ticket.review, state: "pending_review", requested_at: at };
  ticket.updated_at = at;
  if (write) atomicWrite(resolve(paths.sharedDriveRoot, `${ticketId.toLowerCase()}-artifact.json`), `${JSON.stringify(artifact, null, 2)}\n`);
  const events = [event(at, "artifact_published", {
    artifact_id: artifact.id,
    storage_kind: artifact.storage_kind,
    native_workspace_format: artifact.native_workspace_format,
    local_edit_format: artifact.local_edit_format
  })];
  writeTicket(record, ticket, events, write);
  return { workspaceRoot: paths.root, write, ticketId, status: ticket.status, artifact: copy(artifact), events };
}

/** Review a published mock artifact; approval moves the canonical ticket folder to archive. */
export function reviewArtifact({ workspaceRoot, ticketId, reviewerId, decision, write = false, now = new Date().toISOString() } = {}) {
  const paths = runtimePaths(workspaceRoot);
  assertTicketId(ticketId);
  if (!isNonEmptyString(reviewerId)) throw new TypeError("reviewerId is required.");
  const normalizedDecision = String(decision ?? "").toLowerCase();
  if (!new Set(["approved", "rejected"]).has(normalizedDecision)) throw new TypeError("decision must be approved or rejected.");
  const records = listTickets(paths);
  validateDependencyGraph(records);
  const record = records.find((candidate) => candidate.ticket.ticket_id === ticketId && !candidate.archived);
  if (!record) throw new Error(`ticket ${ticketId} does not exist in the active board.`);
  const ticket = copy(record.ticket);
  if (ticket.status !== "awaiting_review") throw new Error(`ticket ${ticketId} is not awaiting review.`);
  if (ticket.reviewer_id !== reviewerId) throw new Error(`reviewer ${reviewerId} is not assigned to ${ticketId}.`);
  const at = canonicalTime(now, "now");
  if (normalizedDecision === "approved" && existsSync(ticketPaths(paths, ticketId, true).directory)) {
    throw new Error(`archive already contains ${ticketId}.`);
  }
  ticket.status = normalizedDecision === "approved" ? "done" : "blocked";
  ticket.review = {
    ...ticket.review,
    state: normalizedDecision === "approved" ? "approved" : "changes_requested",
    decision: normalizedDecision,
    decided_at: at,
    reviewer_id: reviewerId
  };
  if (normalizedDecision === "rejected") {
    const owner = loadRoster(paths).get(ticket.owner_id);
    const nextAt = addMinutes(at, owner.requirement_cooldown_minutes);
    ticket.blocking_inputs = [...ticket.blocking_inputs, {
      id: "review-changes",
      kind: "review",
      description: "Kenji requested changes to the published mock artifact."
    }];
    ticket.requirements = [...ticket.requirements, {
      id: "review-changes",
      type: "human_input",
      description: "Kenji requested changes to the published mock artifact.",
      state: "unresolved",
      human: {
        employee_id: ticket.owner_id,
        channel: "telegram_delivery",
        question: "Please confirm the requested artifact changes before the next review."
      },
      follow_up: {
        employee_id: ticket.owner_id,
        attempts: 0,
        last_at: null,
        next_at: nextAt,
        cooldown_minutes: owner.requirement_cooldown_minutes,
        delivery_id: null,
        status: "pending",
        escalation: null
      }
    }];
  }
  ticket.updated_at = at;
  const events = [event(at, "artifact_reviewed", { reviewer_id: reviewerId, decision: normalizedDecision })];
  const downstreamResolutions = normalizedDecision === "approved"
    ? resolveDependentOutputRequirements(records, ticket, at)
    : [];
  writeTicket(record, ticket, events, write);
  for (const downstream of downstreamResolutions) writeTicket(downstream.record, downstream.ticket, downstream.events, write);
  let archivePath = null;
  if (normalizedDecision === "approved") {
    archivePath = ticketPaths(paths, ticketId, true).directory;
    if (write) {
      mkdirSync(dirname(archivePath), { recursive: true });
      renameSync(record.directory, archivePath);
    }
  }
  return {
    workspaceRoot: paths.root,
    write,
    ticketId,
    status: ticket.status,
    decision: normalizedDecision,
    archivePath,
    events,
    resolvedDependencies: downstreamResolutions.map((resolution) => ({
      ticketId: resolution.ticket.ticket_id,
      requirementIds: resolution.requirementIds
    }))
  };
}

/** Seed only deterministic fake employee policy and howie-ai shared mock evidence, then scan the meeting. */
export function seedDemo({ workspaceRoot, write = false } = {}) {
  const paths = runtimePaths(workspaceRoot);
  const changes = [];
  const employeeExample = readText(resolve(fixtureRoot, "people/employees.private.example.json"), "employee example");
  const geoInput = readText(resolve(fixtureRoot, "shared-drive/geo-source.json"), "mock Drive input");
  if (!existsSync(paths.peoplePath)) {
    changes.push({ type: "create", path: paths.peoplePath, source: "employees.private.example.json" });
    if (write) atomicWrite(paths.peoplePath, employeeExample);
  }
  const geoInputPath = resolve(paths.sharedDriveRoot, "geo-source.json");
  if (!existsSync(geoInputPath)) {
    changes.push({ type: "create", path: geoInputPath, source: "geo-source.json" });
    if (write) atomicWrite(geoInputPath, geoInput);
  }
  const meeting = scanMeeting({ workspaceRoot: paths.root, write });
  return { workspaceRoot: paths.root, write, changes, meeting };
}

/** Update only the explicit fake employee route gate; tickets and Drive files are untouched. */
export function setEmployeeRoutePolicy({ workspaceRoot, employeeId, enabled, write = false } = {}) {
  const paths = runtimePaths(workspaceRoot);
  if (!isNonEmptyString(employeeId) || typeof enabled !== "boolean") {
    throw new TypeError("employeeId and boolean enabled are required.");
  }
  const roster = readJson(paths.peoplePath, "employee directory");
  if (roster.schema_version !== 1 || !Array.isArray(roster.employees)) {
    throw new Error("employee directory must be schema_version 1 with an employees array.");
  }
  const employee = roster.employees.find((candidate) => candidate.id === employeeId);
  if (!employee) throw new Error(`employee ${employeeId} is not in the private employee directory.`);
  employee.route_enabled = enabled;
  if (write) atomicWrite(paths.peoplePath, `${JSON.stringify(roster, null, 2)}\n`);
  return { workspaceRoot: paths.root, write, employeeId, enabled };
}

function weekStart(timestamp) {
  const date = new Date(timestamp);
  const day = date.getUTCDay();
  const offset = day === 0 ? 6 : day - 1;
  date.setUTCDate(date.getUTCDate() - offset);
  date.setUTCHours(0, 0, 0, 0);
  return date.toISOString().slice(0, 10);
}

/** Generate a derived weekly report; it never becomes a second task system. */
export function generateWeeklyReport({ workspaceRoot, now, write = false } = {}) {
  const paths = runtimePaths(workspaceRoot);
  const generatedAt = canonicalTime(now, "now");
  const board = inspectBoard({ workspaceRoot: paths.root });
  const lines = [
    "---",
    `week_of: ${JSON.stringify(weekStart(generatedAt))}`,
    `generated_at: ${JSON.stringify(generatedAt)}`,
    "---",
    "",
    "# Howie AI weekly report",
    "",
    `Blocked: ${board.counts.blocked}; in progress: ${board.counts.in_progress}; awaiting review: ${board.counts.awaiting_review}; done: ${board.counts.done}.`,
    ""
  ];
  for (const task of board.tasks) {
    lines.push(`- ${task.ticketId} — ${task.status} — ${task.title}; owner ${task.ownerId}; due ${task.dueAt}.`);
  }
  const markdown = `${lines.join("\n")}\n`;
  const reportPath = resolve(paths.reportsRoot, `weekly-${weekStart(generatedAt)}.md`);
  if (write) atomicWrite(reportPath, markdown);
  return { workspaceRoot: paths.root, write, generatedAt, reportPath, markdown, board };
}

/**
 * Narrow dashboard action dispatcher. A caller must set `enabled: true`; the
 * action is then routed only to one deterministic local mutation API.
 */
export function runDashboardAction({
  workspaceRoot,
  action,
  enabled = false,
  ticketId,
  requirementId,
  employeeId,
  text,
  reviewerId,
  decision,
  routeEnabled,
  now
} = {}) {
  if (enabled !== true) throw new Error("dashboard action requires enabled: true.");
  let result;
  switch (action) {
    case "seed": result = seedDemo({ workspaceRoot, write: true }); break;
    case "scan": result = scanMeeting({ workspaceRoot, write: true }); break;
    case "pulse": result = runPulse({ workspaceRoot, now, write: true }); break;
    case "preview_human_request": result = previewHumanRequest({
      workspaceRoot,
      ticketId,
      requirementId,
      now: now ?? new Date().toISOString(),
      write: true
    }); break;
    case "simulate_human_response": result = recordHumanResponse({
      workspaceRoot,
      ticketId,
      requirementId,
      employeeId,
      text,
      now: now ?? new Date().toISOString(),
      write: true
    }); break;
    case "reply": result = recordReply({ workspaceRoot, ticketId, employeeId, text, now, write: true }); break;
    case "publish": result = publishArtifact({ workspaceRoot, ticketId, write: true }); break;
    case "review": result = reviewArtifact({ workspaceRoot, ticketId, reviewerId, decision, now, write: true }); break;
    case "report": result = generateWeeklyReport({ workspaceRoot, now, write: true }); break;
    case "toggle_employee_access": result = setEmployeeRoutePolicy({ workspaceRoot, employeeId, enabled: routeEnabled, write: true }); break;
    default: throw new Error("dashboard action must be seed, scan, pulse, preview_human_request, simulate_human_response, reply, publish, review, report, or toggle_employee_access.");
  }
  return { action, result, state: dashboardState({ workspaceRoot, now: now ?? new Date().toISOString() }) };
}

function argumentValue(argumentsList, name) {
  const index = argumentsList.indexOf(name);
  return index === -1 ? undefined : argumentsList[index + 1];
}

function printResult(result) {
  console.log(JSON.stringify(result, null, 2));
}

function runCli() {
  const [command, ...argumentsList] = process.argv.slice(2);
  const workspaceRoot = argumentValue(argumentsList, "--workspace")
    ? resolve(argumentValue(argumentsList, "--workspace"))
    : defaultWorkspaceRoot;
  const write = argumentsList.includes("--write");
  switch (command) {
    case "board": return printResult(inspectBoard({ workspaceRoot }));
    case "scan": return printResult(scanMeeting({ workspaceRoot, write }));
    case "pulse": return printResult(runPulse({ workspaceRoot, now: argumentValue(argumentsList, "--now"), write }));
    case "reply": return printResult(recordReply({
      workspaceRoot,
      ticketId: argumentValue(argumentsList, "--ticket"),
      employeeId: argumentValue(argumentsList, "--employee"),
      text: argumentValue(argumentsList, "--text"),
      write
    }));
    case "publish": return printResult(publishArtifact({ workspaceRoot, ticketId: argumentValue(argumentsList, "--ticket"), write }));
    case "review": return printResult(reviewArtifact({
      workspaceRoot,
      ticketId: argumentValue(argumentsList, "--ticket"),
      reviewerId: argumentValue(argumentsList, "--reviewer"),
      decision: argumentValue(argumentsList, "--decision"),
      now: argumentValue(argumentsList, "--now") ?? new Date().toISOString(),
      write
    }));
    case "seed": return printResult(seedDemo({ workspaceRoot, write }));
    case "report": return printResult(generateWeeklyReport({ workspaceRoot, now: argumentValue(argumentsList, "--now"), write }));
    default:
      throw new Error("Usage: company-manager <board|scan|pulse|reply|publish|review|seed|report> --workspace path [--write]");
  }
}

const invokedAsScript = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedAsScript) {
  try {
    runCli();
  } catch (error) {
    console.error(`Company manager error: ${error.message}`);
    process.exitCode = 1;
  }
}
