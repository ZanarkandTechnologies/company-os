import assert from "node:assert/strict";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  unlinkSync,
  writeFileSync
} from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  dashboardState,
  generateWeeklyReport,
  inspectBoard,
  previewHumanRequest,
  publishArtifact,
  recordHumanResponse,
  recordReply,
  reviewArtifact,
  runDashboardAction,
  runPulse,
  scanMeeting,
  seedDemo
} from "../scripts/company-manager.mjs";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const managerCli = resolve(projectRoot, "scripts/company-manager.mjs");
const meetingFixturePath = resolve(projectRoot, "fixtures/company-manager/meetings/mock-weekly-meeting.json");
const auroraMeetingFixturePath = resolve(projectRoot, "fixtures/company-manager/meetings/aurora-lithium-weekly-input.json");
const auroraDirectoryFixturePath = resolve(projectRoot, "fixtures/company-manager/people/aurora-lithium.employees.private.example.json");
const geoTicket = "TASK-1001";

function sandbox() {
  return mkdtempSync(resolve(tmpdir(), "howie-company-manager-test-"));
}

function ticket(root, ticketId, archived = false) {
  const path = archived
    ? resolve(root, "tickets/archive", ticketId, "ticket.md")
    : resolve(root, "tickets", ticketId, "ticket.md");
  return readFileSync(path, "utf8");
}

