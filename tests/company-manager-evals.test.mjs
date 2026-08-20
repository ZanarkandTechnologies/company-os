import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const runner = resolve(projectRoot, "scripts/run-company-manager-evals.mjs");
const taskFile = resolve(projectRoot, ".farplane/evals/tasks/harness_tasks.json");

function sandbox() {
  return mkdtempSync(resolve(tmpdir(), "howie-company-manager-eval-test-"));
}

function execute(output, ...extra) {
  return spawnSync(process.execPath, [runner, "--output", output, ...extra], {
    cwd: projectRoot,
    encoding: "utf8"
  });
}

const root = sandbox();
try {
  const normalOutput = resolve(root, "normal");
  const normal = execute(normalOutput);
  assert.equal(normal.status, 0, `${normal.stdout}${normal.stderr}`);
  const summary = JSON.parse(readFileSync(resolve(normalOutput, "summary.json"), "utf8"));
  assert.equal(summary.suite, "company-manager");
  assert.equal(summary.overall_verdict, "pass");
  assert.equal(summary.pass, true);
  assert.deepEqual(summary.counts, { pass: 3, gap: 0, error: 0 });
  assert.deepEqual(summary.tasks.map((task) => task.task_id), [
    "company_manager_meeting_parallel_workers",
    "company_manager_stale_drive_expert_chase",
    "company_manager_end_of_week_escalation"
  ]);

  const firstDetail = JSON.parse(readFileSync(resolve(normalOutput, "tasks/company_manager_meeting_parallel_workers.json"), "utf8"));
  assert.equal(firstDetail.verdict, "pass");
  assert.equal(firstDetail.checks.find((item) => item.id === "meeting_creates_four_canonical_tickets").pass, true);
  assert.equal(firstDetail.checks.find((item) => item.id === "timeline_is_derived_from_canonical_tickets").pass, true);
  assert.equal(firstDetail.checks.find((item) => item.id === "eligible_work_has_parallel_worker_dispatch").pass, true);
  assert.equal(firstDetail.trace.some((entry) => entry.kind === "filesystem_setup"), true);
  assert.equal(firstDetail.trace.some((entry) => entry.kind === "meeting_input"), true);
  assert.equal(firstDetail.trace.some((entry) => entry.kind === "worker_dispatch"), true);
  assert.equal(firstDetail.filesystem.final_files.some((file) => file.path.endsWith("tickets/archive/TASK-1001/ticket.md")), true);
  assert.equal(firstDetail.checks.find((item) => item.id === "filesystem_evidence_has_replayable_hashes").pass, true);
  assert.equal(firstDetail.checks.find((item) => item.id === "filesystem_evidence_has_canonical_content_snapshot").pass, true);
  assert.equal(firstDetail.checks.find((item) => item.id === "filesystem_evidence_records_created_and_workflow_deltas").pass, true);
  assert.equal(firstDetail.filesystem.meeting_delta.created.some((file) => file.path === "tickets/TASK-1001/ticket.md"), true);
  assert.equal(firstDetail.filesystem.workflow_delta.modified.some((file) => file.path === "tickets/TASK-1002/ticket.md"), true);
  assert.equal(firstDetail.filesystem.final_files.find((file) => file.path === "tickets/TASK-1002/ticket.md").content_preview.includes("TASK-1002"), true);

  const staleDriveDetail = JSON.parse(readFileSync(resolve(normalOutput, "tasks/company_manager_stale_drive_expert_chase.json"), "utf8"));
  assert.equal(staleDriveDetail.checks.find((item) => item.id === "unavailable_scoped_drive_input_fails_closed").pass, true);
  assert.equal(staleDriveDetail.checks.find((item) => item.id === "missing_input_does_not_unblock_ticket").pass, true);
  assert.equal(staleDriveDetail.checks.find((item) => item.id === "missing_input_creates_bounded_expert_chase").pass, true);
  assert.equal(staleDriveDetail.trace.some((entry) => entry.kind === "expert_chase"), true);
  assert.equal(staleDriveDetail.filesystem.final_files.some((file) => file.path.endsWith("people/employees.private.json")), true);
  assert.equal(staleDriveDetail.filesystem.workflow_delta.deleted.some((file) => file.path === "drive-mock/howie-ai-shared/geo-source.json"), true);

  const escalationDetail = JSON.parse(readFileSync(resolve(normalOutput, "tasks/company_manager_end_of_week_escalation.json"), "utf8"));
  assert.equal(escalationDetail.checks.find((item) => item.id === "repeated_chases_obey_cooldown_policy").pass, true);
  assert.equal(escalationDetail.checks.find((item) => item.id === "end_of_week_blocked_work_records_escalation").pass, true);
  assert.equal(escalationDetail.trace.some((entry) => entry.kind === "escalation"), true);
  assert.equal(escalationDetail.filesystem.workflow_delta.modified.some((file) => file.path === "tickets/TASK-1001/progress.md"), true);

  const reportOutput = resolve(root, "report-only");
  const report = execute(reportOutput, "--allow-gaps");
  assert.equal(report.status, 0, `${report.stdout}${report.stderr}`);
  assert.equal(existsSync(resolve(reportOutput, "summary.json")), true);
} finally {
  rmSync(root, { recursive: true, force: true });
}

const taskRows = JSON.parse(readFileSync(taskFile, "utf8"));
assert.equal(taskRows.length, 3);
assert.equal(taskRows.every((task) => task.context === ""), true);
console.log("✓ Company manager eval runner proves all three local Company Manager operating loops.");
