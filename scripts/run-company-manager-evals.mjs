/**
 * Deterministic proof runner for the Company Manager POC.
 *
 * This is deliberately not an agent or live-service runner. It exercises the
 * file-first simulator in an isolated temporary workspace and writes a
 * Farplane-shaped summary plus one detail JSON file per task. Unsupported
 * requested behavior is reported as a `gap` and makes the normal command fail.
 */
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, unlinkSync, writeFileSync, mkdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { tmpdir } from "node:os";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  inspectBoard,
  publishArtifact,
  recordHumanResponse,
  recordReply,
  reviewArtifact,
  runPulse,
  seedDemo
} from "./company-manager.mjs";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const defaultTaskFile = resolve(projectRoot, ".farplane/evals/tasks/harness_tasks.json");

function parseArgs(argv) {
  const args = { allowGaps: false, taskFile: defaultTaskFile };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--allow-gaps") {
      args.allowGaps = true;
      continue;
    }
    if (argument === "--task-file" || argument === "--output") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) throw new Error(`${argument} requires a path.`);
      args[argument === "--task-file" ? "taskFile" : "output"] = resolve(projectRoot, value);
      index += 1;
      continue;
    }
    if (argument === "--help") {
      console.log("Usage: node scripts/run-company-manager-evals.mjs [--task-file path] [--output path] [--allow-gaps]");
      process.exit(0);
    }
    throw new Error(`Unknown argument: ${argument}`);
  }
  return args;
}

function readTasks(taskFile) {
  const parsed = JSON.parse(readFileSync(taskFile, "utf8"));
  if (!Array.isArray(parsed) || parsed.length === 0) throw new Error(`${taskFile} must contain a non-empty task list.`);
  for (const task of parsed) {
    if (!task || typeof task !== "object") throw new Error(`${taskFile} task rows must be objects.`);
    if (typeof task.id !== "string" || !task.id) throw new Error(`${taskFile} task rows require an id.`);
    if (typeof task.title !== "string" || !task.title) throw new Error(`${task.id} requires a title.`);
    if (typeof task.query !== "string" || !task.query) throw new Error(`${task.id} requires a query.`);
    if (!Array.isArray(task.reference_points) || task.reference_points.length === 0) {
      throw new Error(`${task.id} requires non-empty reference_points.`);
    }
    if (!Array.isArray(task.files) || task.files.some((file) => typeof file !== "string" || !file)) {
      throw new Error(`${task.id} files must be non-empty strings.`);
    }
    for (const file of task.files) {
      const absolute = resolve(projectRoot, file);
      if (!absolute.startsWith(`${projectRoot}/`) || !existsSync(absolute)) {
        throw new Error(`${task.id} names a missing or unsafe fixture file: ${file}`);
      }
    }
  }
  return parsed;
}

function check(id, pass, expected, observed) {
  return { id, pass, expected, observed };
}

function sandbox() {
  return mkdtempSync(resolve(tmpdir(), "howie-company-manager-eval-"));
}

function progressText(workspaceRoot, ticketId) {
  return readFileSync(resolve(workspaceRoot, "tickets", ticketId, "progress.md"), "utf8");
}

function workspaceFiles(workspaceRoot) {
  const files = [];
  function visit(directory) {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) visit(path);
      else if (entry.isFile()) {
        const relativePath = relative(workspaceRoot, path).replaceAll("\\", "/");
        const contents = readFileSync(path);
        const file = {
          path: relativePath,
          bytes: statSync(path).size,
          sha256: createHash("sha256").update(contents).digest("hex")
        };
        if (/^tickets\/(?:archive\/)?TASK-\d+\/(?:ticket|progress)\.md$/.test(relativePath)
          || /^tickets\/(?:archive\/)?TASK-\d+\/artifacts\/[^/]+\.(?:md|json)$/.test(relativePath)
          || /^reports\/[^/]+\.md$/.test(relativePath)) {
          const content = contents.toString("utf8");
          file.content_preview = content.length > 4_000
            ? `${content.slice(0, 4_000)}\n… [truncated]`
            : content;
        }
        files.push(file);
      }
    }
  }
  if (existsSync(workspaceRoot)) visit(workspaceRoot);
  return files.sort((left, right) => left.path.localeCompare(right.path));
}

