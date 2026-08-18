import type { Session, SessionEvent } from '@deepseek-ai/dsh-session'
import { describe, expect, it } from 'vitest'
import { extractTurn, renderMemoryText } from '../src/turn.js'

function sessionWith(events: SessionEvent[]): Session {
  return { id: 'dsh-session-1', events } as unknown as Session
}

describe('turn projection', () => {
  it('keeps direct user and visible assistant text in event order', () => {
    const events = [
      { type: 'turn/start', seq: 0, time: 10, data: { turn: 1 } },
      {
        type: 'user/message', seq: 1, time: 11,
        data: {
          id: 'u1', role: 'user',
          content: [{ type: 'text', text: 'remember blue' }, { type: 'image', attachment: {} }],
          source: { kind: 'user' },
        },
      },
      {
        type: 'user/message', seq: 2, time: 12,
        data: {
          id: 'p1', role: 'user', content: [{ type: 'text', text: 'private plugin context' }],
          source: { kind: 'plugin', plugin: 'test' },
        },
      },
      {
        type: 'assistant/message', seq: 3, time: 13,
        data: {
          turn: 1, step: 1,
          message: {
            id: 'a1', role: 'assistant',
            content: [
              { type: 'reasoning', text: 'private chain' },
              { type: 'tool-call', id: 'call-1', name: 'lookup', arguments: '{}' },
              { type: 'text', text: 'I will remember blue.' },
            ],
            source: { kind: 'model', provider: 'test', model: 'test' },
          },
        },
      },
      { type: 'turn/end', seq: 4, time: 14, data: { turn: 1, reason: { kind: 'completed' } } },
    ] as unknown as SessionEvent[]
    const session = sessionWith(events)

    expect(extractTurn(session, events[4] as Extract<SessionEvent, { type: 'turn/end' }>))
      .toEqual({
        dshSessionId: 'dsh-session-1',
        turn: 1,
        turnEndSeq: 4,
        timestamp: 14,
        reason: 'completed',
        messages: [
          { role: 'user', content: 'remember blue\n[image]', sourceEventSeq: 1 },
          { role: 'assistant', content: 'I will remember blue.', sourceEventSeq: 3 },
        ],
      })
  })

  it('does not cross a preceding turn boundary', () => {
    const staleEnd = {
      type: 'turn/end', seq: 0, time: 1, data: { turn: 1, reason: { kind: 'completed' } },
    } as unknown as Extract<SessionEvent, { type: 'turn/end' }>
    expect(extractTurn(sessionWith([staleEnd]), staleEnd)).toBeUndefined()
  })

  it('skips turns without memory-relevant content', () => {
    const events = [
      { type: 'turn/start', seq: 0, time: 1, data: { turn: 1 } },
      { type: 'turn/end', seq: 1, time: 2, data: { turn: 1, reason: { kind: 'aborted', reason: { kind: 'user' } } } },
    ] as unknown as SessionEvent[]
    expect(extractTurn(
      sessionWith(events),
      events[1] as Extract<SessionEvent, { type: 'turn/end' }>,
    )).toBeUndefined()
  })

  it('renders unknown user content conservatively and hides assistant protocol blocks', () => {
    expect(renderMemoryText([{ type: 'audio' }], 'user')).toBe('[audio]')
    expect(renderMemoryText([{ type: 'audio' }, { type: 'reasoning', text: 'x' }], 'assistant'))
      .toBe('')
  })
})
