/**
 * Local-only dashboard server for the dependency-aware Company Plan.
 *
 * It serves a read-only projection of canonical ticket folders and exposes
 * only explicit simulator actions. In particular, a Telegram delivery draft
 * is a persisted no-send record; this server has no transport, contacts, or
 * external-service client.
 */
import { createServer } from "node:http";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { basename, dirname, resolve } from "node:path";
import { dashboardState, runDashboardAction } from "./company-manager.mjs";
import { runCompanyManagerEvals } from "./run-company-manager-evals.mjs";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dashboardPath = resolve(projectRoot, "dashboard/index.html");
const mineBackdropPath = resolve(projectRoot, "dashboard/assets/mine-cave.png");
const ganttStylePath = resolve(projectRoot, "node_modules/frappe-gantt/dist/frappe-gantt.css");
const ganttScriptPath = resolve(projectRoot, "node_modules/frappe-gantt/dist/frappe-gantt.umd.js");
const workspaceRoot = process.env.HOWIE_DASHBOARD_WORKSPACE_PATH
  ? resolve(process.env.HOWIE_DASHBOARD_WORKSPACE_PATH)
  : resolve(projectRoot, "workspaces/howie-ai");
const evalRunsRoot = resolve(workspaceRoot, "eval-runs");
const agentRunsRoot = resolve(workspaceRoot, "agent-runs");
// A proof dashboard can read one immutable, captured Hermes run while its
// canonical board comes from the run's isolated workspace. This keeps demo
// evidence separate from the mutable local simulator.
const agentEvalOutputRoot = process.env.HOWIE_DASHBOARD_AGENT_EVAL_PATH
  ? resolve(process.env.HOWIE_DASHBOARD_AGENT_EVAL_PATH)
  : null;
const readOnly = process.env.HOWIE_DASHBOARD_READ_ONLY === "1";
const host = process.env.HOWIE_DASHBOARD_HOST ?? "127.0.0.1";
const port = Number(process.env.PORT ?? 4173);
const nativeHermesDashboard = configuredNativeHermesDashboard(process.env.HOWIE_HERMES_DASHBOARD_URL);
const maxRequestBytes = 16 * 1024;
const demoTimes = {
  pulse: "2026-08-11T09:00:00.000Z",
  preview: "2026-08-11T09:01:00.000Z",
  response: "2026-08-11T09:05:00.000Z",
  review: "2026-08-11T10:00:00.000Z"
};