function filesystemDelta(before, after) {
  const beforeByPath = new Map(before.map((file) => [file.path, file]));
  const afterByPath = new Map(after.map((file) => [file.path, file]));
  return {
    created: after.filter((file) => !beforeByPath.has(file.path)),
    modified: after
      .filter((file) => beforeByPath.has(file.path) && beforeByPath.get(file.path).sha256 !== file.sha256)
      .map((file) => ({
        ...file,
        previous_bytes: beforeByPath.get(file.path).bytes,
        previous_sha256: beforeByPath.get(file.path).sha256
      })),
    deleted: before.filter((file) => !afterByPath.has(file.path))
  };
}

function filesystemEvidence(beforeMeeting, afterMeeting, finalFiles) {
  return {
    meeting_delta: filesystemDelta(beforeMeeting, afterMeeting),
    workflow_delta: filesystemDelta(afterMeeting, finalFiles),
    final_files: finalFiles
  };
}

function filesystemProofChecks(filesystem) {
  const finalFiles = filesystem.final_files ?? [];
  const meetingCreated = filesystem.meeting_delta?.created ?? [];
  const workflowDelta = filesystem.workflow_delta ?? { created: [], modified: [], deleted: [] };
  return [
    check(
      "filesystem_evidence_has_replayable_hashes",
      finalFiles.length > 0 && finalFiles.every((file) => /^[a-f0-9]{64}$/.test(file.sha256)),
      "every final file has a SHA-256 snapshot",
      finalFiles.map((file) => ({ path: file.path, sha256: file.sha256 }))
    ),
    check(
      "filesystem_evidence_has_canonical_content_snapshot",
      finalFiles.some((file) => file.path.includes("/ticket.md") && typeof file.content_preview === "string" && file.content_preview.includes("TASK-")),
      "at least one canonical ticket content preview accompanies the file hash",
      finalFiles.filter((file) => typeof file.content_preview === "string").map((file) => file.path)
    ),
    check(
      "filesystem_evidence_records_created_and_workflow_deltas",
      meetingCreated.some((file) => /^tickets\/TASK-\d+\/ticket\.md$/.test(file.path))
        && workflowDelta.created.length + workflowDelta.modified.length + workflowDelta.deleted.length > 0,
      "the proof records meeting-created tickets and later workflow file deltas",
      {
        meetingCreated: meetingCreated.map((file) => file.path),
        workflow: {
          created: workflowDelta.created.map((file) => file.path),
          modified: workflowDelta.modified.map((file) => file.path),
          deleted: workflowDelta.deleted.map((file) => file.path)
        }
      }
    )
  ];
}

function trace(at, actor, kind, text, files = []) {
  return { at, actor, kind, text, files };
}

