import { describe, expect, it } from 'vitest'
import {
  DEFAULT_API_KEY_ENV,
  DEFAULT_ASSISTANT_ID,
  DEFAULT_MCP_CWD,
  DEFAULT_REGION,
  resolveConfig,
  type Config,
} from '../src/config.js'

const required: Config = {
  spaceId: 'space-1',
  actorId: 'user-1',
}

describe('resolveConfig', () => {
  it('resolves data-plane and MCP defaults', () => {
    expect(resolveConfig(required)).toMatchObject({
      apiKeyEnv: DEFAULT_API_KEY_ENV,
      spaceId: 'space-1',
      actorId: 'user-1',
      assistantId: DEFAULT_ASSISTANT_ID,
      region: DEFAULT_REGION,
      dataEndpoint: `https://memory.${DEFAULT_REGION}.huaweicloud-agentarts.com`,
      mcpEnabled: true,
      mcpServerName: 'agentarts-memory',
      mcpCommand: 'agentarts-memory-mcp',
      mcpArgs: [],
      mcpCwd: DEFAULT_MCP_CWD,
      mcpFailOnStartupError: true,
    })
  })

  it('normalizes an explicit endpoint without rewriting its path', () => {
    expect(resolveConfig({ ...required, dataEndpoint: 'http://localhost:9000/api/' }).dataEndpoint)
      .toBe('http://localhost:9000/api')
  })

  it.each([
    [{ ...required, apiKey: ' ' }, 'apiKey'],
    [{ ...required, apiKeyEnv: 'not-valid' }, 'credential ref'],
    [{ ...required, actorId: '' }, 'actorId'],
    [{ ...required, maxRetries: -1 }, 'maxRetries'],
    [{ ...required, requestTimeoutMs: 0 }, 'requestTimeoutMs'],
    [{ ...required, mcpServerName: 'not valid' }, 'mcpServerName'],
    [{ ...required, mcpCommand: ' ' }, 'mcpCommand'],
    [{ ...required, dataEndpoint: 'file:///tmp/memory' }, 'dataEndpoint'],
  ] as const)('rejects invalid %s configuration', (input, field) => {
    expect(() => resolveConfig(input)).toThrow(field)
  })
})
