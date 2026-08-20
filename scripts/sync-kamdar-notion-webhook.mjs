#!/usr/bin/env node

import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, statSync } from "node:fs";
import { basename, dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const sources = [
  {
    source: join(projectRoot, "profiles", "kamdar-ai", "plugins", "platforms", "notion"),
    destination: "plugins/platforms/notion",
  },
  {
    source: join(projectRoot, "skills", "notion-webhook-onboarding"),
    destination: "skills/notion-webhook-onboarding",
  },
];

function usage() {
  return "node scripts/sync-kamdar-notion-webhook.mjs --target <Hermes profile dir> [--check|--apply]";
}

function parseArgs(argv) {
  const targetIndex = argv.indexOf("--target");
  const apply = argv.includes("--apply");
  const check = argv.includes("--check");
  if (targetIndex < 0 || !argv[targetIndex + 1] || apply === check) {
    throw new Error(usage());
  }
  return { target: resolve(argv[targetIndex + 1]), apply };
}

function filesUnder(root, prefix = "") {
  const absolute = join(root, prefix);
  return readdirSync(absolute, { withFileTypes: true }).flatMap((entry) => {
    if (entry.name === "__pycache__" || entry.name.endsWith(".pyc")) return [];
    const path = join(prefix, entry.name);
    return entry.isDirectory() ? filesUnder(root, path) : [path];
  });
}

function assertSafeTarget(target) {
  if (!existsSync(target) || !statSync(target).isDirectory()) {
    throw new Error(`target profile does not exist: ${target}`);
  }
  const parent = basename(dirname(target));
  if (parent !== "profiles" || target === dirname(target)) {
    throw new Error("target must be one existing Hermes profile directory");
  }
  if (!existsSync(join(target, "config.yaml"))) {
    throw new Error("target does not look like an installed Hermes profile");
  }
}

function main() {
  const { target, apply } = parseArgs(process.argv.slice(2));
  assertSafeTarget(target);
  const files = sources.flatMap(({ source, destination }) =>
    filesUnder(source).map((path) => ({
      source: join(source, path),
      destination: join(destination, path),
    })),
  );
  const drift = files.filter((file) => {
    const destination = join(target, file.destination);
    return !existsSync(destination) || !readFileSync(file.source).equals(readFileSync(destination));
  });

  if (apply) {
    for (const file of drift) {
      const destination = join(target, file.destination);
      mkdirSync(dirname(destination), { recursive: true });
      copyFileSync(file.source, destination);
    }
  }

  const untouched = ["config.yaml", ".env", "sessions", "memories", "skills outside notion-webhook-onboarding"];
  process.stdout.write(`${JSON.stringify({
    state: apply ? "applied" : drift.length ? "drift" : "clean",
    target,
    files_checked: files.length,
    files_written: apply ? drift.length : 0,
    drift: drift.map((file) => file.destination.split(sep).join("/")),
    untouched,
  })}\n`);
  if (!apply && drift.length) process.exitCode = 1;
}

main();
