import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

export const MANAGER_STATE_SCHEMA_VERSION = 1;
export const PULSE_INTERVAL_MS = 30 * 60 * 1000;

const commitmentStatuses = new Set(["open", "resolved"]);
const escalationStatuses = new Set(["pending", "escalated", "suppressed", "not_required"]);
const outboxStatuses = new Set(["draft", "approved_for_poc", "sent", "failed", "suppressed"]);
const outboxTypes = new Set(["reminder", "commitment_escalation", "meeting_note_escalation"]);
const inboundTypes = new Set(["receipt", "artifact", "meeting_note"]);
const isoPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:Z|[+-]\d{2}:\d{2})$/;

export class ManagerStateValidationError extends Error {
  constructor(errors) {
    super(`Manager state is invalid: ${errors.join("; ")}`);
    this.name = "ManagerStateValidationError";
    this.errors = errors;
  }
}

function isObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function isIsoTimestamp(value) {
  return typeof value === "string" && isoPattern.test(value) && Number.isFinite(Date.parse(value));
}

function isHttpUrl(value) {
  if (!isNonEmptyString(value)) return false;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}

function nullableIsoTimestamp(value) {
  return value === null || isIsoTimestamp(value);
}

function addError(errors, condition, message) {
  if (!condition) errors.push(message);
}

function uniqueString(value, set, errors, label) {
  if (!isNonEmptyString(value)) {
    errors.push(`${label} must be a non-empty string.`);
    return;
  }
  if (set.has(value)) errors.push(`${label} duplicates ${value}.`);
  set.add(value);
}

function validArtifact(artifact, label, errors) {
  if (artifact === null) return;
  if (!isObject(artifact)) {
    errors.push(`${label} must be an object or null.`);
    return;
  }
  addError(errors, isNonEmptyString(artifact.id), `${label}.id must be a non-empty string.`);
  addError(errors, isNonEmptyString(artifact.name), `${label}.name must be a non-empty string.`);
  addError(errors, artifact.url === undefined || artifact.url === null || isNonEmptyString(artifact.url), `${label}.url must be a non-empty string or null when present.`);
}

function validTaskLink(taskLink, label, errors) {
  if (!isObject(taskLink)) {
    errors.push(`${label} must be an object.`);
    return;
  }
  addError(errors, isNonEmptyString(taskLink.id), `${label}.id must be a non-empty string.`);
  addError(errors, taskLink.url === undefined || taskLink.url === null || isNonEmptyString(taskLink.url), `${label}.url must be a non-empty string or null when present.`);
}

function validExpectedMeetingNote(value, label, errors) {
  if (value === undefined || value === null) return;
  if (!isObject(value)) {
    errors.push(`${label} must be an object or null.`);
    return;
  }
  addError(errors, isIsoTimestamp(value.deadline), `${label}.deadline must be an ISO timestamp.`);
  addError(errors, nullableIsoTimestamp(value.receivedAt ?? null), `${label}.receivedAt must be an ISO timestamp or null.`);
}

function validArtifactEvidence(value, label, errors) {
  if (value === undefined || value === null) return;
  if (!isObject(value)) {
    errors.push(`${label} must be an object or null.`);
    return;
  }
  addError(errors, isNonEmptyString(value.id), `${label}.id must be a non-empty string.`);
  addError(errors, isNonEmptyString(value.name), `${label}.name must be a non-empty string.`);
  addError(errors, isHttpUrl(value.url), `${label}.url must be an http(s) URL.`);
  addError(errors, isIsoTimestamp(value.receivedAt), `${label}.receivedAt must be an ISO timestamp.`);
  addError(errors, isNonEmptyString(value.sourceEventId), `${label}.sourceEventId must be a non-empty string.`);
}

