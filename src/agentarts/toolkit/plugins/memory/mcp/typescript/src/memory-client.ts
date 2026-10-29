// High-level memory operations — TypeScript port of
// src/agentarts/toolkit/plugins/memory/agentarts_client.py, calling the
// data-plane REST API directly instead of the Python SDK.
//
// Read-only search. Writing (add_messages) stays with the platform
// hooks/plugins, so this server needs no session management.

import { DEFAULT_MIN_SCORE, DEFAULT_TOP_K } from "./config.js";
import { MemoryDataPlane, SearchRecord, SearchRequestBody } from "./api.js";

export interface SearchItem {
  content: string;
  score: number;
  type: string;
}

// ── normalization helpers (parity with the Python client) ──

function extractContent(record: unknown): string {
  if (record === null || record === undefined) return "";
  if (typeof record === "string") return record;
  if (typeof record === "object") {
    const r = record as Record<string, unknown>;
    for (const key of ["content", "text", "summary", "message"]) {
      const val = r[key];
      if (val) return String(val);
    }
    // nested record
    const inner = r["record"];
    if (inner) return extractContent(inner);
  }
  return String(record);
}

function extractType(record: unknown): string {
  if (typeof record === "object" && record !== null) {
    const r = record as Record<string, unknown>;
    for (const key of ["strategy_type", "memory_type", "type", "strategy"]) {
      const val = r[key];
      if (val) return String(val);
    }
    const inner = r["record"];
    if (typeof inner === "object" && inner !== null) return extractType(inner);
  }
  return "";
}

function normalizeSearchResults(resp: { records?: SearchRecord[]; results?: SearchRecord[] }): SearchItem[] {
  const raw = resp.records ?? resp.results ?? [];
  return raw.map((item) => {
    const rec = (item ?? {}) as SearchRecord;
    const record = rec.record !== undefined ? rec.record : rec;
    return {
      content: extractContent(record),
      score: typeof rec.score === "number" ? rec.score : 0,
      type: extractType(record),
    };
  });
}

export interface SearchOptions {
  query: string;
  userId: string;
  /** Rerank is backend-ON by default; the server resolves this from
   *  AGENTARTS_MEMORY_RERANK (default off) — same flow as userId. */
  rerank?: boolean;
  strategy_type?: string;
  top_k?: number;
  min_score?: number;
  start_time?: number;
  end_time?: number;
}

export class MemoryClient {
  constructor(private readonly api: MemoryDataPlane) {}

  /** Semantic search; optional filters are omitted from the body when unset
   *  (same as the Python SDK's MemorySearchFilter.to_dict). */
  async searchMemories(opts: SearchOptions): Promise<SearchItem[]> {
    const body: SearchRequestBody = {
      query: opts.query,
      top_k: opts.top_k ?? DEFAULT_TOP_K,
      min_score: opts.min_score ?? DEFAULT_MIN_SCORE,
      actor_id: opts.userId,
    };
    body.rerank = opts.rerank ?? false;
    if (opts.strategy_type !== undefined) body.strategy_type = opts.strategy_type;
    if (opts.start_time !== undefined) body.start_time = opts.start_time;
    if (opts.end_time !== undefined) body.end_time = opts.end_time;
    const resp = await this.api.searchMemories(body);
    return normalizeSearchResults(resp);
  }
}
