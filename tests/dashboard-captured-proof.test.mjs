import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const projectRoot = resolve(import.meta.dirname, "..");
const serverModulePath = resolve(projectRoot, "scripts/serve-dashboard.mjs");
const root = mkdtempSync(resolve(tmpdir(), "howie-captured-proof-dashboard-"));
const workspace = resolve(root, "workspace");
const evidence = resolve(root, "evidence");
const original = Object.fromEntries(["HOWIE_DASHBOARD_WORKSPACE_PATH", "HOWIE_DASHBOARD_AGENT_EVAL_PATH", "HOWIE_DASHBOARD_READ_ONLY"].map((key) => [key, process.env[key]]));

function write(path, text) {
  mkdirSync(resolve(path, ".."), { recursive: true });
  writeFileSync(path, text, "utf8");
}

function frontmatter(ticket) {
  return ["---", ...Object.entries(ticket).map(([key, value]) => `${key}: ${JSON.stringify(value)}`), "---", ""].join("\n");
}

try {
  const ticket = {
    ticket_id: "TASK-3001",
    title: "Technical geo report",
    description: "Draft the technical report for review.",
    workstream: "Technical",
    owner_id: "manager",
    reviewer_id: "principal-geologist",
    start_at: "2026-08-17T09:00:00.000Z",
    due_at: "2026-08-18T16:00:00.000Z",
    status: "awaiting_review",
    requirements: [{
      id: "review-geo-report",
      type: "human_input",
      description: "Principal Geologist review.",
      state: "unresolved",
      human: { employee_id: "principal-geologist", channel: "telegram_delivery", question: "Approve, revise, or reject?" },
      follow_up: { employee_id: "principal-geologist", last_at: "2026-08-17T09:00:00.000Z", next_at: "2026-08-18T09:00:00.000Z", attempts: 1, cooldown_minutes: 1440, status: "pending", delivery_id: "delivery-001", escalation: null }
    }],
    mock_skill_dependencies: [{ id: "geo-report", template: "templates/geo-report.md", input_ids: [], outputs: [{ id: "geo-report-draft", description: "Reviewable geo report." }] }],
    artifact: { path: "tickets/TASK-3001/artifacts/geo-report-draft.md", state: "drafted" },
    review: { reviewer_id: "principal-geologist", state: "pending_review", decided_at: null, decision: null },
    created_at: "2026-08-17T09:00:00.000Z",
    updated_at: "2026-08-17T09:00:00.000Z"
  };
  write(resolve(workspace, "tickets/TASK-3001/ticket.md"), frontmatter(ticket));
  write(resolve(workspace, "tickets/TASK-3001/progress.md"), '- 2026-08-17T09:00:00.000Z — **telegram_delivery_draft** — {"at":"2026-08-17T09:00:00.000Z","type":"telegram_delivery_draft","delivery_id":"delivery-001","requirement_id":"review-geo-report","employee_id":"principal-geologist","delivery":"draft_only"}\n');
  write(resolve(workspace, "shared-drive/aurora/source.md"), "Synthetic source\n");
  write(resolve(evidence, "runs/real_meeting_to_tickets/result.json"), JSON.stringify({ id: "real_meeting_to_tickets", profile: "howie-ai", channel_message: "Here are the meeting notes.", manager_reply: "I created the plan.", files: { setup: [], delta: { created: [], modified: [], deleted: [] }, final: [] }, checks: { hermes_session_completed: true } }));
  write(resolve(evidence, "runs/real_meeting_to_tickets/prompt.md"), "Process meeting notes.");
  write(resolve(evidence, "runs/real_meeting_to_tickets/stdout.txt"), "Session: 20260813_010101_abcdef\n");
  write(resolve(evidence, "summary.json"), JSON.stringify({ suite: "howie-real-hermes-agent", pass: true, completed_at: "2026-08-17T09:00:00.000Z", scenarios: [{ id: "real_meeting_to_tickets", title: "Meeting to work", pass: true, exit_code: 0 }] }));

  process.env.HOWIE_DASHBOARD_WORKSPACE_PATH = workspace;
  process.env.HOWIE_DASHBOARD_AGENT_EVAL_PATH = evidence;
  process.env.HOWIE_DASHBOARD_READ_ONLY = "1";
  const { createDashboardServer } = await import(`${pathToFileURL(serverModulePath).href}?captured-proof-test=${Date.now()}`);
  const server = createDashboardServer();
  await new Promise((resolveListen, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", resolveListen); });
  try {
    const address = server.address();
    const baseUrl = `http://127.0.0.1:${address.port}`;
    const state = await (await fetch(`${baseUrl}/api/state`)).json();
    assert.equal(state.readOnly, true);
    assert.equal(state.board.tasks.length, 1);
    assert.equal(state.board.tasks[0].ticketId, "TASK-3001");
    assert.equal(state.board.tasks[0].nextChaseAt, "2026-08-18T09:00:00.000Z");
    assert.equal(state.board.tasks[0].pendingDeliveries[0].deliveryId, "delivery-001");
    assert.equal(state.driveFiles[0].path, "shared-drive/aurora/source.md");
    const proof = await (await fetch(`${baseUrl}/api/agent-evals/latest`)).json();
    assert.equal(proof.latest.summary.pass, true);
    assert.equal(proof.latest.scenarios[0].hermes_session, null, "A Hermes UI link is optional and must not be invented without an explicit local dashboard URL.");
    const action = await fetch(`${baseUrl}/api/action`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ action: "pulse" }) });
    assert.equal(action.status, 403);
  } finally {
    await new Promise((resolveClose) => server.close(resolveClose));
  }
} finally {
  for (const [key, value] of Object.entries(original)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  rmSync(root, { recursive: true, force: true });
}

console.log("✓ Captured Hermes proof dashboard is read-only and projects the canonical run state.");
