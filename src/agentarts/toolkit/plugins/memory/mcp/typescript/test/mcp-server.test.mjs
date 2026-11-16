// End-to-end tests for the AgentArts Memory MCP server.
//
// Spawns dist/index.mjs (the exact artifact an MCP host runs) against a mock
// AgentArts data plane, then asserts:
//   - MCP protocol behavior (initialize / tools/list / tools/call / errors)
//   - the exact REST wire format of search_memories: path, Bearer auth,
//     request body — the expected values mirror the Python SDK's data-plane
//     branch (agentarts/sdk/service/memory_service.py) and its normalization
//     layer (toolkit/plugins/memory/agentarts_client.py)
//
// No network access, no real credentials, no test dependencies (node:test).

import { after, before, describe, test } from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { once } from "node:events";

const SPACE = "sp-test-123";
const API_KEY = "test-key-xyz";
const USER = "cc-user";
const BASE = `/v1/core/spaces/${SPACE}`;

// Public contract expectations, deliberately independent of implementation constants.
const CATEGORIES_BY_KIND = {
  observation: ["bugfix", "feature", "refactor", "change", "discovery", "decision", "security_alert", "security_note", "sensitive"],
  experience: ["feature", "bugfix", "testing", "build-env"],
};
const ALL_CATEGORIES = ["bugfix", "feature", "refactor", "change", "discovery", "decision", "security_alert", "security_note", "sensitive", "testing", "build-env"];

// ── mock AgentArts data plane ─────────────────────────────────────────

let calls = [];

function mockHandler(req, res) {
  let body = "";
  req.on("data", (c) => (body += c));
  req.on("end", () => {
    calls.push({ method: req.method, url: req.url, auth: req.headers.authorization, body: body ? JSON.parse(body) : null });
    res.setHeader("content-type", "application/json");

    if (req.method === "POST" && req.url === `${BASE}/memories/search`) {
      const q = JSON.parse(body).query;
      if (q === "boom") {
        res.statusCode = 500;
        res.end(JSON.stringify({ error_code: "InternalError", error_msg: "backend exploded" }));
      } else {
        res.end(JSON.stringify({ records: [{ record: { content: "found it", strategy_type: "semantic" }, score: 0.88 }], total: 1 }));
      }
      return;
    }
    res.statusCode = 404;
    res.end(JSON.stringify({ error_code: "NotFound", error_msg: `unexpected path ${req.url}` }));
  });
}

// ── MCP server harness ────────────────────────────────────────────────

function startMcp(env) {
  const child = spawn("node", ["dist/index.mjs"], {
    stdio: ["pipe", "pipe", "ignore"],
    env: {
      ...process.env,
      HUAWEICLOUD_SDK_MEMORY_API_KEY: "",
      AGENTARTS_MEMORY_RERANK: "0",
      ...env,
    },
  });
  let nextId = 1;
  const pending = new Map();
  let buf = "";
  child.stdout.on("data", (d) => {
    buf += d;
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, i);
      buf = buf.slice(i + 1);
      if (!line.trim()) continue;
      const msg = JSON.parse(line);
      if (pending.has(msg.id)) {
        pending.get(msg.id)(msg);
        pending.delete(msg.id);
      }
    }
  });
  const rpc = (method, params) => {
    const id = nextId++;
    const p = Promise.race([
      new Promise((resolve) => pending.set(id, resolve)),
      new Promise((_, reject) => setTimeout(() => reject(new Error(`no response to ${method} #${id}`)), 5000)),
    ]);
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
    return p;
  };
  const callTool = async (name, args) => {
    const r = await rpc("tools/call", { name, arguments: args });
    return JSON.parse(r.result.content[0].text);
  };
  return {
    child,
    rpc,
    callTool,
    kill: () => child.kill(),
  };
}

// ── tests ─────────────────────────────────────────────────────────────

