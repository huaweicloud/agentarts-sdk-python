import { Context } from '@deepseek-ai/cordis'
import { CredentialProvider } from '@deepseek-ai/dsh-credentials'
import type { CredentialInfo, CredentialRef, ResolvedCredential } from '@deepseek-ai/dsh-credentials'
import { createAssistantMessage, createUserMessage } from '@deepseek-ai/dsh-llm'
import { SessionId, SessionStore } from '@deepseek-ai/dsh-session'
import SystemPrompt from '@deepseek-ai/dsh-system-prompt'
import { ToolRuntime } from '@deepseek-ai/dsh-tools'
import { fileURLToPath } from 'node:url'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as AgentArtsMemory from '../src/index.js'

const contexts: Context[] = []
const MEMORY_KEY = 'HUAWEICLOUD_SDK_MEMORY_API_KEY'

class TestCredentials extends CredentialProvider {
  private value = 'credential-secret'

  async resolve(ref: CredentialRef): Promise<ResolvedCredential | undefined> {
    return ref === MEMORY_KEY ? { value: this.value, source: 'test' } : undefined
  }

  async describe(ref: CredentialRef): Promise<CredentialInfo> {
    return ref === MEMORY_KEY
      ? { configured: true, source: 'test', writable: true }
      : { configured: false, writable: true }
  }

  async set(ref: CredentialRef, value: string): Promise<void> {
    if (ref === MEMORY_KEY) this.value = value
  }

  async unset(ref: CredentialRef): Promise<void> {
    if (ref === MEMORY_KEY) this.value = ''
  }
}

afterEach(async () => {
  await Promise.all(contexts.splice(0).map(context => context.fiber.dispose()))
  vi.unstubAllGlobals()
})

describe('Cordis integration', () => {
  it('provisions the installed AgentArts MCP server through the generic DSH bridge', () => {
    expect(AgentArtsMemory.createMcpClientConfig(AgentArtsMemory.resolveConfig({
      apiKey: 'secret',
      spaceId: 'space-1',
      actorId: 'actor-1',
      assistantId: 'assistant-1',
      region: 'cn-north-4',
      dataEndpoint: 'https://memory.example.test/',
      mcpCwd: '/srv/dsh',
    }), 'secret')).toEqual({
      transport: 'stdio',
      serverName: 'agentarts-memory',
      command: 'agentarts-memory-mcp',
      args: [],
      env: {
        HUAWEICLOUD_SDK_MEMORY_API_KEY: 'secret',
        HUAWEICLOUD_SDK_REGION: 'cn-north-4',
        AGENTARTS_MEMORY_SPACE_ID: 'space-1',
        AGENTARTS_MEMORY_ACTOR_ID: 'actor-1',
        AGENTARTS_MEMORY_ASSISTANT_ID: 'assistant-1',
        AGENTARTS_MEMORY_DATA_ENDPOINT: 'https://memory.example.test',
      },
      cwd: '/srv/dsh',
      toolCallTimeoutMs: 60_000,
      failOnStartupError: true,
    })
  })

  it('launches MCP, discovers ltm_search, and registers the namespaced DSH tool', async () => {
    const context = new Context()
    contexts.push(context)
    await context.plugin(SessionStore)
    await context.plugin(SystemPrompt, { persona: '' })
    await context.plugin(ToolRuntime)
    await context.plugin(TestCredentials)
    await context.plugin(AgentArtsMemory, {
      spaceId: 'space-1',
      actorId: 'actor-1',
      mcpCommand: process.execPath,
      mcpArgs: [fileURLToPath(new URL('./fixture-mcp.cjs', import.meta.url))],
      mcpFailOnStartupError: true,
    })

    const tool = context.tools.get('mcp__agentarts-memory__ltm_search')
    expect(tool).toBeDefined()
    expect(tool?.description).toContain('long-term memory')
    expect(context.tools.get('ltm_search')).toBeUndefined()
  })

  it('observes a real DSH session and drains its turn write', async () => {
    const fetch = vi.fn<typeof globalThis.fetch>()
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 'session-1' }), {
        status: 201,
        headers: { 'content-type': 'application/json' },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [], count: 2 }), {
        status: 201,
        headers: { 'content-type': 'application/json' },
      }))
    vi.stubGlobal('fetch', fetch)

    const context = new Context()
    contexts.push(context)
    await context.plugin(SessionStore)
    await context.plugin(SystemPrompt, { persona: '' })
    await context.plugin(ToolRuntime)
    await context.plugin(TestCredentials)
    await context.plugin(AgentArtsMemory, {
      spaceId: 'space-1',
      actorId: 'actor-1',
      dataEndpoint: 'https://memory.example.test',
      mcpEnabled: false,
    })

    const session = context.sessions.create(SessionId('session-1'))
    session.append('turn/start', { turn: 1 })
    session.append('user/message', createUserMessage({
      content: [{ type: 'text', text: 'remember green' }],
      source: { kind: 'user' },
    }), { surfaceOp: 'append' })
    session.append('assistant/message', {
      turn: 1,
      step: 1,
      message: createAssistantMessage({
        content: [{ type: 'text', text: 'I will remember green.' }],
        source: { provider: 'test', model: 'test' },
      }),
    }, { surfaceOp: 'append' })
    session.append('turn/end', { turn: 1, reason: { kind: 'completed' } })

    await context.parallel('session/flush', session)

    expect(fetch).toHaveBeenCalledTimes(2)
    const [, write] = fetch.mock.calls[1] ?? []
    expect(write?.headers).toMatchObject({ Authorization: 'Bearer credential-secret' })
    expect(JSON.parse(String(write?.body))).toMatchObject({
      messages: [
        { role: 'user', parts: [{ type: 'text', text: 'remember green' }] },
        { role: 'assistant', parts: [{ type: 'text', text: 'I will remember green.' }] },
      ],
    })
  })
})
