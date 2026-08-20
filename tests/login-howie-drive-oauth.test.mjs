import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = readFileSync(resolve(projectRoot, "scripts/login-howie-drive-oauth.py"), "utf8");

test("live Drive OAuth helper binds the official endpoint and keeps secrets out of output", () => {
  assert.match(source, /EXPECTED_DRIVE_ENDPOINT = "https:\/\/drivemcp\.googleapis\.com\/mcp\/v1"/);
  assert.match(source, /with force_interactive_oauth\(\):\n\s+server = await asyncio\.wait_for\(_connect_server/);
  assert.match(source, /set_secret_scope\(build_profile_secret_scope\(profile_home\)\)/);
  assert.match(source, /HermesTokenStorage\("googledrive"\)\.has_cached_tokens\(\)/);
  assert.match(source, /AUTHORIZED Google Drive MCP with \{len\(tools\)\} permitted tools/);
  assert.doesNotMatch(source, /print\([^\n]*(client_id|client_secret|authorization_url|token)/i);
});
