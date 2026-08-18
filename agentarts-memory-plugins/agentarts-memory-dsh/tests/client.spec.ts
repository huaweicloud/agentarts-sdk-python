import { describe, expect, it, vi } from 'vitest'
import {
  AgentArtsDataPlaneClient,
  AgentArtsHttpError,
  toAgentArtsSessionId,
} from '../src/client.js'
import { resolveConfig } from '../src/config.js'
import type { TurnBatch } from '../src/turn.js'

const config = resolveConfig({
  apiKey: 'top-secret',
  spaceId: 'space/one',
  actorId: 'actor-1',
  assistantId: 'assistant-1',
  dataEndpoint: 'https://memory.example.test',
  requestTimeoutMs: 1_000,
  maxRetries: 0,
})

const batch: TurnBatch = {
  dshSessionId: 'dsh-session-1',
  turn: 3,
  turnEndSeq: 42,
  timestamp: 1234,
  reason: 'completed',
  messages: [
    { role: 'user', content: 'hello', sourceEventSeq: 40 },
    { role: 'assistant', content: 'hi', sourceEventSeq: 41 },
  ],
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

describe('AgentArtsDataPlaneClient', () => {
  it('maps DSH session ids to stable AgentArts UUIDs', () => {
    expect(toAgentArtsSessionId('session-c4bb3657-46c2-4805-a93f-31f523bb1b14'))
      .toBe('c4bb3657-46c2-4805-a93f-31f523bb1b14')
    expect(toAgentArtsSessionId('dsh-session-1')).toBe(toAgentArtsSessionId('dsh-session-1'))
    expect(toAgentArtsSessionId('dsh-session-1'))
      .toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-8[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/)
    expect(toAgentArtsSessionId('dsh-session-1')).not.toBe(toAgentArtsSessionId('dsh-session-2'))
  })

  it('creates a deterministic remote session with participant identity', async () => {
    const remoteId = toAgentArtsSessionId('dsh-session-1')
    const fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValue(jsonResponse({ id: remoteId }, 201))
    const client = new AgentArtsDataPlaneClient(config, fetch)

    await expect(client.createOrReuseSession('dsh-session-1')).resolves.toBe(remoteId)
    const [url, init] = fetch.mock.calls[0] ?? []
    expect(url).toBe('https://memory.example.test/v1/core/spaces/space%2Fone/sessions')
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer top-secret' })
    expect(JSON.parse(String(init?.body))).toMatchObject({
      id: remoteId,
      actor_id: 'actor-1',
      assistant_id: 'assistant-1',
      meta: { source: 'deepseek-harness', dsh_session_id: 'dsh-session-1' },
    })
  })

  it('treats create conflict as resume and writes an idempotent turn batch', async () => {
    const fetch = vi.fn<typeof globalThis.fetch>()
      .mockResolvedValueOnce(jsonResponse({ error_code: 'ALREADY_EXISTS', error_msg: 'exists' }, 409))
      .mockResolvedValueOnce(jsonResponse({ items: [], count: 2 }, 201))
    const client = new AgentArtsDataPlaneClient(config, fetch)

    const remote = await client.createOrReuseSession('dsh-session-1')
    await client.addTurn(remote, batch)

    expect(remote).toBe(toAgentArtsSessionId('dsh-session-1'))
    const [, init] = fetch.mock.calls[1] ?? []
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>
    expect(body).toMatchObject({
      timestamp: 1234,
      is_force_extract: false,
      messages: [
        { role: 'user', parts: [{ type: 'text', text: 'hello' }] },
        { role: 'assistant', parts: [{ type: 'text', text: 'hi' }] },
      ],
    })
    expect(JSON.parse(String((body.messages as Array<Record<string, unknown>>)[0]?.meta))).toEqual({
      source: 'deepseek-harness',
      dsh_session_id: 'dsh-session-1',
      dsh_turn: 3,
      dsh_turn_end_seq: 42,
      dsh_turn_reason: 'completed',
    })
    expect(body.idempotency_key).toMatch(/^dsh-turn-[0-9a-f]{64}$/)
  })

  it('retries a transient service failure', async () => {
    const retryConfig = { ...config, maxRetries: 1, retryBaseDelayMs: 1 }
    const fetch = vi.fn<typeof globalThis.fetch>()
      .mockResolvedValueOnce(jsonResponse({ error_code: 'BUSY', error_msg: 'later' }, 503))
      .mockResolvedValueOnce(jsonResponse({ id: toAgentArtsSessionId('dsh-session-1') }, 201))
    const client = new AgentArtsDataPlaneClient(retryConfig, fetch)

    await expect(client.createOrReuseSession('dsh-session-1'))
      .resolves.toBe(toAgentArtsSessionId('dsh-session-1'))
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('reports service diagnostics without exposing the API key', async () => {
    const fetch = vi.fn<typeof globalThis.fetch>()
      .mockResolvedValue(jsonResponse({ error_code: 'UNAUTHORIZED', error_msg: 'bad credential' }, 401))
    const client = new AgentArtsDataPlaneClient(config, fetch)

    const error = await client.createOrReuseSession('dsh-session-1').catch(value => value as Error)
    expect(error).toBeInstanceOf(AgentArtsHttpError)
    expect(error.message).toContain('UNAUTHORIZED')
    expect(error.message).not.toContain('top-secret')
  })
})
