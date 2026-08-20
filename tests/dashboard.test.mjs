import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const projectRoot = resolve(import.meta.dirname, "..");
const workspaceRoot = mkdtempSync(resolve(tmpdir(), "howie-dependency-dashboard-test-"));
const serverModulePath = resolve(projectRoot, "scripts/serve-dashboard.mjs");
const originalWorkspace = process.env.HOWIE_DASHBOARD_WORKSPACE_PATH;
const originalNativeHermesDashboard = process.env.HOWIE_HERMES_DASHBOARD_URL;

async function startServer() {
  process.env.HOWIE_DASHBOARD_WORKSPACE_PATH = workspaceRoot;
  process.env.HOWIE_HERMES_DASHBOARD_URL = "http://127.0.0.1:9119";
  const { createDashboardServer } = await import(`${pathToFileURL(serverModulePath).href}?dependency-dashboard-test=${Date.now()}`);
  const server = createDashboardServer();
  await new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolveListen);
  });
  const address = server.address();
  return { server, baseUrl: `http://127.0.0.1:${address.port}` };
}

async function request(baseUrl, path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, options);
  const body = await response.json().catch(() => null);
  return { response, body };
}

function action(baseUrl, body) {
  return request(baseUrl, "/api/action", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body)
  });
}

function task(state, ticketId) {
  const result = state.board.tasks.find(candidate => candidate.ticketId === ticketId);
  assert.ok(result, `Expected ${ticketId} in dashboard projection.`);
  return result;
}