function evaluateMeetingParallelWorkers() {
  const workspaceRoot = sandbox();
  try {
    const traceEvents = [];
    const beforeMeeting = workspaceFiles(workspaceRoot);
    const seeded = seedDemo({ workspaceRoot, write: true });
    const setupFiles = workspaceFiles(workspaceRoot);
    traceEvents.push(trace(
      "2026-08-10T09:00:00.000Z",
      "Fixture setup",
      "filesystem_setup",
      "Created the private employee directory, scoped mock Drive source, and empty ticket workspace.",
      setupFiles.filter((file) => !file.path.endsWith("ticket.md") && !file.path.endsWith("progress.md"))
    ));
    traceEvents.push(trace(
      "2026-08-10T09:00:00.000Z",
      "Meeting summary",
      "meeting_input",
      `Loaded the frozen weekly summary and created ${seeded.meeting.createdTicketIds.join(", ")}.`,
      setupFiles.filter((file) => /tickets\/TASK-\d+\/(ticket|progress)\.md$/.test(file.path))
    ));
    const board = inspectBoard({ workspaceRoot, now: "2026-08-11T09:00:00.000Z" });
    const taskIds = board.tasks.map((task) => task.ticketId).sort();
    const timeline = board.gantt.map((item) => item.ticketId).sort();
    const geoReply = recordReply({
      workspaceRoot,
      ticketId: "TASK-1001",
      employeeId: "kenji",
      text: "The approved geo workbook is in the scoped shared folder.",
      now: "2026-08-11T09:01:00.000Z",
      write: true
    });
    traceEvents.push(trace(
      "2026-08-11T09:01:00.000Z",
      "Kenji",
      "human_reply",
      "Confirmed the approved geo source in the scoped shared folder. TASK-1001 remains blocked until the pulse dispatches its eligible skill."
    ));
    const geoWorkerPulse = runPulse({ workspaceRoot, now: "2026-08-11T09:02:00.000Z", maxWorkers: 2, write: true });
    traceEvents.push(trace(
      "2026-08-11T09:02:00.000Z",
      "Howie",
      "worker_dispatch",
      `Dispatched ${geoWorkerPulse.workerDispatches.map((worker) => `${worker.workerId} → ${worker.ticketId}`).join(", ")}.`,
      geoWorkerPulse.workerDispatches.map((worker) => ({ path: relative(workspaceRoot, worker.draftArtifactPath).replaceAll("\\", "/"), bytes: statSync(worker.draftArtifactPath).size }))
    ));
    publishArtifact({ workspaceRoot, ticketId: "TASK-1001", write: true });
    reviewArtifact({ workspaceRoot, ticketId: "TASK-1001", reviewerId: "kenji", decision: "approved", now: "2026-08-11T09:03:00.000Z", write: true });
    traceEvents.push(trace(
      "2026-08-11T09:03:00.000Z",
      "Kenji",
      "artifact_review",
      "Approved the geo report. Its output now resolves the deck and model dependencies.",
      workspaceFiles(workspaceRoot).filter((file) => file.path.startsWith("tickets/archive/TASK-1001/"))
    ));
    recordHumanResponse({
      workspaceRoot,
      ticketId: "TASK-1002",
      requirementId: "deck-direction",
      employeeId: "kenji",
      text: "Use the approved geo evidence for an early-stage mining investor narrative.",
      now: "2026-08-11T09:04:00.000Z",
      write: true
    });
    recordHumanResponse({
      workspaceRoot,
      ticketId: "TASK-1003",
      requirementId: "model-assumptions",
      employeeId: "kenji",
      text: "Use the approved geo evidence and current operating assumptions.",
      now: "2026-08-11T09:04:30.000Z",
      write: true
    });
    traceEvents.push(trace(
      "2026-08-11T09:04:30.000Z",
      "Kenji",
      "human_reply",
      "Provided the fundraising direction and model assumptions for the now-unblocked parallel work."
    ));
    const parallelWorkerPulse = runPulse({ workspaceRoot, now: "2026-08-11T09:05:00.000Z", maxWorkers: 2, write: true });
    traceEvents.push(trace(
      "2026-08-11T09:05:00.000Z",
      "Howie",
      "worker_dispatch",
      `Dispatched ${parallelWorkerPulse.workerDispatches.map((worker) => `${worker.workerId} → ${worker.ticketId}`).join(", ")} in parallel.`,
      parallelWorkerPulse.workerDispatches.map((worker) => ({ path: relative(workspaceRoot, worker.draftArtifactPath).replaceAll("\\", "/"), bytes: statSync(worker.draftArtifactPath).size }))
    ));
    const workerEvents = ["TASK-1002", "TASK-1003"].flatMap((ticketId) => progressText(workspaceRoot, ticketId)
      .split("\n")
      .filter((line) => /mock_worker_dispatched/.test(line)));
    const activeAfterDispatch = inspectBoard({ workspaceRoot, now: "2026-08-11T09:05:00.000Z" }).tasks
      .filter((task) => task.status === "in_progress")
      .map((task) => task.ticketId);
    const checks = [
      check(
        "meeting_creates_four_canonical_tickets",
        seeded.meeting.createdTicketIds.length === 4 && taskIds.length === 4,
        "four canonical ticket records from the frozen meeting",
        { createdTicketIds: seeded.meeting.createdTicketIds, taskIds }
      ),
      check(
        "timeline_is_derived_from_canonical_tickets",
        timeline.length === 4 && timeline.every((ticketId) => taskIds.includes(ticketId)),
        "one timeline entry with dates for every canonical ticket",
        { timeline: board.gantt }
      ),
      check(
        "eligible_work_has_parallel_worker_dispatch",
        geoReply.status === "blocked"
          && geoWorkerPulse.workerDispatches.length === 1
          && parallelWorkerPulse.workerDispatches.map((worker) => worker.ticketId).join(",") === "TASK-1002,TASK-1003"
          && activeAfterDispatch.join(",") === "TASK-1002,TASK-1003"
          && workerEvents.length === 2,
        "two dependency-ready independent tasks start in sorted local worker slots; blocked tasks do not start",
        {
          boundedReplyStatus: geoReply.status,
          geoWorkerDispatches: geoWorkerPulse.workerDispatches,
          parallelWorkerDispatches: parallelWorkerPulse.workerDispatches,
          activeAfterDispatch,
          workerEvents,
          note: "Workers are deterministic local mock slots; no external worker, message, Drive, or scheduler is started."
        }
      )
    ];
    const finalFiles = workspaceFiles(workspaceRoot);
    const filesystem = filesystemEvidence(beforeMeeting, setupFiles, finalFiles);
    return {
      checks: [...checks, ...filesystemProofChecks(filesystem)],
      evidence: { createdTicketIds: seeded.meeting.createdTicketIds, timeline: board.gantt },
      trace: traceEvents,
      filesystem
    };
  } finally {
    rmSync(workspaceRoot, { recursive: true, force: true });
  }
}

