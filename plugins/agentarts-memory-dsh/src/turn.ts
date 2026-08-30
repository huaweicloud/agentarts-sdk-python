/** Projection of one closed DSH turn into AgentArts text messages. */

import type { Session, SessionEvent } from '@deepseek-ai/dsh-session'

/** One text message ready for the AgentArts data plane. */
export interface TurnMessage {
  role: 'user' | 'assistant'
  content: string
  sourceEventSeq: number
}

/** A closed DSH turn and its memory-relevant messages. */
export interface TurnBatch {
  dshSessionId: string
  turn: number
  turnEndSeq: number
  timestamp: number
  reason: string
  messages: TurnMessage[]
}

type TurnEndEvent = Extract<SessionEvent, { type: 'turn/end' }>

function record(value: unknown): Record<string, unknown> | undefined {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined
}

/** Render model-visible blocks without retaining private reasoning or tool protocol payloads. */
export function renderMemoryText(content: readonly unknown[], role: 'user' | 'assistant'): string {
  const parts: string[] = []
  for (const value of content) {
    const block = record(value)
    const type = block?.['type']
    const text = block?.['text']
    if (type === 'text' && typeof text === 'string') {
      if (text.trim() !== '') parts.push(text)
      continue
    }
    if (type === 'image' && role === 'user') {
      parts.push('[image]')
      continue
    }
    if (role === 'user' && typeof type === 'string'
      && type !== 'reasoning' && type !== 'tool-call' && type !== 'tool-result') {
      parts.push(`[${type}]`)
    }
  }
  return parts.join('\n').trim()
}

/** Project the exact event interval closed by one `turn/end`. */
export function extractTurn(session: Session, turnEnd: TurnEndEvent): TurnBatch | undefined {
  const events = session.events
  if (events[turnEnd.seq] !== turnEnd) return undefined

  let start = -1
  for (let index = turnEnd.seq - 1; index >= 0; index -= 1) {
    const event = events[index]
    if (event?.type === 'turn/start' && event.data.turn === turnEnd.data.turn) {
      start = index
      break
    }
    if (event?.type === 'turn/end') break
  }
  if (start < 0) return undefined

  const messages: TurnMessage[] = []
  for (const event of events.slice(start + 1, turnEnd.seq)) {
    if (event.type === 'user/message' && event.data.source.kind === 'user') {
      const content = renderMemoryText(event.data.content, 'user')
      if (content !== '') messages.push({ role: 'user', content, sourceEventSeq: event.seq })
    } else if (event.type === 'assistant/message') {
      const content = renderMemoryText(event.data.message.content, 'assistant')
      if (content !== '') messages.push({ role: 'assistant', content, sourceEventSeq: event.seq })
    }
  }
  if (messages.length === 0) return undefined

  return {
    dshSessionId: session.id,
    turn: turnEnd.data.turn,
    turnEndSeq: turnEnd.seq,
    timestamp: turnEnd.time,
    reason: turnEnd.data.reason.kind,
    messages,
  }
}
