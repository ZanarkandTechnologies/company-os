#!/usr/bin/env node

import {
  chmodSync,
  cpSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  renameSync,
  writeFileSync
} from "node:fs";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const sourceRoot = resolve(projectRoot, "fixtures/company-manager");

function usage() {
  return "Usage: node scripts/prepare-howie-live-workspace.mjs --workspace <absolute-directory> [--apply]";
}

function parseArguments(args) {
  let workspace;
  let apply = false;
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === "--apply") {
      apply = true;
      continue;
    }
    if (argument !== "--workspace") throw new Error(`unknown argument: ${argument}`);
    workspace = args[index + 1];
    index += 1;
  }
  if (!workspace || !isAbsolute(workspace)) throw new Error(usage());
  return { workspace: resolve(workspace), apply };
}

function writePrivateFile(path, content) {
  const temporary = join(dirname(path), `.howie-live-${process.pid}-${Date.now()}`);
  writeFileSync(temporary, content, { mode: 0o600 });
  chmodSync(temporary, 0o600);
  renameSync(temporary, path);
  chmodSync(path, 0o600);
}

function writeReadOnlyFile(path, content) {
  writeFileSync(path, content, { mode: 0o644 });
}

function meetingSummary() {
  return `# Aurora Lithium weekly operating review — fictional\n\nThis is synthetic acceptance data for the Howie AI demo.\n\n## CEO decisions and commitments\n\n1. **Geology — TASK-2001.** Prepare a review-ready Aurora Basin geology review by 19 August. The approved fictional source facts are available in the dedicated Howie Drive fixture. Avery owns the work; Rohan reviews it.\n2. **Finance — TASK-2002.** Build a fictional 13-week cash forecast by 20 August after Mina confirms the pricing case. Rohan reviews it.\n3. **Operations — TASK-2003.** Prepare a fictional operating-risk brief by 20 August after Rohan chooses the risk to prioritise. Avery reviews it.\n4. **Executive operations — TASK-2004.** Assemble the weekly operating pack by 22 August after the approved geology review and cash forecast exist. Rohan reviews it.\n\n## Manager instruction\n\nCreate the four canonical tickets. Start every task with all inputs available now. For every blocked person-specific input, record the role, question, next follow-up time and a draft delivery event. Do not claim a message was sent unless a delivery receipt exists.\n`;
}

function safeDirectory() {
  return `# Synthetic Howie AI directory\n\n- Avery Chen — Geology Lead — accountable for fictional geology inputs — Australia/Perth\n- Mina Patel — Finance Lead — accountable for fictional pricing assumptions — Asia/Singapore\n- Rohan Davis — Operations Lead — accountable for fictional operating risks and reviews — Asia/Kuala_Lumpur\n`;
}

function readMeetingEnvelope() {
  const source = resolve(sourceRoot, "meetings/aurora-lithium-weekly-input.json");
  return readFileSync(source, "utf8");
}

function readPrivateDirectory() {
  const source = resolve(sourceRoot, "people/aurora-lithium.employees.private.example.json");
  const parsed = JSON.parse(readFileSync(source, "utf8"));
  parsed.employees = parsed.employees.map((employee) => ({
    ...employee,
    role: employee.id === "avery-geology" ? "Geology Lead" : employee.id === "mina-finance" ? "Finance Lead" : "Operations Lead",
    accountable_for: employee.id === "avery-geology"
      ? "fictional geology inputs"
      : employee.id === "mina-finance"
        ? "fictional pricing assumptions"
        : "fictional operating risks and reviews"
  }));
  return `${JSON.stringify(parsed, null, 2)}\n`;
}

function main() {
  const { workspace, apply } = parseArguments(process.argv.slice(2));
  const existing = existsSync(workspace);
  if (existing) {
    const stat = lstatSync(workspace);
    if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error("workspace must be a real directory");
  }
  const targetPaths = [
    "inbox/meeting-summary.md",
    "inbox/weekly-meeting.private.json",
    "company-directory.md",
    "people/employees.private.json",
    "drive/",
    "shared-drive/geo-source.json",
    "tickets/",
    "tickets/archive/",
    "reports/"
  ];
  if (!apply) {
    console.log(`CHECK prepared synthetic live workspace paths: ${targetPaths.join(", ")}`);
    return;
  }
  for (const directory of ["inbox", "people", "drive", "tickets", "tickets/archive", "reports"]) {
    mkdirSync(join(workspace, directory), { recursive: true });
  }
  // This is the deterministic local stand-in while the real remote Drive MCP
  // fixture is awaiting service access. It is deliberately copied before the
  // agent starts, then treated as read-only input by the profile.
  cpSync(resolve(sourceRoot, "shared-drive"), join(workspace, "shared-drive"), {
    recursive: true,
    force: true,
    errorOnExist: false
  });
  writeReadOnlyFile(join(workspace, "inbox/meeting-summary.md"), meetingSummary());
  writePrivateFile(join(workspace, "inbox/weekly-meeting.private.json"), readMeetingEnvelope());
  writeReadOnlyFile(join(workspace, "company-directory.md"), safeDirectory());
  writePrivateFile(join(workspace, "people/employees.private.json"), readPrivateDirectory());
  writePrivateFile(join(workspace, "drive/fixture-manifest.private.json"), `${JSON.stringify({
    schema_version: 1,
    fixture_kind: "fake-company-data",
    approved_root_id: null,
    approved_root_label: "Aurora Lithium fake-data root (pending real Drive seed)",
    allowed_fixture_titles: []
  }, null, 2)}\n`);
  writeReadOnlyFile(join(workspace, "README.md"), `# Howie AI live acceptance workspace\n\nSynthetic company data only. The Drive fixture manifest and employee directory are private runtime state. Hermes may read meeting inputs and native skills, then write only canonical ticket folders.\n`);
  console.log("APPLIED synthetic Howie live workspace; no Drive, Telegram, or model call was made.");
}

try {
  main();
} catch (error) {
  console.error(`Howie live workspace error: ${error.message}`);
  process.exitCode = 1;
}
