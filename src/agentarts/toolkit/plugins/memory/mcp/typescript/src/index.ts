#!/usr/bin/env node
// AgentArts Memory MCP server (TypeScript) — stdio transport.
//
// TypeScript port of src/agentarts/toolkit/plugins/memory/mcp/server.py.
// Instead of wrapping the Python agentarts SDK, this server calls the
// Huawei Cloud AgentArts Memory data-plane REST API directly (the same
// endpoints as resources/scripts/_shared.mjs).
//
// Exposes a single MCP tool. Read-only by design: writing is handled by the
// platform hooks/plugins, so this server needs no session management:
//   - search_memories — semantic search of cloud memories
//
// Lifecycle is managed by the platform (Claude Code / Codex / OpenCode):
// the platform launches this binary as a subprocess and communicates via
// stdin/stdout JSON-RPC.

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

import {
  DEFAULT_MIN_SCORE,
  DEFAULT_TOP_K,
  getApiKey,
  getBaseUrl,
  getSpaceId,
  resolveRerank,
  resolveUserId,
} from "./config.js";
import { MemoryDataPlane } from "./api.js";
import { MemoryClient } from "./memory-client.js";

// All logging goes to stderr — stdout carries the JSON-RPC stream.
function log(...args: unknown[]): void {
  console.error("[agentarts-memory]", ...args);
}

function errorText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

// ── shared client instance ──
let client: MemoryClient | null = null;

function getClient(): MemoryClient {
  if (client === null) {
    client = new MemoryClient(
      new MemoryDataPlane(getBaseUrl(), getApiKey(), getSpaceId()),
      resolveRerank(),
    );
  }
  return client;
}

// ── MCP server instance ──
const server = new McpServer(
  { name: "agentarts-memory", version: "1.0.0" },
  {
    instructions:
      "AgentArts Memory provides cross-session cloud memory via Huawei Cloud. " +
      "Use search_memories to find relevant past context.",
  },
);

function jsonResult(payload: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(payload, null, 2) }] };
}

// ── Tool: search_memories ──
server.registerTool(
  "search_memories",
  {
    description:
      "Search cloud memories by semantic similarity. Optional filters: " +
      "strategy_type (memory type: semantic, episodic, user_preference, summary " +
      "or procedural — other values are rejected by the backend), " +
      "start_time/end_time (Unix milliseconds).",
    inputSchema: {
      query: z.string().describe("Natural-language search query."),
      strategy_type: z
        .string()
        .optional()
        .describe("Filter by memory type: semantic, episodic, user_preference, summary or procedural."),
      top_k: z
        .number()
        .int()
        .min(1)
        .max(100)
        .default(DEFAULT_TOP_K)
        .describe("Maximum results to return (1-100)."),
      min_score: z
        .number()
        .min(0)
        .max(1)
        .default(DEFAULT_MIN_SCORE)
        .describe("Minimum similarity score (0.0-1.0)."),
      start_time: z
        .number()
        .int()
        .min(0)
        .optional()
        .describe("Time range start, Unix timestamp in milliseconds."),
      end_time: z
        .number()
        .int()
        .min(0)
        .optional()
        .describe("Time range end, Unix timestamp in milliseconds."),
    },
  },
  async ({ query, strategy_type, top_k, min_score, start_time, end_time }) => {
    try {
      const results = await getClient().searchMemories({
        query,
        userId: resolveUserId(),
        strategy_type,
        top_k,
        min_score,
        start_time,
        end_time,
      });
      return jsonResult({ results, total: results.length, query });
    } catch (e) {
      log("search_memories failed:", errorText(e));
      return jsonResult({ error: errorText(e), results: [], total: 0 });
    }
  },
);

// ── entry point ──
async function main(): Promise<void> {
  if (!getSpaceId() || !getApiKey()) {
    const missing = [!getSpaceId() && "AGENTARTS_MEMORY_SPACE_ID", !getApiKey() && "HUAWEICLOUD_SDK_MEMORY_API_KEY"]
      .filter(Boolean)
      .join(", ");
    log(`warning: missing configuration: ${missing}`);
  }

  const transport = new StdioServerTransport();
  await server.connect(transport);
  log(`MCP server (typescript) running on stdio, endpoint=${getBaseUrl()}, rerank=${resolveRerank()}`);
}

main().catch((e) => {
  log("fatal:", errorText(e));
  process.exit(1);
});
