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
    env: { ...process.env, ...env },
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
      "end_time", "min_score", "query", "start_time", "strategy_type", "top_k",
    ]);
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
