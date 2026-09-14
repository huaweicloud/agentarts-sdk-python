/** Serialized, lifecycle-aware turn synchronization. */

import type { Session, SessionEvent } from '@deepseek-ai/dsh-session'
import type { TurnDataPlane } from './client.js'
import { extractTurn } from './turn.js'

type TurnEndEvent = Extract<SessionEvent, { type: 'turn/end' }>

interface Logger {
  warn(message: string): void
}

interface SessionState {
  remoteSession: Promise<string> | undefined
  tail: Promise<void>
}

/** Serializes writes per DSH session and exposes drain points for flush and teardown. */
export class TurnSyncCoordinator {
  private readonly states = new Map<Session, SessionState>()
  private accepting = true

  constructor(
    private readonly client: TurnDataPlane,
    private readonly logger: Logger,
  ) {}

  enqueue(session: Session, event: TurnEndEvent): void {
    if (!this.accepting) return
    const batch = extractTurn(session, event)
    if (batch === undefined) return

    let state = this.states.get(session)
    if (state === undefined) {
      state = { remoteSession: undefined, tail: Promise.resolve() }
      this.states.set(session, state)
    }
    const selected = state
    const pending = selected.tail.then(async () => {
      const creation = selected.remoteSession
        ?? this.client.createOrReuseSession(batch.dshSessionId)
      selected.remoteSession = creation
      let remoteSession: string
      try {
        remoteSession = await creation
      } catch (error: unknown) {
        if (selected.remoteSession === creation) selected.remoteSession = undefined
        throw error
      }
      await this.client.addTurn(remoteSession, batch)
    })
    selected.tail = pending.catch((error: unknown) => {
      this.logger.warn(
        `agentarts-memory-dsh: turn ${batch.turn} sync failed for session "${batch.dshSessionId}": ${String(error)}`,
      )
    })
  }

  /** Wait until every turn accepted for this exact session has settled. */
  flush(session: Session): Promise<void> {
    return this.states.get(session)?.tail ?? Promise.resolve()
  }

  /** Retire one disposed session after its accepted writes settle. */
  release(session: Session): void {
    const state = this.states.get(session)
    if (state === undefined) return
    void state.tail.finally(() => {
      if (this.states.get(session) === state) this.states.delete(session)
    })
  }

  /** Stop accepting events, drain accepted writes, and release network requests. */
  async dispose(): Promise<void> {
    this.accepting = false
    await Promise.all([...this.states.values()].map(state => state.tail))
    this.states.clear()
    this.client.close()
  }
}
