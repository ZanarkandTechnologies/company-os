import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = readFileSync(resolve(projectRoot, "scripts/seed-howie-drive-fixture.py"), "utf8");

test("Drive fixture seeder is fake-only and records root scope privately", () => {
  assert.match(source, /Howie AI — Aurora Lithium POC \(synthetic\)/);
  assert.match(source, /No real company, reserve, financial, or personnel data is represented here/);
  assert.match(source, /server\.session\.call_tool\("create_file"/);
  assert.doesNotMatch(source, /call_tool\("(search_files|read_file_content|copy_file|get_file_permissions)/);
  assert.match(source, /fixture-manifest\.private\.json/);
  assert.match(source, /os\.chmod\(path, stat\.S_IRUSR \| stat\.S_IWUSR\)/);
  assert.doesNotMatch(source, /print\([^\n]*(root_id|client_secret|token)/i);
});
