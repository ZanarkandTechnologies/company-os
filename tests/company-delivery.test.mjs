import assert from "node:assert/strict";
import { appendFileSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { deliverCompanyChases, formatChaseMessage } from "../scripts/deliver-company-chases.mjs";
import { recordReply, runPulse, seedDemo } from "../scripts/company-manager.mjs";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const deliveryWorkerSource = readFileSync(resolve(projectRoot, "scripts", "deliver-company-chases.mjs"), "utf8");

assert.match(deliveryWorkerSource, /"send", "--json", "--to", `telegram:\$\{target\}`, message/);
assert.doesNotMatch(deliveryWorkerSource, /"--message"/);

{
  const message = formatChaseMessage({
    draft: {
      requirement_id: "pricing-case",
      question: "Which pricing case should the first cash forecast use?"
    },
    task: {
      ticketId: "TASK-0002",
      title: "13-week cash forecast",
      dueAt: "2026-08-20T17:00:00.000Z",
      requirements: [{ id: "pricing-case", description: "Finance must confirm the pricing case before the cash forecast can start.", human: { brief: {
        title: "cash planning decision",
        context: "I’m building this week’s 13-week cash forecast so we can see whether the operating plan preserves runway.",
        decision: "Which pricing case should the first forecast use?",
        recommendation: "Use Base unless you see a reason to plan defensively now.",
        options: ["Base", "Downside", "Upside"],
        reply: "Reply Base, Downside, or Upside with one short reason.",
        outcome: "I’ll build the forecast and flag the runway decision points for review."
      } } }],
      mockSkillDependencies: [{ id: "financial-model" }]
    },
    employee: { display_name: "Mina Patel", role: "Finance Lead" }
  });
  assert.match(message, /\*Manager · cash planning decision\*/);
  assert.match(message, /whether the operating plan preserves runway/);
  assert.match(message, /\*Decision:\* Which pricing case should the first forecast use\?/);
  assert.match(message, /\*My recommendation:\* Use Base/);
  assert.match(message, /\*Options:\* Base · Downside · Upside/);
  assert.match(message, /\*After your reply:\* I’ll build the forecast/);
  assert.doesNotMatch(message, /TASK-|mock|synthetic|Requested from|Due:/i);
}

const geoTicket = "TASK-1001";

function sandbox() {
  return mkdtempSync(resolve(tmpdir(), "howie-company-delivery-test-"));
}

function progressPath(root) {
  return resolve(root, "tickets", geoTicket, "progress.md");
}

function rosterPath(root) {
  return resolve(root, "people", "employees.private.json");
}

function seedDraft(root, at = "2026-08-11T09:00:00.000Z") {
  seedDemo({ workspaceRoot: root, write: true });
  const pulse = runPulse({ workspaceRoot: root, now: at, write: true });
  assert.equal(pulse.deliveryDrafts.length, 1);
  return pulse.deliveryDrafts[0];
}

{
  const root = sandbox();
  try {
    const draft = seedDraft(root);
    let calls = 0;
    const result = deliverCompanyChases({
      workspaceRoot: root,
      now: "2026-08-11T09:01:00.000Z",
      runHermes() { calls += 1; throw new Error("must not run in dry mode"); }
    });
    assert.equal(result.mode, "dry_run");
    assert.equal(result.exitCode, 0);
    assert.equal(calls, 0);
    assert.deepEqual(result.attempts.map((attempt) => attempt.status), ["dry_run"]);
    assert.match(readFileSync(progressPath(root), "utf8"), new RegExp(`\\*\\*telegram_delivery_receipt\\*\\*.*${draft.deliveryId}.*dry_run`));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

{
  const root = sandbox();
  try {
    seedDraft(root);
    let calls = 0;
    const ungated = deliverCompanyChases({
      workspaceRoot: root,
      send: true,
      env: {},
      now: "2026-08-11T09:01:00.000Z",
      runHermes() { calls += 1; return { status: 0 }; }
    });
    assert.equal(calls, 0);
    assert.deepEqual(ungated.attempts.map((attempt) => attempt.reason), ["explicit_send_gate_required"]);
    assert.doesNotMatch(readFileSync(progressPath(root), "utf8"), /telegram_delivery_receipt/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

{
  const root = sandbox();
  try {
    seedDraft(root);
    const failed = deliverCompanyChases({
      workspaceRoot: root,
      send: true,
      env: { HOWIE_POC_ENABLE_SEND: "1" },
      now: "2026-08-11T09:01:00.000Z",
      runHermes() { return { status: 1, stderr: "fake Hermes failure" }; }
    });
    assert.deepEqual(failed.attempts.map((attempt) => attempt.status), ["failed"]);
    assert.match(readFileSync(progressPath(root), "utf8"), /"status":"failed"/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

{
  const root = sandbox();
  try {
    const draft = seedDraft(root);
    const calls = [];
    const result = deliverCompanyChases({
      workspaceRoot: root,
      send: true,
      env: { HOWIE_POC_ENABLE_SEND: "1" },
      now: "2026-08-11T09:01:00.000Z",
      runHermes(call) { calls.push(call); return { status: 0, stdout: '{"success":true,"message_id":"test-message-42"}' }; }
    });
    assert.equal(result.mode, "send");
    assert.equal(result.exitCode, 0);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].target, "1000000001");
    assert.equal(calls[0].deliveryId, draft.deliveryId);
    assert.match(calls[0].message, /\*Manager · decision needed\*/);
    assert.match(calls[0].message, /\*Decision:\*/);
    assert.match(calls[0].message, /\*Reply:\*/);
    assert.match(calls[0].message, /\*After your reply:\*/);
    assert.deepEqual(result.attempts.map((attempt) => attempt.status), ["sent"]);
    assert.match(readFileSync(progressPath(root), "utf8"), /"platform_message_id":"test-message-42"/);
    const replay = deliverCompanyChases({
      workspaceRoot: root,
      send: true,
      env: { HOWIE_POC_ENABLE_SEND: "1" },
      now: "2026-08-11T09:02:00.000Z",
      runHermes() { throw new Error("terminal receipt must block a replay"); }
    });
    assert.deepEqual(replay.attempts.map((attempt) => attempt.reason), ["terminal_receipt_exists"]);
    assert.deepEqual(replay.attempts.map((attempt) => attempt.status), ["skipped"]);
    assert.equal(replay.exitCode, 0);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

{
  const root = sandbox();
  try {
    seedDraft(root);
    const roster = JSON.parse(readFileSync(rosterPath(root), "utf8"));
    roster.employees[0].outbound_allowed = false;
    writeFileSync(rosterPath(root), `${JSON.stringify(roster, null, 2)}\n`);
    let calls = 0;
    const result = deliverCompanyChases({
      workspaceRoot: root,
      send: true,
      env: { HOWIE_POC_ENABLE_SEND: "1" },
      now: "2026-08-11T09:01:00.000Z",
      runHermes() { calls += 1; return { status: 0 }; }
    });
    assert.equal(calls, 0);
    assert.deepEqual(result.attempts.map((attempt) => attempt.reason), ["outbound_route_disabled"]);
    assert.doesNotMatch(readFileSync(progressPath(root), "utf8"), /telegram_delivery_receipt/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

{
  const root = sandbox();
  try {
    const draft = seedDraft(root);
    appendFileSync(progressPath(root), `- 2026-08-11T09:00:30.000Z — **telegram_delivery_receipt** — ${JSON.stringify({
      at: "2026-08-11T09:00:30.000Z",
      type: "telegram_delivery_receipt",
      delivery_id: "TASK-1001:other-requirement:1",
      requirement_id: "other-requirement",
      employee_id: "kenji",
      status: "sent",
      delivery: "local_receipt"
    })}\n`);
    let calls = 0;
    const result = deliverCompanyChases({
      workspaceRoot: root,
      send: true,
      env: { HOWIE_POC_ENABLE_SEND: "1" },
      now: "2026-08-11T09:01:00.000Z",
      runHermes() { calls += 1; return { status: 0 }; }
    });
    assert.equal(calls, 0);
    assert.equal(result.attempts.find((attempt) => attempt.deliveryId === draft.deliveryId).reason, "employee_global_cooldown");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

{
  const root = sandbox();
  try {
    seedDraft(root);
    recordReply({
      workspaceRoot: root,
      ticketId: geoTicket,
      employeeId: "kenji",
      text: "The geo workbook is in the scoped shared folder.",
      now: "2026-08-11T09:01:00.000Z",
      write: true
    });
    let calls = 0;
    const result = deliverCompanyChases({
      workspaceRoot: root,
      send: true,
      env: { HOWIE_POC_ENABLE_SEND: "1" },
      now: "2026-08-11T09:02:00.000Z",
      runHermes() { calls += 1; return { status: 0 }; }
    });
    assert.equal(calls, 0);
    assert.deepEqual(result.attempts.map((attempt) => attempt.reason), ["stale_delivery_draft"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

console.log("✓ Company delivery worker enforces explicit gates and canonical ticket-progress receipts.");
