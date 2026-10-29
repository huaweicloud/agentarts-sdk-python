// Environment and configuration for the AgentArts Memory MCP server.
//
// Mirrors src/agentarts/toolkit/plugins/memory/agentarts_client.py and the
// hook scripts in resources/scripts/_shared.mjs: the server talks to the
// Huawei Cloud AgentArts Memory data-plane REST API directly.

export const ENV_API_KEY = "HUAWEICLOUD_SDK_MEMORY_API_KEY";
export const ENV_SPACE_ID = "AGENTARTS_MEMORY_SPACE_ID";
export const ENV_REGION = "HUAWEICLOUD_SDK_REGION";
export const ENV_REGION_ALT = "HUAWEICLOUD_REGION";
export const ENV_REGION_OS = "OS_REGION_NAME";
export const ENV_DATA_ENDPOINT = "AGENTARTS_MEMORY_DATA_ENDPOINT";
export const ENV_PLATFORM = "AGENTARTS_MEMORY_PLATFORM";
export const ENV_USER_ID = "AGENTARTS_MEMORY_USER_ID";
export const ENV_RERANK = "AGENTARTS_MEMORY_RERANK";

export const DEFAULT_REGION = "cn-southwest-2";
export const DEFAULT_TOP_K = 5;
export const DEFAULT_MIN_SCORE = 0.7;
export const DEFAULT_TIMEOUT_MS = 30_000;

/** Data-plane region: HUAWEICLOUD_SDK_REGION > HUAWEICLOUD_REGION > OS_REGION_NAME. */
export function getRegion(): string {
  return (
    process.env[ENV_REGION] ||
    process.env[ENV_REGION_ALT] ||
    process.env[ENV_REGION_OS] ||
    DEFAULT_REGION
  );
}

/** Data-plane base URL, overridable via AGENTARTS_MEMORY_DATA_ENDPOINT. */
export function getBaseUrl(): string {
  const explicit = process.env[ENV_DATA_ENDPOINT];
  if (explicit) return explicit.replace(/\/+$/, "");
  return `https://memory.${getRegion()}.huaweicloud-agentarts.com`;
}

export function getApiKey(): string {
  return process.env[ENV_API_KEY] || "";
}

export function getSpaceId(): string {
  return process.env[ENV_SPACE_ID] || "";
}

// ── platform detection (parity with the Python MCP server) ──

const PLATFORM_USER_ID: Record<string, string> = {
  "claude-code": "cc-user",
  codex: "codex-user",
  opencode: "opencode-user",
  unknown: "__default__",
};

export function detectPlatform(): string {
  const explicit = process.env[ENV_PLATFORM];
  if (explicit) return explicit;
  if (process.env.CLAUDE_PLUGIN_ROOT) return "claude-code";
  if (process.env.CODEX_PLUGIN_ROOT) return "codex";
  if (process.env.OPENCODE_PLUGIN_ROOT) return "opencode";
  return "unknown";
}

/** Search-result reranking. The backend enables rerank by default (SDK 0.1.9);
 *  this server turns it OFF by default — the operator opts in via env, the tool
 *  never exposes it to the model. Truthy values: "1" / "true" (case-insensitive). */
export function resolveRerank(): boolean {
  const v = process.env[ENV_RERANK];
  return v === "1" || (v ?? "").toLowerCase() === "true";
}

/** Resolve the memory actor: AGENTARTS_MEMORY_USER_ID > platform default. */
export function resolveUserId(): string {
  const explicit = process.env[ENV_USER_ID];
  if (explicit) return explicit;
  return PLATFORM_USER_ID[detectPlatform()] ?? "__default__";
}
