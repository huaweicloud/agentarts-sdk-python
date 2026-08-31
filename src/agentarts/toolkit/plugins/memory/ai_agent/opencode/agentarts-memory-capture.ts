// agentarts-memory-agent OpenCode plugin — direct cloud REST integration.
//
// Drop this file into ~/.config/opencode/plugins/ and reference it in
// ~/.config/opencode/opencode.json:
//   { "plugin": ["./plugins/agentarts-memory-capture.ts"] }

import type { Plugin } from "@opencode-ai/plugin";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// ---------------------------------------------------------------------------
// Cloud config
// ---------------------------------------------------------------------------
const ENV_API_KEY = "HUAWEICLOUD_SDK_MEMORY_API_KEY";
const ENV_SPACE_ID = "AGENTARTS_MEMORY_SPACE_ID";
const ENV_REGION = "HUAWEICLOUD_SDK_REGION";
const ENV_DATA_ENDPOINT = "AGENTARTS_MEMORY_DATA_ENDPOINT";
const DEFAULT_REGION = "cn-southwest-2";
const ASSISTANT_ID = "agentarts-memory-agent";

const DEBUG = process.env.AGENTARTS_MEMORY_DEBUG === "1";

function getCloudBaseUrl(): string {
  const explicit = process.env[ENV_DATA_ENDPOINT];
  if (explicit) return explicit.replace(/\/$/, "");
  const region = process.env[ENV_REGION] || DEFAULT_REGION;
  return `https://memory.${region}.huaweicloud-agentarts.com`;
}

function getApiKey(): string {
  return process.env[ENV_API_KEY] || "";
}

function getSpaceId(): string {
  return process.env[ENV_SPACE_ID] || "";
}

function detectOpenCodePlatform(): string {
  if (process.env.OPENCODE_PLUGIN_ROOT) return "opencode";
  return "opencode";
}

const PLATFORM_USER_ID: Record<string, string> = {
  "opencode": "opencode-user",
  "unknown": "__default__",
};

let _cachedDefaultUserId: string | null = null;
function getDefaultUserId(): string {
  if (_cachedDefaultUserId === null) {
    _cachedDefaultUserId = process.env.AGENTARTS_MEMORY_USER_ID || PLATFORM_USER_ID[detectOpenCodePlatform()];
  }
  return _cachedDefaultUserId;
}

const SEARCH_MEM_NUM = 5;
const SEARCH_SUMMARY_NUM = 3;
const DEFAULT_THRESHOLD = 0.3;

function resolveUserId(payload: unknown): string {
  if (payload && typeof payload === "object") {
    const explicit = (payload as any).user_id || (payload as any).userId;
    if (explicit && typeof explicit === "string" && explicit.trim()) {
      return explicit.trim();
    }
  }
  return getDefaultUserId();
}

function authHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${getApiKey()}`,
  };
}

// ---------------------------------------------------------------------------
// Session cache (file-based, cross-process)
// ---------------------------------------------------------------------------
const SESSION_CACHE_DIR = join(tmpdir(), "agentarts_memory");
const SESSION_CACHE_FILE = join(SESSION_CACHE_DIR, "sessions.json");
const SESSION_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

function readSessionCache(): Record<string, unknown> {
  try {
    if (existsSync(SESSION_CACHE_FILE)) {
      return JSON.parse(readFileSync(SESSION_CACHE_FILE, "utf8"));
    }
  } catch {}
  return {};
}

function writeSessionCache(data: Record<string, unknown>): void {
  try {
    mkdirSync(SESSION_CACHE_DIR, { recursive: true });
    writeFileSync(SESSION_CACHE_FILE, JSON.stringify(data, null, 2), "utf8");
  } catch {}
}

async function getSessionId(scopeId: string, userId: string): Promise<string> {
  const cacheKey = `${scopeId}:${userId}`;
  const cache = readSessionCache();
  const entry = cache[cacheKey];
  // Backwards compat: old format stored a plain string; force re-create.
  if (entry && typeof entry === "object" && entry.sid) {
    const e = entry as { sid: string; ts: number };
    if (Date.now() - e.ts < SESSION_TTL_MS) return e.sid;
  }

  const baseUrl = getCloudBaseUrl();
  const spaceId = getSpaceId();
  const res = await fetch(`${baseUrl}/v1/core/spaces/${spaceId}/sessions`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ actor_id: userId, assistant_id: ASSISTANT_ID }),
    signal: AbortSignal.timeout(3000),
  });
  if (!res.ok) throw new Error(`create session failed: ${res.status}`);
  const data = await res.json();
  const sid = data.id || data.session_id || "";
  if (!sid) throw new Error("create session returned empty id");

  cache[cacheKey] = { sid, ts: Date.now() };
  writeSessionCache(cache);
  return sid;
}

function invalidateSession(scopeId: string, userId: string): void {
  const cacheKey = `${scopeId}:${userId}`;
  const cache = readSessionCache();
  delete cache[cacheKey];
  writeSessionCache(cache);
}

// ---------------------------------------------------------------------------
// HTTP helpers — all calls go to cloud REST API directly
// ---------------------------------------------------------------------------
async function post(path: string, body: Record<string, unknown>, timeoutMs = 3000): Promise<void> {
  await postWithStatus(path, body, timeoutMs);
}

async function postWithStatus(path: string, body: Record<string, unknown>, timeoutMs = 3000): Promise<{ ok: boolean; status: number }> {
  try {
    const baseUrl = getCloudBaseUrl();
    const res = await fetch(`${baseUrl}${path}`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (DEBUG && !res.ok) console.error(`[agentarts] POST ${path} returned ${res.status}`);
    return { ok: res.ok, status: res.status };
  } catch (e) {
    if (DEBUG) console.error(`[agentarts] POST ${path} failed:`, (e as Error).message);
  }
  return { ok: false, status: 0 };
}

async function postJson(path: string, body: Record<string, unknown>, timeoutMs = 3000): Promise<unknown | null> {
  try {
    const baseUrl = getCloudBaseUrl();
    const opts: RequestInit = { method: "POST", headers: authHeaders(), body: JSON.stringify(body) };
    if (timeoutMs > 0) opts.signal = AbortSignal.timeout(timeoutMs);
    const res = await fetch(`${baseUrl}${path}`, opts);
    if (res.ok) return await res.json();
    if (DEBUG) console.error(`[agentarts] POST ${path} returned ${res.status}`);
  } catch (e) {
    if (DEBUG) console.error(`[agentarts] POST ${path} (json) failed:`, (e as Error).message);
  }
  return null;
}

async function getJson(path: string, timeoutMs = 2000): Promise<unknown | null> {
  try {
    const baseUrl = getCloudBaseUrl();
    const res = await fetch(`${baseUrl}${path}`, {
      method: "GET",
      headers: authHeaders(),
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (res.ok) return await res.json();
  } catch {}
  return null;
}

// ---------------------------------------------------------------------------
// Cloud REST path builders
// ---------------------------------------------------------------------------
function epSearchMemories(spaceId: string): string {
  return `/v1/core/spaces/${spaceId}/memories/search`;
}

function epListMemories(spaceId: string, limit: number, offset: number): string {
  return `/v1/core/spaces/${spaceId}/memories?limit=${limit}&offset=${offset}`;
}

function epAddMessages(spaceId: string, sid: string): string {
  return `/v1/core/spaces/${spaceId}/sessions/${sid}/messages`;
}

// ---------------------------------------------------------------------------
// High-level operations
// ---------------------------------------------------------------------------
async function addMessages(
  messages: Array<{ role: string; content: string }>,
  scopeId: string,
  userId = getDefaultUserId(),
): Promise<void> {
  try {
    const spaceId = getSpaceId();
    if (!spaceId || !getApiKey()) return;
    const sid = await getSessionId(scopeId, userId);

    const sdkMsgs = messages.map((m) => ({
      role: m.role,
      parts: [{ type: "text", text: m.content }],
      actor_id: userId,
      assistant_id: ASSISTANT_ID,
    }));

    const body = {
      messages: sdkMsgs,
      is_force_extract: false,
    };
    const { ok, status } = await postWithStatus(epAddMessages(spaceId, sid), body);

    // Session expired or deleted on the cloud side — invalidate cache and retry once.
    if (!ok && (status === 404 || status === 410)) {
      invalidateSession(scopeId, userId);
      const newSid = await getSessionId(scopeId, userId);
      await post(epAddMessages(spaceId, newSid), body);
    }
  } catch (e) {
    if (DEBUG) console.error(`[agentarts] addMessages failed:`, (e as Error).message);
  }
}

async function searchAndFormat(
  query: string,
  scopeId: string,
  userId = getDefaultUserId(),
): Promise<string> {
  const spaceId = getSpaceId();
  if (!spaceId || !getApiKey()) return "";

  const [searchResult, listResult] = await Promise.all([
    postJson(epSearchMemories(spaceId), {
      query,
      top_k: SEARCH_MEM_NUM,
      min_score: DEFAULT_THRESHOLD,
      actor_id: userId,
    }),
    getJson(epListMemories(spaceId, Math.max(SEARCH_SUMMARY_NUM * 5, 10), 0)),
  ]);

  // Parse search results (handle both "records" and "results" formats)
  const memItems: Array<Record<string, unknown>> = [];
  const rawResults = (searchResult as any)?.records || (searchResult as any)?.results || [];
  for (const item of rawResults) {
    const record = item.record || item;
    const content = record.content || record.text || record.summary || "";
    const score = item.score || 0;
    const type = record.strategy_type || record.memory_type || record.type || "";
    memItems.push({
      content: String(content).slice(0, 300),
      score: Number(score),
      type,
    });
  }

  // Parse list results for summary types
  const summaryTypes: Record<string, boolean> = { summary: true, episodic: true, user_preference: true };
  const allItems = (listResult as any)?.items || [];
  const summaryItems: Array<Record<string, unknown>> = [];
  for (const m of allItems) {
    const type = m.strategy_type || m.memory_type || m.type || "";
    if (type in summaryTypes) {
      summaryItems.push({ content: String(m.content || "").slice(0, 300), score: 0, type });
    }
  }
  const finalSummaryItems = summaryItems.length > 0
    ? summaryItems
    : allItems.map((m: any) => ({
        content: String(m.content || "").slice(0, 300),
        score: 0,
        type: m.strategy_type || m.memory_type || m.type || "",
      }));

  const lines: string[] = [];
  if (memItems.length) {
    lines.push("## Related Memories");
    for (const r of memItems) {
      const label = r.type ? `[${r.type}]` : "";
      lines.push(`- ${label} ${r.content} (score: ${Number(r.score || 0).toFixed(2)})`);
    }
  }
  if (finalSummaryItems.length) {
    if (lines.length) lines.push("");
    lines.push("## Related History Summaries");
    for (const r of finalSummaryItems.slice(0, SEARCH_SUMMARY_NUM)) {
      lines.push(`- ${r.content} (score: ${Number(r.score || 0).toFixed(2)})`);
    }
  }
  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// System prompt instructions
// ---------------------------------------------------------------------------
const AGENTARTS_INSTRUCTIONS = `<agentarts-memory-instructions>
You have access to Huawei Cloud AgentArts Memory for persistent cross-session memory.

