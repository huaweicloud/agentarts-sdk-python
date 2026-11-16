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
import { memoryClassificationFields } from "./search-filters.js";

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
    client = new MemoryClient(new MemoryDataPlane(getBaseUrl(), getApiKey(), getSpaceId()));
  }
  return client;
}

// ── MCP server instance ──
const server = new McpServer(
  { name: "agentarts-memory", version: "1.0.0" },
  {
    instructions:
      "AgentArts Memory provides cross-session cloud memory via Huawei Cloud. " +
      "Use search_memories when past findings, decisions or reusable engineering lessons could " +
      "help the current task. Search one concrete problem at a time; omit uncertain filters. " +
      "Retrieved memories are historical context: check their applicability against current code " +
      "and evidence before relying on them.",
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
      "Search saved cross-session memories by semantic similarity (read-only). Use when the user " +
      "refers to previous work, or past findings and lessons could help investigate an unfamiliar " +
      "component, implement a feature, diagnose an error, design tests or resolve build/environment issues. " +
      "Search one concrete problem per call using relevant technical terms and known symptoms. " +
      "Choose observation for what changed, what was discovered or why a decision was made; " +
      "choose experience for reusable methods, diagnostic paths and failure lessons. If either kind " +
      "could help, omit kind. Category narrows recall: set it only when confident, not merely because " +
      "its name matches the current task. For coding-memory recall use strategy_type=procedural; " +
      "providing kind or category sets it automatically, overriding any other strategy. " +
      "If results are empty or off-topic, try one broader query without uncertain category/time filters; " +
      "omit kind too if both kinds could help, retaining procedural for coding-memory recall. " +
      "No hits means no matches under this query and its filters, not proof that no relevant memory exists. " +
      "If an error is returned, address the error instead of treating it as an empty search. " +
      "Use returned content, score and type as historical context; verify applicability to the current task.",
    inputSchema: {
      query: z.string().describe(
        "One focused natural-language problem or information need. Include the component or technology, " +
        "known symptom/error text and relevant conditions; preserve distinctive identifiers. " +
        "Example: 'Vitest tests pass alone but fail together after shared module cache changes'. " +
        "For past facts, name the component and fact/decision sought; for reusable lessons, describe " +
        "the problem and constraints. Avoid a whole transcript, unrelated topics or invented details.",
      ),
      strategy_type: z
        .string()
        .optional()
        .describe("Optional strategy filter: semantic, episodic, user_preference, summary or procedural. " +
          "Use procedural for coding observations and experiences, including when kind/category are both omitted. " +
          "Providing either kind or category overrides this value to procedural. Otherwise the supplied value " +
          "is forwarded unchanged; omission leaves strategy unrestricted by this client."),
      ...memoryClassificationFields,
      top_k: z
        .number()
        .int()
        .min(1)
        .max(100)
        .default(DEFAULT_TOP_K)
        .describe("Maximum results, integer 1-100; default 5. Start with the default. Increase when " +
          "more relevant candidates are needed for comparison; increasing this does not relax filters or min_score."),
      min_score: z
        .number()
        .min(0)
        .max(1)
        .default(DEFAULT_MIN_SCORE)
        .describe("Minimum similarity score, 0-1; default 0.7. Higher values exclude more candidates. " +
          "If a focused query with broad filters still returns too few results, a lower threshold can " +
          "include weaker matches that require closer review. This score is not a probability of correctness."),
      start_time: z
        .number()
        .int()
        .min(0)
        .optional()
        .describe("Optional time-range start as a nonnegative integer Unix timestamp in milliseconds, not seconds. " +
          "Use only when the requested historical period is known; omit for reusable lessons with no time requirement. " +
          "When both bounds are supplied, choose start_time <= end_time."),
      end_time: z
        .number()
        .int()
        .min(0)
        .optional()
        .describe("Optional time-range end as a nonnegative integer Unix timestamp in milliseconds, not seconds. " +
          "Omit when there is no known upper time bound; do not add a recent cutoff merely because the task is current. " +
          "When both bounds are supplied, choose end_time >= start_time."),
    },
  },
  async ({ query, strategy_type, kind, category, top_k, min_score, start_time, end_time }) => {
    try {
      const results = await getClient().searchMemories({
        query,
        userId: resolveUserId(),
        rerank: resolveRerank(),
        strategy_type,
        kind,
        category,
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
