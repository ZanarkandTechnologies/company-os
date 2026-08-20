import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import test from "node:test";

const root = resolve(import.meta.dirname, "..");
const durableTemplates = ["project", "task", "resource", "decision"];

test("durable Company OS records expose consistent metadata and value framing", () => {
  for (const name of durableTemplates) {
    const content = readFileSync(join(root, "templates", `${name}.md`), "utf8");
    assert.match(content, /^---\ntemplate_id: company-os-/);
    assert.match(content, /template_version: "0\.2\.0"/);
    assert.match(content, /kind: company-record-template/);
    assert.match(content, /status: active/);
    assert.match(content, /owner: HermesCorp/);
    assert.match(content, /opens_with:\n  - outcome\n  - why/);
    assert.match(content, /required_properties:/);
    assert.match(content, /> \*\*Outcome\*\*/);
    assert.match(content, /> \*\*Why\*\*/);
  }
});

test("Weekly Report opens with an executable executive-summary template", () => {
  const report = readFileSync(join(root, "templates", "weekly-report.md"), "utf8");
  assert.match(report, /template_version: "0\.3\.0"/);
  assert.match(report, /opens_with:\n  - executive-summary/);
  assert.doesNotMatch(report, /> \*\*Outcome\*\*/);
  assert.doesNotMatch(report, /> \*\*Why\*\*/);
  assert.match(report, /\{\{EXECUTIVE_SUMMARY — Write exactly three sentences:/);
  assert.match(report, /\{\{Promote to Issue \\| Duplicate \\| Monitor \\| Dismiss\}\}/);
  assert.match(report, /`evidence_window:` \{\{START_TIMESTAMP\}\}\.\.\{\{END_TIMESTAMP\}\}/);
});

test("Tasks are the shared Task, Issue, and Meeting table", () => {
  const task = readFileSync(join(root, "templates/task.md"), "utf8");
  assert.match(task, /type_options:\n  - Task\n  - Issue\n  - Meeting/);
  assert.match(task, /Meeting notes and updates/);
});

test("durable records retain their explicit promotion gates", () => {
  const resource = readFileSync(join(root, "templates/resource.md"), "utf8");
  const decision = readFileSync(join(root, "templates/decision.md"), "utf8");
  assert.match(resource, /promotion_gate: future-value/);
  assert.match(decision, /promotion_gate: precedent-value/);
});

test("automation index resolves both independent automation files", () => {
  const index = readFileSync(join(root, "automations.md"), "utf8");
  for (const filename of ["daily-operating-update.md", "weekly-operating-review.md"]) {
    assert.ok(existsSync(join(root, "automations", filename)));
    assert.match(index, new RegExp(`automations/${filename.replace(".", "\\.")}`));
  }
  assert.match(index, /`Task`, `Issue`, and `Meeting`/);
  assert.match(index, /> \*\*Outcome\*\*/);
  assert.match(index, /> \*\*Why\*\*/);
});

test("Daily stages candidates and Weekly owns selective promotion", () => {
  const daily = readFileSync(join(root, "automations/daily-operating-update.md"), "utf8");
  const weekly = readFileSync(join(root, "automations/weekly-operating-review.md"), "utf8");
  for (const process of [
    "progress-extraction",
    "problem-extraction",
    "sop-extraction",
    "documentation-template-check",
    "chase-planning",
    "weekly-draft-projection",
  ]) {
    assert.match(daily, new RegExp("> ### `" + process + "`"));
  }
  assert.doesNotMatch(daily, /Progress and chasing/);
  for (const process of ["issue-promotion", "decision-promotion", "skill-promotion"]) {
    assert.match(weekly, new RegExp("> ### `" + process + "`"));
  }
  assert.match(daily, /must not promote Issues, Decisions, Resources, or Skills/);
  assert.match(daily, /Send nothing unless the/);
  assert.match(daily, /post one source-local comment containing the missing items/);
  assert.match(daily, /does\n> not edit the record, create a weekly candidate/);
  assert.match(weekly, /accepted candidates to Tasks with `Type = Issue`/);
  assert.match(weekly, /No canonical work item was cleared or deleted/);
});

test("automation files pair fill-in-place output templates with golden examples", () => {
  for (const filename of ["daily-operating-update.md", "weekly-operating-review.md"]) {
    const content = readFileSync(join(root, "automations", filename), "utf8");
    const expectedVersion = filename === "daily-operating-update.md" ? "0.7.0" : "0.5.0";
    assert.match(content, new RegExp(`automation_version: "${expectedVersion.replaceAll(".", "\\.")}"`));
    assert.match(content, /## Output template/);
    assert.match(content, /\{\{[^\n}]+\}\}/);
    assert.match(content, /## Golden example/);
    assert.match(content, /### Input and context/);
    assert.match(content, /### Accepted output/);
    assert.match(content, /### Why it passes/);
    assert.match(content, /### Tempting negative/);
    assert.match(content, /### Transferable invariants/);
    assert.match(content, /### Non-copyable facts and wording/);
    assert.match(content, /### Proof receipt/);
    assert.match(content, /heldout_required: true/);
    assert.match(content, /Generate fresh (findings|conclusions) and wording from the current company's evidence/);
  }
});

test("Daily checks records edited today against Notion templates and comments at source", () => {
  const daily = readFileSync(join(root, "automations", "daily-operating-update.md"), "utf8");
  const index = readFileSync(join(root, "automations.md"), "utf8");
  assert.match(daily, /- documentation-template-check/);
  assert.match(daily, /> ### `documentation-template-check`/);
  assert.match(daily, /input_window: current-local-day/);
  assert.match(daily, /created or edited during\n  the current local day/);
  assert.match(daily, /resolves the applicable Notion template by record type/);
  assert.match(daily, /Record type, template used, and missing required information/);
  assert.match(daily, /For documentation, could you define done/);
  assert.match(daily, /Do not project documentation comments into the weekly draft/);
  assert.match(daily, /`daily-documentation-check` skill/);
  assert.match(daily, /company_timezone/);
  assert.match(daily, /configuration_gap: unmapped_template/);
  assert.doesNotMatch(daily, /watermark/);
  assert.match(index, /not\n  projected into the weekly Report or processed by Weekly/);
});

test("every Weekly promotion lane carries the disposition enum at point of use", () => {
  const weekly = readFileSync(join(root, "automations", "weekly-operating-review.md"), "utf8");
  for (const process of [
    "issue-promotion",
    "decision-promotion",
    "resource-promotion",
    "skill-promotion",
  ]) {
    assert.match(
      weekly,
      new RegExp("`" + process + "` \\| \\{\\{Candidate plus Promoted \\\\\\| Duplicate \\\\\\| Monitor \\\\\\| Dismissed\\}\\}"),
    );
  }
});

test("Weekly does not process Daily documentation comments", () => {
  const weekly = readFileSync(join(root, "automations", "weekly-operating-review.md"), "utf8");
  assert.doesNotMatch(weekly, /documentation-resolution|documentation-template-check|documentation comments/);
  assert.doesNotMatch(readFileSync(join(root, "templates", "weekly-report.md"), "utf8"), /## Documentation quality/);
});
