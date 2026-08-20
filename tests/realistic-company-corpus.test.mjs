import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const corpusRoot = resolve(projectRoot, "fixtures/company-manager/shared-drive/aurora-lithium");
const meetingPath = resolve(projectRoot, "fixtures/company-manager/meetings/aurora-operator-weekly-transcript.md");

function markdownFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return markdownFiles(path);
    return entry.name.endsWith(".md") ? [path] : [];
  });
}

const customerFacingRecords = [...markdownFiles(corpusRoot), meetingPath];
for (const recordPath of customerFacingRecords) {
  const record = readFileSync(recordPath, "utf8");
  assert.doesNotMatch(record, /\b(?:synthetic|mock|fixture|fake|test data|illustrative)\b/i, recordPath);
}

const technical = readFileSync(resolve(corpusRoot, "sources/mining/technical-source.md"), "utf8");
const finance = readFileSync(resolve(corpusRoot, "sources/finance/operating-assumptions.md"), "utf8");
const compliance = readFileSync(resolve(corpusRoot, "sources/operations/compliance-evidence.md"), "utf8");
assert.match(technical, /64 completed drill holes/);
assert.match(finance, /opening cash USD 4\.2m/);
assert.match(compliance, /Contractor insurance evidence has not been filed/);

console.log("✓ Aurora Lithium source records read as ordinary company records while retaining concrete operating facts.");
