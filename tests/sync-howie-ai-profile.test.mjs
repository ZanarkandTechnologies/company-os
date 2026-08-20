import assert from "node:assert/strict";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { tmpdir } from "node:os";
import test from "node:test";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const syncScript = resolve(projectRoot, "scripts/sync-howie-ai-profile.mjs");
const sourceProfile = resolve(projectRoot, "profiles/howie-ai");
const artifactSkillNames = [
  "geo-report",
  "fundraising-deck",
  "financial-model",
  "compliance-report",
  "weekly-operating-report",
  "cash-flow-forecast",
  "budget-variance-report",
  "customer-research",
  "outreach-campaign",
  "deal-memo",
  "commercial-proposal",
  "ads-campaign",
  "contractor-procurement-pack",
  "operating-risk-brief",
  "exploration-program",
  "production-performance-report"
];

function runSync(...arguments_) {
  return spawnSync(process.execPath, [syncScript, ...arguments_], {
    cwd: projectRoot,
    encoding: "utf8"
  });
}

function telegramToolsets(config) {
  const match = config.match(/platform_toolsets:\n  telegram:\n((?:    - [^\n]+\n)+)/);
  assert.ok(match, "rendered config has a Telegram toolset list");
  return match[1].trim().split("\n").map((line) => line.replace(/^\s*-\s+/, ""));
}

