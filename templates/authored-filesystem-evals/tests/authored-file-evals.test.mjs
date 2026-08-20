import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { evaluateAuthoredFileEval, prepareAuthoredFileEval, validateAuthoredFileEval } from "../scripts/authored-file-evals.mjs";

const root = mkdtempSync(resolve(tmpdir(), "authored-filesystem-eval-template-"));
const definition = validateAuthoredFileEval({
  schema_version: 1,
  id: "file-contract",
  title: "Proves created, modified, and deleted files",
  owner_message: "Prepare the requested record from the supplied source.",
  profile: { name: "Test manager", soul: "Use only supplied source evidence.", memory: "", skills: ["weekly-report"] },
  fixture_files: [
    { path: "source.md", content: "Approved input\n" },
    { path: "tickets/TASK-1/progress.md", content: "# Progress\nold line\n" },
    { path: "obsolete.md", content: "Remove me\n" }
  ],
  file_assertions: [
    { path: "artifacts/report.md", event: "created", content: { added: ["Approved input"], present: ["Review needed"], absent: ["invented"] } },
    { path: "tickets/TASK-1/progress.md", event: "modified", content: { added: ["artifact_drafted"], removed: ["old line"], present: ["review"], absent: ["message sent"] } },
    { path: "obsolete.md", event: "deleted", content: { removed: ["Remove me"] } }
  ]
});

try {
  assert.throws(() => validateAuthoredFileEval({ ...definition, fixture_files: [{ path: "../escape.md", content: "no" }] }), /isolated test workspace/);
  assert.throws(() => validateAuthoredFileEval({ ...definition, file_assertions: [{ path: "missing.md", event: "modified", content: {} }] }), /needs that file in fixture_files/);
  const prepared = prepareAuthoredFileEval(definition, { outputRoot: resolve(root, "runs") });
  assert.equal(existsSync(resolve(prepared.workspace, "AGENTS.md")), true);
  assert.match(readFileSync(resolve(prepared.workspace, ".authored-eval.md"), "utf8"), /Prepare the requested record/);
  assert.match(readFileSync(resolve(prepared.workspace, "profile/ENABLED-SKILLS.md"), "utf8"), /weekly-report/);
  const after = [
    ...prepared.before.filter((file) => !["obsolete.md", "tickets/TASK-1/progress.md"].includes(file.path)),
    { path: "tickets/TASK-1/progress.md", content: "# Progress\nartifact_drafted\nreview\n", sha256: "changed", bytes: 35 },
    { path: "artifacts/report.md", content: "Approved input\nReview needed\n", sha256: "new", bytes: 29 }
  ];
  const score = evaluateAuthoredFileEval(definition, prepared.before, after);
  assert.equal(score.pass, true);
  assert.equal(score.counts.fail, 0);
  assert.equal(score.checks.length, 11);
} finally {
  rmSync(root, { recursive: true, force: true });
}

console.log("✓ Authored filesystem eval template validates isolation, file events, and content relations.");
