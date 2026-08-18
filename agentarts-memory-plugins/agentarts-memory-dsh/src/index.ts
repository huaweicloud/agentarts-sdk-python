/**
 * DeepSeek Harness integration for AgentArts Memory turn ingestion and MCP recall.
 *
 * @module agentarts-memory-dsh
 */

import type { Context } from '@deepseek-ai/cordis'
import * as McpClient from '@deepseek-ai/dsh-mcp-client'
import type {} from '@deepseek-ai/dsh-session'
import type {} from '@deepseek-ai/dsh-tools'
import { AgentArtsDataPlaneClient } from './client.js'
import { Config, resolveConfig } from './config.js'
import type { Config as PluginConfig, ResolvedConfig } from './config.js'
import { TurnSyncCoordinator } from './sync.js'

export { AgentArtsDataPlaneClient, AgentArtsHttpError } from './client.js'
export type { TurnDataPlane } from './client.js'
export { Config, resolveConfig } from './config.js'
export type { Config as PluginConfig, ResolvedConfig } from './config.js'
export { TurnSyncCoordinator } from './sync.js'
export { extractTurn, renderMemoryText } from './turn.js'
export type { TurnBatch, TurnMessage } from './turn.js'

/** Cordis plugin name used by loader diagnostics. */
export const name = 'agentarts-memory-dsh'

/** DSH services used by turn observation and the generic MCP bridge. */
export const inject = ['sessions', 'tools']

/** Build the generic DSH MCP row used to provision the installed search server. */
export function createMcpClientConfig(config: ResolvedConfig): McpClient.Config {
  return {
    transport: 'stdio',
    serverName: config.mcpServerName,
    command: config.mcpCommand,
    args: [...config.mcpArgs],
    // dsh-mcp-client scrubs credential-like ambient variables before spawn, so
    // every value needed by agentarts-memory-mcp is passed explicitly.
    env: {
      HUAWEICLOUD_SDK_MEMORY_API_KEY: config.apiKey,
      HUAWEICLOUD_SDK_REGION: config.region,
      AGENTARTS_MEMORY_SPACE_ID: config.spaceId,
      AGENTARTS_MEMORY_DATA_ENDPOINT: config.dataEndpoint,
    },
    cwd: config.mcpCwd,
    toolCallTimeoutMs: config.mcpToolCallTimeoutMs,
    failOnStartupError: config.mcpFailOnStartupError,
  }
}

/** Attach turn synchronization and, by default, the search-only MCP child. */
export async function apply(ctx: Context, config: PluginConfig): Promise<void> {
  const resolved = resolveConfig(config)
  const client = new AgentArtsDataPlaneClient(resolved)
  const coordinator = new TurnSyncCoordinator(client, ctx.logger)

  ctx.on('session/event', (session, event) => {
    if (event.type === 'turn/end') coordinator.enqueue(session, event)
  })
  ctx.on('session/flush', session => coordinator.flush(session))
  ctx.on('session/disposed', session => coordinator.release(session))
  ctx.effect(() => () => coordinator.dispose(), 'agentarts-memory-dsh.sync')

  if (!resolved.mcpEnabled) return
  await McpClient.apply(ctx, createMcpClientConfig(resolved))
}