const root = sandbox();
try {
  const preview = seedDemo({ workspaceRoot: root, write: false });
  assert.equal(preview.meeting.createdTicketIds.length, 4);
  assert.equal(existsSync(resolve(root, "tickets")), false);

  const seeded = seedDemo({ workspaceRoot: root, write: true });
  assert.equal(seeded.meeting.createdTicketIds.length, 4);
  assert.equal(existsSync(resolve(root, "people/employees.private.json")), true);
  assert.equal(existsSync(resolve(root, "drive-mock/howie-ai-shared/geo-source.json")), true);
  assert.equal(existsSync(resolve(root, "tickets", geoTicket, "ticket.md")), true);
  assert.equal(existsSync(resolve(root, "tickets", geoTicket, "progress.md")), true);
  assert.equal(existsSync(resolve(root, "tasks.json")), false);
  assert.equal(existsSync(resolve(root, "inbox")), false);
  assert.equal(existsSync(resolve(root, "outbox")), false);

  const board = inspectBoard({ workspaceRoot: root });
  assert.equal(board.tasks.length, 4);
  assert.deepEqual(board.counts, { blocked: 4, in_progress: 0, awaiting_review: 0, done: 0 });
  assert.equal(board.tasks.every((task) => task.status === "blocked" && task.reviewerId === "kenji"), true);
  assert.equal(board.tasks.find((task) => task.ticketId === "TASK-1001").requirements[0].type, "human_input");
  assert.deepEqual(board.tasks.find((task) => task.ticketId === "TASK-1002").blockedBy.map((blocker) => blocker.type), ["skill_output", "human_input"]);
  assert.equal(board.tasks.find((task) => task.ticketId === "TASK-1004").requirements.length, 3);
  assert.equal(board.tasks.find((task) => task.ticketId === "TASK-1001").unblocks.length, 3);
  assert.equal(board.tasks.find((task) => task.ticketId === "TASK-1001").skillOutputs[0].outputId, "geo-report");
  assert.equal(board.tasks.find((task) => task.ticketId === "TASK-1001").eligibleHumanRequest.requirementId, "geo-source-file");
  assert.equal(board.gantt.length, 4);
  assert.match(ticket(root, geoTicket), /mock-geo-report/);
  assert.match(readFileSync(resolve(root, "tickets", geoTicket, "progress.md"), "utf8"), /meeting_scanned/);

  const scanReplay = scanMeeting({ workspaceRoot: root, write: true });
  assert.deepEqual(scanReplay.createdTicketIds, []);
  assert.equal(scanReplay.skippedTicketIds.length, 4);

  const firstPulse = runPulse({ workspaceRoot: root, now: "2026-08-11T09:00:00.000Z", write: true });
  assert.equal(firstPulse.deliveryDrafts.length, 1);
  assert.equal(firstPulse.deliveryDrafts[0].ticketId, geoTicket);
  assert.equal(firstPulse.deliveryDrafts[0].requirementId, "geo-source-file");
  assert.equal(firstPulse.deliveryDrafts[0].delivery, "draft_only");
  assert.equal(firstPulse.cooldowns.length, 0);
  assert.match(ticket(root, geoTicket), /"attempts":1/);
  assert.match(readFileSync(resolve(root, "tickets", geoTicket, "progress.md"), "utf8"), /telegram_delivery_draft/);
  const repeatPulse = runPulse({ workspaceRoot: root, now: "2026-08-11T09:00:00.000Z", write: true });
  assert.equal(repeatPulse.chases.length, 0);

  assert.throws(
    () => recordReply({ workspaceRoot: root, ticketId: geoTicket, employeeId: "not-kenji", text: "Shared the file", write: true }),
    /not in the private employee directory/
  );

  const reply = recordReply({ workspaceRoot: root, ticketId: geoTicket, employeeId: "kenji", text: "The geo workbook is in the Howie AI shared folder.", now: "2026-08-11T09:05:00.000Z", write: true });
  assert.equal(reply.status, "blocked");
  assert.equal(reply.acceptedDriveInput.storage_kind, "binary_local_edit");
  assert.equal(reply.acceptedDriveInput.native_workspace_format, null);
  assert.equal(reply.draftArtifactPath, null);
  assert.match(readFileSync(resolve(root, "tickets", geoTicket, "progress.md"), "utf8"), /simulated_human_response/);
  const geoWorkerPulse = runPulse({ workspaceRoot: root, now: "2026-08-11T09:06:00.000Z", write: true });
  assert.deepEqual(geoWorkerPulse.workerDispatches.map((worker) => worker.ticketId), [geoTicket]);
  assert.equal(inspectBoard({ workspaceRoot: root }).tasks.find((task) => task.ticketId === geoTicket).status, "in_progress");
  assert.equal(existsSync(geoWorkerPulse.workerDispatches[0].draftArtifactPath), true);
  assert.match(readFileSync(resolve(root, "tickets", geoTicket, "progress.md"), "utf8"), /mock_worker_dispatched/);

  const publication = publishArtifact({ workspaceRoot: root, ticketId: geoTicket, write: true });
  assert.equal(publication.status, "awaiting_review");
  assert.equal(publication.artifact.storage_kind, "native_workspace");
  assert.equal(publication.artifact.native_workspace_format, "application/vnd.google-apps.document");
  assert.equal(publication.artifact.local_edit_format, null);
  assert.equal(existsSync(resolve(root, "drive-mock/howie-ai-shared/task-1001-artifact.json")), true);

  assert.throws(
    () => reviewArtifact({ workspaceRoot: root, ticketId: geoTicket, reviewerId: "other", decision: "approved", write: true, now: "2026-08-11T10:00:00.000Z" }),
    /not assigned/
  );
  const reviewed = reviewArtifact({ workspaceRoot: root, ticketId: geoTicket, reviewerId: "kenji", decision: "approved", write: true, now: "2026-08-11T10:00:00.000Z" });
  assert.equal(reviewed.status, "done");
  assert.deepEqual(reviewed.resolvedDependencies, [
    { ticketId: "TASK-1002", requirementIds: ["geo-report-input"] },
    { ticketId: "TASK-1003", requirementIds: ["geo-report-input"] },
    { ticketId: "TASK-1004", requirementIds: ["geo-report-input"] }
  ]);
  assert.equal(existsSync(resolve(root, "tickets", geoTicket)), false);
  assert.equal(existsSync(resolve(root, "tickets/archive", geoTicket, "ticket.md")), true);
  assert.match(ticket(root, geoTicket, true), /status: "done"/);
  const archivedProgress = readFileSync(resolve(root, "tickets/archive", geoTicket, "progress.md"), "utf8");
  assert.match(archivedProgress, /meeting_scanned/);
  assert.match(archivedProgress, /telegram_delivery_draft/);
  assert.match(archivedProgress, /artifact_reviewed/);

  const deckPreview = previewHumanRequest({
    workspaceRoot: root,
    ticketId: "TASK-1002",
    requirementId: "deck-direction",
    now: "2026-08-11T12:00:00.000Z",
    write: true
  });
  assert.equal(deckPreview.deliveryDraft.channel, "telegram_delivery");
  const deckResponse = runDashboardAction({
    workspaceRoot: root,
    action: "simulate_human_response",
    enabled: true,
    ticketId: "TASK-1002",
    requirementId: "deck-direction",
    employeeId: "kenji",
    text: "Target early-stage mining investors with the geo evidence first.",
    now: "2026-08-11T12:01:00.000Z"
  });
  assert.equal(deckResponse.result.status, "blocked");

  const modelResponse = recordHumanResponse({
    workspaceRoot: root,
    ticketId: "TASK-1003",
    requirementId: "model-assumptions",
    employeeId: "kenji",
    text: "Use the approved geo report and current operating assumptions.",
    now: "2026-08-11T12:01:30.000Z",
    write: true
  });
  assert.equal(modelResponse.status, "blocked");
  const parallelWorkers = runPulse({ workspaceRoot: root, now: "2026-08-11T12:02:00.000Z", maxWorkers: 2, write: true });
  assert.deepEqual(parallelWorkers.workerDispatches.map((worker) => worker.ticketId), ["TASK-1002", "TASK-1003"]);
  assert.deepEqual(parallelWorkers.workerDispatches.map((worker) => worker.workerId), ["howie-worker-1", "howie-worker-2"]);
  publishArtifact({ workspaceRoot: root, ticketId: "TASK-1002", write: true });
  reviewArtifact({ workspaceRoot: root, ticketId: "TASK-1002", reviewerId: "kenji", decision: "approved", now: "2026-08-11T12:03:00.000Z", write: true });
  publishArtifact({ workspaceRoot: root, ticketId: "TASK-1003", write: true });
  reviewArtifact({ workspaceRoot: root, ticketId: "TASK-1003", reviewerId: "kenji", decision: "approved", now: "2026-08-11T12:04:00.000Z", write: true });
  const weekly = inspectBoard({ workspaceRoot: root, now: "2026-08-11T12:05:00.000Z" }).tasks.find((task) => task.ticketId === "TASK-1004");
  assert.equal(weekly.requirements.every((requirement) => requirement.state === "resolved"), true);
  assert.equal(weekly.readiness.state, "eligible");
  assert.deepEqual(weekly.readiness.eligibleSkillIds, ["mock-weekly-report"]);

  const report = generateWeeklyReport({ workspaceRoot: root, now: "2026-08-11T10:00:00.000Z", write: true });
  assert.equal(existsSync(report.reportPath), true);
  assert.match(report.markdown, /TASK-1001 — done/);
  const dashboard = dashboardState({ workspaceRoot: root, now: "2026-08-11T10:00:00.000Z" });
  assert.equal(dashboard.board.counts.done, 3);
  assert.equal(dashboard.employees[0].id, "kenji");
  assert.equal(dashboard.employees[0].routeEnabled, true);
  assert.equal(dashboard.board.tasks[0].description.length > 0, true);
  assert.equal(dashboard.board.tasks[0].mockSkillDependencies.length, 1);
  assert.equal(dashboard.driveFiles.every((file) => file.scope === "howie-ai/shared"), true);
  assert.equal(dashboard.lastActions.length > 0, true);
  assert.throws(() => runDashboardAction({ workspaceRoot: root, action: "report" }), /enabled: true/);
  assert.equal(runDashboardAction({ workspaceRoot: root, action: "report", enabled: true, now: "2026-08-11T10:00:00.000Z" }).state.board.counts.done, 3);
  const disabledRoute = runDashboardAction({
    workspaceRoot: root,
    action: "toggle_employee_access",
    enabled: true,
    employeeId: "kenji",
    routeEnabled: false,
    now: "2026-08-11T12:00:00.000Z"
  });
  assert.equal(disabledRoute.result.enabled, false);
  assert.equal(disabledRoute.state.employees[0].routeEnabled, false);
  assert.equal(runPulse({ workspaceRoot: root, now: "2026-08-11T12:00:00.000Z", write: true }).chases.length, 0);
} finally {
  rmSync(root, { recursive: true, force: true });
}

