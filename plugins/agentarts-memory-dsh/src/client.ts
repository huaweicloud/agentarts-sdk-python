/** Minimal AgentArts Memory data-plane client for closed-turn ingestion. */

import { createHash } from 'node:crypto'
import type { ResolvedConfig } from './config.js'
import type { TurnBatch } from './turn.js'

type Fetch = typeof globalThis.fetch
export type ApiKeyResolver = () => Promise<string>

interface AgentArtsErrorBody {
  error_code?: unknown
  error_msg?: unknown
}

/** HTTP failure with credential-free diagnostics. */
export class AgentArtsHttpError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(`AgentArts Memory request failed (${status}, ${code}): ${message}`)
    this.name = 'AgentArtsHttpError'
  }
}

/** Operations required by the turn-sync coordinator. */
export interface TurnDataPlane {
  createOrReuseSession(dshSessionId: string): Promise<string>
  addTurn(memorySessionId: string, batch: TurnBatch): Promise<void>
  close(): void
}

function encodePath(value: string): string {
  return encodeURIComponent(value)
}

const AGENTARTS_SESSION_ID_PATTERN = /^[a-zA-Z0-9._-]{1,64}$/
const MAX_MESSAGES_PER_REQUEST = 100

/** Preserve supported DSH session ids, with a deterministic fallback for unsupported ids. */
export function toAgentArtsSessionId(dshSessionId: string): string {
  if (AGENTARTS_SESSION_ID_PATTERN.test(dshSessionId)) return dshSessionId

  // UUIDv8 reserves the payload for application-defined deterministic schemes.
  const bytes = createHash('sha256')
    .update('agentarts-memory-dsh\0')
    .update(dshSessionId)
    .digest()
    .subarray(0, 16)
  bytes[6] = (bytes[6]! & 0x0f) | 0x80
  bytes[8] = (bytes[8]! & 0x3f) | 0x80
  const hex = bytes.toString('hex')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}`
    + `-${hex.slice(16, 20)}-${hex.slice(20)}`
}

function idempotencyKey(batch: TurnBatch, chunkIndex?: number): string {
  const chunk = chunkIndex === undefined ? '' : `\0${chunkIndex}`
  const source = `${batch.dshSessionId}\0${batch.turn}\0${batch.turnEndSeq}${chunk}`
  return `dsh-turn-${createHash('sha256').update(source).digest('hex')}`
}

function retryable(error: unknown): boolean {
  return !(error instanceof AgentArtsHttpError) || error.status === 429 || error.status >= 500
}

function delay(milliseconds: number, signal: AbortSignal): Promise<void> {
  if (signal.aborted) return Promise.reject(signal.reason)
  return new Promise((resolve, reject) => {
    const onAbort = (): void => {
      clearTimeout(timer)
      reject(signal.reason)
    }
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', onAbort)
      resolve()
    }, milliseconds)
    signal.addEventListener('abort', onAbort, { once: true })
  })
}

async function errorFromResponse(response: Response): Promise<AgentArtsHttpError> {
  let body: AgentArtsErrorBody = {}
  try {
    body = await response.json() as AgentArtsErrorBody
  } catch {
    // A non-JSON failure body carries no stable diagnostic fields.
  }
  const code = typeof body.error_code === 'string' ? body.error_code : 'HTTP_ERROR'
  const message = typeof body.error_msg === 'string' ? body.error_msg : response.statusText || 'request rejected'
  return new AgentArtsHttpError(response.status, code, message)
}

/** Data-plane client using the same REST contract and Bearer authentication as the Python SDK. */
export class AgentArtsDataPlaneClient implements TurnDataPlane {
  private readonly lifetime = new AbortController()

  constructor(
    private readonly config: ResolvedConfig,
    private readonly fetchImplementation: Fetch = globalThis.fetch,
    private readonly resolveApiKey: ApiKeyResolver = async () => {
      if (config.apiKey === undefined) {
        throw new Error(`agentarts-memory-dsh: credential "${config.apiKeyEnv}" is not configured`)
      }
      return config.apiKey
    },
  ) {}

  async createOrReuseSession(dshSessionId: string): Promise<string> {
    const memorySessionId = toAgentArtsSessionId(dshSessionId)
    const path = `/v1/core/spaces/${encodePath(this.config.spaceId)}/sessions`
    try {
      const response = await this.request('POST', path, {
        id: memorySessionId,
        actor_id: this.config.actorId,
        assistant_id: this.config.assistantId,
        meta: { source: 'deepseek-harness', dsh_session_id: dshSessionId },
      })
      const id = (response as Record<string, unknown>)['id']
      if (typeof id !== 'string' || id === '') {
        throw new Error('AgentArts Memory session response did not contain an id')
      }
      return id
    } catch (error: unknown) {
      if (error instanceof AgentArtsHttpError && error.status === 409) return memorySessionId
      throw error
    }
  }

  async addTurn(memorySessionId: string, batch: TurnBatch): Promise<void> {
    const path = `/v1/core/spaces/${encodePath(this.config.spaceId)}/sessions/`
      + `${encodePath(memorySessionId)}/messages`
    // AgentArts session metadata is structured JSON, but message metadata is a
    // JSON-encoded string in the current data-plane contract.
    const meta = JSON.stringify({
      source: 'deepseek-harness',
      dsh_session_id: batch.dshSessionId,
      dsh_turn: batch.turn,
      dsh_turn_end_seq: batch.turnEndSeq,
      dsh_turn_reason: batch.reason,
    })
    const messages = batch.messages.map(message => ({
      role: message.role,
      parts: [{ type: 'text', text: message.content }],
      actor_id: this.config.actorId,
      assistant_id: this.config.assistantId,
      meta,
    }))
    const chunkCount = Math.ceil(messages.length / MAX_MESSAGES_PER_REQUEST)
    for (let chunkIndex = 0; chunkIndex < chunkCount; chunkIndex += 1) {
      const offset = chunkIndex * MAX_MESSAGES_PER_REQUEST
      await this.request('POST', path, {
        messages: messages.slice(offset, offset + MAX_MESSAGES_PER_REQUEST),
        timestamp: batch.timestamp,
        idempotency_key: idempotencyKey(batch, chunkCount === 1 ? undefined : chunkIndex),
        // Force extraction only after the complete turn has been written.
        is_force_extract: this.config.forceExtract && chunkIndex === chunkCount - 1,
      })
    }
  }

  close(): void {
    this.lifetime.abort(new Error('agentarts-memory-dsh disposed'))
  }

  private async request(method: string, path: string, body: unknown): Promise<unknown> {
    let attempt = 0
    while (true) {
      const timeout = new AbortController()
      const timer = setTimeout(
        () => timeout.abort(new Error(`AgentArts Memory request timed out after ${this.config.requestTimeoutMs}ms`)),
        this.config.requestTimeoutMs,
      )
      const signal = AbortSignal.any([this.lifetime.signal, timeout.signal])
      try {
        const apiKey = await this.resolveApiKey()
        const response = await this.fetchImplementation(`${this.config.dataEndpoint}${path}`, {
          method,
          headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
            'User-Agent': 'agentarts-memory-dsh/0.1.0',
          },
          body: JSON.stringify(body),
          signal,
        })
        if (!response.ok) throw await errorFromResponse(response)
        if (response.status === 204) return {}
        const contentType = response.headers.get('content-type') ?? ''
        return contentType.startsWith('application/json') ? await response.json() : {}
      } catch (error: unknown) {
        if (this.lifetime.signal.aborted || attempt >= this.config.maxRetries || !retryable(error)) {
          throw error
        }
        const wait = this.config.retryBaseDelayMs * (2 ** attempt)
        attempt += 1
        await delay(wait, this.lifetime.signal)
      } finally {
        clearTimeout(timer)
      }
    }
  }
}
