import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";

const root = resolve(import.meta.dirname, "..");
const distribution = resolve(root, "profiles/kamdar-ai");
const deploy = resolve(distribution, "deploy");
const notionSync = resolve(root, "scripts/sync-kamdar-notion-webhook.mjs");

function run(command, args, options = {}) {
  return spawnSync(command, args, {
    cwd: root,
    encoding: "utf8",
    ...options,
  });
}

test("Kamdar distribution declares the bounded Notion and Doppler contract", () => {
  const manifest = readFileSync(join(distribution, "distribution.yaml"), "utf8");
  const config = readFileSync(join(distribution, "config.yaml"), "utf8");
  const service = readFileSync(join(deploy, "kamdar-hermes.service.template"), "utf8");
  const caddy = readFileSync(join(deploy, "kamdar-notion.caddy.template"), "utf8");

  assert.match(manifest, /^name: kamdar-ai$/m);
  assert.match(manifest, /hermes_requires: ">=0\.20\.0"/);
  for (const name of [
    "OPENROUTER_API_KEY",
    "NOTION_TOKEN",
    "NOTION_WEBHOOK_PUBLIC_URL",
    "NOTION_ROOT_PAGE_ID",
    "NOTION_ALLOWED_DATA_SOURCES",
    "NOTION_COMMENT_TRIGGER",
  ]) {
    assert.match(manifest, new RegExp(`name: ${name}`));
  }
  assert.match(config, /plugins:\n  enabled:\n    - notion-platform/);
  assert.match(config, /host: 127\.0\.0\.1/);
  assert.match(config, /path: \/notion\/webhook/);
  assert.match(config, /comment\.created/);
  assert.match(config, /display:\n  busy_input_mode: queue/);
  assert.match(service, /ExecStart=__DOPPLER_BIN__ run --scope __PROFILE_HOME__ -- __HERMES_BIN__ .* gateway run/);
  assert.match(service, /NoNewPrivileges=true/);
  assert.doesNotMatch(manifest, /name: NOTION_ENABLE_COMMENT_REPLIES/);
  assert.match(manifest, /distribution_owned:[\s\S]*- skills/);
  assert.match(caddy, /handle \/notion\/webhook/);
  assert.doesNotMatch(caddy, /handle \/notion\/health/);
  assert.match(caddy, /respond 404/);
  assert.doesNotMatch(caddy, /reverse_proxy 0\.0\.0\.0/);
});

test("Kamdar package reuses the reviewed Notion plugin without drift", () => {
  const canonical = resolve(root, "profiles/howie-ai/plugins/platforms/notion");
  const packaged = resolve(distribution, "plugins/platforms/notion");
  for (const filename of ["__init__.py", "adapter.py", "api.py", "cli.py", "plugin.yaml", "protocol.py"]) {
    assert.equal(
      readFileSync(join(packaged, filename), "utf8"),
      readFileSync(join(canonical, filename), "utf8"),
      `${filename} drifted from the reviewed TASK-0006 source`,
    );
  }
});

test("Kamdar package reuses the root Notion onboarding skill without drift", () => {
  const canonical = resolve(root, "skills/notion-webhook-onboarding");
  const packaged = resolve(distribution, "skills/notion-webhook-onboarding");
  for (const filename of [
    "SKILL.md",
    "qa_checklist.md",
    "evals/evals.json",
    "scripts/notion_webhook_onboard.py",
    "tests/test_onboarding_cli.py",
  ]) {
    assert.equal(
      readFileSync(join(packaged, filename), "utf8"),
      readFileSync(join(canonical, filename), "utf8"),
      `${filename} drifted from the root Company OS skill`,
    );
  }
});