const inaccessibleRoot = sandbox();
try {
  seedDemo({ workspaceRoot: inaccessibleRoot, write: true });
  unlinkSync(resolve(inaccessibleRoot, "drive-mock/howie-ai-shared/geo-source.json"));
  assert.throws(
    () => recordReply({ workspaceRoot: inaccessibleRoot, ticketId: geoTicket, employeeId: "kenji", text: "I shared an inaccessible file.", write: true }),
    /no accessible howie-ai shared mock Drive file/
  );
  assert.match(ticket(inaccessibleRoot, geoTicket), /status: "blocked"/);
  const inaccessibleProgress = readFileSync(resolve(inaccessibleRoot, "tickets", geoTicket, "progress.md"), "utf8");
  assert.match(inaccessibleProgress, /telegram_delivery_draft/);
  assert.match(inaccessibleProgress, /request_scoped_source_refresh/);
  assert.match(inaccessibleProgress, /TASK-1001:geo-source-file:1/);
} finally {
  rmSync(inaccessibleRoot, { recursive: true, force: true });
}

const escalationRoot = sandbox();
try {
  seedDemo({ workspaceRoot: escalationRoot, write: true });
  const firstEscalationPulse = runPulse({ workspaceRoot: escalationRoot, now: "2026-08-17T16:00:00.000Z", write: true });
  const secondEscalationPulse = runPulse({ workspaceRoot: escalationRoot, now: "2026-08-17T18:01:00.000Z", write: true });
  assert.equal(firstEscalationPulse.escalations.length, 0);
  assert.deepEqual(secondEscalationPulse.escalations, [{
    ticketId: geoTicket,
    at: "2026-08-17T18:01:00.000Z",
    next_owner_id: "howie-ai",
    reason: "Blocked after 2 bounded follow-ups; TASK-1001 is past its due date.",
    requirement_id: "geo-source-file",
    employee_id: "kenji",
    trigger: "repeated_follow_up"
  }]);
  const escalationProgress = readFileSync(resolve(escalationRoot, "tickets", geoTicket, "progress.md"), "utf8");
  assert.match(escalationProgress, /ticket_escalated/);
  assert.equal(runPulse({ workspaceRoot: escalationRoot, now: "2026-08-17T20:02:00.000Z", write: true }).escalations.length, 0);
} finally {
  rmSync(escalationRoot, { recursive: true, force: true });
}

