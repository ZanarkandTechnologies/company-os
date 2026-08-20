import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, statSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { tmpdir } from "node:os";
import test from "node:test";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const script = resolve(projectRoot, "scripts/prepare-howie-live-workspace.mjs");

test("live workspace preparation creates only synthetic fixture inputs", () => {
  const root = mkdtempSync(join(tmpdir(), "howie-live-workspace-"));
  const workspace = join(root, "workspace");
  try {
    const check = spawnSync(process.execPath, [script, "--workspace", workspace], { cwd: projectRoot, encoding: "utf8" });
    assert.equal(check.status, 0, check.stderr);
    assert.match(check.stdout, /CHECK prepared synthetic live workspace paths/);
    const apply = spawnSync(process.execPath, [script, "--workspace", workspace, "--apply"], { cwd: projectRoot, encoding: "utf8" });
    assert.equal(apply.status, 0, apply.stderr);
    assert.match(readFileSync(join(workspace, "inbox/meeting-summary.md"), "utf8"), /TASK-2001/);
    assert.match(readFileSync(join(workspace, "company-directory.md"), "utf8"), /Avery Chen/);
    const privateDirectory = JSON.parse(readFileSync(join(workspace, "people/employees.private.json"), "utf8"));
    assert.equal(privateDirectory.fake_data_only, true);
    assert.equal(privateDirectory.employees.length, 3);
    assert.equal(statSync(join(workspace, "people/employees.private.json")).mode & 0o777, 0o600);
    assert.equal(statSync(join(workspace, "inbox/weekly-meeting.private.json")).mode & 0o777, 0o600);
    const driveManifest = JSON.parse(readFileSync(join(workspace, "drive/fixture-manifest.private.json"), "utf8"));
    assert.equal(driveManifest.approved_root_id, null);
    assert.equal(statSync(join(workspace, "drive/fixture-manifest.private.json")).mode & 0o777, 0o600);
    const localDriveSource = JSON.parse(readFileSync(join(workspace, "shared-drive/geo-source.json"), "utf8"));
    assert.equal(localDriveSource.name, "Geo source workbook.xlsx");
    assert.equal(localDriveSource.project, "Aurora Lithium Project");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