Relevant memories are automatically injected before each turn. The conversation prompt
is recorded to cloud memory after each user turn.

Use /recall [query] to search past memories, and /remember [content] to explicitly save.
Never fabricate memory results — only present what the tools return.
</agentarts-memory-instructions>`;

// ---------------------------------------------------------------------------
// Session state
// ---------------------------------------------------------------------------
let activeSessionId: string | null = null;
let sessionUserId: string | null = null;
const DEFAULT_SCOPE_ID = process.env.AGENTARTS_MEMORY_PROJECT_NAME || "opencode-default";
let projectScopeId: string = DEFAULT_SCOPE_ID;
const contextInjectedSessions = new Set<string>();
const sessionLastUserQuery = new Map<string, string>();
const sessionPendingAdd = new Map<string, string>();
const sessionSearchResult = new Map<string, string>();

// ---------------------------------------------------------------------------
// Plugin
// ---------------------------------------------------------------------------
export const AgentArtsMemoryCapturePlugin: Plugin = async (ctx) => {
  const cwd = ctx.worktree || ctx.project?.id || "";
  if (cwd) {
    const raw = cwd.replace(/[\\/]+$/, "");
    const derived = raw.split(/[\\/]/).pop()?.trim();
    if (derived) projectScopeId = derived;
  }

  const getUserId = () => sessionUserId || resolveUserId(ctx);

  return {
    event: async ({ event }) => {
      const type = event.type;
      const props = (event as any).properties || {};

      // ── session.created ──
      if (type === "session.created") {
        const info = props.info as Record<string, unknown> | undefined;
        activeSessionId = (info?.id as string) || props.sessionID || null;
        if (!activeSessionId) return;

        sessionUserId = resolveUserId(props);

        contextInjectedSessions.delete(activeSessionId);
        sessionLastUserQuery.delete(activeSessionId);
        sessionPendingAdd.delete(activeSessionId);
        sessionSearchResult.delete(activeSessionId);
      }

      // ── session.deleted ──
      if (type === "session.deleted") {
        const sid = (props.info as any)?.id || props.sessionID || activeSessionId;
        if (sid) {
          if (sid === activeSessionId) {
            activeSessionId = null;
            sessionUserId = null;
          }
          contextInjectedSessions.delete(sid);
          sessionLastUserQuery.delete(sid);
          sessionPendingAdd.delete(sid);
          sessionSearchResult.delete(sid);
        }
      }

      // ── message.updated (assistant) ──
      if (type === "message.updated") {
        const info = props.info as Record<string, unknown> | undefined;
        if (!info) return;
        if (info.role === "assistant") {
          const sid = props.sessionID || (info.sessionID as string) || activeSessionId;
          if (!sid) return;
          const pendingQuery = sessionPendingAdd.get(sid);
          if (!pendingQuery) return;
          sessionPendingAdd.delete(sid);
          await addMessages(
            [{ role: "user", content: pendingQuery }],
            `${projectScopeId}:${sid}`,
            getUserId(),
          );
        }
      }
    },

    "chat.message": async (input: any, output: any) => {
      const sid = input.sessionID || activeSessionId;
      if (!sid) return;

      const parts = output.parts || [];
      const textParts = parts.filter(
        (p: any) => p.type === "text" && !p.synthetic && !p.ignored,
      );
      const userText = textParts.map((p: any) => p.text || "").join("\n");
      if (!userText) return;

      const query = userText.slice(0, 2000);

      sessionLastUserQuery.set(sid, query);
      sessionPendingAdd.set(sid, userText.slice(0, 8000));

      const searchResult = await searchAndFormat(query, projectScopeId, getUserId());
      if (searchResult) sessionSearchResult.set(sid, searchResult);
      else sessionSearchResult.delete(sid);
    },

    "experimental.chat.system.transform": async (input: any, output: any) => {
      const sid = input.sessionID || activeSessionId;
      if (!sid) return;
      if (!Array.isArray(output.system)) return;

      if (!contextInjectedSessions.has(sid)) {
        output.system.push(AGENTARTS_INSTRUCTIONS);
        contextInjectedSessions.add(sid);
      }

      const cachedResult = sessionSearchResult.get(sid);
      if (cachedResult) {
        output.system.push(cachedResult);
      }
    },

    "experimental.session.compacting": async (input: any, output: any) => {
      const sid = input.sessionID || activeSessionId;
      if (!sid) return;

      const cachedResult = sessionSearchResult.get(sid);
      const context =
        cachedResult ||
        (sessionLastUserQuery.has(sid)
          ? await searchAndFormat(sessionLastUserQuery.get(sid)!, projectScopeId, getUserId())
          : "");
      if (context && Array.isArray(output.context)) {
        output.context.push(context);
      }
    },

    config: async (input: any) => {
      if (DEBUG) {
        console.error("[agentarts] config loaded:", { theme: input.theme, model: input.model });
      }
    },
  };
};