function validEscalation(value, label, errors) {
  if (!isObject(value)) {
    errors.push(`${label} must be an object.`);
    return;
  }
  addError(errors, isNonEmptyString(value.owner), `${label}.owner must be a non-empty string.`);
  addError(errors, nullableIsoTimestamp(value.escalateAt), `${label}.escalateAt must be an ISO timestamp or null.`);
  addError(errors, escalationStatuses.has(value.status), `${label}.status is invalid.`);
  addError(errors, value.outboxActionId === null || isNonEmptyString(value.outboxActionId), `${label}.outboxActionId must be a non-empty string or null.`);
}

/**
 * Validate the state owned by the deterministic manager layer. Validation is
 * fail-closed: callers must not pulse or reconcile an invalid state.
 */
export function validateManagerState(state) {
  const errors = [];
  if (!isObject(state)) return { valid: false, errors: ["Root must be an object."] };

  addError(errors, state.schemaVersion === MANAGER_STATE_SCHEMA_VERSION, `schemaVersion must be ${MANAGER_STATE_SCHEMA_VERSION}.`);
  addError(errors, state.kind === "howie-manager-state", 'kind must be "howie-manager-state".');
  addError(errors, isIsoTimestamp(state.updatedAt), "updatedAt must be an ISO timestamp.");
  addError(errors, Array.isArray(state.commitments), "commitments must be an array.");
  addError(errors, Array.isArray(state.outbox), "outbox must be an array.");
  addError(errors, Array.isArray(state.events), "events must be an array.");
  if (errors.length > 0) return { valid: false, errors };

  const commitmentIds = new Set();
  const taskIds = new Set();
  const artifactIds = new Set();
  for (const [index, commitment] of state.commitments.entries()) {
    const label = `commitments[${index}]`;
    if (!isObject(commitment)) {
      errors.push(`${label} must be an object.`);
      continue;
    }
    uniqueString(commitment.id, commitmentIds, errors, `${label}.id`);
    addError(errors, isNonEmptyString(commitment.title), `${label}.title must be a non-empty string.`);
    addError(errors, isNonEmptyString(commitment.owner), `${label}.owner must be a non-empty string; use "unresolved" when unknown.`);
    addError(errors, nullableIsoTimestamp(commitment.startAt), `${label}.startAt must be an ISO timestamp or null.`);
    addError(errors, nullableIsoTimestamp(commitment.deadline), `${label}.deadline must be an ISO timestamp or null.`);
    validArtifact(commitment.requiredArtifact, `${label}.requiredArtifact`, errors);
    validTaskLink(commitment.taskLink, `${label}.taskLink`, errors);
    if (isObject(commitment.taskLink)) uniqueString(commitment.taskLink.id, taskIds, errors, `${label}.taskLink.id`);
    if (isObject(commitment.requiredArtifact)) uniqueString(commitment.requiredArtifact.id, artifactIds, errors, `${label}.requiredArtifact.id`);
    addError(errors, commitmentStatuses.has(commitment.status), `${label}.status is invalid.`);
    addError(errors, nullableIsoTimestamp(commitment.nextReminderAt), `${label}.nextReminderAt must be an ISO timestamp or null.`);
    addError(errors, Number.isInteger(commitment.attemptCount) && commitment.attemptCount >= 0, `${label}.attemptCount must be a non-negative integer.`);
    validEscalation(commitment.escalation, `${label}.escalation`, errors);
    validExpectedMeetingNote(commitment.expectedMeetingNote, `${label}.expectedMeetingNote`, errors);
    validArtifactEvidence(commitment.artifactEvidence, `${label}.artifactEvidence`, errors);
    addError(errors, commitment.resolvedAt === undefined || nullableIsoTimestamp(commitment.resolvedAt), `${label}.resolvedAt must be an ISO timestamp or null when present.`);
    if (commitment.status === "resolved") {
      addError(errors, commitment.nextReminderAt === null, `${label}.nextReminderAt must be null when resolved.`);
      addError(errors, isIsoTimestamp(commitment.resolvedAt), `${label}.resolvedAt is required when resolved.`);
      addError(errors, isObject(commitment.artifactEvidence), `${label}.artifactEvidence is required when resolved.`);
      if (isObject(commitment.artifactEvidence) && isObject(commitment.requiredArtifact)) {
        addError(errors, commitment.artifactEvidence.id === commitment.requiredArtifact.id, `${label}.artifactEvidence.id must match requiredArtifact.id.`);
      }
    }
    if (commitment.expectedMeetingNote && isObject(commitment.escalation)) {
      addError(errors, commitment.escalation.owner === "howie", `${label}.escalation.owner must be "howie" when an expected meeting note is tracked.`);
      addError(errors, commitment.escalation.status !== "not_required", `${label}.escalation.status cannot be "not_required" when an expected meeting note is tracked.`);
    }
  }

  const outboxIds = new Set();
  const idempotencyKeys = new Set();
  for (const [index, action] of state.outbox.entries()) {
    const label = `outbox[${index}]`;
    if (!isObject(action)) {
      errors.push(`${label} must be an object.`);
      continue;
    }
    uniqueString(action.id, outboxIds, errors, `${label}.id`);
    uniqueString(action.idempotencyKey, idempotencyKeys, errors, `${label}.idempotencyKey`);
    addError(errors, outboxTypes.has(action.type), `${label}.type is invalid.`);
    addError(errors, commitmentIds.has(action.commitmentId), `${label}.commitmentId must reference a commitment.`);
    addError(errors, taskIds.has(action.taskId), `${label}.taskId must reference a commitment taskLink.`);
    addError(errors, isNonEmptyString(action.recipient), `${label}.recipient must be a non-empty string.`);
    addError(errors, isNonEmptyString(action.message), `${label}.message must be a non-empty string.`);
    addError(errors, outboxStatuses.has(action.status), `${label}.status is invalid.`);
    addError(errors, isIsoTimestamp(action.createdAt), `${label}.createdAt must be an ISO timestamp.`);
    addError(errors, isIsoTimestamp(action.triggerAt), `${label}.triggerAt must be an ISO timestamp.`);
    addError(errors, action.source === "manager-pulse", `${label}.source must be "manager-pulse".`);
    addError(errors, action.suppressedAt === undefined || nullableIsoTimestamp(action.suppressedAt), `${label}.suppressedAt must be an ISO timestamp or null when present.`);
  }

  const eventIds = new Set();
  const sourceEventIds = new Set();
  for (const [index, event] of state.events.entries()) {
    const label = `events[${index}]`;
    if (!isObject(event)) {
      errors.push(`${label} must be an object.`);
      continue;
    }
    uniqueString(event.id, eventIds, errors, `${label}.id`);
    addError(errors, isNonEmptyString(event.type), `${label}.type must be a non-empty string.`);
    addError(errors, isIsoTimestamp(event.at), `${label}.at must be an ISO timestamp.`);
    addError(errors, isNonEmptyString(event.source), `${label}.source must be a non-empty string.`);
    addError(errors, event.commitmentId === null || commitmentIds.has(event.commitmentId), `${label}.commitmentId must be null or reference a commitment.`);
    addError(errors, event.sourceEventId === undefined || isNonEmptyString(event.sourceEventId), `${label}.sourceEventId must be a non-empty string when present.`);
    if (event.sourceEventId !== undefined && isNonEmptyString(event.sourceEventId)) {
      if (sourceEventIds.has(event.sourceEventId)) errors.push(`${label}.sourceEventId duplicates ${event.sourceEventId}.`);
      sourceEventIds.add(event.sourceEventId);
    }
  }

  return { valid: errors.length === 0, errors };
}

