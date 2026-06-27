#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { execSync } from "node:child_process";

async function readPayload() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  return JSON.parse(raw || "{}");
}

export async function main() {
  const payload = await readPayload();
  const repoRoot = payload.cwd || process.cwd();
  
  try {
    const pythonPath = process.platform === "win32" ? "venv\\Scripts\\python.exe" : "venv/bin/python";
    const execPath = fs.existsSync(path.join(repoRoot, pythonPath)) ? pythonPath : "python";
    execSync(`${execPath} scripts/sync_khuym_harness.py`, { stdio: "inherit", cwd: repoRoot });
  } catch (error) {
    // Fail silently or print error to stderr to not block the IDE pipeline
    process.stderr.write(`Sync Hook Warning: ${error.message}\n`);
  }

  process.stdout.write(JSON.stringify({ continue: true }));
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main();
}