const followUpRoot = sandbox();
try {
  const meeting = JSON.parse(readFileSync(meetingFixturePath, "utf8"));
  meeting.tasks[1].requirements = meeting.tasks[1].requirements.filter((requirement) => requirement.id === "deck-direction");
  meeting.tasks[1].mock_skill_dependencies[0].input_ids = ["deck-direction"];
  const rosterFixture = JSON.parse(readFileSync(resolve(projectRoot, "fixtures/company-manager/people/employees.private.example.json"), "utf8"));
  const peopleRoot = resolve(followUpRoot, "people");
  const { mkdirSync, writeFileSync } = await import("node:fs");
  mkdirSync(peopleRoot, { recursive: true });
  writeFileSync(resolve(peopleRoot, "employees.private.json"), `${JSON.stringify(rosterFixture, null, 2)}\n`);
  const driveRoot = resolve(followUpRoot, "drive-mock", "howie-ai-shared");
  mkdirSync(driveRoot, { recursive: true });
  writeFileSync(
    resolve(driveRoot, "geo-source.json"),
    readFileSync(resolve(projectRoot, "fixtures/company-manager/shared-drive/geo-source.json"), "utf8")
  );
  scanMeeting({ workspaceRoot: followUpRoot, meeting, write: true });
  const first = runPulse({ workspaceRoot: followUpRoot, now: "2026-08-11T09:00:00.000Z", write: true });
  assert.deepEqual(first.deliveryDrafts.map((draft) => draft.ticketId), [geoTicket]);
  assert.deepEqual(first.cooldowns, [{
    ticketId: "TASK-1002",
    requirementId: "deck-direction",
    reason: "employee_global_cooldown",
    availableAt: "2026-08-11T11:00:00.000Z"
  }]);
  const deferred = inspectBoard({ workspaceRoot: followUpRoot, now: "2026-08-11T09:00:00.000Z" }).tasks.find((task) => task.ticketId === "TASK-1002");
  assert.equal(deferred.nextChaseAt, "2026-08-11T09:00:00.000Z");
  assert.equal(deferred.outstandingPeople[0].followUp.attempts, 0);
  recordReply({
    workspaceRoot: followUpRoot,
    ticketId: geoTicket,
    employeeId: "kenji",
    text: "The geo workbook is in the scoped shared folder.",
    now: "2026-08-11T09:01:00.000Z",
    write: true
  });
  const second = runPulse({ workspaceRoot: followUpRoot, now: "2026-08-11T11:00:00.000Z", write: true });
  assert.deepEqual(second.deliveryDrafts.map((draft) => draft.ticketId), ["TASK-1002"]);
  const deckProgress = readFileSync(resolve(followUpRoot, "tickets", "TASK-1002", "progress.md"), "utf8");
  assert.match(deckProgress, /telegram_delivery_draft/);
  assert.match(deckProgress, /"requirement_id":"deck-direction"/);
  assert.match(deckProgress, /"employee_id":"kenji"/);
  assert.doesNotMatch(ticket(followUpRoot, "TASK-1002"), /chase:/);
} finally {
  rmSync(followUpRoot, { recursive: true, force: true });
}