export function assertValidManagerState(state) {
  const result = validateManagerState(state);
  if (!result.valid) throw new ManagerStateValidationError(result.errors);
}

export function validateInboundEvent(inbound) {
  const errors = [];
  if (!isObject(inbound)) return { valid: false, errors: ["Inbound event must be an object."] };
  addError(errors, isNonEmptyString(inbound.id), "Inbound event id must be a non-empty string.");
  addError(errors, inboundTypes.has(inbound.type), "Inbound event type is invalid.");
  addError(errors, isIsoTimestamp(inbound.receivedAt), "Inbound event receivedAt must be an ISO timestamp.");
  addError(errors, inbound.taskId === undefined || isNonEmptyString(inbound.taskId), "Inbound event taskId must be a non-empty string when present.");
  addError(errors, inbound.taskIds === undefined || (Array.isArray(inbound.taskIds) && inbound.taskIds.length > 0 && inbound.taskIds.every(isNonEmptyString) && new Set(inbound.taskIds).size === inbound.taskIds.length), "Inbound event taskIds must be a non-empty array of unique task ids when present.");
  addError(errors, !(inbound.taskId !== undefined && inbound.taskIds !== undefined), "Inbound event cannot include both taskId and taskIds.");
  if (inbound.artifact !== undefined) validArtifact(inbound.artifact, "Inbound event artifact", errors);
  if (inbound.type === "artifact") {
    addError(errors, isObject(inbound.artifact), "Artifact events require an artifact object.");
    addError(errors, isHttpUrl(inbound.artifact?.url), "Artifact events require an http(s) artifact.url proof link.");
  }
  return { valid: errors.length === 0, errors };
}

