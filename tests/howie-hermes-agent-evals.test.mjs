import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { managerReplyChecks, runHowieHermesAgentEvals } from "../scripts/run-howie-hermes-agent-evals.mjs";

assert.equal(managerReplyChecks("The follow-ups are attached below.").manager_reply_makes_no_unavailable_attachment_claim, false);
assert.equal(managerReplyChecks("Four reports are ready for review.").manager_reply_makes_no_unavailable_attachment_claim, true);
assert.equal(managerReplyChecks("Four reports are attached below.").manager_reply_makes_no_unavailable_attachment_claim, false);

const root = mkdtempSync(resolve(tmpdir(), "howie-real-hermes-eval-test-"));
try {
  const result = runHowieHermesAgentEvals({ output: resolve(root, "run"), dryRun: true, env: {} });
  assert.equal(result.exitCode, 0);
  assert.equal(result.summary.real_agent, false);
  assert.deepEqual(result.summary.counts, { pass: 0, fail: 0, skipped: 3 });
  const meeting = JSON.parse(readFileSync(resolve(result.outputRoot, "runs/real_meeting_to_tickets/result.json"), "utf8"));
  assert.equal(meeting.files.setup.some((file) => file.path === "profile/SOUL.md"), true);
  assert.equal(typeof meeting.files.setup.find((file) => file.path === "profile/SOUL.md").content_preview, "string");
  assert.equal(meeting.files.setup.some((file) => file.path === ".hermes.md"), true);
  assert.equal(meeting.files.setup.some((file) => file.path === "meetings/MEETING-2026-08-17-aurora-weekly/transcript.md"), true);
  assert.equal(typeof meeting.files.setup.find((file) => file.path === "meetings/MEETING-2026-08-17-aurora-weekly/transcript.md").content_preview, "string");
  assert.equal(meeting.files.setup.some((file) => file.path === "company-directory.md"), true);
  const directoryPreview = meeting.files.setup.find((file) => file.path === "company-directory.md").content_preview;
  assert.match(directoryPreview, /Aurora Lithium — internal directory/);
  assert.doesNotMatch(directoryPreview, /\b(?:synthetic|mock|fixture|fake|test identity)\b/i);
  assert.equal(meeting.files.setup.some((file) => file.path === "skills/geo-report/SKILL.md"), true);
  assert.equal(meeting.files.setup.some((file) => file.path === "skills/geo-report/templates/geo-report.md"), true);
  assert.equal(meeting.files.delta.created.length, 0);
  assert.equal(meeting.real_agent, false);
  assert.equal(meeting.manager_reply, null);
  assert.match(meeting.channel_message, /^Here are the weekly Aurora Lithium meeting notes\./);
  assert.match(readFileSync(resolve(result.outputRoot, "runs/real_meeting_to_tickets/prompt.md"), "utf8"), /one concise Telegram-ready update from Manager/);
  const chase = JSON.parse(readFileSync(resolve(result.outputRoot, "runs/real_blocked_ticket_expert_chase/result.json"), "utf8"));
  assert.equal(chase.files.setup.some((file) => file.path === "tickets/TASK-2101/ticket.md"), true);
  assert.equal(chase.files.setup.some((file) => file.path === "company-directory.md"), true);
  assert.match(chase.channel_message, /Run pulse\.$/);
  const escalation = JSON.parse(readFileSync(resolve(result.outputRoot, "runs/real_missing_drive_escalation/result.json"), "utf8"));
  assert.equal(escalation.files.setup.some((file) => file.path === "tickets/TASK-2201/ticket.md"), true);
  assert.match(escalation.channel_message, /end of the week\. Run pulse\./i);
} finally {
  rmSync(root, { recursive: true, force: true });
}

console.log("✓ Real Hermes agent evaluator prepares isolated company workspaces without invoking external services in dry-run mode.");