function evaluateStaleDriveExpertChase() {
  const workspaceRoot = sandbox();
  try {
    const traceEvents = [];
    const beforeMeeting = workspaceFiles(workspaceRoot);
    seedDemo({ workspaceRoot, write: true });
    const setupFiles = workspaceFiles(workspaceRoot);
    traceEvents.push(trace(
      "2026-08-10T09:00:00.000Z",
      "Fixture setup",
      "filesystem_setup",
      "Created the scoped mock Drive source and four meeting tickets.",
      setupFiles
    ));
    unlinkSync(resolve(workspaceRoot, "drive-mock/howie-ai-shared/geo-source.json"));
    traceEvents.push(trace(
      "2026-08-11T09:00:30.000Z",
      "Fixture setup",
      "stale_source",
      "Removed the expected scoped geo source to simulate a stale or unavailable Drive file."
    ));
    let failure = null;
    try {
      recordReply({
        workspaceRoot,
        ticketId: "TASK-1001",
        employeeId: "kenji",
        text: "The expected source is unavailable.",
        now: "2026-08-11T09:01:00.000Z",
        write: true
      });
    } catch (error) {
      failure = error.message;
    }
    traceEvents.push(trace(
      "2026-08-11T09:01:00.000Z",
      "Howie",
      "expert_chase",
      "Rejected the unavailable source, kept TASK-1001 blocked, and prepared one preview-only request for a scoped source refresh."
    ));
    const board = inspectBoard({ workspaceRoot, now: "2026-08-11T09:01:00.000Z" });
    const geo = board.tasks.find((task) => task.ticketId === "TASK-1001");
    const progress = progressText(workspaceRoot, "TASK-1001");
    const expertChaseEvents = progress.split("\n").filter((line) => /telegram_delivery_draft/.test(line) && /request_scoped_source_refresh/.test(line));
    const checks = [
      check(
        "unavailable_scoped_drive_input_fails_closed",
        /no accessible howie-ai shared mock Drive file/.test(failure ?? ""),
        "the unavailable scoped Drive file is rejected",
        { failure }
      ),
      check(
        "missing_input_does_not_unblock_ticket",
        geo?.status === "blocked" && geo.requirements.some((requirement) => requirement.id === "geo-source-file" && requirement.state === "unresolved"),
        "TASK-1001 remains blocked with its Drive input unresolved",
        { status: geo?.status, requirements: geo?.requirements }
      ),
      check(
        "missing_input_creates_bounded_expert_chase",
        expertChaseEvents.length === 1
          && /geo-source-file/.test(expertChaseEvents[0])
          && /request_scoped_source_refresh/.test(expertChaseEvents[0])
          && /TASK-1001:geo-source-file:1/.test(expertChaseEvents[0])
          && /draft_only/.test(expertChaseEvents[0]),
        "one bounded, task-local expert chase names the missing input and local delivery-draft boundary",
        {
          expertChaseEvents,
          note: "The unavailable file remains rejected; the event only requests a scoped source refresh locally."
        }
      )
    ];
    const finalFiles = workspaceFiles(workspaceRoot);
    const filesystem = filesystemEvidence(beforeMeeting, setupFiles, finalFiles);
    return {
      checks: [...checks, ...filesystemProofChecks(filesystem)],
      evidence: { failure, status: geo?.status, expertChaseEvents },
      trace: traceEvents,
      filesystem
    };
  } finally {
    rmSync(workspaceRoot, { recursive: true, force: true });
  }
}

