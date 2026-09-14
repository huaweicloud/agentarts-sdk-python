/**
 * DeepSeek Harness integration for AgentArts Memory turn ingestion and MCP recall.
 *
 * @module agentarts-memory-dsh
 */

import type { Context } from '@deepseek-ai/cordis'
import { launchEnvironmentOf } from '@deepseek-ai/dsh-launch-environment'
import * as McpClient from '@deepseek-ai/dsh-mcp-client'
import type {} from '@deepseek-ai/dsh-session'
import type {} from '@deepseek-ai/dsh-tools'
import { AgentArtsDataPlaneClient } from './client.js'
import { Config, resolveConfig } from './config.js'
import type { Config as PluginConfig, ResolvedConfig } from './config.js'
import { TurnSyncCoordinator } from './sync.js'

export { AgentArtsDataPlaneClient, AgentArtsHttpError } from './client.js'
export type { ApiKeyResolver, TurnDataPlane } from './client.js'
export { Config, resolveConfig } from './config.js'
export type { Config as PluginConfig, ResolvedConfig } from './config.js'
export { TurnSyncCoordinator } from './sync.js'
export { extractTurn, renderMemoryText } from './turn.js'
export type { TurnBatch, TurnMessage } from './turn.js'

/** Cordis plugin name used by loader diagnostics. */
export const name = 'agentarts-memory-dsh'

/** DSH services used by turn observation and the generic MCP bridge. */
export const inject = ['sessions', 'tools']

/** Resolve the current API key without exposing it through Cordis configuration. */
export async function resolveApiKey(ctx: Context, config: ResolvedConfig): Promise<string> {
  if (config.apiKey !== undefined) return config.apiKey

  const credentials = ctx.get('credentials')
  const value = credentials !== undefined
    ? (await credentials.resolve(config.apiKeyEnv))?.value
    : launchEnvironmentOf(ctx).get(config.apiKeyEnv)?.value
  if (value === undefined || value.length === 0) {
    throw new Error(
      `agentarts-memory-dsh: credential "${config.apiKeyEnv}" is not configured; `
      + 'store it through the DSH credentials service or set it in the launch environment',
    )
  }
  return value
}

/** Build the generic DSH MCP row used to provision the installed search server. */
export function createMcpClientConfig(config: ResolvedConfig, apiKey: string): McpClient.Config {
  return {
    transport: 'stdio',
    serverName: config.mcpServerName,
    command: config.mcpCommand,
    args: [...config.mcpArgs],
    // dsh-mcp-client scrubs credential-like ambient variables before spawn, so
    // every value needed by agentarts-memory-mcp is passed explicitly.
    env: {
      HUAWEICLOUD_SDK_MEMORY_API_KEY: apiKey,
      HUAWEICLOUD_SDK_REGION: config.region,
      AGENTARTS_MEMORY_SPACE_ID: config.spaceId,
      AGENTARTS_MEMORY_ACTOR_ID: config.actorId,
      AGENTARTS_MEMORY_ASSISTANT_ID: config.assistantId,
      AGENTARTS_MEMORY_DATA_ENDPOINT: config.dataEndpoint,
    },
    cwd: config.mcpCwd,
    toolCallTimeoutMs: config.mcpToolCallTimeoutMs,
    failOnStartupError: config.mcpFailOnStartupError,
  }
}

/** Attach turn synchronization and, by default, the AgentArts MCP child. */
export async function apply(ctx: Context, config: PluginConfig): Promise<void> {
  const resolved = resolveConfig(config)
  const apiKey = await resolveApiKey(ctx, resolved)
  const client = new AgentArtsDataPlaneClient(
    resolved,
    globalThis.fetch,
    () => resolveApiKey(ctx, resolved),
  )
  const coordinator = new TurnSyncCoordinator(client, ctx.logger)

  ctx.on('session/event', (session, event) => {
    if (event.type === 'turn/end') coordinator.enqueue(session, event)
  })
  ctx.on('session/flush', session => coordinator.flush(session))
  ctx.on('session/disposed', session => coordinator.release(session))
  ctx.effect(() => () => coordinator.dispose(), 'agentarts-memory-dsh.sync')

  if (!resolved.mcpEnabled) return
  await McpClient.apply(ctx, createMcpClientConfig(resolved, apiKey))
}
