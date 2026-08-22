#!/usr/bin/env node
// PreCompact — inject relevant memories via stdout before context compression.
import {
  resolveProject,
  searchAndFormat,
  isSdkChildContext,
  resolveUserId,
  coerceText,
  formatOutput,
} from "./_shared.mjs";

async function main() {
  let input = "";
  for await (const chunk of process.stdin) input += chunk;
  let data;
  try { data = JSON.parse(input); } catch { return; }
  if (isSdkChildContext(data)) return;

  const cwd = data.cwd || process.cwd();
  const scopeId = resolveProject(cwd);
  const userId = resolveUserId(data);

  // Extract query from conversation (last user message).
  const messages = data.messages || [];
  let query = "";
  for (const m of messages) {
    if (m.role === "user") query = coerceText(m.content).slice(0, 500);
  }
  if (!query) query = scopeId;

  const context = await searchAndFormat(query, scopeId, userId);
  if (context) process.stdout.write(formatOutput(context, "preCompact"));
}

main();