function assertValidInboundEvent(inbound) {
  const result = validateInboundEvent(inbound);
  if (!result.valid) throw new ManagerStateValidationError(result.errors);
}

function validMeetingCommitment(row, label, errors) {
  if (!isObject(row)) {
    errors.push(`${label} must be an object.`);
    return;
  }
  addError(errors, isNonEmptyString(row.id), `${label}.id must be a non-empty string.`);
  addError(errors, isNonEmptyString(row.title), `${label}.title must be a non-empty string.`);
  addError(errors, isNonEmptyString(row.owner), `${label}.owner must be a non-empty string; use "unresolved" when unknown.`);
  addError(errors, nullableIsoTimestamp(row.startAt), `${label}.startAt must be an ISO timestamp or null.`);
  addError(errors, nullableIsoTimestamp(row.deadline), `${label}.deadline must be an ISO timestamp or null.`);
  validArtifact(row.requiredArtifact, `${label}.requiredArtifact`, errors);
  validTaskLink(row.taskLink, `${label}.taskLink`, errors);
  addError(errors, nullableIsoTimestamp(row.nextReminderAt), `${label}.nextReminderAt must be an ISO timestamp or null.`);
  validEscalation(row.escalation, `${label}.escalation`, errors);
  validExpectedMeetingNote(row.expectedMeetingNote, `${label}.expectedMeetingNote`, errors);
  if (row.expectedMeetingNote && isObject(row.escalation)) {
    addError(errors, row.escalation.owner === "howie", `${label}.escalation.owner must be "howie" when an expected meeting note is tracked.`);
    addError(errors, row.escalation.status !== "not_required", `${label}.escalation.status cannot be "not_required" when an expected meeting note is tracked.`);
  }
}

/** Validate a manual meeting event before it can create manager commitments. */
export function validateMeetingEvent(event) {
  const errors = [];
  if (!isObject(event)) return { valid: false, errors: ["Meeting event must be an object."] };
  addError(errors, isNonEmptyString(event.id), "Meeting event id must be a non-empty string.");
  addError(errors, isIsoTimestamp(event.at), "Meeting event at must be an ISO timestamp.");
  addError(errors, isNonEmptyString(event.source), "Meeting event source must be a non-empty string.");
  addError(errors, Array.isArray(event.commitments), "Meeting event commitments must be an array.");
  if (!Array.isArray(event.commitments)) return { valid: false, errors };

  const commitmentIds = new Set();
  for (const [index, row] of event.commitments.entries()) {
    validMeetingCommitment(row, `Meeting event commitments[${index}]`, errors);
    if (isObject(row)) uniqueString(row.id, commitmentIds, errors, `Meeting event commitments[${index}].id`);
  }
  return { valid: errors.length === 0, errors };
}

