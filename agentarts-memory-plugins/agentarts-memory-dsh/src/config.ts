/** Validated configuration for the AgentArts Memory DSH plugin. */

import z from '@deepseek-ai/schemastery'

export const DEFAULT_REGION = 'cn-southwest-2'
export const DEFAULT_ASSISTANT_ID = 'deepseek-harness'
export const DEFAULT_REQUEST_TIMEOUT_MS = 30_000
export const DEFAULT_MAX_RETRIES = 2
export const DEFAULT_RETRY_BASE_DELAY_MS = 250
export const DEFAULT_MCP_SERVER_NAME = 'agentarts-memory'
export const DEFAULT_MCP_COMMAND = 'agentarts-memory-mcp'
export const DEFAULT_MCP_ARGS: string[] = []
export const DEFAULT_MCP_CWD = process.cwd()
export const DEFAULT_MCP_TOOL_CALL_TIMEOUT_MS = 60_000

/** User configuration accepted from `cordis.yml`. */
export interface Config {
  /** AgentArts Memory data-plane API key. */
  apiKey: string
  /** Existing AgentArts Memory Space id. */
  spaceId: string
  /** Stable human or tenant identity recorded on synchronized sessions and messages. */
  actorId: string
  /** Stable assistant identity recorded on synchronized messages. */
  assistantId?: string
  /** Huawei Cloud region used to derive the data endpoint. */
  region?: string
  /** Explicit AgentArts Memory data endpoint, primarily for private endpoints and tests. */
  dataEndpoint?: string
  /** Per-request timeout for session creation and turn writes. */
  requestTimeoutMs?: number
  /** Number of retries after a retryable data-plane failure. */
  maxRetries?: number
  /** Initial exponential retry delay. */
  retryBaseDelayMs?: number
  /** Force memory extraction after every synchronized turn. */
  forceExtract?: boolean
  /** Start the AgentArts search-only MCP server and expose its tools. */
  mcpEnabled?: boolean
  /** Namespace used in `mcp__<serverName>__ltm_search`. */
  mcpServerName?: string
  /** Installed executable that starts the AgentArts Memory MCP server. */
  mcpCommand?: string
  /** Arguments passed directly to the MCP executable. */
  mcpArgs?: string[]
  /** Working directory for the MCP child. */
  mcpCwd?: string
  /** Timeout for each model-initiated MCP search. */
  mcpToolCallTimeoutMs?: number
  /** Fail plugin activation if MCP search cannot be discovered at startup. */
  mcpFailOnStartupError?: boolean
}

/** Complete values consumed by the runtime. */
export interface ResolvedConfig {
  apiKey: string
  spaceId: string
  actorId: string
  assistantId: string
  region: string
  dataEndpoint: string
  requestTimeoutMs: number
  maxRetries: number
  retryBaseDelayMs: number
  forceExtract: boolean
  mcpEnabled: boolean
  mcpServerName: string
  mcpCommand: string
  mcpArgs: string[]
  mcpCwd: string
  mcpToolCallTimeoutMs: number
  mcpFailOnStartupError: boolean
}

/** Cordis configuration schema. */
export const Config: z<Config> = z.object({
  apiKey: z.string().required(),
  spaceId: z.string().required(),
  actorId: z.string().required(),
  assistantId: z.string().default(DEFAULT_ASSISTANT_ID),
  region: z.string().default(DEFAULT_REGION),
  dataEndpoint: z.string(),
  requestTimeoutMs: z.number().default(DEFAULT_REQUEST_TIMEOUT_MS),
  maxRetries: z.number().default(DEFAULT_MAX_RETRIES),
  retryBaseDelayMs: z.number().default(DEFAULT_RETRY_BASE_DELAY_MS),
  forceExtract: z.boolean().default(false),
  mcpEnabled: z.boolean().default(true),
  mcpServerName: z.string().default(DEFAULT_MCP_SERVER_NAME),
  mcpCommand: z.string().default(DEFAULT_MCP_COMMAND),
  mcpArgs: z.array(String).default(DEFAULT_MCP_ARGS),
  mcpCwd: z.string().default(DEFAULT_MCP_CWD),
  mcpToolCallTimeoutMs: z.number().default(DEFAULT_MCP_TOOL_CALL_TIMEOUT_MS),
  mcpFailOnStartupError: z.boolean().default(true),
})

