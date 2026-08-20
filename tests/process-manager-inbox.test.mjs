import assert from "node:assert/strict";
import {
  existsSync,
  mkdtempSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync
} from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const processor = resolve(projectRoot, "scripts/process-manager-inbox.mjs");

function fixture(name) {
  return readFileSync(resolve(projectRoot, "fixtures", name), "utf8");
}

function createSandbox(eventFiles) {
  const root = mkdtempSync(resolve(tmpdir(), "howie-manager-inbox-test-"));
  const statePath = resolve(root, "manager-state.json");
  const inboxPath = resolve(root, "inbox");
  const processedPath = resolve(root, "processed");
  mkdirSync(inboxPath);
  writeFileSync(statePath, fixture("manager-state.json"));
  for (const [name, fixtureName] of Object.entries(eventFiles)) {
    writeFileSync(resolve(inboxPath, name), fixture(fixtureName));
  }
  return { root, statePath, inboxPath, processedPath };
}

function runProcessor(sandbox, args = []) {
  return spawnSync(process.execPath, [
    processor,
    "--state", sandbox.statePath,
    "--inbox", sandbox.inboxPath,
    "--processed", sandbox.processedPath,
    ...args
  ], {
    cwd: projectRoot,
    encoding: "utf8"
  });
}

function readState(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

const dryRun = createSandbox({ "001-meeting.json": "manager-inbox-meeting.json" });
try {
  const original = readFileSync(dryRun.statePath, "utf8");
  writeFileSync(resolve(dryRun.inboxPath, "README.md"), "Inbox documentation is not an event envelope.\n");
  const result = runProcessor(dryRun);
  assert.equal(result.status, 0, `${result.stdout}${result.stderr}`);
  assert.match(result.stdout, /preview 001-meeting\.json: meeting recorded/);
  assert.equal(readFileSync(dryRun.statePath, "utf8"), original);
  assert.deepEqual(readdirSync(dryRun.inboxPath), ["001-meeting.json", "README.md"]);
  assert.equal(existsSync(dryRun.processedPath), false);
} finally {
  rmSync(dryRun.root, { recursive: true, force: true });
}

const writeAndMove = createSandbox({ "001-meeting.json": "manager-inbox-meeting.json" });
try {
  writeFileSync(resolve(writeAndMove.inboxPath, "README.md"), "Inbox documentation is not an event envelope.\n");
  const result = runProcessor(writeAndMove, ["--write"]);
  assert.equal(result.status, 0, `${result.stdout}${result.stderr}`);
  assert.match(result.stdout, /processed 001-meeting\.json: meeting recorded/);
  const state = readState(writeAndMove.statePath);
  assert.equal(state.commitments.length, 2);
  assert.equal(state.events.length, 3);
  assert.deepEqual(readdirSync(writeAndMove.inboxPath), ["README.md"]);
  assert.deepEqual(readdirSync(writeAndMove.processedPath), ["001-meeting.json"]);
  assert.equal(readFileSync(resolve(writeAndMove.processedPath, "001-meeting.json"), "utf8"), fixture("manager-inbox-meeting.json"));

  writeFileSync(resolve(writeAndMove.inboxPath, "002-meeting-replay.json"), fixture("manager-inbox-meeting.json"));
  const stateBeforeReplay = readState(writeAndMove.statePath);
  const replay = runProcessor(writeAndMove, ["--write"]);
  assert.equal(replay.status, 0, `${replay.stdout}${replay.stderr}`);
  assert.match(replay.stdout, /processed 002-meeting-replay\.json: meeting duplicate/);
  assert.deepEqual(readState(writeAndMove.statePath), stateBeforeReplay);
  assert.deepEqual(readdirSync(writeAndMove.inboxPath), ["README.md"]);
  assert.deepEqual(readdirSync(writeAndMove.processedPath), ["001-meeting.json", "002-meeting-replay.json"]);
} finally {
  rmSync(writeAndMove.root, { recursive: true, force: true });
}

const inboundArtifact = createSandbox({ "001-artifact.json": "manager-inbox-artifact.json" });
try {
  const result = runProcessor(inboundArtifact, ["--write"]);
  assert.equal(result.status, 0, `${result.stdout}${result.stderr}`);
  assert.match(result.stdout, /processed 001-artifact\.json: inbound resolved/);
  assert.equal(readState(inboundArtifact.statePath).commitments[0].status, "resolved");
  assert.deepEqual(readdirSync(inboundArtifact.inboxPath), []);
  assert.deepEqual(readdirSync(inboundArtifact.processedPath), ["001-artifact.json"]);
} finally {
  rmSync(inboundArtifact.root, { recursive: true, force: true });
}

const malformed = createSandbox({ "999-malformed.json": "manager-inbox-malformed.json" });
try {
  const original = readFileSync(malformed.statePath, "utf8");
  const result = runProcessor(malformed, ["--write"]);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /999-malformed\.json/);
  assert.equal(readFileSync(malformed.statePath, "utf8"), original);
  assert.deepEqual(readdirSync(malformed.inboxPath), ["999-malformed.json"]);
  assert.equal(existsSync(malformed.processedPath), false);
} finally {
  rmSync(malformed.root, { recursive: true, force: true });
}

const processedCollision = createSandbox({ "001-meeting.json": "manager-inbox-meeting.json" });
try {
  mkdirSync(processedCollision.processedPath);
  writeFileSync(resolve(processedCollision.processedPath, "001-meeting.json"), "preserved prior archive\n");
  const original = readFileSync(processedCollision.statePath, "utf8");
  const result = runProcessor(processedCollision, ["--write"]);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /processed event already exists/);
  assert.equal(readFileSync(processedCollision.statePath, "utf8"), original);
  assert.deepEqual(readdirSync(processedCollision.inboxPath), ["001-meeting.json"]);
  assert.equal(readFileSync(resolve(processedCollision.processedPath, "001-meeting.json"), "utf8"), "preserved prior archive\n");
} finally {
  rmSync(processedCollision.root, { recursive: true, force: true });
}

console.log("✓ Manager inbox processor guards passed.");