function assertValidMeetingEvent(event) {
  const result = validateMeetingEvent(event);
  if (!result.valid) throw new ManagerStateValidationError(result.errors);
}

function copy(value) {
  return structuredClone(value);
}

function canonicalTimestamp(value, label) {
  if (!isIsoTimestamp(value)) throw new TypeError(`${label} must be an ISO timestamp.`);
  return new Date(value).toISOString();
}

function appendEvent(state, event) {
  if (state.events.some((existing) => existing.id === event.id)) return false;
  state.events.push(event);
  return true;
}

function commitmentFromMeetingRow(row) {
  return {
    id: row.id,
    title: row.title,
    owner: row.owner,
    startAt: row.startAt,
    deadline: row.deadline,
    requiredArtifact: copy(row.requiredArtifact),
    taskLink: copy(row.taskLink),
    status: "open",
    nextReminderAt: row.nextReminderAt,
    attemptCount: 0,
    escalation: copy(row.escalation),
    expectedMeetingNote: copy(row.expectedMeetingNote ?? null),
    artifactEvidence: null,
    resolvedAt: null
  };
}

/**
 * Record one structured meeting event. It only creates commitment IDs that do
 * not already exist; it does not send, schedule, or create Kanban work.
 */
export function recordMeetingEvent(inputState, meetingEvent) {
  assertValidManagerState(inputState);
  assertValidMeetingEvent(meetingEvent);
  const state = copy(inputState);
  const meetingAt = canonicalTimestamp(meetingEvent.at, "meetingEvent.at");

  if (state.events.some((event) => event.sourceEventId === meetingEvent.id)) {
    return { state, disposition: "duplicate", commitmentsCreated: [], eventsAdded: [] };
  }

  const existingCommitmentIds = new Set(state.commitments.map((commitment) => commitment.id));
  const commitmentsCreated = [];
  const eventsAdded = [];
  const meetingRecorded = {
    id: `meeting:${meetingEvent.id}`,
    type: "meeting_recorded",
    at: meetingAt,
    source: meetingEvent.source,
    commitmentId: null,
    sourceEventId: meetingEvent.id
  };
  appendEvent(state, meetingRecorded);
  eventsAdded.push(meetingRecorded);

  for (const row of meetingEvent.commitments) {
    if (existingCommitmentIds.has(row.id)) continue;
    const commitment = commitmentFromMeetingRow(row);
    state.commitments.push(commitment);
    existingCommitmentIds.add(commitment.id);
    commitmentsCreated.push(commitment.id);
    const commitmentRecorded = {
      id: `meeting:${meetingEvent.id}:commitment:${commitment.id}`,
      type: "commitment_recorded",
      at: meetingAt,
      source: meetingEvent.source,
      commitmentId: commitment.id,
      meetingEventId: meetingEvent.id
    };
    appendEvent(state, commitmentRecorded);
    eventsAdded.push(commitmentRecorded);
  }

  assertValidManagerState(state);
  state.updatedAt = meetingAt;
  return { state, disposition: "recorded", commitmentsCreated, eventsAdded };
}

function actionFor({ type, commitment, triggerAt, createdAt, recipient, message }) {
  const key = `${type}:${commitment.id}:${triggerAt}`;
  return {
    id: key,
    idempotencyKey: key,
    type,
    commitmentId: commitment.id,
    taskId: commitment.taskLink.id,
    recipient,
    message,
    status: "draft",
    createdAt,
    triggerAt,
    source: "manager-pulse"
  };
}