describe("agentarts-memory MCP server (with credentials)", () => {
  let httpServer, mcp;

  before(async () => {
    httpServer = createServer(mockHandler);
    await once(httpServer.listen(0, "127.0.0.1"), "listening");
    mcp = startMcp({
      AGENTARTS_MEMORY_DATA_ENDPOINT: `http://127.0.0.1:${httpServer.address().port}`,
      HUAWEICLOUD_SDK_MEMORY_API_KEY: API_KEY,
      AGENTARTS_MEMORY_SPACE_ID: SPACE,
      AGENTARTS_MEMORY_USER_ID: USER,
    });
    const init = await mcp.rpc("initialize", {
      protocolVersion: "2025-06-18",
      capabilities: {},
      clientInfo: { name: "test", version: "0.0.0" },
    });
    assert.equal(init.result.serverInfo.name, "agentarts-memory");
    mcp.child.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n");
  });

  after(() => {
    mcp.kill();
    httpServer.close();
  });

  test("initialize handshake reports server identity", async () => {
    const r = await mcp.rpc("initialize", {
      protocolVersion: "2025-06-18",
      capabilities: {},
      clientInfo: { name: "test", version: "0.0.0" },
    });
    assert.equal(r.result.serverInfo.name, "agentarts-memory");
    assert.equal(r.result.serverInfo.version, "1.0.0");
    assert.ok(r.result.capabilities.tools);
  });

  test("tools/list: only search_memories is exposed", async () => {
    const r = await mcp.rpc("tools/list");
    const tools = r.result.tools;
    assert.deepEqual(tools.map((t) => t.name), ["search_memories"]);
    // query is required; top_k/min_score have defaults and stay optional.
    assert.deepEqual(tools.find((t) => t.name === "search_memories").inputSchema.required, ["query"]);
    const props = tools.find((t) => t.name === "search_memories").inputSchema.properties;
    assert.deepEqual(Object.keys(props).sort(), [
      "category", "end_time", "kind", "min_score", "query", "start_time", "strategy_type", "top_k",
    ]);
    assert.equal(props.kind.type, "string");
    assert.deepEqual(props.kind.enum, ["observation", "experience"]);
    assert.equal(props.category.type, "string");
    assert.deepEqual(props.category.enum, ALL_CATEGORIES);
    assert.ok(!Object.hasOwn(props.kind, "default"));
    assert.ok(!Object.hasOwn(props.category, "default"));
  });

  test("search_memories: REST wire format (path, bearer auth, body defaults)", async () => {
    const out = await mcp.callTool("search_memories", { query: "hello world" });
    const call = calls.find((c) => c.url === `${BASE}/memories/search` && c.body.query === "hello world");
    assert.ok(call, "search endpoint was called");
    assert.equal(call.auth, `Bearer ${API_KEY}`);
    // Defaults mirror the Python server: top_k=5, min_score=0.7, actor_id from
    // env; rerank is pinned off unless the operator opts in. deepEqual is
    // strict, so this also proves the optional filters are omitted when unset.
    assert.deepEqual(call.body, { query: "hello world", top_k: 5, min_score: 0.7, actor_id: USER, rerank: false });
    // Normalized result: {content, score, type} from records[].record/score.
    assert.deepEqual(out.results, [{ content: "found it", score: 0.88, type: "semantic" }]);
    assert.equal(out.total, 1);
    assert.equal(out.query, "hello world");
  });

  test("search_memories: all six parameters are forwarded", async () => {
    await mcp.callTool("search_memories", {
      query: "custom k",
      strategy_type: "episodic",
      top_k: 12,
      min_score: 0.3,
      start_time: 1760000000000,
      end_time: 1770000000000,
    });
    const call = calls.find((c) => c.body?.query === "custom k");
    assert.deepEqual(call.body, {
      query: "custom k",
      strategy_type: "episodic",
      top_k: 12,
      min_score: 0.3,
      actor_id: USER,
      start_time: 1760000000000,
      end_time: 1770000000000,
      rerank: false,
    });
  });

  test("search_memories: all eight parameters reach the request body", async () => {
    const args = {
      query: "all eight parameters",
      strategy_type: "procedural",
      kind: "experience",
      category: "build-env",
      top_k: 12,
      min_score: 0.3,
      start_time: 1760000000000,
      end_time: 1770000000000,
    };
    await mcp.callTool("search_memories", args);
    const call = calls.find(c => c.body?.query === args.query);
    assert.ok(call);
    assert.deepEqual(call.body, { ...args, actor_id: USER, rerank: false });
  });

  for (const [kind, categories] of Object.entries(CATEGORIES_BY_KIND)) {
    test(`search_memories: kind=${kind} omits category and selects procedural`, async () => {
      const query = `kind only ${kind}`;
      await mcp.callTool("search_memories", { query, kind });
      const call = calls.find(c => c.body?.query === query);
      assert.ok(call);
      assert.deepEqual(call.body, {
        query, kind, strategy_type: "procedural", top_k: 5, min_score: 0.7,
        actor_id: USER, rerank: false,
      });
    });

    for (const category of categories) {
      test(`search_memories: forwards ${kind}/${category}`, async () => {
        const query = `pair ${kind}/${category}`;
        await mcp.callTool("search_memories", { query, kind, category });
        const call = calls.find(c => c.body?.query === query);
        assert.ok(call);
        assert.deepEqual(call.body, {
          query, kind, category, strategy_type: "procedural", top_k: 5, min_score: 0.7,
          actor_id: USER, rerank: false,
        });
      });
    }
  }

  for (const category of ALL_CATEGORIES) {
    test(`search_memories: category=${category} alone leaves kind unrestricted`, async () => {
      const query = `category only ${category}`;
      await mcp.callTool("search_memories", { query, category });
      const call = calls.find(c => c.body?.query === query);
      assert.ok(call);
      assert.deepEqual(call.body, {
        query, category, strategy_type: "procedural", top_k: 5, min_score: 0.7,
        actor_id: USER, rerank: false,
      });
    });
  }

  for (const filters of [
    { kind: "observation" },
    { category: "bugfix" },
    { kind: "experience", category: "testing" },
  ]) {
    test(`search_memories: ${JSON.stringify(filters)} overrides an explicit non-procedural strategy`, async () => {
      const query = `override ${JSON.stringify(filters)}`;
      await mcp.callTool("search_memories", { query, strategy_type: "semantic", ...filters });
      const call = calls.find(c => c.body?.query === query);
      assert.ok(call);
      assert.deepEqual(call.body, {
        query, ...filters, strategy_type: "procedural", top_k: 5, min_score: 0.7,
        actor_id: USER, rerank: false,
      });
    });
  }

  for (const field of ["kind", "category"]) {
    for (const value of ["unknown", "", "all", null, 1, true, [], {}, " feature "]) {
      test(`search_memories: rejects ${field}=${JSON.stringify(value)} without HTTP`, async () => {
        const countBefore = calls.length;
        const response = await mcp.rpc("tools/call", {
          name: "search_memories",
          arguments: { query: "invalid classification", [field]: value },
        });
        assert.ok(response.error || response.result?.isError, "invalid enum/type must produce an MCP error");
        assert.match(JSON.stringify(response.error ?? response.result), new RegExp(field));
        assert.equal(calls.length, countBefore, "invalid classification must not reach the backend");
      });
    }
  }

  for (const [kind, category] of [
    ["observation", "testing"],
    ["observation", "build-env"],
    ["experience", "discovery"],
    ["experience", "security_alert"],
  ]) {
    test(`search_memories: rejects mismatched ${kind}/${category} without HTTP`, async () => {
      const countBefore = calls.length;
      const out = await mcp.callTool("search_memories", { query: "mismatched classification", kind, category });
      assert.match(out.error, /not valid for kind/);
      assert.match(out.error, new RegExp(kind));
      assert.match(out.error, new RegExp(category));
      assert.deepEqual(out.results, []);
      assert.equal(out.total, 0);
      assert.equal(calls.length, countBefore, "mismatched category must not reach the backend");
    });
  }

  test("backend 5xx: tool returns an error payload, not a protocol error", async () => {
    const out = await mcp.callTool("search_memories", { query: "boom" });
    assert.match(out.error, /InternalError/);
    assert.match(out.error, /backend exploded/);
    assert.deepEqual(out.results, []);
    assert.equal(out.total, 0);
  });

  test("read-only: no session/message endpoints are ever called", () => {
    assert.ok(calls.length > 0);
    for (const c of calls) {
      assert.doesNotMatch(c.url, /\/sessions/, `write-path endpoint hit: ${c.url}`);
    }
  });

  test("unknown tool: JSON-RPC level error, no crash", async () => {
    const r = await mcp.rpc("tools/call", { name: "add_messages", arguments: { messages: [] } });
    assert.ok(r.error || r.result?.isError, "unknown tool must produce an error");
  });
});