const twoRequirementsRoot = sandbox();
try {
  const meeting = JSON.parse(readFileSync(meetingFixturePath, "utf8"));
  meeting.tasks[0].blocking_inputs.push({
    id: "geo-audience",
    kind: "kenji_reply",
    description: "Kenji must confirm the report audience."
  });
  meeting.tasks[0].requirements.push({
    id: "geo-audience",
    type: "human_input",
    description: "Kenji must confirm the report audience.",
    state: "unresolved",
    human: {
      employee_id: "kenji",
      channel: "telegram_delivery",
      question: "Who is the geo report for?"
    },
    follow_up: {
      employee_id: "kenji",
      attempts: 0,
      last_at: null,
      next_at: "2026-08-11T09:00:00.000Z",
      cooldown_minutes: 120,
      delivery_id: null,
      status: "pending",
      escalation: null
    }
  });
  meeting.tasks[0].mock_skill_dependencies[0].input_ids.push("geo-audience");
  const peopleRoot = resolve(twoRequirementsRoot, "people");
  const { mkdirSync, writeFileSync } = await import("node:fs");
  mkdirSync(peopleRoot, { recursive: true });
  writeFileSync(
    resolve(peopleRoot, "employees.private.json"),
    readFileSync(resolve(projectRoot, "fixtures/company-manager/people/employees.private.example.json"), "utf8")
  );
  const driveRoot = resolve(twoRequirementsRoot, "drive-mock", "howie-ai-shared");
  mkdirSync(driveRoot, { recursive: true });
  writeFileSync(
    resolve(driveRoot, "geo-source.json"),
    readFileSync(resolve(projectRoot, "fixtures/company-manager/shared-drive/geo-source.json"), "utf8")
  );
  scanMeeting({ workspaceRoot: twoRequirementsRoot, meeting, write: true });
  const first = runPulse({ workspaceRoot: twoRequirementsRoot, now: "2026-08-11T09:00:00.000Z", write: true });
  assert.deepEqual(first.deliveryDrafts.map((draft) => draft.requirementId), ["geo-audience"]);
  const initiallyBlocked = inspectBoard({ workspaceRoot: twoRequirementsRoot, now: "2026-08-11T09:00:00.000Z" }).tasks.find((task) => task.ticketId === geoTicket);
  assert.equal(initiallyBlocked.outstandingPeople.find((person) => person.requirementId === "geo-audience").followUp.attempts, 1);
  assert.equal(initiallyBlocked.outstandingPeople.find((person) => person.requirementId === "geo-source-file").followUp.attempts, 0);
  assert.equal(initiallyBlocked.outstandingPeople.find((person) => person.requirementId === "geo-source-file").followUp.nextAt, "2026-08-11T09:00:00.000Z");
  recordHumanResponse({
    workspaceRoot: twoRequirementsRoot,
    ticketId: geoTicket,
    requirementId: "geo-audience",
    employeeId: "kenji",
    text: "The geology leadership team.",
    now: "2026-08-11T09:01:00.000Z",
    write: true
  });
  const second = runPulse({ workspaceRoot: twoRequirementsRoot, now: "2026-08-11T11:00:00.000Z", write: true });
  assert.deepEqual(second.deliveryDrafts.map((draft) => draft.requirementId), ["geo-source-file"]);
} finally {
  rmSync(twoRequirementsRoot, { recursive: true, force: true });
}