function enqueueDraft(state, action, eventAt) {
  if (state.outbox.some((existing) => existing.idempotencyKey === action.idempotencyKey)) return false;
  state.outbox.push(action);
  appendEvent(state, {
    id: `pulse:${action.id}`,
    type: `${action.type}_drafted`,
    at: eventAt,
    source: "manager-pulse",
    commitmentId: action.commitmentId,
    outboxActionId: action.id
  });
  return true;
}

function canSendReminder(commitment) {
  return commitment.status === "open"
    && commitment.requiredArtifact !== null
    && commitment.owner !== "unresolved"
    && commitment.escalation.status !== "escalated";
}

function isDue(timestamp, nowMs) {
  return isIsoTimestamp(timestamp) && Date.parse(timestamp) <= nowMs;
}

/**
 * Produce only manager-owned `draft` actions. This function never invokes a
 * gateway, Hermes, or another delivery mechanism.
 */
export function pulseManagerState(inputState, now) {
  assertValidManagerState(inputState);
  const state = copy(inputState);
  const runAt = canonicalTimestamp(now, "now");
  const runAtMs = Date.parse(runAt);
  const actionsCreated = [];
  let changed = false;

  for (const commitment of state.commitments) {
    if (commitment.status !== "open") continue;

    const missedMeetingNote = commitment.expectedMeetingNote
      && commitment.expectedMeetingNote.receivedAt === null
      && isDue(commitment.expectedMeetingNote.deadline, runAtMs);
    const escalationDue = isDue(commitment.escalation.escalateAt, runAtMs);

    if (commitment.escalation.status === "pending" && (missedMeetingNote || escalationDue)) {
      const type = missedMeetingNote ? "meeting_note_escalation" : "commitment_escalation";
      const triggerAt = missedMeetingNote
        ? canonicalTimestamp(commitment.expectedMeetingNote.deadline, "expectedMeetingNote.deadline")
        : canonicalTimestamp(commitment.escalation.escalateAt, "escalation.escalateAt");
      const message = missedMeetingNote
        ? `Howie: the expected meeting note for ${commitment.title} is overdue and has not been recorded.`
        : `Howie: ${commitment.title} needs an escalation because its follow-up deadline has passed.`;
      const action = actionFor({
        type,
        commitment,
        triggerAt,
        createdAt: runAt,
        recipient: commitment.escalation.owner,
        message
      });
      const wasCreated = enqueueDraft(state, action, runAt);
      const existing = state.outbox.find((item) => item.idempotencyKey === action.idempotencyKey);
      if (wasCreated) actionsCreated.push(action);
      if (existing && commitment.escalation.status === "pending") {
        commitment.escalation.status = "escalated";
        commitment.escalation.outboxActionId = existing.id;
        changed = true;
      }
      changed ||= wasCreated;
    }

    if (!canSendReminder(commitment) || !isDue(commitment.nextReminderAt, runAtMs)) continue;
    const triggerAt = canonicalTimestamp(commitment.nextReminderAt, "nextReminderAt");
    const action = actionFor({
      type: "reminder",
      commitment,
      triggerAt,
      createdAt: runAt,
      recipient: commitment.owner,
      message: `Reminder: ${commitment.requiredArtifact.name} is still needed for ${commitment.title}. Please publish the agreed artifact and reply with its link.`
    });
    const wasCreated = enqueueDraft(state, action, runAt);
    const existing = state.outbox.find((item) => item.idempotencyKey === action.idempotencyKey);
    if (wasCreated) {
      actionsCreated.push(action);
      commitment.attemptCount += 1;
    }
    if (existing && Date.parse(commitment.nextReminderAt) <= runAtMs) {
      commitment.nextReminderAt = new Date(runAtMs + PULSE_INTERVAL_MS).toISOString();
      changed = true;
    }
    changed ||= wasCreated;
  }

  if (changed) state.updatedAt = runAt;
  return { state, actionsCreated, eventsAdded: state.events.slice(inputState.events.length) };
}