function requireNonEmpty(name: string, value: string | undefined): string {
  const normalized = value?.trim() ?? ''
  if (normalized === '') throw new TypeError(`agentarts-memory-dsh: ${name} must be a non-empty string`)
  return normalized
}

function requirePositiveInteger(name: string, value: number): number {
  if (!Number.isSafeInteger(value) || value < 1) {
    throw new TypeError(`agentarts-memory-dsh: ${name} must be a positive safe integer`)
  }
  return value
}

function resolveEndpoint(endpoint: string | undefined, region: string): string {
  const candidate = endpoint?.trim() || `https://memory.${region}.huaweicloud-agentarts.com`
  let parsed: URL
  try {
    parsed = new URL(candidate)
  } catch (error: unknown) {
    throw new TypeError('agentarts-memory-dsh: dataEndpoint must be an absolute HTTP(S) URL', { cause: error })
  }
  if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
    throw new TypeError('agentarts-memory-dsh: dataEndpoint must use HTTP or HTTPS')
  }
  return parsed.href.replace(/\/$/, '')
}

/** Resolve defaults and validate programmatic calls that bypass Schemastery. */
export function resolveConfig(config: Config): ResolvedConfig {
  const apiKey = requireNonEmpty('apiKey', config.apiKey)
  const spaceId = requireNonEmpty('spaceId', config.spaceId)
  const actorId = requireNonEmpty('actorId', config.actorId)
  const assistantId = requireNonEmpty('assistantId', config.assistantId ?? DEFAULT_ASSISTANT_ID)
  const region = requireNonEmpty('region', config.region ?? DEFAULT_REGION)
  const requestTimeoutMs = requirePositiveInteger(
    'requestTimeoutMs',
    config.requestTimeoutMs ?? DEFAULT_REQUEST_TIMEOUT_MS,
  )
  const maxRetries = config.maxRetries ?? DEFAULT_MAX_RETRIES
  if (!Number.isSafeInteger(maxRetries) || maxRetries < 0) {
    throw new TypeError('agentarts-memory-dsh: maxRetries must be a non-negative safe integer')
  }
  const retryBaseDelayMs = requirePositiveInteger(
    'retryBaseDelayMs',
    config.retryBaseDelayMs ?? DEFAULT_RETRY_BASE_DELAY_MS,
  )
  const mcpServerName = requireNonEmpty(
    'mcpServerName',
    config.mcpServerName ?? DEFAULT_MCP_SERVER_NAME,
  )
  if (!/^[A-Za-z0-9_-]{1,32}$/.test(mcpServerName)) {
    throw new TypeError('agentarts-memory-dsh: mcpServerName must match [A-Za-z0-9_-]{1,32}')
  }
  const mcpArgs = [...(config.mcpArgs ?? DEFAULT_MCP_ARGS)]
  if (mcpArgs.some(argument => typeof argument !== 'string')) {
    throw new TypeError('agentarts-memory-dsh: every mcpArgs entry must be a string')
  }

  return {
    apiKey,
    spaceId,
    actorId,
    assistantId,
    region,
    dataEndpoint: resolveEndpoint(config.dataEndpoint, region),
    requestTimeoutMs,
    maxRetries,
    retryBaseDelayMs,
    forceExtract: config.forceExtract ?? false,
    mcpEnabled: config.mcpEnabled ?? true,
    mcpServerName,
    mcpCommand: requireNonEmpty('mcpCommand', config.mcpCommand ?? DEFAULT_MCP_COMMAND),
    mcpArgs,
    mcpCwd: config.mcpCwd?.trim() || DEFAULT_MCP_CWD,
    mcpToolCallTimeoutMs: requirePositiveInteger(
      'mcpToolCallTimeoutMs',
      config.mcpToolCallTimeoutMs ?? DEFAULT_MCP_TOOL_CALL_TIMEOUT_MS,
    ),
    mcpFailOnStartupError: config.mcpFailOnStartupError ?? true,
  }
}