function sendJson(response, status, value) {
  response.writeHead(status, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" });
  response.end(`${JSON.stringify(value)}\n`);
}

function readJsonBody(request) {
  return new Promise((resolveBody, reject) => {
    let body = "";
    request.setEncoding("utf8");
    request.on("data", (chunk) => {
      body += chunk;
      if (Buffer.byteLength(body) > maxRequestBytes) {
        reject(new Error("Request body is too large."));
        request.destroy();
      }
    });
    request.on("end", () => {
      if (!body) return resolveBody({});
      try {
        const value = JSON.parse(body);
        if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Action body must be a JSON object.");
        resolveBody(value);
      } catch (error) {
        reject(new Error(`Invalid JSON action body: ${error.message}`));
      }
    });
    request.on("error", reject);
  });
}

function requiredString(value, field) {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${field} is required.`);
  return value;
}

function actionRequest(body) {
  switch (body.action) {
    case "seed":
      return { action: "seed", enabled: true };
    case "pulse":
      return { action: "pulse", enabled: true, now: demoTimes.pulse };
    case "preview_human_request":
      return {
        action: "preview_human_request",
        enabled: true,
        ticketId: requiredString(body.ticketId, "ticketId"),
        requirementId: requiredString(body.requirementId, "requirementId"),
        now: demoTimes.preview
      };
    case "simulate_human_response":
      return {
        action: "simulate_human_response",
        enabled: true,
        ticketId: requiredString(body.ticketId, "ticketId"),
        requirementId: requiredString(body.requirementId, "requirementId"),
        employeeId: requiredString(body.employeeId, "employeeId"),
        text: requiredString(body.text, "text"),
        now: demoTimes.response
      };
    case "publish":
      return { action: "publish", enabled: true, ticketId: requiredString(body.ticketId, "ticketId") };
    case "review":
      return {
        action: "review",
        enabled: true,
        ticketId: requiredString(body.ticketId, "ticketId"),
        reviewerId: requiredString(body.reviewerId, "reviewerId"),
        decision: "approved",
        now: demoTimes.review
      };
    default:
      throw new Error("Unsupported dashboard action.");
  }
}

function actionMessage(action) {
  const messages = {
    seed: "Frozen dependency scenario loaded locally.",
    pulse: "Local pulse completed; eligible local work started and any Telegram request remains a no-send draft.",
    preview_human_request: "Simulated Telegram delivery draft recorded. No message was sent.",
    simulate_human_response: "Local simulated reply recorded; readiness recomputed.",
    publish: "Local upstream output published for review.",
    review: "Local review recorded; downstream readiness recomputed."
  };
  return messages[action] ?? "Local simulation step completed.";
}

function readJsonFile(path, label) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    throw new Error(`Could not read ${label}: ${error.message}`);
  }
}

function capturedFrontmatter(markdown, label) {
  const match = String(markdown || "").match(/^---\n([\s\S]*?)\n---\n?/);
  if (!match) throw new Error(`${label} needs frontmatter.`);
  const metadata = {};
  for (const line of match[1].split("\n")) {
    if (!line) continue;
    const separator = line.indexOf(": ");
    if (separator < 1) throw new Error(`${label} has invalid frontmatter.`);
    metadata[line.slice(0, separator)] = JSON.parse(line.slice(separator + 2));
  }
  return metadata;
}

function capturedProgress(ticketId, workspace) {
  const path = resolve(workspace, "tickets", ticketId, "progress.md");
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8").split("\n").flatMap((line) => {
    const match = line.match(/^- ([^ ]+) — \*\*([^*]+)\*\* — (\{.*\})$/);
    if (!match) return [];
    try {
      return [{ at: match[1], type: match[2], ...JSON.parse(match[3]), ticketId, line }];
    } catch {
      return [];
    }
  });
}

function capturedDriveFiles(root, relativePath = "") {
  if (!existsSync(root)) return [];
  return readdirSync(root, { withFileTypes: true }).flatMap((entry) => {
    const childPath = resolve(root, entry.name);
    const childRelative = relativePath ? `${relativePath}/${entry.name}` : entry.name;
    if (entry.isDirectory()) return capturedDriveFiles(childPath, childRelative);
    if (!entry.isFile()) return [];
    return [{ name: entry.name, path: `shared-drive/${childRelative}`, scope: "Aurora Lithium shared Drive", storage_kind: "source_reference" }];
  });
}

/**
 * A captured Hermes run writes a smaller, source-owned ticket contract than
 * the mutable local simulator. This adapter is deliberately read-only: it
 * creates the same dashboard projection without attempting to validate,
 * normalize, or rewrite captured evidence through the simulator.
 */
function capturedHermesDashboardState(workspace) {
  const ticketsRoot = resolve(workspace, "tickets");
  const ticketIds = existsSync(ticketsRoot)
    ? readdirSync(ticketsRoot, { withFileTypes: true }).filter((entry) => entry.isDirectory() && /^TASK-\d{4}$/.test(entry.name)).map((entry) => entry.name).sort()
    : [];
  const records = ticketIds.map((ticketId) => ({
    ticketId,
    ticket: capturedFrontmatter(readFileSync(resolve(ticketsRoot, ticketId, "ticket.md"), "utf8"), `ticket ${ticketId}`),
    progress: capturedProgress(ticketId, workspace)
  }));
  const byId = new Map(records.map((record) => [record.ticketId, record]));
  const allProgress = records.flatMap((record) => record.progress);
  const tasks = records.map(({ ticketId, ticket, progress }) => {
    const requirements = Array.isArray(ticket.requirements) ? ticket.requirements.map((requirement) => ({
      id: requirement.id,
      type: requirement.type,
      description: requirement.description,
      state: requirement.state,
      human: requirement.human ? {
        employeeId: requirement.human.employee_id,
        channel: requirement.human.channel,
        question: requirement.human.question
      } : undefined,
      followUp: requirement.follow_up ? {
        employeeId: requirement.follow_up.employee_id,
        lastAt: requirement.follow_up.last_at,
        nextAt: requirement.follow_up.next_at,
        attempts: requirement.follow_up.attempts,
        cooldownMinutes: requirement.follow_up.cooldown_minutes,
        status: requirement.follow_up.status,
        deliveryId: requirement.follow_up.delivery_id
      } : undefined,
      upstream: requirement.upstream ? {
        ticketId: requirement.upstream.ticket_id,
        skillId: requirement.upstream.skill_id,
        outputId: requirement.upstream.output_id
      } : undefined
    })) : [];
    const skillOutputs = (Array.isArray(ticket.mock_skill_dependencies) ? ticket.mock_skill_dependencies : []).flatMap((skill) =>
      (Array.isArray(skill.outputs) ? skill.outputs : []).map((output) => ({
        skillId: skill.id,
        outputId: output.id,
        description: output.description,
        approved: ticket.review?.decision === "approved"
      }))
    );
    const blockedBy = requirements.filter((requirement) => requirement.type === "skill_output").map((requirement) => ({
      ticketId: requirement.upstream?.ticketId,
      skillId: requirement.upstream?.skillId,
      outputId: requirement.upstream?.outputId,
      requirementId: requirement.id
    }));
    const unblocks = records.flatMap((other) => (Array.isArray(other.ticket.requirements) ? other.ticket.requirements : [])
      .filter((requirement) => requirement.type === "skill_output" && requirement.upstream?.ticket_id === ticketId)
      .map((requirement) => ({ ticketId: other.ticketId, requirementId: requirement.id, skillId: requirement.upstream?.skill_id, outputId: requirement.upstream?.output_id })));
    const outstandingPeople = requirements.filter((requirement) => requirement.type === "human_input" && requirement.state === "unresolved")
      .map((requirement) => ({ requirementId: requirement.id, employeeId: requirement.human?.employeeId, followUp: requirement.followUp }));
    const pendingDeliveries = progress.filter((event) => event.delivery_id).map((event) => ({
      ticketId,
      deliveryId: event.delivery_id,
      requirementId: event.requirement_id,
      employeeId: event.employee_id,
      type: event.type,
      status: event.delivery || "recorded",
      at: event.at
    }));
    const unresolvedRequirementIds = requirements.filter((requirement) => requirement.state === "unresolved").map((requirement) => requirement.id);
    return {
      ticketId,
      title: ticket.title,
      description: ticket.description,
      workstream: ticket.workstream,
      ownerId: ticket.owner_id,
      reviewerId: ticket.reviewer_id,
      status: ticket.status,
      startAt: ticket.start_at,
      dueAt: ticket.due_at,
      nextChaseAt: outstandingPeople.map((person) => person.followUp?.nextAt).filter(Boolean).sort()[0] ?? null,
      chaseAttempts: outstandingPeople.reduce((total, person) => total + Number(person.followUp?.attempts || 0), 0),
      blockingInputs: requirements.filter((requirement) => requirement.state === "unresolved").map((requirement) => ({ id: requirement.id, description: requirement.description })),
      mockSkillDependencies: ticket.mock_skill_dependencies || [],
      requirements,
      blockedBy,
      unblocks,
      skillOutputs,
      readiness: { state: ticket.status, unresolvedRequirementIds, eligibleSkillIds: ticket.status === "in_progress" ? (ticket.mock_skill_dependencies || []).map((skill) => skill.id) : [] },
      eligibleHumanRequest: null,
      eligibleHumanRequests: [],
      outstandingPeople,
      pendingDeliveries,
      artifact: ticket.artifact || null,
      review: ticket.review || null,
      archived: false
    };
  });
  const counts = Object.fromEntries(["blocked", "in_progress", "awaiting_review", "done"].map((status) => [status, tasks.filter((task) => task.status === status).length]));
  const deliveryEvents = tasks.flatMap((task) => task.pendingDeliveries);
  return {
    board: {
      workspaceRoot: workspace,
      generatedAt: records.map((record) => record.ticket.updated_at).filter(Boolean).sort().at(-1) ?? null,
      tasks,
      gantt: tasks.map((task) => ({ ticketId: task.ticketId, title: task.title, startAt: task.startAt, dueAt: task.dueAt, status: task.status })),
      counts
    },
    employees: [],
    driveFiles: capturedDriveFiles(resolve(workspace, "shared-drive")),
    weeklyReport: null,
    lastActions: allProgress.slice(-24).map((event) => ({ ticketId: event.ticketId, line: event.line })),
    deliveryEvents,
    deliveryTimeline: deliveryEvents
  };
}

function presentationState() {
  return readOnly && agentEvalOutputRoot
    ? { ...capturedHermesDashboardState(workspaceRoot), readOnly: true }
    : { ...dashboardState({ workspaceRoot }), readOnly };
}

function presentationReply(text) {
  return String(text || "")
    .replace(/^🎉\s*Conversation completed after .*$/gmi, "")
    .trim();
}

function configuredNativeHermesDashboard(value) {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (!/^https?:$/.test(url.protocol) || !["127.0.0.1", "localhost", "::1"].includes(url.hostname)) return null;
    url.hash = "";
    url.search = "";
    return url;
  } catch {
    return null;
  }
}

function safeHermesSessionId(value) {
  const sessionId = String(value ?? "").trim();
  return /^[A-Za-z0-9_-]{8,128}$/.test(sessionId) ? sessionId : null;
}

function sessionIdFromTranscript(text) {
  return safeHermesSessionId(String(text ?? "").match(/^Session:\s+([A-Za-z0-9_-]+)/m)?.[1]);
}

function nativeHermesSession(sessionId, profile) {
  if (!nativeHermesDashboard || !sessionId || !/^[A-Za-z0-9_-]{1,128}$/.test(String(profile ?? ""))) return null;
  const url = new URL(nativeHermesDashboard.toString());
  url.pathname = `${url.pathname.replace(/\/$/, "")}/chat`;
  url.searchParams.set("profile", profile);
  url.searchParams.set("resume", sessionId);
  return { id: sessionId, url: url.toString() };
}

function readEvalRun(outputRoot) {
  const summary = readJsonFile(resolve(outputRoot, "summary.json"), "eval summary");
  if (!Array.isArray(summary.tasks)) throw new Error("Eval summary has no task list.");
  const tasks = summary.tasks.map((task) => readJsonFile(resolve(outputRoot, "tasks", `${task.task_id}.json`), `eval task ${task.task_id}`));
  return { runId: basename(outputRoot), summary, tasks };
}

function latestEvalRun() {
  if (!existsSync(evalRunsRoot)) return null;
  const directories = readdirSync(evalRunsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && existsSync(resolve(evalRunsRoot, entry.name, "summary.json")))
    .map((entry) => entry.name)
    .sort();
  if (!directories.length) return null;
  return readEvalRun(resolve(evalRunsRoot, directories.at(-1)));
}

function readAgentEvalRun(outputRoot) {
  const summary = readJsonFile(resolve(outputRoot, "summary.json"), "real Hermes eval summary");
  if (summary.suite !== "howie-real-hermes-agent" || !Array.isArray(summary.scenarios)) {
    throw new Error("Agent eval summary is not a Howie Hermes behavior run.");
  }
  const scenarios = summary.scenarios.map((scenario) => {
    const scenarioId = requiredString(scenario.id, "scenario id");
    if (!/^[a-z0-9][a-z0-9_-]*$/i.test(scenarioId)) throw new Error(`Unsafe real Hermes scenario id: ${scenarioId}`);
    // `summary.json` and `result.json` are developer artifacts, not authority
    // to read arbitrary local paths. Every displayable file is derived from the
    // run directory selected above; paths embedded in result.json are evidence
    // only and must never become dashboard read targets.
    const scenarioRoot = resolve(outputRoot, "runs", scenarioId);
    const result = readJsonFile(resolve(scenarioRoot, "result.json"), `real Hermes scenario ${scenarioId}`);
    const readText = (path) => existsSync(path) ? readFileSync(path, "utf8") : "";
    const { artifact_paths: ignoredArtifactPaths, ...publicResult } = result;
    const sessionId = safeHermesSessionId(publicResult.hermes_session_id)
      ?? sessionIdFromTranscript(readText(resolve(scenarioRoot, "stdout.txt")));
    return {
      ...publicResult,
      manager_reply: presentationReply(publicResult.manager_reply),
      prompt: readText(resolve(scenarioRoot, "prompt.md")),
      hermes_session: nativeHermesSession(sessionId, publicResult.profile)
    };
  });
  return {
    runId: basename(outputRoot),
    summary: {
      ...summary,
      scenarios: summary.scenarios.map(({ id, title, pass, exit_code }) => ({ id, title, pass, exit_code }))
    },
    scenarios
  };
}

function latestAgentEvalRun() {
  if (agentEvalOutputRoot) {
    if (!existsSync(resolve(agentEvalOutputRoot, "summary.json"))) return null;
    try {
      return readAgentEvalRun(agentEvalOutputRoot);
    } catch {
      return null;
    }
  }
  if (!existsSync(agentRunsRoot)) return null;
  const directories = readdirSync(agentRunsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && existsSync(resolve(agentRunsRoot, entry.name, "summary.json")))
    .map((entry) => resolve(agentRunsRoot, entry.name));
  const readable = [];
  for (const directory of directories) {
    try {
      readable.push(readAgentEvalRun(directory));
    } catch {
      // Agent-run folders may include interrupted or incompatible developer attempts.
    }
  }
  readable.sort((left, right) => String(right.summary.completed_at || "").localeCompare(String(left.summary.completed_at || "")));
  return readable.find((run) => run.summary.pass === true) ?? readable[0] ?? null;
}

function runEvalSuite() {
  const runId = `${new Date().toISOString().replace(/[:.]/g, "-")}-company-manager`;
  const outputRoot = resolve(evalRunsRoot, runId);
  const result = runCompanyManagerEvals({ output: outputRoot, allowGaps: true });
  return { ...readEvalRun(result.outputRoot), outputRoot: result.outputRoot };
}

function handleApi(request, response, url) {
  if (url.pathname === "/api/agent-evals/latest") {
    if (request.method !== "GET") return sendJson(response, 405, { error: "Method not allowed." });
    return sendJson(response, 200, { latest: latestAgentEvalRun() });
  }
  if (url.pathname === "/api/evals/latest") {
    if (request.method !== "GET") return sendJson(response, 405, { error: "Method not allowed." });
    return sendJson(response, 200, { latest: latestEvalRun() });
  }
  if (url.pathname === "/api/evals/run") {
    if (request.method !== "POST") return sendJson(response, 405, { error: "Method not allowed." });
    if (readOnly) return sendJson(response, 403, { error: "This captured proof dashboard is read-only." });
    readJsonBody(request)
      .then(() => sendJson(response, 200, { latest: runEvalSuite() }))
      .catch((error) => sendJson(response, 400, { error: error.message }));
    return true;
  }
  if (url.pathname === "/api/state") {
    if (request.method !== "GET") return sendJson(response, 405, { error: "Method not allowed." });
    return sendJson(response, 200, presentationState());
  }
  if (url.pathname !== "/api/action") return sendJson(response, 404, { error: "API route not found." });
  if (request.method !== "POST") return sendJson(response, 405, { error: "Method not allowed." });
  if (readOnly) return sendJson(response, 403, { error: "This captured proof dashboard is read-only." });
  readJsonBody(request)
    .then((body) => {
      const requested = actionRequest(body);
      const output = runDashboardAction({ workspaceRoot, ...requested });
      sendJson(response, 200, {
        state: output.state,
        actionResult: { action: requested.action, message: actionMessage(requested.action) }
      });
    })
    .catch((error) => sendJson(response, 400, { error: error.message }));
  return true;
}

export function createDashboardServer() {
  return createServer((request, response) => {
    const url = new URL(request.url, `http://${request.headers.host ?? "localhost"}`);
    if (url.pathname === "/favicon.ico" && request.method === "GET") {
      response.writeHead(204, { "cache-control": "no-store" });
      response.end();
      return;
    }
    if (url.pathname.startsWith("/api/")) {
      handleApi(request, response, url);
      return;
    }
    if (url.pathname === "/assets/mine-cave.png" && request.method === "GET") {
      try {
        response.writeHead(200, { "content-type": "image/png", "cache-control": "public, max-age=3600" });
        response.end(readFileSync(mineBackdropPath));
      } catch (error) {
        response.writeHead(500, { "content-type": "text/plain; charset=utf-8" });
        response.end(`Dashboard backdrop unavailable: ${error.message}`);
      }
      return;
    }
    if ((url.pathname === "/vendor/frappe-gantt.css" || url.pathname === "/vendor/frappe-gantt.umd.js") && request.method === "GET") {
      const isStyle = url.pathname.endsWith(".css");
      try {
        response.writeHead(200, {
          "content-type": isStyle ? "text/css; charset=utf-8" : "application/javascript; charset=utf-8",
          "cache-control": "public, max-age=3600"
        });
        response.end(readFileSync(isStyle ? ganttStylePath : ganttScriptPath));
      } catch (error) {
        response.writeHead(500, { "content-type": "text/plain; charset=utf-8" });
        response.end(`Dashboard Gantt renderer unavailable: ${error.message}`);
      }
      return;
    }
    if (url.pathname !== "/" || request.method !== "GET") {
      response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
      response.end("Not found");
      return;
    }
    try {
      response.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" });
      response.end(readFileSync(dashboardPath));
    } catch (error) {
      response.writeHead(500, { "content-type": "text/plain; charset=utf-8" });
      response.end(`Dashboard unavailable: ${error.message}`);
    }
  });
}

const invokedAsScript = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedAsScript) {
  createDashboardServer().listen(port, host, () => {
    console.log(`Howie dependency dashboard: http://${host}:${port}`);
  });
}