try {
  const { server, baseUrl } = await startServer();
  try {
    const page = await fetch(`${baseUrl}/`);
    const html = await page.text();
    assert.equal(page.status, 200);
    assert.match(html, /Howie/);
    assert.match(html, /This Week/);
    assert.match(html, /System Proof/);
    assert.match(html, /Evidence/);
    assert.match(html, /Company Plan/);
    assert.match(html, /ticket-drawer/);
    assert.match(html, /What is needed/);
    assert.match(html, /Delivery event timeline/);
    assert.match(html, /Hermes behavior/);
    assert.match(html, /Real-agent eval conversation with Manager/);
    assert.match(html, /The Howie AI profile and the company records supplied to this session/);
    assert.match(html, /Profile \+ inputs/);
    assert.match(html, /What Manager can use/);
    assert.match(html, /What changed/);
    assert.match(html, /session-panel/);
    assert.match(html, /agent-setup-files/);
    assert.match(html, /agent-capabilities/);
    assert.match(html, /agent-change-checks/);
    assert.match(html, /file-inspector/);
    assert.match(html, /six-ticket weekly plan/);
    assert.match(html, /matched the missing workbook to the principal geologist/);
    assert.match(html, /four days overdue and remains blocked after two follow-ups/);
    assert.match(html, /2 · Find the expert/);
    assert.match(html, /sending remains CLI-only/);
    assert.match(html, /data-page="week"/);
    assert.match(html, /data-page="proof"/);
    assert.match(html, /data-page="evals"/);
    assert.match(html, /data-action": action/);
    assert.match(html, /vendor\/frappe-gantt\.css/);
    assert.match(html, /vendor\/frappe-gantt\.umd\.js/);
    assert.match(html, /new window\.Gantt/);
    assert.match(html, /aria-modal="true"/);
    assert.match(html, /prefers-reduced-motion/);
    assert.match(html, /assets\/mine-cave\.png/);
    assert.match(html, /width: min\(1280px, calc\(100% - 64px\)\)/);
    assert.doesNotMatch(html, /<summary>Developer evidence<\/summary>/);
    assert.doesNotMatch(html, /data-action="reply_geo"|data-action="seed_demo"|data-action="send"|Record Kenji reply/);
    assert.doesNotMatch(html, /https?:\/\//);

    const asset = await fetch(`${baseUrl}/assets/mine-cave.png`);
    assert.equal(asset.status, 200);
    assert.equal(asset.headers.get("content-type"), "image/png");
    assert.ok((await asset.arrayBuffer()).byteLength > 1000, "Expected the supplied mine backdrop to be served.");

    const ganttStyle = await fetch(`${baseUrl}/vendor/frappe-gantt.css`);
    assert.equal(ganttStyle.status, 200);
    assert.equal(ganttStyle.headers.get("content-type"), "text/css; charset=utf-8");
    assert.match(await ganttStyle.text(), /gantt-container/);

    const ganttScript = await fetch(`${baseUrl}/vendor/frappe-gantt.umd.js`);
    assert.equal(ganttScript.status, 200);
    assert.equal(ganttScript.headers.get("content-type"), "application\/javascript; charset=utf-8");
    assert.match(await ganttScript.text(), /Gantt/);

    let result = await request(baseUrl, "/api/state");
    assert.equal(result.response.status, 200);
    assert.deepEqual(result.body.board.counts, { blocked: 0, in_progress: 0, awaiting_review: 0, done: 0 });

    result = await request(baseUrl, "/api/evals/latest");
    assert.equal(result.response.status, 200);
    assert.equal(result.body.latest, null);

    result = await request(baseUrl, "/api/agent-evals/latest");
    assert.equal(result.response.status, 200);
    assert.equal(result.body.latest, null);

    const agentRunRoot = resolve(workspaceRoot, "agent-runs/2026-08-12-boundary-test");
    const scenarioRoot = resolve(agentRunRoot, "runs/real_case");
    const outsidePath = resolve(workspaceRoot, "not-an-agent-artifact.txt");
    mkdirSync(scenarioRoot, { recursive: true });
    writeFileSync(outsidePath, "PRIVATE OUTSIDE CONTENT\n", "utf8");
    writeFileSync(resolve(scenarioRoot, "prompt.md"), "Canonical scenario prompt.\n", "utf8");
    writeFileSync(resolve(scenarioRoot, "stdout.txt"), "I created the plan and started the ready work.\nSession:        20260812_120557_48a879\n", "utf8");
    writeFileSync(resolve(scenarioRoot, "stderr.txt"), "", "utf8");
    writeFileSync(resolve(scenarioRoot, "usage.json"), JSON.stringify({ completed: true, model: "mock-model" }), "utf8");
    writeFileSync(resolve(scenarioRoot, "result.json"), JSON.stringify({
      id: "real_case",
      channel_message: "Here are the weekly meeting notes.",
      manager_reply: "I created the plan and started the ready work.",
      profile: "howieaieva",
      files: { final: [] },
      artifact_paths: { prompt: outsidePath, stdout: outsidePath, stderr: outsidePath, usage: outsidePath }
    }), "utf8");
    writeFileSync(resolve(agentRunRoot, "summary.json"), JSON.stringify({
      suite: "howie-real-hermes-agent",
      pass: true,
      completed_at: "2026-08-12T00:00:00.000Z",
      scenarios: [{ id: "real_case", title: "Boundary test", pass: true, exit_code: 0, result_path: outsidePath }]
    }), "utf8");

    result = await request(baseUrl, "/api/agent-evals/latest");
    assert.equal(result.response.status, 200);
    assert.equal(result.body.latest.runId, "2026-08-12-boundary-test");
    assert.equal(result.body.latest.scenarios[0].prompt, "Canonical scenario prompt.\n");
    assert.equal(result.body.latest.scenarios[0].channel_message, "Here are the weekly meeting notes.");
    assert.equal(result.body.latest.scenarios[0].manager_reply, "I created the plan and started the ready work.");
    assert.deepEqual(result.body.latest.scenarios[0].hermes_session, {
      id: "20260812_120557_48a879",
      url: "http://127.0.0.1:9119/chat?profile=howieaieva&resume=20260812_120557_48a879"
    });
    assert.equal(Object.hasOwn(result.body.latest.scenarios[0], "stdout"), false);
    assert.equal(JSON.stringify(result.body.latest).includes("PRIVATE OUTSIDE CONTENT"), false);
    assert.equal(JSON.stringify(result.body.latest).includes(outsidePath), false);

    result = await request(baseUrl, "/api/evals/run", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{}"
    });
    assert.equal(result.response.status, 200);
    assert.equal(result.body.latest.summary.pass, true);
    assert.deepEqual(result.body.latest.summary.counts, { pass: 3, gap: 0, error: 0 });
    assert.equal(result.body.latest.tasks.length, 3);
    assert.equal(result.body.latest.tasks[0].trace.some((entry) => entry.kind === "meeting_input"), true);
    assert.equal(result.body.latest.tasks[0].filesystem.final_files.some((file) => file.path.endsWith("ticket.md")), true);
    assert.equal(result.body.latest.tasks[0].filesystem.meeting_delta.created.some((file) => file.path === "tickets/TASK-1001/ticket.md"), true);
    assert.equal(result.body.latest.tasks[0].filesystem.workflow_delta.modified.some((file) => file.path === "tickets/TASK-1002/ticket.md"), true);
    assert.match(result.body.latest.tasks[0].filesystem.final_files.find((file) => file.path === "tickets/TASK-1002/ticket.md").sha256, /^[a-f0-9]{64}$/);

    result = await request(baseUrl, "/api/state");
    assert.equal(result.response.status, 200);
    assert.deepEqual(result.body.board.counts, { blocked: 0, in_progress: 0, awaiting_review: 0, done: 0 });

    result = await request(baseUrl, "/api/evals/latest");
    assert.equal(result.response.status, 200);
    assert.equal(result.body.latest.summary.suite, "company-manager");

    result = await request(baseUrl, "/api/unknown");
    assert.equal(result.response.status, 404);
    assert.equal(result.body.error, "API route not found.");

    result = await action(baseUrl, { action: "unsupported" });
    assert.equal(result.response.status, 400);
    assert.match(result.body.error, /Unsupported dashboard action/);

    result = await action(baseUrl, { action: "send" });
    assert.equal(result.response.status, 400);
    assert.match(result.body.error, /Unsupported dashboard action/);

    result = await action(baseUrl, { action: "preview_human_request" });
    assert.equal(result.response.status, 400);
    assert.match(result.body.error, /ticketId is required/);

    result = await action(baseUrl, { action: "seed" });
    assert.equal(result.response.status, 200);
    assert.equal(result.body.state.board.tasks.length, 4);
    assert.equal(result.body.state.board.counts.blocked, 4);
    assert.match(result.body.actionResult.message, /Frozen dependency scenario loaded locally/);

    const geoBefore = task(result.body.state, "TASK-1001");
    const deckBefore = task(result.body.state, "TASK-1002");
    const geoHumanRequirement = geoBefore.requirements.find(requirement => requirement.type === "human_input");
    assert.ok(geoHumanRequirement, "Geo ticket must expose its declared human requirement.");
    assert.equal(geoHumanRequirement.human.channel, "telegram_delivery");
    assert.equal(geoHumanRequirement.followUp.employeeId, geoHumanRequirement.human.employeeId);
    assert.equal(geoHumanRequirement.followUp.attempts, 0);
    assert.equal(geoHumanRequirement.followUp.lastAt, null);
    assert.match(geoHumanRequirement.followUp.nextAt, /^2026-08-11T/);
    assert.equal(geoHumanRequirement.followUp.deliveryId, null);
    assert.equal(geoHumanRequirement.followUp.status, "pending");
    assert.equal(deckBefore.requirements.some(requirement => requirement.type === "skill_output" && requirement.upstream.ticketId === "TASK-1001" && requirement.upstream.outputId === "geo-report"), true);
    assert.equal(geoBefore.skillOutputs.some(output => output.outputId === "geo-report"), true);
    assert.equal(geoBefore.unblocks.some(edge => edge.ticketId === "TASK-1002"), true);
    assert.equal(deckBefore.blockedBy.some(edge => edge.ticketId === "TASK-1001" && edge.outputId === "geo-report"), true);
    assert.equal(geoBefore.outstandingPeople.length, 1);
    assert.equal(geoBefore.outstandingPeople[0].requirementId, geoHumanRequirement.id);
    assert.equal(geoBefore.outstandingPeople[0].employeeId, geoHumanRequirement.human.employeeId);
    assert.deepEqual(geoBefore.outstandingPeople[0].followUp, geoHumanRequirement.followUp);
    assert.deepEqual(geoBefore.pendingDeliveries, []);

    result = await action(baseUrl, { action: "preview_human_request", ticketId: geoBefore.ticketId, requirementId: geoHumanRequirement.id });
    assert.equal(result.response.status, 200);
    assert.match(result.body.actionResult.message, /No message was sent/);
    assert.match(JSON.stringify(result.body.state.lastActions), /telegram_delivery_draft/);
    const geoAfterDraft = task(result.body.state, "TASK-1001");
    assert.equal(geoAfterDraft.pendingDeliveries.length, 1);
    assert.equal(geoAfterDraft.pendingDeliveries[0].delivery, "draft_only");
    assert.equal(result.body.state.deliveryEvents.some(event => event.ticketId === "TASK-1001" && event.type === "telegram_delivery_draft"), true);
    assert.equal(JSON.stringify(result.body.state.deliveryEvents).includes("telegram_target"), false, "Dashboard state must never expose a contact target.");

    result = await action(baseUrl, {
      action: "simulate_human_response",
      ticketId: geoBefore.ticketId,
      requirementId: geoHumanRequirement.id,
      employeeId: geoHumanRequirement.human.employeeId,
      text: "Confirmed in the local dashboard test fixture."
    });
    assert.equal(result.response.status, 200);
    assert.equal(task(result.body.state, "TASK-1001").status, "blocked");
    assert.equal(task(result.body.state, "TASK-1001").requirements.find(requirement => requirement.id === geoHumanRequirement.id).state, "resolved");

    result = await action(baseUrl, { action: "pulse" });
    assert.equal(result.response.status, 200);
    assert.equal(task(result.body.state, "TASK-1001").status, "in_progress");
    assert.match(JSON.stringify(result.body.state.lastActions), /mock_worker_dispatched/);

    result = await action(baseUrl, { action: "publish", ticketId: "TASK-1001" });
    assert.equal(result.response.status, 200);
    assert.equal(task(result.body.state, "TASK-1001").status, "awaiting_review");

    result = await action(baseUrl, { action: "review", ticketId: "TASK-1001", reviewerId: "kenji" });
    assert.equal(result.response.status, 200);
    assert.equal(task(result.body.state, "TASK-1001").status, "done");
    for (const ticketId of ["TASK-1002", "TASK-1003"]) {
      const downstream = task(result.body.state, ticketId);
      assert.equal(downstream.requirements.some(requirement => requirement.type === "skill_output" && requirement.state === "resolved" && requirement.upstream.ticketId === "TASK-1001"), true, `${ticketId} must resolve the upstream geo requirement after approval.`);
    }
  } finally {
    await new Promise(resolveClose => server.close(resolveClose));
  }
} finally {
  if (originalWorkspace === undefined) delete process.env.HOWIE_DASHBOARD_WORKSPACE_PATH;
  else process.env.HOWIE_DASHBOARD_WORKSPACE_PATH = originalWorkspace;
  if (originalNativeHermesDashboard === undefined) delete process.env.HOWIE_HERMES_DASHBOARD_URL;
  else process.env.HOWIE_HERMES_DASHBOARD_URL = originalNativeHermesDashboard;
  rmSync(workspaceRoot, { recursive: true, force: true });
}

console.log("✓ Dependency dashboard API and projection controls passed.");