describe("agentarts-memory MCP server (rerank enabled via env)", () => {
  let httpServer, mcp;

  before(async () => {
    httpServer = createServer(mockHandler);
    await once(httpServer.listen(0, "127.0.0.1"), "listening");
    mcp = startMcp({
      AGENTARTS_MEMORY_DATA_ENDPOINT: `http://127.0.0.1:${httpServer.address().port}`,
      HUAWEICLOUD_SDK_MEMORY_API_KEY: API_KEY,
      AGENTARTS_MEMORY_SPACE_ID: SPACE,
      AGENTARTS_MEMORY_USER_ID: USER,
      AGENTARTS_MEMORY_RERANK: "1",
    });
    await mcp.rpc("initialize", { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "test", version: "0.0.0" } });
  });

  after(() => {
    mcp.kill();
    httpServer.close();
  });

  test("AGENTARTS_MEMORY_RERANK=1 sends rerank: true in the search body", async () => {
    await mcp.callTool("search_memories", { query: "rerank on please" });
    const call = calls.find((c) => c.body?.query === "rerank on please");
    assert.ok(call, "search was called");
    assert.equal(call.body.rerank, true);
  });
});

describe("agentarts-memory MCP server (missing credentials)", () => {
  let mcp;

  before(async () => {
    // Endpoint points at an unreachable port — the auth check must fire first,
    // so no network access happens at all.
    mcp = startMcp({
      AGENTARTS_MEMORY_DATA_ENDPOINT: "http://127.0.0.1:1",
      AGENTARTS_MEMORY_SPACE_ID: SPACE,
      AGENTARTS_MEMORY_USER_ID: USER,
    });
    await mcp.rpc("initialize", { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "test", version: "0.0.0" } });
  });

  after(() => mcp.kill());

  test("tool call degrades to an error payload naming the missing env var", async () => {
    const out = await mcp.callTool("search_memories", { query: "anything" });
    assert.match(out.error, /HUAWEICLOUD_SDK_MEMORY_API_KEY/);
    assert.deepEqual(out.results, []);
    assert.equal(out.total, 0);
  });
});