function candidateCommitments(state, inbound) {
  const requestedTaskIds = inbound.taskIds ?? (inbound.taskId === undefined ? undefined : [inbound.taskId]);
  const byTask = requestedTaskIds === undefined
    ? null
    : state.commitments.filter((commitment) => requestedTaskIds.includes(commitment.taskLink.id));
  const artifactId = inbound.artifact?.id;
  const byArtifact = artifactId === undefined
    ? null
    : state.commitments.filter((commitment) => commitment.requiredArtifact?.id === artifactId);
  if (byTask && byArtifact) return byTask.filter((taskMatch) => byArtifact.includes(taskMatch));
  return byTask ?? byArtifact ?? [];
}

function suppressPendingActions(state, commitmentId, at, actionTypes = null) {
  let suppressed = 0;
  for (const action of state.outbox) {
    if (action.commitmentId !== commitmentId || !["draft", "approved_for_poc"].includes(action.status)) continue;
    if (actionTypes && !actionTypes.has(action.type)) continue;
    action.status = "suppressed";
    action.suppressedAt = at;
    suppressed += 1;
  }
  return suppressed;
}

/**
 * Reconcile one receipt, artifact, or meeting note. Matching is intentionally
 * exact: a task link id and/or required artifact id must identify one task.
 */
export function reconcileManagerInbound(inputState, inbound) {
  assertValidManagerState(inputState);
  assertValidInboundEvent(inbound);
  const state = copy(inputState);
  const receivedAt = canonicalTimestamp(inbound.receivedAt, "inbound.receivedAt");

  if (state.events.some((event) => event.sourceEventId === inbound.id)) {
    return { state, disposition: "duplicate", commitmentId: null, eventsAdded: [] };
  }

  const candidates = candidateCommitments(state, inbound);
  if (candidates.length !== 1) {
    const disposition = candidates.length === 0 ? "unmatched" : "ambiguous";
    const event = {
      id: `inbound:${inbound.id}`,
      type: `inbound_${disposition}`,
      at: receivedAt,
      source: "manager-reconcile",
      commitmentId: null,
      sourceEventId: inbound.id
    };
    appendEvent(state, event);
    state.updatedAt = receivedAt;
    return { state, disposition, commitmentId: null, eventsAdded: [event] };
  }

  const commitment = candidates[0];
  if (inbound.type === "meeting_note") {
    if (commitment.expectedMeetingNote) commitment.expectedMeetingNote.receivedAt = receivedAt;
    if (commitment.escalation.status === "pending") commitment.escalation.status = "suppressed";
    const suppressedActions = suppressPendingActions(state, commitment.id, receivedAt, new Set(["meeting_note_escalation"]));
    const event = {
      id: `inbound:${inbound.id}`,
      type: "meeting_note_recorded",
      at: receivedAt,
      source: "manager-reconcile",
      commitmentId: commitment.id,
      sourceEventId: inbound.id,
      suppressedActions
    };
    appendEvent(state, event);
    state.updatedAt = receivedAt;
    return { state, disposition: "recorded", commitmentId: commitment.id, eventsAdded: [event] };
  }

  if (inbound.type === "receipt") {
    const event = {
      id: `inbound:${inbound.id}`,
      type: "receipt_acknowledged",
      at: receivedAt,
      source: "manager-reconcile",
      commitmentId: commitment.id,
      sourceEventId: inbound.id
    };
    appendEvent(state, event);
    state.updatedAt = receivedAt;
    return { state, disposition: "acknowledged", commitmentId: commitment.id, eventsAdded: [event] };
  }

  if (commitment.status === "resolved") {
    const event = {
      id: `inbound:${inbound.id}`,
      type: "inbound_ignored_resolved",
      at: receivedAt,
      source: "manager-reconcile",
      commitmentId: commitment.id,
      sourceEventId: inbound.id
    };
    appendEvent(state, event);
    state.updatedAt = receivedAt;
    return { state, disposition: "already_resolved", commitmentId: commitment.id, eventsAdded: [event] };
  }

  commitment.status = "resolved";
  commitment.resolvedAt = receivedAt;
  commitment.nextReminderAt = null;
  commitment.artifactEvidence = {
    id: inbound.artifact.id,
    name: inbound.artifact.name,
    url: inbound.artifact.url,
    receivedAt,
    sourceEventId: inbound.id
  };
  if (commitment.escalation.status === "pending") commitment.escalation.status = "suppressed";
  const suppressedActions = suppressPendingActions(state, commitment.id, receivedAt);
  const event = {
    id: `inbound:${inbound.id}`,
    type: "artifact_reconciled",
    at: receivedAt,
    source: "manager-reconcile",
    commitmentId: commitment.id,
    sourceEventId: inbound.id,
    suppressedActions
  };
  appendEvent(state, event);
  state.updatedAt = receivedAt;
  return { state, disposition: "resolved", commitmentId: commitment.id, eventsAdded: [event] };
}

