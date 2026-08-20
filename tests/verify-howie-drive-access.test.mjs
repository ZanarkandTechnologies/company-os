import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = readFileSync(resolve(root, "scripts/verify-howie-drive-access.py"), "utf8");

test("Drive access verifier only sends the non-matching read sentinel", () => {
  assert.match(source, /server\.session\.call_tool\(\n\s+"search_files"/);
  assert.match(source, /title = '__howie_oauth_sentinel__'/);
  assert.doesNotMatch(source, /call_tool\("(create_file|read_file_content|copy_file|get_file_permissions)/);
  assert.doesNotMatch(source, /print\([^\n]*(token|client_secret|root_id)/i);
});
