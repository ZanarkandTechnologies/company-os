#!/usr/bin/env node

import { chmodSync, lstatSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, join, resolve } from "node:path";

function parseArguments(args) {
  const values = new Map();
  let apply = false;
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === "--apply") {
      apply = true;
      continue;
    }
    if (!["--profile-home", "--provider-env", "--drive-credentials"].includes(argument)) {
      throw new Error(`unknown argument: ${argument}`);
    }
    const value = args[index + 1];
    if (!value || value.startsWith("--") || !isAbsolute(value)) {
      throw new Error(`${argument} requires an absolute path.`);
    }
    values.set(argument, resolve(value));
    index += 1;
  }
  for (const name of ["--profile-home", "--provider-env", "--drive-credentials"]) {
    if (!values.has(name)) throw new Error(`${name} is required.`);
  }
  return {
    apply,
    profileHome: values.get("--profile-home"),
    providerEnv: values.get("--provider-env"),
    driveCredentials: values.get("--drive-credentials")
  };
}

function readRegularFile(path) {
  const stat = lstatSync(path);
  if (!stat.isFile() || stat.isSymbolicLink()) throw new Error(`expected a regular file: ${path}`);
  return readFileSync(path, "utf8");
}

function parseEnv(source) {
  const values = new Map();
  for (const rawLine of source.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const match = line.match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
    if (!match) continue;
    let value = match[2].trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    values.set(match[1], value);
  }
  return values;
}

function upsertEnv(source, updates) {
  const pending = new Map(updates);
  const rendered = [];
  for (const line of source.split(/\r?\n/)) {
    const match = line.match(/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=/);
    if (!match || !pending.has(match[1])) {
      rendered.push(line);
      continue;
    }
    rendered.push(`${match[1]}=${pending.get(match[1])}`);
    pending.delete(match[1]);
  }
  while (rendered.length && rendered.at(-1) === "") rendered.pop();
  for (const [key, value] of pending) rendered.push(`${key}=${value}`);
  return `${rendered.join("\n")}\n`;
}

function atomicPrivateWrite(path, content) {
  const temporary = join(dirname(path), `.howie-private-${process.pid}-${Date.now()}`);
  writeFileSync(temporary, content, { mode: 0o600 });
  chmodSync(temporary, 0o600);
  renameSync(temporary, path);
  chmodSync(path, 0o600);
}

function main() {
  const options = parseArguments(process.argv.slice(2));
  const profileStat = lstatSync(options.profileHome);
  if (!profileStat.isDirectory() || profileStat.isSymbolicLink()) {
    throw new Error(`profile home must be a real directory: ${options.profileHome}`);
  }
  const providerKey = parseEnv(readRegularFile(options.providerEnv)).get("OPENROUTER_API_KEY");
  if (!providerKey) throw new Error("provider env does not contain OPENROUTER_API_KEY.");

  const credentialEnvelope = JSON.parse(readRegularFile(options.driveCredentials));
  const credentials = credentialEnvelope.installed ?? credentialEnvelope.web;
  if (!credentials || typeof credentials.client_id !== "string" || !credentials.client_id.endsWith(".apps.googleusercontent.com")) {
    throw new Error("Drive credential file must contain an installed or web OAuth client ID.");
  }
  if (typeof credentials.client_secret !== "string" || !credentials.client_secret) {
    throw new Error("Drive credential file must contain an OAuth client secret.");
  }

  const environmentPath = join(options.profileHome, ".env");
  const nextEnvironment = upsertEnv(readRegularFile(environmentPath), new Map([
    ["OPENROUTER_API_KEY", providerKey],
    ["GOOGLE_DRIVE_MCP_CLIENT_ID", credentials.client_id],
    ["GOOGLE_DRIVE_MCP_CLIENT_SECRET", credentials.client_secret]
  ]));
  const summary = "OpenRouter and Google Drive OAuth credentials are present in the private howie-ai profile environment.";
  if (!options.apply) {
    console.log(`CHECK ${summary}`);
    return;
  }
  atomicPrivateWrite(environmentPath, nextEnvironment);
  console.log(`APPLIED ${summary}`);
}

try {
  main();
} catch (error) {
  console.error(`Howie private runtime error: ${error.message}`);
  process.exitCode = 1;
}
