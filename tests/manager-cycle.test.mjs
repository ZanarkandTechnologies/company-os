import assert from "node:assert/strict";
import { existsSync, mkdtempSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { runManagerCycle } from "../scripts/run-manager-cycle.mjs";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function fixture(name) {
  return readFileSync(resolve(projectRoot, "fixtures", name), "utf8");
}

function sandbox(eventFiles = {}) {
  const root = mkdtempSync(resolve(tmpdir(), "howie-manager-cycle-test-"));
  const statePath = resolve(root, "manager-state.json");
  const inboxPath = resolve(root, "inbox");
  const processedPath = resolve(root, "processed");
  mkdirSync(inboxPath);
  writeFileSync(statePath, fixture("manager-state.json"));
  for (const [name, source] of Object.entries(eventFiles)) writeFileSync(resolve(inboxPath, name), fixture(source));
  return { root, statePath, inboxPath, processedPath };
}

const preview = sandbox({ "001-meeting.json": "manager-inbox-meeting.json" });
try {
  const original = readFileSync(preview.statePath, "utf8");
  const result = runManagerCycle({ ...preview, now: "2026-08-10T10:00:00.000Z" });
  assert.equal(result.blocked, false);
  assert.equal(result.inbox.outcomes.length, 1);
  assert.equal(result.pulse.actionsCreated.length, 1);
  assert.equal(readFileSync(preview.statePath, "utf8"), original);
  assert.deepEqual(readdirSync(preview.inboxPath), ["001-meeting.json"]);
  assert.equal(existsSync(preview.processedPath), false);
} finally {
  rmSync(preview.root, { recursive: true, force: true });
}

const write = sandbox({ "001-meeting.json": "manager-inbox-meeting.json" });
try {
  const result = runManagerCycle({ ...write, now: "2026-08-10T10:00:00.000Z", write: true });
  assert.equal(result.blocked, false);
  const state = JSON.parse(readFileSync(write.statePath, "utf8"));
  assert.equal(state.commitments.length, 2);
  assert.equal(state.outbox.length, 1);
  assert.deepEqual(readdirSync(write.inboxPath), []);
  assert.deepEqual(readdirSync(write.processedPath), ["001-meeting.json"]);
} finally {
  rmSync(write.root, { recursive: true, force: true });
}

const malformed = sandbox({ "999-malformed.json": "manager-inbox-malformed.json" });
try {
  const original = readFileSync(malformed.statePath, "utf8");
  const result = runManagerCycle({ ...malformed, now: "2026-08-10T10:00:00.000Z", write: true });
  assert.equal(result.blocked, true);
  assert.equal(result.pulse, null);
  assert.equal(readFileSync(malformed.statePath, "utf8"), original);
  assert.deepEqual(readdirSync(malformed.inboxPath), ["999-malformed.json"]);
} finally {
  rmSync(malformed.root, { recursive: true, force: true });
}

console.log("✓ Manager cycle guards passed.");