test("VPS scripts are syntactically valid and bootstrap has a no-side-effect dry run", () => {
  for (const filename of ["bootstrap-vps.sh", "verify-vps.sh"]) {
    const syntax = run("bash", ["-n", join(deploy, filename)]);
    assert.equal(syntax.status, 0, syntax.stderr);
  }
  const dryRun = run("bash", [
    join(deploy, "bootstrap-vps.sh"),
    "--hostname",
    "notion.example.com",
    "--dry-run",
  ]);
  assert.equal(dryRun.status, 0, dryRun.stderr);
  assert.match(dryRun.stdout, /dry_run=pass/);
  assert.match(dryRun.stdout, /hostname=notion\.example\.com/);
});

test("Hermes installs the package in isolation and discovers the Notion toolset", () => {
  const hermesHome = mkdtempSync(join(tmpdir(), "kamdar-profile-test-"));
  try {
    const env = { ...process.env, HERMES_HOME: hermesHome };
    const install = run(
      "hermes",
      ["profile", "install", distribution, "--name", "kamdar-test", "--yes"],
      { env },
    );
    assert.equal(install.status, 0, install.stderr || install.stdout);
    assert.match(install.stdout, /Installed 'kamdar-test'/);

    const tools = run("hermes", ["-p", "kamdar-test", "tools", "list"], { env });
    assert.equal(tools.status, 0, tools.stderr || tools.stdout);
    assert.match(tools.stdout, /notion_connector/);

    const skills = run("hermes", ["-p", "kamdar-test", "skills", "list"], { env });
    assert.equal(skills.status, 0, skills.stderr || skills.stdout);
    assert.match(skills.stdout, /notion-webhook-onboarding/);

    const installed = join(hermesHome, "profiles/kamdar-test");
    assert.match(readFileSync(join(installed, ".env.EXAMPLE"), "utf8"), /NOTION_TOKEN=/);
    assert.match(
      readFileSync(join(installed, "skills/notion-webhook-onboarding/SKILL.md"), "utf8"),
      /comment replies are always enabled/i,
    );
    assert.throws(() => readFileSync(join(installed, ".env"), "utf8"));
  } finally {
    rmSync(hermesHome, { recursive: true, force: true });
  }
});

test("Notion updater changes only its owned plugin and skill paths", () => {
  const hermesHome = mkdtempSync(join(tmpdir(), "kamdar-notion-sync-test-"));
  const profile = join(hermesHome, "profiles", "existing-profile");
  try {
    mkdirSync(join(profile, "skills", "existing-skill"), { recursive: true });
    mkdirSync(join(profile, "plugins", "platforms", "other"), { recursive: true });
    writeFileSync(join(profile, "config.yaml"), "custom: true\n");
    writeFileSync(join(profile, ".env"), "SECRET=preserved\n");
    writeFileSync(join(profile, "skills", "existing-skill", "SKILL.md"), "existing\n");
    writeFileSync(join(profile, "plugins", "platforms", "other", "plugin.yaml"), "existing\n");

    const apply = run("node", [notionSync, "--target", profile, "--apply"]);
    assert.equal(apply.status, 0, apply.stderr || apply.stdout);
    const receipt = JSON.parse(apply.stdout);
    assert.equal(receipt.state, "applied");
    assert.ok(receipt.files_written > 0);
    assert.equal(readFileSync(join(profile, "config.yaml"), "utf8"), "custom: true\n");
    assert.equal(readFileSync(join(profile, ".env"), "utf8"), "SECRET=preserved\n");
    assert.equal(readFileSync(join(profile, "skills", "existing-skill", "SKILL.md"), "utf8"), "existing\n");
    assert.equal(readFileSync(join(profile, "plugins", "platforms", "other", "plugin.yaml"), "utf8"), "existing\n");
    assert.ok(existsSync(join(profile, "skills", "notion-webhook-onboarding", "SKILL.md")));

    const check = run("node", [notionSync, "--target", profile, "--check"]);
    assert.equal(check.status, 0, check.stderr || check.stdout);
    assert.equal(JSON.parse(check.stdout).state, "clean");
  } finally {
    rmSync(hermesHome, { recursive: true, force: true });
  }
});
