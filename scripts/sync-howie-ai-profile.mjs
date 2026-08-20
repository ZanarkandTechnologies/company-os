#!/usr/bin/env node

import {
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  writeFileSync
} from "node:fs";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const sourceProfile = resolve(projectRoot, "profiles/howie-ai");
const manifestPath = resolve(sourceProfile, "profile.manifest.json");

const expectedManifestEntries = [
  { source: "SOUL.md", target: "SOUL.md", kind: "file" },
  { source: "config.template.yaml", target: "config.yaml", kind: "template" },
  { source: "skills", target: "skills", kind: "directory" },
  { source: "plugins", target: "plugins", kind: "directory" }
];

const expectedWorkspaceContext = {
  source: "workspace-context.hermes.md",
  target: ".hermes.md",
  kind: "file"
};

const requiredRuntimeExclusions = [
  ".env",
  "auth.json",
  "credentials/**",
  "mcp-tokens/**",
  "oauth/**",
  "pairing/**",
  "drive/fixture-manifest.private.json",
  "people/employees.private.json",
  "sessions/**",
  "gateway*"
];

const requiredEmployeeFields = [
  "id",
  "display_name",
  "role",
  "accountable_for",
  "telegram_target",
  "inbound_allowed",
  "outbound_allowed",
  "test_opt_in",
  "route_enabled",
  "timezone",
  "global_cooldown_minutes",
  "requirement_cooldown_minutes",
  "allowed_mock_drive_scopes"
];

const expectedNativeSkillPackages = [
  { name: "company-ops-manager", template: null },
  { name: "meeting-intake", template: null },
  { name: "drive-company-files", template: null },
  { name: "company-directory", template: null },
  { name: "geo-report", template: "templates/geo-report.md" },
  { name: "fundraising-deck", template: "templates/fundraising-deck.md" },
  { name: "financial-model", template: "templates/financial-model.md" },
  { name: "compliance-report", template: "templates/compliance-report.md" },
  { name: "weekly-operating-report", template: "templates/weekly-operating-report.md" },
  { name: "cash-flow-forecast", template: "templates/cash-flow-forecast.md" },
  { name: "budget-variance-report", template: "templates/budget-variance-report.md" },
  { name: "customer-research", template: "templates/customer-research-brief.md" },
  { name: "outreach-campaign", template: "templates/outreach-campaign.md" },
  { name: "deal-memo", template: "templates/deal-memo.md" },
  { name: "commercial-proposal", template: "templates/commercial-proposal.md" },
  { name: "ads-campaign", template: "templates/ads-campaign-brief.md" },
  { name: "contractor-procurement-pack", template: "templates/contractor-procurement-pack.md" },
  { name: "operating-risk-brief", template: "templates/operating-risk-brief.md" },
  { name: "exploration-program", template: "templates/exploration-program.md" },
  { name: "production-performance-report", template: "templates/production-performance-report.md" }
];

function usage() {
  return [
    "Usage:",
    "  node scripts/sync-howie-ai-profile.mjs --target <absolute-profile-home> --workspace-root <absolute-ops-workspace> [--check|--dry-run]",
    "  node scripts/sync-howie-ai-profile.mjs --target <absolute-profile-home> --workspace-root <absolute-ops-workspace> --apply",
    "",
    "The default is --check. --apply writes only SOUL.md, rendered config.yaml, source-owned skills/, source-owned plugins/, and the workspace .hermes.md. Private runtime data is excluded."
  ].join("\n");
}

function fail(message) {
  console.error(`Howie profile sync error: ${message}`);
  process.exitCode = 1;
}

function parseArguments(args) {
  let target;
  let workspaceRoot;
  let mode;

  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === "--help" || argument === "-h") {
      console.log(usage());
      process.exit(0);
    }
    if (argument === "--target" || argument === "--workspace-root") {
      const value = args[index + 1];
      if (!value || value.startsWith("--")) throw new Error(`${argument} requires a path.`);
      if (argument === "--target") target = value;
      else workspaceRoot = value;
      index += 1;
      continue;
    }
    if (argument === "--check" || argument === "--dry-run") {
      if (mode && mode !== "check") throw new Error("--apply cannot be combined with --check or --dry-run.");
      mode = "check";
      continue;
    }
    if (argument === "--apply") {
      if (mode && mode !== "apply") throw new Error("--apply cannot be combined with --check or --dry-run.");
      mode = "apply";
      continue;
    }
    throw new Error(`unknown argument: ${argument}`);
  }

  if (!target || !workspaceRoot) throw new Error("--target and --workspace-root are required.\n\n" + usage());
  if (!isAbsolute(target) || !isAbsolute(workspaceRoot)) {
    throw new Error("--target and --workspace-root must be absolute paths.");
  }

  return { mode: mode ?? "check", target: resolve(target), workspaceRoot: resolve(workspaceRoot) };
}