const malformedRosterRoot = sandbox();
try {
  seedDemo({ workspaceRoot: malformedRosterRoot, write: true });
  const peoplePath = resolve(malformedRosterRoot, "people", "employees.private.json");
  const malformed = JSON.parse(readFileSync(peoplePath, "utf8"));
  malformed.employees[0].telegram_target = "not-a-telegram-chat-id";
  const { writeFileSync } = await import("node:fs");
  writeFileSync(peoplePath, `${JSON.stringify(malformed, null, 2)}\n`);
  assert.throws(() => dashboardState({ workspaceRoot: malformedRosterRoot }), /numeric Telegram chat ID/);
} finally {
  rmSync(malformedRosterRoot, { recursive: true, force: true });
}

const auroraMeetingRoot = sandbox();
try {
  const meetingInput = JSON.parse(readFileSync(auroraMeetingFixturePath, "utf8"));
  const directory = JSON.parse(readFileSync(auroraDirectoryFixturePath, "utf8"));
  assert.equal(meetingInput.kind, "pre_extracted_weekly_meeting");
  assert.equal(meetingInput.synthetic, true);
  assert.equal(meetingInput.meeting.tasks.length, 4);
  assert.equal(directory.fake_data_only, true);
  assert.equal(directory.employees.length, 3);
  assert.equal(directory.employees.every((employee) => employee.test_opt_in && employee.outbound_allowed), true);
  mkdirSync(resolve(auroraMeetingRoot, "people"), { recursive: true });
  writeFileSync(resolve(auroraMeetingRoot, "people", "employees.private.json"), `${JSON.stringify(directory, null, 2)}\n`);

  const scanned = scanMeeting({ workspaceRoot: auroraMeetingRoot, meeting: meetingInput, write: true });
  assert.deepEqual(scanned.createdTicketIds, ["TASK-2001", "TASK-2002", "TASK-2003", "TASK-2004"]);
  const pulse = runPulse({ workspaceRoot: auroraMeetingRoot, now: "2026-08-18T00:00:00.000Z", write: true });
  assert.deepEqual(pulse.workerDispatches.map((worker) => worker.ticketId), ["TASK-2001"]);
  assert.deepEqual(pulse.deliveryDrafts.map((draft) => `${draft.ticketId}:${draft.requirementId}:${draft.employeeId}`), [
    "TASK-2002:finance-scenario:mina-finance",
    "TASK-2003:operating-risk-priority:rohan-operations"
  ]);
  const board = inspectBoard({ workspaceRoot: auroraMeetingRoot, now: "2026-08-18T00:00:00.000Z" });
  assert.equal(board.tasks.find((task) => task.ticketId === "TASK-2001").status, "in_progress");
  for (const [ticketId, requirementId, employeeId] of [
    ["TASK-2002", "finance-scenario", "mina-finance"],
    ["TASK-2003", "operating-risk-priority", "rohan-operations"]
  ]) {
    const task = board.tasks.find((candidate) => candidate.ticketId === ticketId);
    const person = task.outstandingPeople.find((candidate) => candidate.requirementId === requirementId);
    assert.equal(person.employeeId, employeeId);
    assert.equal(person.followUp.attempts, 1);
    assert.equal(person.followUp.lastAt, "2026-08-18T00:00:00.000Z");
    assert.equal(person.followUp.nextAt, "2026-08-18T01:30:00.000Z");
    const progress = readFileSync(resolve(auroraMeetingRoot, "tickets", ticketId, "progress.md"), "utf8");
    assert.match(progress, new RegExp(`"requirement_id":"${requirementId}"`));
    assert.match(progress, new RegExp(`"employee_id":"${employeeId}"`));
  }
  const dashboard = dashboardState({ workspaceRoot: auroraMeetingRoot, now: "2026-08-18T00:00:00.000Z" });
  assert.equal(JSON.stringify(dashboard).includes("+15550100001"), false);
  assert.equal(dashboard.deliveryEvents.length, 2);
} finally {
  rmSync(auroraMeetingRoot, { recursive: true, force: true });
}

