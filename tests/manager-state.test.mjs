import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  ManagerStateValidationError,
  pulseManagerState,
  recordMeetingEvent,
  reconcileManagerInbound,
  validateMeetingEvent,
  validateManagerState
} from "../scripts/manager-state.mjs";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const fixturePath = resolve(projectRoot, "fixtures/manager-state.json");
const meetingFixturePath = resolve(projectRoot, "fixtures/manager-meeting-event.json");

function fixture() {
  return JSON.parse(readFileSync(fixturePath, "utf8"));
}

function meetingFixture() {
  return JSON.parse(readFileSync(meetingFixturePath, "utf8"));
}

function secondCommitment() {
  return {
    id: "legal-register-request",
    title: "Refresh the compliance action register",
    owner: "second-employee",
    startAt: null,
    deadline: "2026-08-13T09:00:00.000Z",
    requiredArtifact: { id: "compliance-register", name: "Compliance register", url: null },
    taskLink: { id: "compliance-register", url: "https://tasks.example.test/compliance-register" },
    status: "open",
    nextReminderAt: "2026-08-10T13:00:00.000Z",
    attemptCount: 0,
    escalation: { owner: "howie", escalateAt: null, status: "not_required", outboxActionId: null },
    expectedMeetingNote: null,
    artifactEvidence: null,
    resolvedAt: null
  };
}

const initial = fixture();
assert.deepEqual(validateManagerState(initial), { valid: true, errors: [] });

const recordedMeeting = recordMeetingEvent(initial, meetingFixture());
assert.equal(recordedMeeting.disposition, "recorded");
assert.deepEqual(recordedMeeting.commitmentsCreated, ["compliance-register-request"]);
assert.equal(recordedMeeting.state.commitments.length, initial.commitments.length + 1);
assert.equal(recordedMeeting.state.commitments.at(-1).owner, "unresolved");
assert.equal(recordedMeeting.state.commitments.at(-1).deadline, null);
assert.equal(recordedMeeting.state.commitments.at(-1).requiredArtifact, null);
assert.equal(recordedMeeting.eventsAdded.length, 2);
assert.deepEqual(recordedMeeting.state.events.slice(0, initial.events.length), initial.events);
assert.equal(validateManagerState(recordedMeeting.state).valid, true);

const replayedMeeting = recordMeetingEvent(recordedMeeting.state, meetingFixture());
assert.equal(replayedMeeting.disposition, "duplicate");
assert.deepEqual(replayedMeeting.commitmentsCreated, []);
assert.deepEqual(replayedMeeting.state, recordedMeeting.state);

const malformedMeeting = meetingFixture();
malformedMeeting.commitments[0].taskLink = null;
assert.equal(validateMeetingEvent(malformedMeeting).valid, false);
assert.throws(
  () => recordMeetingEvent(initial, malformedMeeting),
  ManagerStateValidationError
);

const firstPulse = pulseManagerState(initial, "2026-08-10T10:00:00.000Z");
assert.equal(firstPulse.actionsCreated.length, 1);
assert.equal(firstPulse.actionsCreated[0].type, "reminder");
assert.equal(firstPulse.actionsCreated[0].status, "draft");
assert.equal(firstPulse.actionsCreated[0].recipient, "test-employee");
assert.equal(firstPulse.state.commitments[0].attemptCount, 1);
assert.equal(firstPulse.state.commitments[0].nextReminderAt, "2026-08-10T10:30:00.000Z");
assert.equal(firstPulse.state.events.length, initial.events.length + 1);
assert.deepEqual(firstPulse.state.events.slice(0, initial.events.length), initial.events);

const duplicatePulse = pulseManagerState(firstPulse.state, "2026-08-10T10:00:00.000Z");
assert.equal(duplicatePulse.actionsCreated.length, 0);
assert.deepEqual(duplicatePulse.state, firstPulse.state);

const receipt = reconcileManagerInbound(firstPulse.state, {
  id: "receipt-reply-001",
  type: "receipt",
  receivedAt: "2026-08-10T10:03:00.000Z",
  taskId: "fundraising-data-room"
});
assert.equal(receipt.disposition, "acknowledged");
assert.equal(receipt.state.commitments[0].status, "open");
assert.equal(receipt.state.commitments[0].nextReminderAt, "2026-08-10T10:30:00.000Z");
assert.equal(receipt.state.outbox[0].status, "draft");
assert.equal(receipt.state.events.at(-1).type, "receipt_acknowledged");

const reconciled = reconcileManagerInbound(firstPulse.state, {
  id: "artifact-reply-001",
  type: "artifact",
  receivedAt: "2026-08-10T10:05:00.000Z",
  artifact: { id: "finance-summary", name: "Latest finance summary", url: "https://drive.example.test/finance-summary" }
});
assert.equal(reconciled.disposition, "resolved");
assert.equal(reconciled.commitmentId, "finance-summary-request");
assert.equal(reconciled.state.commitments[0].status, "resolved");
assert.equal(reconciled.state.commitments[0].nextReminderAt, null);
assert.deepEqual(reconciled.state.commitments[0].artifactEvidence, {
  id: "finance-summary",
  name: "Latest finance summary",
  url: "https://drive.example.test/finance-summary",
  receivedAt: "2026-08-10T10:05:00.000Z",
  sourceEventId: "artifact-reply-001"
});
assert.equal(reconciled.state.outbox[0].status, "suppressed");
assert.deepEqual(reconciled.state.events.slice(0, firstPulse.state.events.length), firstPulse.state.events);