function readRegularFile(path) {
  const stat = lstatSync(path);
  if (!stat.isFile() || stat.isSymbolicLink()) throw new Error(`source file must be a regular file: ${path}`);
  return readFileSync(path);
}

function assertManifest() {
  let manifest;
  try {
    manifest = JSON.parse(readRegularFile(manifestPath));
  } catch (error) {
    throw new Error(`could not read ${manifestPath}: ${error.message}`);
  }

  if (manifest.schemaVersion !== 1 || manifest.profile?.name !== "howie-ai") {
    throw new Error("profile manifest must identify howie-ai with schemaVersion 1.");
  }
  const entries = manifest.sync?.sourceOwned;
  if (!Array.isArray(entries) || JSON.stringify(entries) !== JSON.stringify(expectedManifestEntries)) {
    throw new Error("profile manifest must declare exactly the reviewed source-owned sync entries.");
  }
  if (JSON.stringify(manifest.sync?.workspaceContext) !== JSON.stringify(expectedWorkspaceContext)) {
    throw new Error("profile manifest must declare the reviewed source-owned workspace context file.");
  }
  const runtimeExcluded = manifest.sync?.runtimeExcluded;
  if (!Array.isArray(runtimeExcluded) || !requiredRuntimeExclusions.every((path) => runtimeExcluded.includes(path))) {
    throw new Error("profile manifest must exclude private credentials, pairing/session data, and the employee directory from source sync.");
  }
  const employeeDirectory = manifest.privateRuntime?.employeeDirectory;
  if (manifest.privateRuntime?.environmentExample !== "private-runtime.example.env"
    || employeeDirectory?.path !== "people/employees.private.json"
    || employeeDirectory?.example !== "private-roster.example.json"
    || employeeDirectory?.sourceSync !== "excluded"
    || employeeDirectory?.repositoryRuntimeData !== "ignored") {
    throw new Error("profile manifest must document the excluded private runtime environment and employee directory.");
  }
  const driveFixture = manifest.privateRuntime?.driveFixture;
  if (driveFixture?.manifestPath !== "drive/fixture-manifest.private.json"
    || driveFixture?.manifestEnvironmentVariable !== "HOWIE_DRIVE_FIXTURE_MANIFEST"
    || driveFixture?.approvedRootIdEnvironmentVariable !== "HOWIE_DRIVE_FIXTURE_ROOT_ID"
    || driveFixture?.sourceSync !== "excluded"
    || driveFixture?.repositoryRuntimeData !== "ignored") {
    throw new Error("profile manifest must document the excluded private Drive fixture manifest and approved root ID.");
  }
  if (!Array.isArray(manifest.nativeSkillPackages)
    || JSON.stringify(manifest.nativeSkillPackages) !== JSON.stringify(expectedNativeSkillPackages)) {
    throw new Error("profile manifest must declare exactly the reviewed native skill packages and owned templates.");
  }
}

function assertNativeSkillPackages() {
  readRegularFile(resolve(sourceProfile, expectedWorkspaceContext.source));
  for (const skill of expectedNativeSkillPackages) {
    const packageRoot = resolve(sourceProfile, "skills", skill.name);
    const skillPath = resolve(packageRoot, "SKILL.md");
    const source = readRegularFile(skillPath).toString("utf8");
    if (!source.startsWith("---\n") || !source.includes(`name: ${skill.name}\n`)) {
      throw new Error(`native skill package must declare its own name: ${skillPath}`);
    }
    if (skill.template) readRegularFile(resolve(packageRoot, skill.template));
  }
}