const invalidGraphRoot = sandbox();
try {
  const sourceMeeting = () => JSON.parse(readFileSync(meetingFixturePath, "utf8"));
  const unknownProducer = sourceMeeting();
  unknownProducer.tasks[1].requirements[0].upstream.ticket_id = "TASK-9999";
  assert.throws(
    () => scanMeeting({ workspaceRoot: invalidGraphRoot, meeting: unknownProducer, write: true }),
    /unknown producer TASK-9999/
  );
  assert.equal(existsSync(resolve(invalidGraphRoot, "tickets")), false);

  const unknownOutput = sourceMeeting();
  unknownOutput.tasks[1].requirements[0].upstream.output_id = "unknown-output";
  assert.throws(
    () => scanMeeting({ workspaceRoot: invalidGraphRoot, meeting: unknownOutput, write: true }),
    /unknown output TASK-1001\.mock-geo-report\.unknown-output/
  );
  assert.equal(existsSync(resolve(invalidGraphRoot, "tickets")), false);

  const cycle = sourceMeeting();
  cycle.tasks[0].requirements.push({
    id: "weekly-report-input",
    type: "skill_output",
    description: "Use the approved weekly report to validate the geo report.",
    state: "unresolved",
    upstream: { ticket_id: "TASK-1004", skill_id: "mock-weekly-report", output_id: "weekly-report" }
  });
  cycle.tasks[0].mock_skill_dependencies[0].input_ids.push("weekly-report-input");
  assert.throws(
    () => scanMeeting({ workspaceRoot: invalidGraphRoot, meeting: cycle, write: true }),
    /dependency graph cycle/
  );
  assert.equal(existsSync(resolve(invalidGraphRoot, "tickets")), false);
} finally {
  rmSync(invalidGraphRoot, { recursive: true, force: true });
}

const cliRoot = sandbox();
try {
  const seed = spawnSync(process.execPath, [managerCli, "seed", "--workspace", cliRoot, "--write"], { cwd: projectRoot, encoding: "utf8" });
  assert.equal(seed.status, 0, `${seed.stdout}${seed.stderr}`);
  assert.match(seed.stdout, /TASK-1001/);
  const board = spawnSync(process.execPath, [managerCli, "board", "--workspace", cliRoot], { cwd: projectRoot, encoding: "utf8" });
  assert.equal(board.status, 0, `${board.stdout}${board.stderr}`);
  assert.match(board.stdout, /"tasks"/);
  assert.deepEqual(readdirSync(resolve(cliRoot, "tickets")).sort(), ["TASK-1001", "TASK-1002", "TASK-1003", "TASK-1004"]);
} finally {
  rmSync(cliRoot, { recursive: true, force: true });
}

console.log("✓ File-first company manager simulator guards passed.");
