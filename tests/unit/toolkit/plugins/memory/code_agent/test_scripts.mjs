// Node hook script tests — direct cloud REST integration.
// Uses node:test + a file-based fetch stub preload.
import { test } from "node:test";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { pathToFileURL } from "node:url";
import { writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import assert from "node:assert/strict";

const here = fileURLToPath(import.meta.url);
const path = await import("node:path");
const PLUGIN_ROOT = path.resolve(here, "..", "..", "..", "..", "..", "..", "..", "src", "agentarts", "toolkit", "plugins", "memory", "resources");
const SCRIPTS = path.join(PLUGIN_ROOT, "scripts");
const join = path.join;

const CLOUD_ENV = {
  HUAWEICLOUD_SDK_MEMORY_API_KEY: "test-api-key-abcdef-123456",
  AGENTARTS_MEMORY_SPACE_ID: "test-space-12345",
  HUAWEICLOUD_SDK_REGION: "cn-southwest-2",
};

function runHook(scriptName, stdinObj, env = {}) {
  const r = spawnSync(process.execPath, [join(SCRIPTS, scriptName)], {
    input: stdinObj ? JSON.stringify(stdinObj) : "",
    env: { ...process.env, ...env },
    encoding: "utf8",
    timeout: 10000,
  });
  return { stdout: r.stdout, stderr: r.stderr, code: r.status };
}

// Write a preload .mjs that patches globalThis.fetch with canned responses.
// Routes match by URL pathname prefix.
function writeFetchStubPreload(routes) {
  const dir = mkdtempSync(join(tmpdir(), "fetch-stub-"));
  const file = join(dir, "preload.mjs");
  const code = [
    "globalThis.__stubRoutes = " + JSON.stringify(routes) + ";",
    "globalThis.fetch = async (urlStr, opts) => {",
    "  const u = new URL(urlStr);",
    "  const key = u.pathname;",
    "  let body = null;",
    "  for (const k of Object.keys(globalThis.__stubRoutes)) {",
    "    if (key.includes(k)) { body = globalThis.__stubRoutes[k]; break; }",
    "  }",
    "  if (!body && globalThis.__stubRoutes['__default__']) { body = globalThis.__stubRoutes['__default__']; }",
    "  return { ok: true, json: async () => body || {} };",
    "};",
  ].join("\n") + "\n";
  writeFileSync(file, code);
  return file;
}

// ── _shared.mjs unit tests ────────────────────────────────────────
test("_shared.resolveProject uses explicit env override", async () => {
  const mod = await import(join(SCRIPTS, "_shared.mjs") + "?t=" + Date.now());
  process.env.AGENTARTS_MEMORY_PROJECT_NAME = "my-proj";
  assert.equal(mod.resolveProject("/some/cwd"), "my-proj");
  delete process.env.AGENTARTS_MEMORY_PROJECT_NAME;
});

test("_shared.formatOutput returns text for plain platform", async () => {
  const mod = await import(join(SCRIPTS, "_shared.mjs") + "?t=" + (Date.now() + 1));
  assert.equal(mod.formatOutput("hello", "userPromptSubmit"), "hello");
  assert.equal(mod.formatOutput("", "x"), "");
});

test("_shared.coerceText handles string and array", async () => {
  const mod = await import(join(SCRIPTS, "_shared.mjs") + "?t=" + (Date.now() + 2));
  assert.equal(mod.coerceText("abc"), "abc");
  assert.equal(mod.coerceText([{ text: "a" }, "b"]), "a b");
  assert.equal(mod.coerceText(""), "");
});

test("_shared.getCloudBaseUrl constructs from region", async () => {
  const mod = await import(join(SCRIPTS, "_shared.mjs") + "?t=" + (Date.now() + 3));
  process.env.HUAWEICLOUD_SDK_REGION = "cn-north-4";
  assert.equal(mod.getCloudBaseUrl(), "https://memory.cn-north-4.huaweicloud-agentarts.com");
  delete process.env.HUAWEICLOUD_SDK_REGION;
});

test("_shared.getCloudBaseUrl uses explicit endpoint env", async () => {
  const mod = await import(join(SCRIPTS, "_shared.mjs") + "?t=" + (Date.now() + 4));
  process.env.AGENTARTS_MEMORY_DATA_ENDPOINT = "https://custom.example.com";
  assert.equal(mod.getCloudBaseUrl(), "https://custom.example.com");
  delete process.env.AGENTARTS_MEMORY_DATA_ENDPOINT;
});

test("_shared.authHeaders includes Bearer token", async () => {
  const mod = await import(join(SCRIPTS, "_shared.mjs") + "?t=" + (Date.now() + 5));
  process.env.HUAWEICLOUD_SDK_MEMORY_API_KEY = "my-secret-key";
  const headers = mod.authHeaders();
  assert.equal(headers["Authorization"], "Bearer my-secret-key");
  assert.equal(headers["Content-Type"], "application/json");
  delete process.env.HUAWEICLOUD_SDK_MEMORY_API_KEY;
});

test("_shared.healthCheck returns true with env vars set", async () => {
  const mod = await import(join(SCRIPTS, "_shared.mjs") + "?t=" + (Date.now() + 6));
  process.env.HUAWEICLOUD_SDK_MEMORY_API_KEY = "key";
  process.env.AGENTARTS_MEMORY_SPACE_ID = "space";
  const result = await mod.healthCheck();
  assert.equal(result, true);
  delete process.env.HUAWEICLOUD_SDK_MEMORY_API_KEY;
  delete process.env.AGENTARTS_MEMORY_SPACE_ID;
});

test("_shared.healthCheck returns false without env vars", async () => {
  const mod = await import(join(SCRIPTS, "_shared.mjs") + "?t=" + (Date.now() + 7));
  delete process.env.HUAWEICLOUD_SDK_MEMORY_API_KEY;
  delete process.env.AGENTARTS_MEMORY_SPACE_ID;
  const result = await mod.healthCheck();
  assert.equal(result, false);
});

// ── _shared.mjs platform detection ────────────────────────────────
function importDefaultUserId(env) {
  const modUrl = pathToFileURL(join(SCRIPTS, "_shared.mjs")).href + "?t=" + Date.now();
  const r = spawnSync(process.execPath, ["-e",
    `import(${JSON.stringify(modUrl)}).then(m => console.log(m.DEFAULT_USER_ID))`,
  ], {
    env: { ...process.env, ...env },
    encoding: "utf8",
    timeout: 5000,
  });
  return r.stdout.trim();
}

test("_shared: AGENTARTS_MEMORY_PLATFORM=codex yields codex-user", () => {
  assert.equal(importDefaultUserId({ AGENTARTS_MEMORY_PLATFORM: "codex" }), "codex-user");
});

test("_shared: AGENTARTS_MEMORY_PLATFORM=claude-code yields cc-user", () => {
  assert.equal(importDefaultUserId({ AGENTARTS_MEMORY_PLATFORM: "claude-code" }), "cc-user");
});

test("_shared: AGENTARTS_MEMORY_USER_ID overrides platform default", () => {
  assert.equal(
    importDefaultUserId({ AGENTARTS_MEMORY_PLATFORM: "codex", AGENTARTS_MEMORY_USER_ID: "zrm" }),
    "zrm",
  );
});

test("_shared: no platform env yields __default__", () => {
  assert.equal(importDefaultUserId({
    AGENTARTS_MEMORY_PLATFORM: "",
    CLAUDE_PLUGIN_ROOT: "",
    CODEX_PLUGIN_ROOT: "",
    OPENCODE_PLUGIN_ROOT: "",
  }), "__default__");
});

// ── prompt-submit.mjs ─────────────────────────────────────────────
test("prompt-submit without credentials produces no stdout", () => {
  const r = runHook(
    "prompt-submit.mjs",
    { cwd: "/tmp", prompt: "hello world" },
    {
      HUAWEICLOUD_SDK_MEMORY_API_KEY: "",
      AGENTARTS_MEMORY_SPACE_ID: "",
    },
  );
  assert.equal(r.stdout, "");
});

test("prompt-submit with invalid JSON exits cleanly", () => {
  const r = spawnSync(process.execPath, [join(SCRIPTS, "prompt-submit.mjs")], {
    input: "not json",
    env: { ...process.env, ...CLOUD_ENV },
    encoding: "utf8",
    timeout: 10000,
  });
  assert.equal(r.status, 0);
  assert.equal(r.stdout, "");
});

test("prompt-submit injects memory context with stubbed fetch", () => {
  const preload = writeFetchStubPreload({
    "/sessions": { id: "test-session-id" },
    "/messages": { messages: [], count: 0 },
    "/memories/search": {
      records: [{ record: { content: "likes python", strategy_type: "semantic" }, score: 0.9 }],
      total: 1,
    },
    "/memories": {
      items: [{ id: "m1", content: "summary text", strategy_type: "episodic", created_at: "t" }],
      total: 1,
    },
  });
  const r = spawnSync(process.execPath, ["--import", preload, join(SCRIPTS, "prompt-submit.mjs")], {
    input: JSON.stringify({ cwd: "/tmp", prompt: "python" }),
    env: { ...process.env, ...CLOUD_ENV },
    encoding: "utf8",
    timeout: 10000,
  });
  assert.ok(r.stdout.includes("Related Memories"), "stdout: " + r.stdout + " stderr: " + r.stderr);
  assert.ok(r.stdout.includes("likes python"));
  assert.ok(r.stdout.includes("semantic"));
});

// ── pre-compact.mjs ───────────────────────────────────────────────
test("pre-compact without credentials produces no stdout", () => {
  const r = runHook(
    "pre-compact.mjs",
    { cwd: "/tmp", messages: [{ role: "user", content: "compress me" }] },
    {
      HUAWEICLOUD_SDK_MEMORY_API_KEY: "",
      AGENTARTS_MEMORY_SPACE_ID: "",
    },
  );
  assert.equal(r.stdout, "");
});

test("pre-compact exits 0 with valid input", () => {
  const r = runHook(
    "pre-compact.mjs",
    { cwd: "/tmp", messages: [] },
    CLOUD_ENV,
  );
  assert.equal(r.code, 0);
});

test("pre-compact injects memory with stubbed fetch", () => {
  const preload = writeFetchStubPreload({
    "/memories/search": {
      records: [{ record: { content: "past decision", strategy_type: "episodic" }, score: 0.8 }],
      total: 1,
    },
    "/memories": { items: [], total: 0 },
  });
  const r = spawnSync(process.execPath, ["--import", preload, join(SCRIPTS, "pre-compact.mjs")], {
    input: JSON.stringify({
      cwd: "/tmp",
      messages: [{ role: "user", content: "keep context" }],
    }),
    env: { ...process.env, ...CLOUD_ENV },
    encoding: "utf8",
    timeout: 10000,
  });
  assert.ok(r.stdout.includes("Related Memories"), "stdout: " + r.stdout + " stderr: " + r.stderr);
  assert.ok(r.stdout.includes("past decision"));
});
