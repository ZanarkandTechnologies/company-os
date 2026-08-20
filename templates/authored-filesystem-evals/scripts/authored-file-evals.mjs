/**
 * Portable authored filesystem evaluations.
 *
 * A case owns a synthetic fixture, a disposable manager brief, and deterministic
 * assertions over files created, modified, or deleted by an isolated Hermes run.
 */
import { createHash } from "node:crypto";
import { existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const templateRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const defaultCasesRoot = resolve(templateRoot, "cases");
const defaultRunsRoot = resolve(templateRoot, "runs");
const allowedEvents = new Set(["created", "modified", "deleted"]);
const contentRelations = ["added", "removed", "present", "absent"];
const maxFixtureFiles = 32;
const maxAssertions = 32;
const maxTextLength = 20_000;

function asObject(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object.`);
  return value;
}

function asString(value, label, { min = 1, max = maxTextLength } = {}) {
  if (typeof value !== "string") throw new Error(`${label} must be text.`);
  const normalized = value.trim();
  if (normalized.length < min || normalized.length > max) throw new Error(`${label} must be between ${min} and ${max} characters.`);
  return normalized;
}

function asTextList(value, label) {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.length > 12) throw new Error(`${label} must be a list of at most 12 text checks.`);
  return value.map((item, index) => asString(item, `${label}[${index}]`, { max: 1_000 }));
}

export function safeRelativePath(value, label = "path") {
  const path = asString(value, label, { max: 360 }).replaceAll("\\", "/");
  if (path.startsWith("/") || isAbsolute(path) || path.split("/").some((part) => !part || part === "." || part === "..")) {
    throw new Error(`${label} must stay inside the isolated test workspace.`);
  }
  if (["AGENTS.md", ".hermes.md", ".authored-eval.md"].includes(path) || path.startsWith("profile/")) {
    throw new Error(`${label} is reserved for the generated test profile.`);
  }
  return path;
}

function normalizeProfile(value = {}) {
  const profile = asObject(value, "test profile");
  return {
    name: asString(profile.name ?? "Test Manager", "test profile name", { max: 80 }),
    soul: asString(profile.soul ?? "Move the requested work forward using only the supplied files. State missing evidence plainly.", "test profile brief", { max: 8_000 }),
    memory: typeof profile.memory === "string" ? profile.memory.trim().slice(0, 4_000) : "",
    skills: asTextList(profile.skills ?? [], "test profile skills")
  };
}

function normalizeFixtures(value) {
  if (!Array.isArray(value) || value.length > maxFixtureFiles) throw new Error(`fixture_files must contain at most ${maxFixtureFiles} files.`);
  const fixtures = value.map((file, index) => {
    const item = asObject(file, `fixture_files[${index}]`);
    return {
      path: safeRelativePath(item.path, `fixture_files[${index}].path`),
      content: asString(item.content, `fixture_files[${index}].content`, { min: 0, max: maxTextLength })
    };
  });
  if (new Set(fixtures.map((file) => file.path)).size !== fixtures.length) throw new Error("fixture_files cannot contain the same path twice.");
  return fixtures;
}

function normalizeAssertions(value) {
  if (!Array.isArray(value) || value.length < 1 || value.length > maxAssertions) {
    throw new Error(`file_assertions must contain between 1 and ${maxAssertions} expected file events.`);
  }
  const seen = new Set();
  return value.map((assertion, index) => {
    const item = asObject(assertion, `file_assertions[${index}]`);
    const path = safeRelativePath(item.path, `file_assertions[${index}].path`);
    const event = asString(item.event, `file_assertions[${index}].event`, { max: 20 });
    if (!allowedEvents.has(event)) throw new Error(`file_assertions[${index}].event must be created, modified, or deleted.`);
    const key = `${event}:${path}`;
    if (seen.has(key)) throw new Error(`file_assertions contains duplicate ${event} expectation for ${path}.`);
    seen.add(key);
    const content = asObject(item.content ?? {}, `file_assertions[${index}].content`);
    return {
      path,
      event,
      content: Object.fromEntries(contentRelations.map((relation) => [relation, asTextList(content[relation], `file_assertions[${index}].content.${relation}`)]))
    };
  });
}

export function validateAuthoredFileEval(value) {
  const definition = asObject(value, "authored eval");
  const id = asString(definition.id, "id", { min: 3, max: 80 });
  if (!/^[a-z0-9][a-z0-9-]*$/.test(id)) throw new Error("id must use lowercase letters, numbers, and hyphens.");
  const normalized = {
    schema_version: 1,
    id,
    title: asString(definition.title, "title", { min: 4, max: 140 }),
    owner_message: asString(definition.owner_message, "owner message", { min: 4, max: 8_000 }),
    profile: normalizeProfile(definition.profile ?? {}),
    fixture_files: normalizeFixtures(definition.fixture_files ?? []),
    file_assertions: normalizeAssertions(definition.file_assertions)
  };
  const fixturePaths = new Set(normalized.fixture_files.map((file) => file.path));
  for (const assertion of normalized.file_assertions) {
    if (["modified", "deleted"].includes(assertion.event) && !fixturePaths.has(assertion.path)) {
      throw new Error(`${assertion.event} assertion for ${assertion.path} needs that file in fixture_files.`);
    }
  }
  return normalized;
}

function casePath(id, root) {
  return resolve(root, `${id}.json`);
}

function ensureInside(root, path) {
  const inner = relative(root, path);
  if (!inner || inner === ".." || inner.startsWith(`..${sep}`) || isAbsolute(inner)) throw new Error("Generated path escaped its owner root.");
}

function writeText(path, content) {
  mkdirSync(dirname(path), { recursive: true });
  const temp = resolve(dirname(path), `.${process.pid}.${Math.random().toString(16).slice(2)}.tmp`);
  try {
    writeFileSync(temp, content.endsWith("\n") ? content : `${content}\n`, { encoding: "utf8", mode: 0o600 });
    renameSync(temp, path);
  } finally {
    if (existsSync(temp)) rmSync(temp, { force: true });
  }
}

export function listAuthoredFileEvals({ casesDirectory = defaultCasesRoot } = {}) {
  if (!existsSync(casesDirectory)) return [];
  return readdirSync(casesDirectory, { withFileTypes: true })
    .filter((entry) => entry.isFile() && /^[a-z0-9][a-z0-9-]*\.json$/.test(entry.name))
    .map((entry) => validateAuthoredFileEval(JSON.parse(readFileSync(resolve(casesDirectory, entry.name), "utf8"))))
    .sort((left, right) => left.title.localeCompare(right.title));
}

export function readAuthoredFileEval(id, { casesDirectory = defaultCasesRoot } = {}) {
  const safeId = asString(id, "case id", { min: 3, max: 80 });
  if (!/^[a-z0-9][a-z0-9-]*$/.test(safeId)) throw new Error("case id is invalid.");
  const path = casePath(safeId, casesDirectory);
  if (!existsSync(path)) throw new Error(`No authored test exists with id ${safeId}.`);
  return validateAuthoredFileEval(JSON.parse(readFileSync(path, "utf8")));
}

export function saveAuthoredFileEval(value, { casesDirectory = defaultCasesRoot } = {}) {
  const definition = validateAuthoredFileEval(value);
  mkdirSync(casesDirectory, { recursive: true });
  writeText(casePath(definition.id, casesDirectory), JSON.stringify(definition, null, 2));
  return definition;
}

export function snapshotWorkspace(root) {
  const records = [];
  const visit = (directory) => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name);
      const stat = lstatSync(path);
      if (stat.isSymbolicLink()) throw new Error(`Test workspace cannot contain symbolic links: ${path}`);
      if (stat.isDirectory()) visit(path);
      else if (stat.isFile()) {
        const bytes = readFileSync(path);
        records.push({
          path: relative(root, path).replaceAll("\\", "/"),
          bytes: statSync(path).size,
          sha256: createHash("sha256").update(bytes).digest("hex"),
          content: bytes.toString("utf8")
        });
      }
    }
  };
  if (existsSync(root)) visit(root);
  return records.sort((left, right) => left.path.localeCompare(right.path));
}

function profileInstructions(definition) {
  const skills = definition.profile.skills.length ? `\nEnabled test skills: ${definition.profile.skills.join(", ")}.` : "";
  const memory = definition.profile.memory ? `\n\n## Test memory\n\n${definition.profile.memory}` : "";
  return `# ${definition.profile.name}\n\n${definition.profile.soul}${skills}${memory}\n\n## Isolation\n\nWork only inside this disposable evaluation workspace. Do not send messages, browse, call MCP, change permissions, access credentials, or modify runtime/profile settings.\n`;
}

function harnessInstructions(definition) {
  return `# Authored filesystem evaluation\n\nTest: ${definition.title}\n\nThe owner says:\n\n${definition.owner_message}\n\nUse the supplied files to do the work now. Your final response must explain what changed and any honest blocker.\n`;
}

function runId(definition) {
  return `${new Date().toISOString().replace(/[:.]/g, "-")}-${definition.id}`;
}

export function prepareAuthoredFileEval(value, { outputRoot = defaultRunsRoot } = {}) {
  const definition = validateAuthoredFileEval(value);
  const root = resolve(outputRoot, runId(definition));
  const workspace = resolve(root, "workspace");
  ensureInside(resolve(outputRoot), root);
  if (existsSync(root)) throw new Error(`Refusing to overwrite existing authored run: ${root}`);
  mkdirSync(workspace, { recursive: true });
  for (const file of definition.fixture_files) {
    const path = resolve(workspace, file.path);
    ensureInside(workspace, path);
    writeText(path, file.content);
  }
  writeText(resolve(workspace, "AGENTS.md"), profileInstructions(definition));
  writeText(resolve(workspace, ".authored-eval.md"), harnessInstructions(definition));
  writeText(resolve(workspace, "profile/SOUL.md"), `# ${definition.profile.name}\n\n${definition.profile.soul}\n`);
  writeText(resolve(workspace, "profile/MEMORY.md"), definition.profile.memory || "# Test memory\n\nNo additional working memory for this test.\n");
  writeText(resolve(workspace, "profile/ENABLED-SKILLS.md"), `# Enabled test skills\n\n${definition.profile.skills.length ? definition.profile.skills.map((skill) => `- ${skill}`).join("\n") : "- No additional skill package declared"}\n`);
  const before = snapshotWorkspace(workspace);
  writeText(resolve(root, "definition.json"), JSON.stringify(definition, null, 2));
  writeText(resolve(root, "manifest.json"), JSON.stringify({ schema_version: 1, kind: "authored-filesystem-eval", status: "prepared", id: definition.id, workspace: "workspace", prepared_at: new Date().toISOString() }, null, 2));
  return { definition, outputRoot: root, workspace, before };
}

export function evaluateAuthoredFileEval(definitionInput, before, after) {
  const definition = validateAuthoredFileEval(definitionInput);
  const initial = new Map(before.map((record) => [record.path, record]));
  const final = new Map(after.map((record) => [record.path, record]));
  const checks = definition.file_assertions.flatMap((assertion) => {
    const beforeFile = initial.get(assertion.path);
    const afterFile = final.get(assertion.path);
    const eventPass = assertion.event === "created"
      ? !beforeFile && Boolean(afterFile)
      : assertion.event === "modified"
        ? Boolean(beforeFile && afterFile && beforeFile.sha256 !== afterFile.sha256)
        : Boolean(beforeFile && !afterFile);
    const rows = [{ id: `${assertion.event}:${assertion.path}`, label: `${assertion.path} is ${assertion.event}`, pass: eventPass }];
    const beforeContent = beforeFile?.content ?? "";
    const afterContent = afterFile?.content ?? "";
    const predicates = {
      added: (text) => !beforeContent.includes(text) && afterContent.includes(text),
      removed: (text) => beforeContent.includes(text) && !afterContent.includes(text),
      present: (text) => afterContent.includes(text),
      absent: (text) => !afterContent.includes(text)
    };
    const verbs = { added: "adds", removed: "removes", present: "contains", absent: "omits" };
    for (const relation of contentRelations) {
      for (const text of assertion.content[relation]) rows.push({ id: `${relation}:${assertion.path}:${text}`, label: `${assertion.path} ${verbs[relation]} “${text}”`, pass: predicates[relation](text) });
    }
    return rows;
  });
  return { pass: checks.every((check) => check.pass), checks, counts: { pass: checks.filter((check) => check.pass).length, fail: checks.filter((check) => !check.pass).length } };
}

function promptFor(definition) {
  return `Read AGENTS.md, .authored-eval.md, and only the files needed to respond to the owner. Do the work now using only file and skills tools. Do not call external services, send messages, or change runtime/profile settings.\n\nOwner message:\n${definition.owner_message}`;
}

export function runAuthoredFileEval(value, { outputRoot = defaultRunsRoot, env = process.env, dryRun = false } = {}) {
  const prepared = prepareAuthoredFileEval(value, { outputRoot });
  const prompt = promptFor(prepared.definition);
  writeText(resolve(prepared.outputRoot, "prompt.md"), prompt);
  if (dryRun) {
    const score = evaluateAuthoredFileEval(prepared.definition, prepared.before, prepared.before);
    const result = { schema_version: 1, kind: "authored-filesystem-eval", real_agent: false, status: "prepared", id: prepared.definition.id, score, files: { before: prepared.before, after: prepared.before } };
    writeText(resolve(prepared.outputRoot, "result.json"), JSON.stringify(result, null, 2));
    return { ...prepared, result };
  }
  const profile = asString(env.HERMES_EVAL_PROFILE ?? "", "HERMES_EVAL_PROFILE", { max: 100 });
  const output = spawnSync(env.HERMES_BIN || "hermes", [
    "-p", profile, "chat", "--query", prompt, "--verbose", "--source", "authored-filesystem-eval",
    "--in", prepared.workspace, "-t", "file,skills", "--max-turns", "80"
  ], { cwd: templateRoot, env, encoding: "utf8", timeout: 300_000, maxBuffer: 2_000_000 });
  writeText(resolve(prepared.outputRoot, "stdout.txt"), output.stdout || "");
  writeText(resolve(prepared.outputRoot, "stderr.txt"), output.stderr || "");
  const after = snapshotWorkspace(prepared.workspace);
  const score = evaluateAuthoredFileEval(prepared.definition, prepared.before, after);
  const result = {
    schema_version: 1,
    kind: "authored-filesystem-eval",
    real_agent: true,
    status: output.status === 0 ? (score.pass ? "passed" : "failed") : "error",
    id: prepared.definition.id,
    title: prepared.definition.title,
    exit_code: output.status ?? 1,
    timed_out: Boolean(output.error?.code === "ETIMEDOUT"),
    score,
    files: { before: prepared.before, after }
  };
  writeText(resolve(prepared.outputRoot, "result.json"), JSON.stringify(result, null, 2));
  return { ...prepared, result };
}