function assertPrivateExamples() {
  let employeeDirectory;
  try {
    employeeDirectory = JSON.parse(readRegularFile(resolve(sourceProfile, "private-roster.example.json")));
  } catch (error) {
    throw new Error(`could not read the private employee-directory example: ${error.message}`);
  }
  if (employeeDirectory.schema_version !== 1 || employeeDirectory.example_only !== true
    || employeeDirectory.runtime_path !== "people/employees.private.json"
    || !Array.isArray(employeeDirectory.employees) || employeeDirectory.employees.length !== 1) {
    throw new Error("private employee-directory example must define one schema_version 1 example at people/employees.private.json.");
  }
  const employee = employeeDirectory.employees[0];
  if (!employee || typeof employee !== "object" || !requiredEmployeeFields.every((field) => Object.hasOwn(employee, field))
    || typeof employee.id !== "string" || typeof employee.display_name !== "string"
    || typeof employee.role !== "string" || typeof employee.accountable_for !== "string"
    || typeof employee.telegram_target !== "string" || !/^-?\d{5,20}$/.test(employee.telegram_target)
    || typeof employee.inbound_allowed !== "boolean" || typeof employee.outbound_allowed !== "boolean"
    || typeof employee.test_opt_in !== "boolean" || typeof employee.route_enabled !== "boolean"
    || typeof employee.timezone !== "string"
    || !Number.isInteger(employee.global_cooldown_minutes) || employee.global_cooldown_minutes < 0
    || !Number.isInteger(employee.requirement_cooldown_minutes) || employee.requirement_cooldown_minutes < 0
    || !Array.isArray(employee.allowed_mock_drive_scopes)) {
    throw new Error("private employee-directory example must define the reviewed employee route and cooldown fields.");
  }

  const runtimeExample = readRegularFile(resolve(sourceProfile, "private-runtime.example.env")).toString("utf8");
  const expectedEntries = [
    "TELEGRAM_BOT_TOKEN=<private-bot-token>",
    "TELEGRAM_ALLOWED_USERS=<exactly-one-private-operator-user-id>",
    "TELEGRAM_HOME_CHANNEL=<exactly-one-private-operator-chat-id>",
    "GOOGLE_DRIVE_MCP_CLIENT_ID=<private-pre-registered-oauth-client-id>",
    "GOOGLE_DRIVE_MCP_CLIENT_SECRET=<private-pre-registered-oauth-client-secret>",
    "HOWIE_DRIVE_FIXTURE_MANIFEST=drive/fixture-manifest.private.json",
    "HOWIE_DRIVE_FIXTURE_ROOT_ID=<private-fake-drive-root-id>",
    "HOWIE_EMPLOYEE_DIRECTORY=people/employees.private.json",
    "NOTION_TOKEN=<private-integration-token>",
    "NOTION_WEBHOOK_PUBLIC_URL=<public-https-url-ending-in-notion-webhook>",
    "NOTION_ALLOW_ALL_WORKSPACES=true",
    "NOTION_ENABLE_WRITES=false",
    "NOTION_API_VERSION=2025-09-03"
  ];
  if (!expectedEntries.every((entry) => runtimeExample.includes(entry))) {
    throw new Error("private runtime example must name the reviewed Telegram, Drive OAuth, and employee-directory settings without real values.");
  }
}

function assertRelativePath(path) {
  const normalized = path.replaceAll("\\", "/");
  if (!normalized || normalized.startsWith("/") || normalized.split("/").some((part) => part === "" || part === "." || part === "..")) {
    throw new Error(`unsafe source path: ${path}`);
  }
  return normalized;
}

function listDirectoryFiles(directory, prefix = "") {
  const stat = lstatSync(directory);
  if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error(`source directory must be a real directory: ${directory}`);

  const files = new Map();
  for (const entry of readdirSync(directory, { withFileTypes: true }).sort((left, right) => left.name.localeCompare(right.name))) {
    if (entry.name === "__pycache__" || entry.name.endsWith(".pyc") || entry.name.endsWith(".pyo")) continue;
    const relativePath = assertRelativePath(prefix ? `${prefix}/${entry.name}` : entry.name);
    const sourcePath = join(directory, entry.name);
    const sourceStat = lstatSync(sourcePath);
    if (sourceStat.isSymbolicLink()) throw new Error(`symbolic links are not permitted in source skills: ${sourcePath}`);
    if (sourceStat.isDirectory()) {
      for (const [childPath, content] of listDirectoryFiles(sourcePath, relativePath)) files.set(childPath, content);
    } else if (sourceStat.isFile()) {
      files.set(relativePath, readFileSync(sourcePath));
    } else {
      throw new Error(`unsupported source entry: ${sourcePath}`);
    }
  }
  return files;
}

function renderConfig(workspaceRoot) {
  const template = readRegularFile(resolve(sourceProfile, "config.template.yaml")).toString("utf8");
  const token = "{{WORKSPACE_ROOT_YAML}}";
  const tokenCount = template.split(token).length - 1;
  if (tokenCount !== 1) throw new Error(`config template must contain ${token} exactly once.`);
  return Buffer.from(template.replace(token, JSON.stringify(workspaceRoot)), "utf8");
}

function expectedFiles(workspaceRoot) {
  const files = new Map([
    ["SOUL.md", readRegularFile(resolve(sourceProfile, "SOUL.md"))],
    ["config.yaml", renderConfig(workspaceRoot)]
  ]);
  for (const [relativePath, content] of listDirectoryFiles(resolve(sourceProfile, "skills"))) {
    files.set(`skills/${relativePath}`, content);
  }
  for (const [relativePath, content] of listDirectoryFiles(resolve(sourceProfile, "plugins"))) {
    files.set(`plugins/${relativePath}`, content);
  }
  return files;
}

