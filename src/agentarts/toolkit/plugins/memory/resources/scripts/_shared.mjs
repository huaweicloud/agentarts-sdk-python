// agentarts-memory-agent — shared utilities for hook scripts.
//
// Direct cloud REST integration: hook scripts call Huawei Cloud AgentArts
// Memory data-plane API directly via fetch(), without a local HTTP server.

import { execSync } from "node:child_process";
import { basename, join } from "node:path";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";

// Platform detection
// ---------------------------------------------------------------------------
export function detectPlatform() {
  if (process.env.AGENTARTS_MEMORY_PLATFORM) return process.env.AGENTARTS_MEMORY_PLATFORM;
  if (process.env.CLAUDE_PLUGIN_ROOT) return "claude-code";
  if (process.env.CODEX_PLUGIN_ROOT) return "codex";
  if (process.env.OPENCODE_PLUGIN_ROOT) return "opencode";
  return "unknown";
}

const PLATFORM_USER_ID = {
  "claude-code": "cc-user",
  "codex": "codex-user",
  "opencode": "opencode-user",
  "unknown": "__default__",
};

// ---------------------------------------------------------------------------
// Cloud config
// ---------------------------------------------------------------------------
const ENV_API_KEY = "HUAWEICLOUD_SDK_MEMORY_API_KEY";
const ENV_SPACE_ID = "AGENTARTS_MEMORY_SPACE_ID";
const ENV_REGION = "HUAWEICLOUD_SDK_REGION";
const ENV_DATA_ENDPOINT = "AGENTARTS_MEMORY_DATA_ENDPOINT";
const DEFAULT_REGION = "cn-southwest-2";
const ASSISTANT_ID = "agentarts-memory-agent";

export const DEBUG = process.env.AGENTARTS_MEMORY_DEBUG === "1";

export function getCloudBaseUrl() {
  const explicit = process.env[ENV_DATA_ENDPOINT];
  if (explicit) return explicit.replace(/\/$/, "");
  const region = process.env[ENV_REGION] || DEFAULT_REGION;
  return `https://memory.${region}.huaweicloud-agentarts.com`;
}

function getApiKey() {
  return process.env[ENV_API_KEY] || "";
}

function getSpaceId() {
  return process.env[ENV_SPACE_ID] || "";
}

export const DEFAULT_USER_ID =
  process.env.AGENTARTS_MEMORY_USER_ID || PLATFORM_USER_ID[detectPlatform()];

export function resolveUserId(payload) {
  if (process.env.AGENTARTS_MEMORY_USER_ID) return process.env.AGENTARTS_MEMORY_USER_ID;
  if (payload && typeof payload === "object") {
    const explicit = payload.user_id || payload.userId;
    if (explicit && typeof explicit === "string" && explicit.trim()) {
      return explicit.trim();
    }
  }
  return DEFAULT_USER_ID;
}

export const SEARCH_MEM_NUM = 5;
export const SEARCH_SUMMARY_NUM = 3;
export const DEFAULT_THRESHOLD = 0.3;