function evaluateEndOfWeekEscalation() {
  const workspaceRoot = sandbox();
  try {
    const traceEvents = [];
    const beforeMeeting = workspaceFiles(workspaceRoot);
    seedDemo({ workspaceRoot, write: true });
    const setupFiles = workspaceFiles(workspaceRoot);
    traceEvents.push(trace(
      "2026-08-10T09:00:00.000Z",
      "Fixture setup",
      "filesystem_setup",
      "Created the scoped source and four blocked meeting tickets.",
      setupFiles
    ));
    const first = runPulse({ workspaceRoot, now: "2026-08-17T16:00:00.000Z", write: true });
    traceEvents.push(trace(
      "2026-08-17T16:00:00.000Z",
      "Howie",
      "follow_up",
      `Prepared ${first.deliveryDrafts.length} local delivery draft for the overdue geo source. No message was sent.`
    ));
    const second = runPulse({ workspaceRoot, now: "2026-08-17T18:01:00.000Z", write: true });
    traceEvents.push(trace(
      "2026-08-17T18:01:00.000Z",
      "Howie",
      "escalation",
      `Recorded ${second.escalations.length} local escalation after the second overdue follow-up. No notification was sent.`
    ));
    const progress = progressText(workspaceRoot, "TASK-1001");
    const previewEvents = progress.split("\n").filter((line) => line.includes("telegram_delivery_draft"));
    const escalationEvents = progress.split("\n").filter((line) => /\*\*ticket_escalated\*\*/.test(line));
    const checks = [
      check(
        "repeated_chases_obey_cooldown_policy",
        first.deliveryDrafts.length === 1
          && second.deliveryDrafts.length === 1
          && first.deliveryDrafts[0].delivery === "draft_only"
          && second.deliveryDrafts[0].attempt === 2,
        "repeated chases are local delivery drafts and wait for the configured two-hour cooldown",
        { first: first.deliveryDrafts, second: second.deliveryDrafts, previewEvents }
      ),
      check(
        "end_of_week_blocked_work_records_escalation",
        escalationEvents.length === 1
          && /next_owner_id/.test(escalationEvents[0])
          && /howie-ai/.test(escalationEvents[0])
          && /Blocked after 2 bounded follow-ups/.test(escalationEvents[0]),
        "one policy-bounded local escalation event with a next owner and reason",
        {
          escalationEvents,
          note: "Escalation is a local ticket record after the second overdue follow-up; it does not send a notification."
        }
      )
    ];
    const finalFiles = workspaceFiles(workspaceRoot);
    const filesystem = filesystemEvidence(beforeMeeting, setupFiles, finalFiles);
    return {
      checks: [...checks, ...filesystemProofChecks(filesystem)],
      evidence: { first: first.deliveryDrafts, second: second.deliveryDrafts, escalationEvents },
      trace: traceEvents,
      filesystem
    };
  } finally {
    rmSync(workspaceRoot, { recursive: true, force: true });
  }
}

