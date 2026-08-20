import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { homedir } from "node:os";
import { fileURLToPath } from "node:url";
import test from "node:test";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const hermesPython = process.env.HERMES_PYTHON || resolve(homedir(), ".hermes/hermes-agent/venv/bin/python");

test("Notion protocol verifies signatures and persistent deduplication", () => {
  const result = spawnSync("python3", [resolve(root, "tests/notion_webhook_protocol_test.py")], {
    encoding: "utf8",
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" }
  });
  assert.equal(result.status, 0, result.stderr || result.stdout);
});

test("Hermes emits valid non-nested Notion tool definitions", () => {
  const result = spawnSync(hermesPython, [resolve(root, "tests/notion_tool_definition_test.py")], {
    encoding: "utf8",
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" }
  });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  assert.match(result.stdout, /one valid Hermes\/OpenAI wrapper/);
});

test("Notion comment events share one Hermes session per ticket and retain reply routing", () => {
  const result = spawnSync(hermesPython, [resolve(root, "tests/notion_comment_adapter_test.py")], {
    encoding: "utf8",
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" }
  });
  assert.equal(result.status, 0, result.stderr || result.stdout);
});

test("Notion plugin is enabled with a narrow platform toolset and safe defaults", () => {
  const config = readFileSync(resolve(root, "profiles/howie-ai/config.template.yaml"), "utf8");
  const adapter = readFileSync(resolve(root, "profiles/howie-ai/plugins/platforms/notion/adapter.py"), "utf8");
  const api = readFileSync(resolve(root, "profiles/howie-ai/plugins/platforms/notion/api.py"), "utf8");
  assert.match(config, /plugins:\n  enabled:\n    - notion-platform/);
  assert.match(config, /notion:\n    - skills\n    - notion_connector/);
  assert.match(config, /host: 127\.0\.0\.1/);
  assert.match(adapter, /X-Notion-Signature/);
  assert.match(adapter, /verification_token_captured/);
  assert.match(adapter, /name="notion-webhook"/);
  assert.match(adapter, /event_type == "comment\.created"/);
  assert.match(adapter, /api\.get_ticket_context/);
  assert.match(adapter, /api\.create_comment_reply/);
  assert.match(adapter, /discussion:/);
  assert.match(api, /NOTION_ENABLE_WRITES/);
  assert.doesNotMatch(api, /NOTION_ENABLE_COMMENT_REPLIES/);
  assert.match(adapter, /remember_sent_reply/);
  assert.match(api, /"value": "data_source"/);
  assert.match(api, /resolved_comments_available/);
  assert.match(api, /scoped_get_secret/);
  assert.doesNotMatch(adapter, /subprocess|shell=True|eval\(/);
});
