import type { Session, SessionEvent } from '@deepseek-ai/dsh-session'
import { describe, expect, it, vi } from 'vitest'
import type { TurnDataPlane } from '../src/client.js'
import { TurnSyncCoordinator } from '../src/sync.js'
import type { TurnBatch } from '../src/turn.js'

function twoTurnSession(): {
  session: Session
  ends: Array<Extract<SessionEvent, { type: 'turn/end' }>>
} {
  const events = [
    { type: 'turn/start', seq: 0, time: 1, data: { turn: 1 } },
    {
      type: 'user/message', seq: 1, time: 2,
      data: {
        id: 'u1', role: 'user', content: [{ type: 'text', text: 'one' }],
        source: { kind: 'user' },
      },
    },
    { type: 'turn/end', seq: 2, time: 3, data: { turn: 1, reason: { kind: 'completed' } } },
    { type: 'turn/start', seq: 3, time: 4, data: { turn: 2 } },
    {
      type: 'assistant/message', seq: 4, time: 5,
      data: {
        turn: 2, step: 1,
        message: {
          id: 'a2', role: 'assistant', content: [{ type: 'text', text: 'two' }],
          source: { kind: 'model', provider: 'test', model: 'test' },
        },
      },
    },
    { type: 'turn/end', seq: 5, time: 6, data: { turn: 2, reason: { kind: 'max-tokens' } } },
  ] as unknown as SessionEvent[]
  return {
    session: { id: 'session-1', events } as unknown as Session,
    ends: [events[2], events[5]] as Array<Extract<SessionEvent, { type: 'turn/end' }>>,
  }
}

function fakeClient(overrides: Partial<TurnDataPlane> = {}): TurnDataPlane {
  return {
    createOrReuseSession: vi.fn(async () => 'memory-session-1'),
    addTurn: vi.fn(async () => undefined),
    close: vi.fn(),
    ...overrides,
  }
}

describe('TurnSyncCoordinator', () => {
  it('serializes turns, reuses the remote session, and drains on flush', async () => {
    const seen: number[] = []
    const client = fakeClient({
      addTurn: vi.fn(async (_remote: string, batch: TurnBatch) => {
        seen.push(batch.turn)
      }),
    })
    const logger = { warn: vi.fn() }
    const coordinator = new TurnSyncCoordinator(client, logger)
    const { session, ends } = twoTurnSession()

    coordinator.enqueue(session, ends[0]!)
    coordinator.enqueue(session, ends[1]!)
    await coordinator.flush(session)

    expect(seen).toEqual([1, 2])
    expect(client.createOrReuseSession).toHaveBeenCalledTimes(1)
    expect(logger.warn).not.toHaveBeenCalled()
  })

  it('contains a failed write and continues with the next turn', async () => {
    let attempt = 0
    const client = fakeClient({
      addTurn: vi.fn(async () => {
        attempt += 1
        if (attempt === 1) throw new Error('offline')
      }),
    })
    const logger = { warn: vi.fn() }
    const coordinator = new TurnSyncCoordinator(client, logger)
    const { session, ends } = twoTurnSession()

    coordinator.enqueue(session, ends[0]!)
    coordinator.enqueue(session, ends[1]!)
    await coordinator.flush(session)

    expect(client.addTurn).toHaveBeenCalledTimes(2)
    expect(logger.warn).toHaveBeenCalledOnce()
  })

  it('retries remote session creation on a later turn after creation failed', async () => {
    let attempt = 0
    const client = fakeClient({
      createOrReuseSession: vi.fn(async () => {
        attempt += 1
        if (attempt === 1) throw new Error('offline')
        return 'memory-session-1'
      }),
    })
    const logger = { warn: vi.fn() }
    const coordinator = new TurnSyncCoordinator(client, logger)
    const { session, ends } = twoTurnSession()

    coordinator.enqueue(session, ends[0]!)
    await coordinator.flush(session)
    coordinator.enqueue(session, ends[1]!)
    await coordinator.flush(session)

    expect(client.createOrReuseSession).toHaveBeenCalledTimes(2)
    expect(client.addTurn).toHaveBeenCalledTimes(1)
  })

  it('drains and closes exactly once during disposal', async () => {
    const client = fakeClient()
    const coordinator = new TurnSyncCoordinator(client, { warn: vi.fn() })
    const { session, ends } = twoTurnSession()
    coordinator.enqueue(session, ends[0]!)

    await coordinator.dispose()
    coordinator.enqueue(session, ends[1]!)

    expect(client.addTurn).toHaveBeenCalledTimes(1)
    expect(client.close).toHaveBeenCalledOnce()
  })
})