const probes = {
  meeting_tickets_timeline_parallel_workers: evaluateMeetingParallelWorkers,
  stale_drive_expert_chase: evaluateStaleDriveExpertChase,
  end_of_week_escalation: evaluateEndOfWeekEscalation
};

function evaluateTask(task) {
  const probe = task.metadata?.company_manager?.probe;
  const execute = probes[probe];
  if (!execute) {
    return {
      task,
      verdict: "error",
      pass: false,
      checks: [],
      reason: `No deterministic Company Manager probe is registered for ${String(probe)}.`
    };
  }
  try {
    const result = execute();
    const failed = result.checks.filter((item) => !item.pass);
    return {
      task,
      verdict: failed.length === 0 ? "pass" : "gap",
      pass: failed.length === 0,
      checks: result.checks,
      evidence: result.evidence,
      trace: result.trace,
      filesystem: result.filesystem,
      reason: failed.length === 0
        ? "All requested Company Manager behavior is supported by the local POC."
        : `Unsupported POC behavior: ${failed.map((item) => item.id).join(", ")}.`
    };
  } catch (error) {
    return {
      task,
      verdict: "error",
      pass: false,
      checks: [],
      trace: [],
      filesystem: { final_files: [] },
      reason: error instanceof Error ? error.message : String(error)
    };
  }
}

function defaultOutputPath() {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  return resolve(projectRoot, ".farplane/evals/runs", `${timestamp}-company-manager`);
}

function writeJson(path, value) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
}

export function runCompanyManagerEvals({ taskFile = defaultTaskFile, output, allowGaps = false } = {}) {
  const tasks = readTasks(taskFile);
  const outputRoot = resolve(output ?? defaultOutputPath());
  if (existsSync(resolve(outputRoot, "summary.json"))) {
    throw new Error(`Refusing to overwrite existing eval artifact: ${resolve(outputRoot, "summary.json")}`);
  }
  const startedAt = new Date().toISOString();
  const results = tasks.map(evaluateTask);
  const counts = {
    pass: results.filter((result) => result.verdict === "pass").length,
    gap: results.filter((result) => result.verdict === "gap").length,
    error: results.filter((result) => result.verdict === "error").length
  };
  const summary = {
    schema_version: 1,
    suite: "company-manager",
    task_file: resolve(taskFile),
    started_at: startedAt,
    completed_at: new Date().toISOString(),
    overall_verdict: counts.gap === 0 && counts.error === 0 ? "pass" : "gap",
    pass: counts.gap === 0 && counts.error === 0,
    counts,
    tasks: results.map((result) => ({
      task_id: result.task.id,
      title: result.task.title,
      verdict: result.verdict,
      pass: result.pass,
      reason: result.reason,
      detail_path: resolve(outputRoot, "tasks", `${result.task.id}.json`)
    }))
  };
  for (const result of results) writeJson(resolve(outputRoot, "tasks", `${result.task.id}.json`), result);
  writeJson(resolve(outputRoot, "summary.json"), summary);
  return { summary, outputRoot, exitCode: summary.pass || allowGaps ? 0 : 1 };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const result = runCompanyManagerEvals(args);
  console.log(JSON.stringify({ outputRoot: result.outputRoot, ...result.summary }, null, 2));
  process.exitCode = result.exitCode;
}

const invokedAsScript = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedAsScript) {
  try {
    main();
  } catch (error) {
    console.error(`Company manager eval error: ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 2;
  }
}
