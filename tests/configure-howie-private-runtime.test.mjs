import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { tmpdir } from "node:os";
import test from "node:test";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const script = resolve(projectRoot, "scripts/configure-howie-private-runtime.mjs");

test("private runtime setup preserves unrelated values and never prints secrets", () => {
  const root = mkdtempSync(join(tmpdir(), "howie-private-runtime-"));
  const profileHome = join(root, "profile");
  const providerEnv = join(root, "provider.env");
  const credentials = join(root, "credentials.json");
  try {
    mkdirSync(profileHome);
    writeFileSync(join(profileHome, ".env"), "KEEP_ME=present\nGOOGLE_DRIVE_MCP_CLIENT_ID=old\n");
    writeFileSync(providerEnv, "OPENROUTER_API_KEY=provider-secret\n");
    writeFileSync(credentials, JSON.stringify({ installed: {
      client_id: "fake-client.apps.googleusercontent.com",
      client_secret: "drive-secret"
    } }));
    const args = [script, "--profile-home", profileHome, "--provider-env", providerEnv, "--drive-credentials", credentials];
    const check = spawnSync(process.execPath, args, { cwd: projectRoot, encoding: "utf8" });
    assert.equal(check.status, 0, check.stderr);
    assert.doesNotMatch(`${check.stdout}${check.stderr}`, /provider-secret|drive-secret|fake-client/);
    assert.equal(readFileSync(join(profileHome, ".env"), "utf8"), "KEEP_ME=present\nGOOGLE_DRIVE_MCP_CLIENT_ID=old\n");

    const apply = spawnSync(process.execPath, [...args, "--apply"], { cwd: projectRoot, encoding: "utf8" });
    assert.equal(apply.status, 0, apply.stderr);
    assert.doesNotMatch(`${apply.stdout}${apply.stderr}`, /provider-secret|drive-secret|fake-client/);
    const environment = readFileSync(join(profileHome, ".env"), "utf8");
    assert.match(environment, /^KEEP_ME=present$/m);
    assert.match(environment, /^OPENROUTER_API_KEY=provider-secret$/m);
    assert.match(environment, /^GOOGLE_DRIVE_MCP_CLIENT_ID=fake-client\.apps\.googleusercontent\.com$/m);
    assert.match(environment, /^GOOGLE_DRIVE_MCP_CLIENT_SECRET=drive-secret$/m);
    assert.equal(statSync(join(profileHome, ".env")).mode & 0o777, 0o600);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
