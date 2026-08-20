/** Local-only HTTP surface for authoring and running portable filesystem evals. */
import { createServer } from "node:http";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { basename, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { listAuthoredFileEvals, prepareAuthoredFileEval, readAuthoredFileEval, runAuthoredFileEval, saveAuthoredFileEval } from "./authored-file-evals.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const uiPath = resolve(root, "ui/index.html");
const casesDirectory = resolve(process.env.AUTHORED_EVAL_CASES_DIR || resolve(root, "cases"));
const outputRoot = resolve(process.env.AUTHORED_EVAL_RUNS_DIR || resolve(root, "runs"));
const host = process.env.AUTHORED_EVAL_HOST || "127.0.0.1";
const port = Number(process.env.PORT || 4179);
const maxBodyBytes = 256 * 1024;

function sendJson(response, status, value) {
  response.writeHead(status, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" });
  response.end(`${JSON.stringify(value)}\n`);
}

function readJson(request) {
  return new Promise((resolveBody, reject) => {
    let body = "";
    request.setEncoding("utf8");
    request.on("data", (chunk) => {
      body += chunk;
      if (Buffer.byteLength(body) > maxBodyBytes) {
        reject(new Error("Request body is too large."));
        request.destroy();
      }
    });
    request.on("end", () => {
      try { resolveBody(body ? JSON.parse(body) : {}); } catch (error) { reject(new Error(`Invalid JSON: ${error.message}`)); }
    });
    request.on("error", reject);
  });
}

function preparedReceipt(prepared) {
  return { id: prepared.definition.id, outputRoot: prepared.outputRoot, workspace: prepared.workspace, workspaceFileCount: prepared.before.length };
}

function latestResult(id) {
  if (!existsSync(outputRoot)) return null;
  const matches = readdirSync(outputRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && entry.name.endsWith(`-${id}`) && existsSync(resolve(outputRoot, entry.name, "result.json")))
    .map((entry) => entry.name).sort();
  if (!matches.length) return null;
  const runDirectory = resolve(outputRoot, matches.at(-1));
  return { runId: basename(runDirectory), ...JSON.parse(readFileSync(resolve(runDirectory, "result.json"), "utf8")) };
}

function handleApi(request, response, url) {
  if (url.pathname === "/api/cases" && request.method === "GET") return sendJson(response, 200, { cases: listAuthoredFileEvals({ casesDirectory }) });
  if (url.pathname === "/api/results/latest" && request.method === "GET") {
    const id = url.searchParams.get("id") || "";
    return sendJson(response, 200, { latest: latestResult(id) });
  }
  if (url.pathname !== "/api/cases" || request.method !== "POST") return sendJson(response, 404, { error: "Route not found." });
  readJson(request).then((body) => {
    if (body.action === "save") {
      const definition = saveAuthoredFileEval(body.definition, { casesDirectory });
      return sendJson(response, 200, { definition, cases: listAuthoredFileEvals({ casesDirectory }) });
    }
    const definition = readAuthoredFileEval(body.id, { casesDirectory });
    if (body.action === "prepare") {
      return sendJson(response, 200, { prepared: preparedReceipt(prepareAuthoredFileEval(definition, { outputRoot })) });
    }
    if (body.action === "run") {
      const run = runAuthoredFileEval(definition, { outputRoot });
      return sendJson(response, 200, { result: run.result, outputRoot: run.outputRoot });
    }
    throw new Error("Action must be save, prepare, or run.");
  }).catch((error) => sendJson(response, 400, { error: error.message }));
  return true;
}

export function createEvalServer() {
  return createServer((request, response) => {
    const url = new URL(request.url, `http://${request.headers.host || "localhost"}`);
    if (url.pathname.startsWith("/api/")) return handleApi(request, response, url);
    if (url.pathname !== "/" || request.method !== "GET") {
      response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
      return response.end("Not found");
    }
    response.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" });
    response.end(readFileSync(uiPath));
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  createEvalServer().listen(port, host, () => console.log(`Authored filesystem evals: http://${host}:${port}`));
}