function assertTargetIsSafe(target) {
  if (target === projectRoot || target === sourceProfile || target.startsWith(`${sourceProfile}${sep}`)) {
    throw new Error("--target must not be the repository or source profile directory.");
  }
  if (existsSync(target)) {
    const stat = lstatSync(target);
    if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error(`--target must be a real directory when it exists: ${target}`);
  }
}

function assertWorkspaceIsSafe(workspaceRoot) {
  if (workspaceRoot === projectRoot || workspaceRoot === sourceProfile || workspaceRoot.startsWith(`${sourceProfile}${sep}`)) {
    throw new Error("--workspace-root must not be the repository or source profile directory.");
  }
  if (existsSync(workspaceRoot)) {
    const stat = lstatSync(workspaceRoot);
    if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error(`--workspace-root must be a real directory when it exists: ${workspaceRoot}`);
  }
}

function assertSafeDestinationAncestors(target, destination) {
  const pathInsideTarget = relative(target, destination);
  if (!pathInsideTarget || pathInsideTarget.startsWith("..") || isAbsolute(pathInsideTarget)) {
    throw new Error(`destination escapes target: ${destination}`);
  }
  let current = target;
  for (const segment of pathInsideTarget.split(sep).slice(0, -1)) {
    current = join(current, segment);
    if (!existsSync(current)) continue;
    const stat = lstatSync(current);
    if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error(`destination ancestor is not a real directory: ${current}`);
  }
}

function destinationStatus(target, relativePath, content) {
  const destination = resolve(target, relativePath);
  assertSafeDestinationAncestors(target, destination);
  if (!existsSync(destination)) return { relativePath, destination, content, status: "missing" };
  const stat = lstatSync(destination);
  if (!stat.isFile() || stat.isSymbolicLink()) {
    throw new Error(`destination must be a regular file when it exists: ${destination}`);
  }
  return readFileSync(destination).equals(content)
    ? { relativePath, destination, content, status: "current" }
    : { relativePath, destination, content, status: "changed" };
}

function writeSourceOwnedFile(target, item) {
  const parent = dirname(item.destination);
  mkdirSync(parent, { recursive: true });
  assertSafeDestinationAncestors(target, item.destination);
  const temporaryPath = join(parent, `.${item.relativePath.split(sep).at(-1)}.${process.pid}.tmp`);
  try {
    writeFileSync(temporaryPath, item.content, { mode: 0o600 });
    renameSync(temporaryPath, item.destination);
  } finally {
    if (existsSync(temporaryPath)) rmSync(temporaryPath, { force: true });
  }
}

function main() {
  const options = parseArguments(process.argv.slice(2));
  assertManifest();
  assertNativeSkillPackages();
  assertPrivateExamples();
  assertTargetIsSafe(options.target);
  assertWorkspaceIsSafe(options.workspaceRoot);

  const statuses = [
    ...[...expectedFiles(options.workspaceRoot)]
      .map(([relativePath, content]) => ({ ...destinationStatus(options.target, relativePath, content), ownerRoot: options.target })),
    {
      ...destinationStatus(options.workspaceRoot, expectedWorkspaceContext.target, readRegularFile(resolve(sourceProfile, expectedWorkspaceContext.source))),
      ownerRoot: options.workspaceRoot
    }
  ];
  const changes = statuses.filter((item) => item.status !== "current");

  for (const item of statuses) {
    console.log(`${item.status === "current" ? "OK" : item.status.toUpperCase()} ${item.relativePath}`);
  }

  if (options.mode === "check") {
    if (changes.length) {
      console.error(`Check failed: ${changes.length} source-owned file(s) would change. Re-run with --apply to write only the listed files.`);
      process.exitCode = 1;
    } else {
      console.log("Check passed: howie-ai source-owned files are synchronized.");
    }
    return;
  }

  if (!existsSync(options.target)) mkdirSync(options.target, { recursive: true });
  if (!existsSync(options.workspaceRoot)) mkdirSync(options.workspaceRoot, { recursive: true });
  for (const item of changes) writeSourceOwnedFile(item.ownerRoot, item);
  console.log(`Applied ${changes.length} source-owned profile/workspace file(s). No credentials, employee directory, auth, sessions, memories, cron state, pairing, gateway, or scheduler actions were touched.`);
}

try {
  main();
} catch (error) {
  fail(error.message);
}
