import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import test from "node:test";

const root = resolve(import.meta.dirname, "..");
const templates = ["project", "task", "resource", "decision", "weekly-report"];

test("Company OS record templates expose consistent metadata", () => {
  for (const name of templates) {
    const content = readFileSync(join(root, "templates", `${name}.md`), "utf8");
    assert.match(content, /^---\ntemplate_id: company-os-/);
    assert.match(content, /template_version: "0\.1\.0"/);
    assert.match(content, /kind: company-record-template/);
    assert.match(content, /status: active/);
    assert.match(content, /owner: HermesCorp/);
    assert.match(content, /required_properties:/);
  }
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
});

test("Daily stages candidates and Weekly owns selective promotion", () => {
  const daily = readFileSync(join(root, "automations/daily-operating-update.md"), "utf8");
  const weekly = readFileSync(join(root, "automations/weekly-operating-review.md"), "utf8");
  assert.match(daily, /must not promote Issues, Decisions,\nResources, or Skills/);
  assert.match(daily, /Send nothing unless the/);
  assert.match(weekly, /promote an accepted problem into Tasks with `Type = Issue`/);
  assert.match(weekly, /No canonical work item was cleared or deleted/);
});