function readJson(path) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    throw new Error(`could not read ${path}: ${error.message}`);
  }
}

function argumentValue(argumentsList, name) {
  const index = argumentsList.indexOf(name);
  return index === -1 ? undefined : argumentsList[index + 1];
}

function usage() {
  return [
    "Usage:",
    "  node scripts/manager-state.mjs validate --state path.json",
    "  node scripts/manager-state.mjs meeting --state path.json --event meeting.json [--write]",
    "  node scripts/manager-state.mjs pulse --state path.json --now ISO_TIMESTAMP [--write]",
    "  node scripts/manager-state.mjs reconcile --state path.json --inbound inbound.json [--write]"
  ].join("\n");
}

function runCli() {
  const [command, ...argumentsList] = process.argv.slice(2);
  const stateArgument = argumentValue(argumentsList, "--state");
  if (!command || !stateArgument) throw new Error(usage());
  const statePath = resolve(stateArgument);
  const state = readJson(statePath);

  if (command === "validate") {
    assertValidManagerState(state);
    console.log(`✓ Valid manager state: ${state.commitments.length} commitment(s), ${state.outbox.length} outbox action(s), ${state.events.length} event(s).`);
    return;
  }

  let result;
  if (command === "meeting") {
    const eventArgument = argumentValue(argumentsList, "--event");
    if (!eventArgument) throw new Error("meeting requires --event meeting.json.");
    result = recordMeetingEvent(state, readJson(resolve(eventArgument)));
  } else if (command === "pulse") {
    const now = argumentValue(argumentsList, "--now");
    if (!now) throw new Error("pulse requires --now ISO_TIMESTAMP.");
    result = pulseManagerState(state, now);
  } else if (command === "reconcile") {
    const inboundArgument = argumentValue(argumentsList, "--inbound");
    if (!inboundArgument) throw new Error("reconcile requires --inbound inbound.json.");
    result = reconcileManagerInbound(state, readJson(resolve(inboundArgument)));
  } else {
    throw new Error(usage());
  }

  if (argumentsList.includes("--write")) writeFileSync(statePath, `${JSON.stringify(result.state, null, 2)}\n`);
  console.log(JSON.stringify({
    disposition: result.disposition,
    commitmentId: result.commitmentId,
    commitmentsCreated: result.commitmentsCreated ?? [],
    actionsCreated: result.actionsCreated?.map((action) => action.id) ?? [],
    eventsAdded: result.eventsAdded.map((event) => event.id),
    wroteState: argumentsList.includes("--write")
  }, null, 2));
}

const invokedAsScript = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedAsScript) {
  try {
    runCli();
  } catch (error) {
    console.error(`Manager state error: ${error.message}`);
    process.exitCode = 1;
  }
}