const pulseAfterReceipt = pulseManagerState(reconciled.state, "2026-08-10T10:30:00.000Z");
assert.equal(pulseAfterReceipt.actionsCreated.length, 0);

const duplicateInbound = reconcileManagerInbound(reconciled.state, {
  id: "artifact-reply-001",
  type: "artifact",
  receivedAt: "2026-08-10T10:05:00.000Z",
  artifact: { id: "finance-summary", name: "Latest finance summary", url: "https://drive.example.test/finance-summary" }
});
assert.equal(duplicateInbound.disposition, "duplicate");
assert.deepEqual(duplicateInbound.state, reconciled.state);

const ambiguousState = fixture();
ambiguousState.commitments.push(secondCommitment());
const ambiguous = reconcileManagerInbound(ambiguousState, {
  id: "ambiguous-reply-001",
  type: "receipt",
  receivedAt: "2026-08-10T10:05:00.000Z",
  taskIds: ["fundraising-data-room", "compliance-register"]
});
assert.equal(ambiguous.disposition, "ambiguous");
assert.equal(ambiguous.state.commitments.filter((commitment) => commitment.status === "resolved").length, 0);
assert.equal(ambiguous.state.events.at(-1).type, "inbound_ambiguous");

const meetingNoteState = fixture();
meetingNoteState.commitments[0].nextReminderAt = "2026-08-10T15:00:00.000Z";
meetingNoteState.commitments[0].escalation.escalateAt = "2026-08-10T09:30:00.000Z";
meetingNoteState.commitments[0].expectedMeetingNote.deadline = "2026-08-10T09:30:00.000Z";
const missedMeetingNote = pulseManagerState(meetingNoteState, "2026-08-10T10:00:00.000Z");
assert.equal(missedMeetingNote.actionsCreated.length, 1);
assert.equal(missedMeetingNote.actionsCreated[0].type, "meeting_note_escalation");
assert.equal(missedMeetingNote.actionsCreated[0].recipient, "howie");
assert.equal(missedMeetingNote.actionsCreated[0].status, "draft");
assert.equal(missedMeetingNote.state.commitments[0].escalation.status, "escalated");
const repeatMeetingNote = pulseManagerState(missedMeetingNote.state, "2026-08-10T10:30:00.000Z");
assert.equal(repeatMeetingNote.actionsCreated.length, 0);
assert.equal(repeatMeetingNote.state.outbox.length, 1);
const recordedMeetingNote = reconcileManagerInbound(missedMeetingNote.state, {
  id: "meeting-note-001",
  type: "meeting_note",
  receivedAt: "2026-08-10T10:15:00.000Z",
  taskId: "fundraising-data-room"
});
assert.equal(recordedMeetingNote.disposition, "recorded");
assert.equal(recordedMeetingNote.state.commitments[0].expectedMeetingNote.receivedAt, "2026-08-10T10:15:00.000Z");
assert.equal(recordedMeetingNote.state.outbox[0].status, "suppressed");

const malformed = fixture();
malformed.commitments[0].attemptCount = -1;
const invalid = validateManagerState(malformed);
assert.equal(invalid.valid, false);
assert.match(invalid.errors.join("\n"), /attemptCount/);
assert.throws(
  () => pulseManagerState(malformed, "2026-08-10T10:00:00.000Z"),
  ManagerStateValidationError
);

const invalidMeetingNotePolicy = fixture();
invalidMeetingNotePolicy.commitments[0].escalation.status = "not_required";
assert.equal(validateManagerState(invalidMeetingNotePolicy).valid, false);

const invalidStartAt = fixture();
invalidStartAt.commitments[0].startAt = "2026-08-10";
assert.equal(validateManagerState(invalidStartAt).valid, false);

const deliveryLifecycleState = structuredClone(firstPulse.state);
for (const status of ["draft", "approved_for_poc", "sent", "failed", "suppressed"]) {
  const statusState = structuredClone(firstPulse.state);
  statusState.outbox[0].status = status;
  assert.equal(validateManagerState(statusState).valid, true, `expected ${status} to be valid`);
}
deliveryLifecycleState.outbox[0].status = "approved_for_poc";
const resolvedApprovedAction = reconcileManagerInbound(deliveryLifecycleState, {
  id: "artifact-reply-approved-001",
  type: "artifact",
  receivedAt: "2026-08-10T10:06:00.000Z",
  artifact: { id: "finance-summary", name: "Latest finance summary", url: "https://drive.example.test/finance-summary-approved" }
});
assert.equal(resolvedApprovedAction.state.outbox[0].status, "suppressed");

console.log("✓ Manager state validator, pulse, and reconciliation guards passed.");