// ---------------------------------------------------------------------------
// Auth headers
// ---------------------------------------------------------------------------
export function authHeaders() {
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

function readSessionCache() {
  try {
    if (existsSync(SESSION_CACHE_FILE)) {
      return JSON.parse(readFileSync(SESSION_CACHE_FILE, "utf8"));
    }
  } catch {}
  return {};
}

function writeSessionCache(data) {
  try {
    mkdirSync(SESSION_CACHE_DIR, { recursive: true });
    writeFileSync(SESSION_CACHE_FILE, JSON.stringify(data, null, 2), "utf8");
  } catch {}
}

function getCachedSid(cache, cacheKey) {
  const entry = cache[cacheKey];
  if (!entry) return null;
  // Backwards compat: old format stored a plain string.
  if (typeof entry === "string") return null; // force re-create
  if (entry.sid && Date.now() - entry.ts < SESSION_TTL_MS) return entry.sid;
  return null;
}

function invalidateSession(scopeId, userId) {
  const cacheKey = `${scopeId}:${userId}`;
  const cache = readSessionCache();
  delete cache[cacheKey];
  writeSessionCache(cache);
}

export async function getSessionId(scopeId, userId) {
  const cacheKey = `${scopeId}:${userId}`;
  const cache = readSessionCache();
  const cached = getCachedSid(cache, cacheKey);
  if (cached) return cached;

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

// ---------------------------------------------------------------------------
// HTTP helpers — all calls go to cloud REST API directly
// ---------------------------------------------------------------------------
export async function post(path, body, timeoutMs = 3000) {
  const { ok } = await postWithStatus(path, body, timeoutMs);
}

export async function postWithStatus(path, body, timeoutMs = 3000) {
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
    if (DEBUG) console.error(`[agentarts] POST ${path} failed:`, e?.message || e);
  }
  return { ok: false, status: 0 };
}

export async function postJson(path, body, timeoutMs = 3000) {
  try {
    const baseUrl = getCloudBaseUrl();
    const opts = { method: "POST", headers: authHeaders(), body: JSON.stringify(body) };
    if (timeoutMs > 0) opts.signal = AbortSignal.timeout(timeoutMs);
    const res = await fetch(`${baseUrl}${path}`, opts);
    if (res.ok) return await res.json();
    if (DEBUG) console.error(`[agentarts] POST ${path} returned ${res.status}`);
  } catch (e) {
    if (DEBUG) console.error(`[agentarts] POST ${path} (json) failed:`, e?.message || e);
  }
  return null;
}

export async function getJson(path, timeoutMs = 2000) {
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
function epSearchMemories(spaceId) {
  return `/v1/core/spaces/${spaceId}/memories/search`;
}

function epListMemories(spaceId, limit, offset) {
  return `/v1/core/spaces/${spaceId}/memories?limit=${limit}&offset=${offset}`;
}

function epAddMessages(spaceId, sid) {
  return `/v1/core/spaces/${spaceId}/sessions/${sid}/messages`;
}

// ---------------------------------------------------------------------------
// Project resolution — scope_id = project basename for per-project isolation.
// ---------------------------------------------------------------------------
export function resolveProject(cwd) {
  const explicit = process.env.AGENTARTS_MEMORY_PROJECT_NAME;
  if (explicit && explicit.trim()) return explicit.trim();
  const dir = cwd && cwd.trim() ? cwd : process.cwd();
  try {
    const top = execSync("git rev-parse --show-toplevel", {
      cwd: dir,
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 500,
    }).toString().trim();
    if (top) return basename(top);
  } catch {}
  return basename(dir);
}

// ---------------------------------------------------------------------------
// High-level operations
// ---------------------------------------------------------------------------
export async function addMessages(messages, scopeId, userId = DEFAULT_USER_ID) {
  try {
    const spaceId = getSpaceId();
    if (!spaceId || !getApiKey()) return;
    const sid = await getSessionId(scopeId, userId);

    const sdkMsgs = messages.map(m => ({
      role: m.role,
      parts: [{ type: "text", text: m.content }],
      actor_id: userId,
      assistant_id: ASSISTANT_ID,
    }));

    const body = {
      messages: sdkMsgs,
      is_force_extract: false,
    };
    const { ok, status } = await postWithStatus(epAddMessages(spaceId, sid), body, 3000);

    // Session expired or deleted on the cloud side — invalidate cache and retry once.
    if (!ok && (status === 404 || status === 410)) {
      invalidateSession(scopeId, userId);
      const newSid = await getSessionId(scopeId, userId);
      await post(epAddMessages(spaceId, newSid), body, 3000);
    }
  } catch (e) {
    if (DEBUG) console.error(`[agentarts] addMessages failed:`, e?.message || e);
  }
}

/**
 * Combined search — calls cloud /memories/search and /memories (list),
 * merges into a formatted context string for stdout injection.
 */
export async function searchAndFormat(query, scopeId, userId = DEFAULT_USER_ID) {
  const spaceId = getSpaceId();
  if (!spaceId || !getApiKey()) return "";

  const [searchResult, listResult] = await Promise.all([
    postJson(epSearchMemories(spaceId), {
      query,
      top_k: SEARCH_MEM_NUM,
      min_score: DEFAULT_THRESHOLD,
      actor_id: userId,
    }),
    getJson(epListMemories(spaceId, Math.max(SEARCH_SUMMARY_NUM * 5, 10), 0), 2000),
  ]);

  // Parse search results (handle both "records" and "results" formats)
  const memItems = [];
  const rawResults = searchResult?.records || searchResult?.results || [];
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
  const summaryTypes = { summary: true, episodic: true, user_preference: true };
  const allItems = listResult?.items || [];
  const summaryItems = [];
  for (const m of allItems) {
    const type = m.strategy_type || m.memory_type || m.type || "";
    if (type in summaryTypes) {
      summaryItems.push({
        content: String(m.content || "").slice(0, 300),
        score: 0,
        type,
      });
    }
  }
  const finalSummaryItems = summaryItems.length > 0
    ? summaryItems
    : allItems.map(m => ({
        content: String(m.content || "").slice(0, 300),
        score: 0,
        type: m.strategy_type || m.memory_type || m.type || "",
      }));

  // Format output
  const lines = [];
  if (memItems.length) {
    lines.push("## Related Memories");
    for (const r of memItems) {
      const label = r.type ? `[${r.type}]` : "";
      lines.push(`- ${label} ${r.content} (score: ${r.score.toFixed(2)})`);
    }
  }
  if (finalSummaryItems.length) {
    if (lines.length) lines.push("");
    lines.push("## Related History Summaries");
    for (const r of finalSummaryItems.slice(0, SEARCH_SUMMARY_NUM)) {
      lines.push(`- ${r.content} (score: ${r.score.toFixed(2)})`);
    }
  }
  return lines.join("\n");
}

export async function healthCheck() {
  return Boolean(getApiKey() && getSpaceId());
}

// ---------------------------------------------------------------------------
// SDK child guard — prevents sub-agents from double-capturing.
// ---------------------------------------------------------------------------
export function isSdkChildContext(payload) {
  if (process.env.AGENTARTS_SDK_CHILD === "1") return true;
  if (!payload || typeof payload !== "object") return false;
  return payload.entrypoint === "sdk-ts";
}

// ---------------------------------------------------------------------------
// Output format
// ---------------------------------------------------------------------------
export function formatOutput(text, eventType = "generic") {
  return text || "";
}

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------
export function coerceText(content) {
  if (!content) return "";
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((b) => (typeof b === "string" ? b : b?.text || b?.content || ""))
      .filter(Boolean)
      .join(" ");
  }
  return String(content);
}