test("sync checks first, applies only source-owned files, and detects drift", () => {
  const temporaryRoot = mkdtempSync(join(tmpdir(), "howie-ai-profile-sync-"));
  const profileHome = join(temporaryRoot, "profile");
  const workspaceRoot = join(temporaryRoot, "ops-workspace");
  const arguments_ = ["--target", profileHome, "--workspace-root", workspaceRoot];

  try {
    const initialCheck = runSync(...arguments_);
    assert.equal(initialCheck.status, 1);
    assert.match(initialCheck.stdout, /MISSING SOUL\.md/);
    assert.equal(existsSync(profileHome), false);

    mkdirSync(join(profileHome, "sessions"), { recursive: true });
    writeFileSync(join(profileHome, ".env"), "EXAMPLE_SECRET=must-stay-private\n");
    writeFileSync(join(profileHome, "contacts.json"), "{\"private\":true}\n");
    writeFileSync(join(profileHome, "auth.json"), "{\"token\":\"private\"}\n");
    writeFileSync(join(profileHome, "sessions", "existing.json"), "{\"session\":true}\n");
    mkdirSync(join(profileHome, "people"), { recursive: true });
    mkdirSync(join(profileHome, "mcp-tokens"), { recursive: true });
    mkdirSync(join(profileHome, "pairing"), { recursive: true });
    writeFileSync(join(profileHome, "people", "employees.private.json"), "{\"privateEmployeeDirectory\":true}\n");
    writeFileSync(join(profileHome, "mcp-tokens", "googledrive.json"), "{\"token\":\"private\"}\n");
    writeFileSync(join(profileHome, "pairing", "telegram.json"), "{\"pairing\":\"private\"}\n");

    const apply = runSync(...arguments_, "--apply");
    assert.equal(apply.status, 0, apply.stderr);
    assert.equal(readFileSync(join(profileHome, "SOUL.md"), "utf8").includes("# Manager"), true);
    const renderedConfig = readFileSync(join(profileHome, "config.yaml"), "utf8");
    assert.equal(renderedConfig.includes(JSON.stringify(workspaceRoot)), true);
    assert.deepEqual(telegramToolsets(renderedConfig), ["file", "skills", "mcp-googledrive"]);
    assert.match(renderedConfig, /plugins:\n  enabled:\n    - notion-platform/);
    assert.match(renderedConfig, /notion:\n    - skills\n    - notion_connector/);
    assert.match(renderedConfig, /gateway:\n  platforms:\n    notion:\n      enabled: true/);
    assert.match(renderedConfig, /memory:\n  memory_enabled: true\n  user_profile_enabled: true/);
    assert.match(renderedConfig, /model:\n  default: z-ai\/glm-5\.2\n  provider: openrouter/);
    assert.match(renderedConfig, /skills:\n  disabled:/);
    for (const builtinSkill of ["codex", "google-workspace", "notion", "powerpoint", "xlsx"]) {
      assert.match(renderedConfig, new RegExp(`\\n    - ${builtinSkill}\\n`));
    }
    for (const howieSkill of ["company-ops-manager", "meeting-intake", "drive-company-files", "company-directory", ...artifactSkillNames]) {
      assert.doesNotMatch(renderedConfig, new RegExp(`\\n    - ${howieSkill}\\n`));
    }
    assert.match(renderedConfig, /mcp_servers:\n  googledrive:\n    url: "https:\/\/drivemcp\.googleapis\.com\/mcp\/v1"\n    auth: oauth\n    oauth:\n      # Values resolve from the excluded private profile \.env\.\n      client_id: "\$\{GOOGLE_DRIVE_MCP_CLIENT_ID\}"\n      client_secret: "\$\{GOOGLE_DRIVE_MCP_CLIENT_SECRET\}"\n      redirect_host: localhost\n    tools:\n      include:\n        - search_files\n        - read_file_content\n        - get_file_metadata\n        - create_file\n      resources: false\n      prompts: false/);
    assert.equal(existsSync(join(profileHome, "skills/company-ops-manager/SKILL.md")), true);
    assert.equal(existsSync(join(profileHome, "skills/drive-company-files/SKILL.md")), true);
    assert.equal(existsSync(join(profileHome, "skills/company-directory/SKILL.md")), true);
    assert.equal(existsSync(join(profileHome, "skills/compliance-report/SKILL.md")), true);
    assert.equal(existsSync(join(profileHome, "skills/compliance-report/templates/compliance-report.md")), true);
    assert.equal(existsSync(join(profileHome, "skills/customer-research/templates/customer-research-brief.md")), true);
    assert.equal(existsSync(join(profileHome, "skills/production-performance-report/templates/production-performance-report.md")), true);
    assert.equal(existsSync(join(profileHome, "plugins/platforms/notion/plugin.yaml")), true);
    assert.equal(existsSync(join(profileHome, "plugins/platforms/notion/adapter.py")), true);
    assert.equal(existsSync(join(profileHome, "plugins/platforms/notion/__pycache__")), false);
    assert.equal(readFileSync(join(workspaceRoot, ".hermes.md"), "utf8").includes("Reply intake"), true);
    assert.equal(readFileSync(join(profileHome, ".env"), "utf8"), "EXAMPLE_SECRET=must-stay-private\n");
    assert.equal(readFileSync(join(profileHome, "contacts.json"), "utf8"), "{\"private\":true}\n");
    assert.equal(readFileSync(join(profileHome, "auth.json"), "utf8"), "{\"token\":\"private\"}\n");
    assert.equal(readFileSync(join(profileHome, "sessions", "existing.json"), "utf8"), "{\"session\":true}\n");
    assert.equal(readFileSync(join(profileHome, "people", "employees.private.json"), "utf8"), "{\"privateEmployeeDirectory\":true}\n");
    assert.equal(readFileSync(join(profileHome, "mcp-tokens", "googledrive.json"), "utf8"), "{\"token\":\"private\"}\n");
    assert.equal(readFileSync(join(profileHome, "pairing", "telegram.json"), "utf8"), "{\"pairing\":\"private\"}\n");
    assert.equal(existsSync(join(profileHome, "private-roster.example.json")), false);
    assert.equal(existsSync(join(profileHome, "private-runtime.example.env")), false);
    assert.equal(existsSync(join(profileHome, "schedule-policy.md")), false);

    const cleanCheck = runSync(...arguments_, "--dry-run");
    assert.equal(cleanCheck.status, 0, cleanCheck.stderr);
    assert.match(cleanCheck.stdout, /Check passed/);

    writeFileSync(join(profileHome, "config.yaml"), "changed: true\n");
    const driftCheck = runSync(...arguments_);
    assert.equal(driftCheck.status, 1);
    assert.match(driftCheck.stdout, /CHANGED config\.yaml/);

    const repair = runSync(...arguments_, "--apply");
    assert.equal(repair.status, 0, repair.stderr);
    assert.equal(readFileSync(join(profileHome, "config.yaml"), "utf8").includes("changed: true"), false);
  } finally {
    rmSync(temporaryRoot, { recursive: true, force: true });
  }
});

test("source-owned native skill packages declare bounded retrieval, directory, and compliance contracts", () => {
  const manifest = JSON.parse(readFileSync(join(sourceProfile, "profile.manifest.json"), "utf8"));
  const packages = new Map(manifest.nativeSkillPackages.map((entry) => [entry.name, entry.template]));
  const driveSkill = readFileSync(join(sourceProfile, "skills/drive-company-files/SKILL.md"), "utf8");
  const directorySkill = readFileSync(join(sourceProfile, "skills/company-directory/SKILL.md"), "utf8");
  const complianceSkill = readFileSync(join(sourceProfile, "skills/compliance-report/SKILL.md"), "utf8");
  const complianceTemplate = readFileSync(join(sourceProfile, "skills/compliance-report/templates/compliance-report.md"), "utf8");
  const managerSkill = readFileSync(join(sourceProfile, "skills/company-ops-manager/SKILL.md"), "utf8");
  const meetingIntake = readFileSync(join(sourceProfile, "skills/meeting-intake/SKILL.md"), "utf8");
  const geoSkill = readFileSync(join(sourceProfile, "skills/geo-report/SKILL.md"), "utf8");
  const geoTemplate = readFileSync(join(sourceProfile, "skills/geo-report/templates/geo-report.md"), "utf8");
  const workspaceContext = readFileSync(join(sourceProfile, "workspace-context.hermes.md"), "utf8");

  assert.equal(packages.size, 20);
  assert.equal(packages.get("drive-company-files"), null);
  assert.equal(packages.get("company-directory"), null);
  assert.equal(packages.get("compliance-report"), "templates/compliance-report.md");
  assert.deepEqual(manifest.privateRuntime.driveFixture, {
    manifestPath: "drive/fixture-manifest.private.json",
    manifestEnvironmentVariable: "HOWIE_DRIVE_FIXTURE_MANIFEST",
    approvedRootIdEnvironmentVariable: "HOWIE_DRIVE_FIXTURE_ROOT_ID",
    sourceSync: "excluded",
    repositoryRuntimeData: "ignored"
  });
  assert.match(driveSkill, /requires_toolsets:\n      - mcp-googledrive/);
  assert.match(driveSkill, /search_files`, `read_file_content`, `get_file_metadata`, and `create_file`/);
  assert.match(driveSkill, /fixture-manifest\.private\.json/);
  assert.match(driveSkill, /HOWIE_DRIVE_FIXTURE_ROOT_ID/);
  assert.match(driveSkill, /"fixture_kind": "company-pilot-data"/);
  assert.match(driveSkill, /never update an existing file/i);
  assert.doesNotMatch(driveSkill, /requires_toolsets:\n      - file/);
  assert.match(directorySkill, /people\/employees\.private\.json/);
  assert.match(directorySkill, /Never include `telegram_target`/);
  assert.match(directorySkill, /safe projection/i);
  assert.match(complianceSkill, /verified source\s+references/i);
  assert.match(complianceSkill, /named compliance reviewer/i);
  assert.match(complianceSkill, /not legal advice/i);
  assert.match(complianceTemplate, /\| ID \| Obligation or control \| Observation \| Evidence citation \| Owner \| Due date \| Status \| Reviewer disposition \|/);
  assert.match(managerSkill, /`company-directory`/);
  assert.match(managerSkill, /`drive-company-files`/);
  assert.match(managerSkill, /`compliance-report`/);
  assert.match(managerSkill, /JSON-valued YAML front matter/);
  assert.match(managerSkill, /mock_skill_dependencies/);
  assert.match(managerSkill, /"question":"The scoped question"/);
  assert.match(meetingIntake, /`company-directory`/);
  assert.match(meetingIntake, /`drive-company-files`/);
  assert.match(meetingIntake, /`compliance-report`/);
  assert.match(geoSkill, /Do not infer a deposit type, mineralogy, resource confidence category/i);
  assert.match(geoSkill, /source path, source date, and every numerical claim/i);
  assert.match(geoTemplate, /do not infer deposit type, mineralogy,[\s\S]*classification, recovery, or economics/i);
  for (const name of artifactSkillNames) {
    assert.equal(typeof packages.get(name), "string", `${name} is a registered artifact skill`);
    assert.equal(existsSync(join(sourceProfile, "skills", name, "SKILL.md")), true);
    assert.equal(existsSync(join(sourceProfile, "skills", name, packages.get(name))), true);
  }
  assert.deepEqual(manifest.sync.workspaceContext, {
    source: "workspace-context.hermes.md",
    target: ".hermes.md",
    kind: "file"
  });
  assert.match(workspaceContext, /ticket\.md.*current source of truth/s);
  assert.match(workspaceContext, /human_reply_received/);
  assert.match(workspaceContext, /weekday hourly pulse/);
});

test("profile private examples document the canonical excluded employee directory without real values", () => {
  const manifest = JSON.parse(readFileSync(join(sourceProfile, "profile.manifest.json"), "utf8"));
  const employeeDirectory = JSON.parse(readFileSync(join(sourceProfile, "private-roster.example.json"), "utf8"));
  const privateRuntime = readFileSync(join(sourceProfile, "private-runtime.example.env"), "utf8");

  assert.equal(manifest.privateRuntime.employeeDirectory.path, "people/employees.private.json");
  assert.equal(manifest.privateRuntime.employeeDirectory.sourceSync, "excluded");
  assert.equal(manifest.privateRuntime.employeeDirectory.repositoryRuntimeData, "ignored");
  assert.equal(manifest.sync.runtimeExcluded.includes("people/employees.private.json"), true);
  assert.equal(manifest.sync.sourceOwned.some((entry) => entry.source === "private-roster.example.json"), false);
  assert.equal(employeeDirectory.schema_version, 1);
  assert.equal(employeeDirectory.example_only, true);
  assert.deepEqual(Object.keys(employeeDirectory.employees[0]).sort(), [
    "accountable_for",
    "allowed_mock_drive_scopes",
    "display_name",
    "global_cooldown_minutes",
    "id",
    "inbound_allowed",
    "outbound_allowed",
    "requirement_cooldown_minutes",
    "role",
    "route_enabled",
    "telegram_target",
    "test_opt_in",
    "timezone"
  ]);
  assert.match(employeeDirectory.employees[0].telegram_target, /^100000/);
  assert.match(privateRuntime, /^TELEGRAM_BOT_TOKEN=<private-bot-token>$/m);
  assert.match(privateRuntime, /^TELEGRAM_ALLOWED_USERS=<exactly-one-private-operator-user-id>$/m);
  assert.match(privateRuntime, /^TELEGRAM_HOME_CHANNEL=<exactly-one-private-operator-chat-id>$/m);
  assert.match(privateRuntime, /^GOOGLE_DRIVE_MCP_CLIENT_ID=<private-pre-registered-oauth-client-id>$/m);
  assert.match(privateRuntime, /^GOOGLE_DRIVE_MCP_CLIENT_SECRET=<private-pre-registered-oauth-client-secret>$/m);
  assert.match(privateRuntime, /^HOWIE_DRIVE_FIXTURE_MANIFEST=drive\/fixture-manifest\.private\.json$/m);
  assert.match(privateRuntime, /^HOWIE_DRIVE_FIXTURE_ROOT_ID=<private-fake-drive-root-id>$/m);
  assert.match(privateRuntime, /^HOWIE_EMPLOYEE_DIRECTORY=people\/employees\.private\.json$/m);
});

test("sync refuses an apply command that combines check and apply modes", () => {
  const temporaryRoot = mkdtempSync(join(tmpdir(), "howie-ai-profile-sync-"));
  try {
    const result = runSync(
      "--target", join(temporaryRoot, "profile"),
      "--workspace-root", join(temporaryRoot, "ops-workspace"),
      "--check",
      "--apply"
    );
    assert.equal(result.status, 1);
    assert.match(result.stderr, /cannot be combined/);
  } finally {
    rmSync(temporaryRoot, { recursive: true, force: true });
  }
});
