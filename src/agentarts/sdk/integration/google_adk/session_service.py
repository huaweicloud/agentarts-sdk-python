"""
AgentArts Session Service for Google ADK

Implements ``BaseSessionService`` by persisting sessions and events
to the AgentArts Memory backend.

State management strategy (Plan B - full snapshot):
    - **Write**: Each ``append_event`` stores the complete session-scoped
      state in ``message.meta`` under ``_STATE_KEY``.
    - **Read**: State is recovered from the last message's meta (k=1),
      avoiding full history replay. O(1) complexity.
    - Only ``session:`` scoped state is persisted. ``user:`` / ``app:``
      scoped state is silently dropped.

Deduplication:
    Each ``append_event`` uses ``idempotency_key=f"{session_id}:{event.id}"``
    so that re-ingestion by ``MemoryService.add_session_to_memory`` is a
    no-op (409 Conflict, silently caught).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from agentarts.sdk.service import APIException

if TYPE_CHECKING:
    from agentarts.sdk.memory import AsyncMemoryClient, MessageInfo

try:
    from google.adk.events.event import Event
    from google.adk.sessions.base_session_service import (
        BaseSessionService,
        GetSessionConfig,
        ListSessionsResponse,
    )
    from google.adk.sessions.session import Session
    from google.adk.sessions.state import State

    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    BaseSessionService = object  # type: ignore[assignment,misc]
    GetSessionConfig = None  # type: ignore[assignment,misc]
    ListSessionsResponse = None  # type: ignore[assignment,misc]
    Session = None  # type: ignore[assignment,misc]
    State = None  # type: ignore[assignment,misc]
    Event = None  # type: ignore[assignment,misc]

from agentarts.sdk.integration.google_adk.converter import (
    _STATE_KEY,
    _extract_session_scoped_state,
    _messages_to_events,
    _parse_meta,
    event_to_messages,
)

logger = logging.getLogger(__name__)

# Page size limit enforced by the backend.
_PAGE_SIZE = 20

# Conservative upper bound on parts per Event. Used to over-fetch messages
# so that ``_messages_to_events`` can group enough messages to satisfy
# ``num_recent_events``. ADK Events rarely exceed 5 parts (text +
# function_call + function_response), so 10 is a safe multiplier.
_MAX_PARTS_PER_EVENT = 10


class AgentArtsSessionService(BaseSessionService):
    """ADK SessionService backed by AgentArts Memory.

    Maps ADK concepts to AgentArts as follows:
        - ``app_name`` -> ``space_id``
        - ``user_id`` -> ``actor_id``
        - ``session_id`` -> ``session_id``
        - ``Session.events`` -> ``messages``
        - ``Session.state`` -> encoded in ``message.meta`` (full snapshot)
    """

    def __init__(self, client: AsyncMemoryClient):
        self._client = client

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Session:
        """Create a new session in AgentArts.

        Initial state is NOT stored in session.meta; the first
        ``append_event`` will carry the full state snapshot.
        """
        session_info = await self._client.create_memory_session(
            space_id=app_name,
            id=session_id,
            actor_id=user_id,
        )
        return Session(
            id=session_info.id,
            app_name=app_name,
            user_id=user_id,
            state=state or {},
            events=[],
            last_update_time=0.0,
        )

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: GetSessionConfig | None = None,
    ) -> Session | None:
        """Retrieve a session from AgentArts.

        State is read from the last message's meta (k=1, O(1)).
        Events are loaded per ``config.num_recent_events``.
        """
        # 1. Verify session exists
        try:
            await self._client.get_session(
                space_id=app_name, session_id=session_id
            )
        except APIException as e:
            if e.status_code == 404:
                return None
            raise

        # 2. Read full state from the last message's meta
        state: dict[str, Any] = {}
        last_messages = await self._client.get_last_k_messages(
            session_id=session_id, k=1, space_id=app_name
        )
        if last_messages:
            meta_dict = _parse_meta(getattr(last_messages[0], "meta", None))
            if _STATE_KEY in meta_dict:
                stored_state = meta_dict[_STATE_KEY]
                if isinstance(stored_state, str):
                    stored_state = json.loads(stored_state)
                if isinstance(stored_state, dict):
                    state = stored_state

        # 3. Load events (controlled by config.num_recent_events)
        #    ADK's num_recent_events counts Events, not messages. Since one
        #    Event can span multiple messages (one per part), we over-fetch
        #    by _MAX_PARTS_PER_EVENT to ensure enough messages are retrieved,
        #    then trim the resulting Event list to the requested count.
        target_count = config.num_recent_events if config else None
        if target_count == 0:
            events: list[Event] = []
        else:
            fetch_count = (
                target_count * _MAX_PARTS_PER_EVENT
                if target_count is not None
                else None
            )
            all_messages = await self._fetch_messages(
                app_name, session_id, fetch_count
            )
            events = _messages_to_events(all_messages)
            if target_count is not None:
                events = events[-target_count:]

        # 4. Filter by after_timestamp
        if config and config.after_timestamp:
            events = [e for e in events if e.timestamp >= config.after_timestamp]

        last_update_time = events[-1].timestamp if events else 0.0

        return Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=state,
            events=events,
            last_update_time=last_update_time,
        )

    async def _fetch_messages(
        self,
        space_id: str,
        session_id: str,
        target_count: int | None,
    ) -> list[MessageInfo]:
        """Fetch messages with pagination, respecting the backend's
        ``limit=20`` hard cap.

        Args:
            target_count: ``None`` = load all, ``>0`` = load most recent N.
        """
        # Simple path: small count fits in one page
        if target_count is not None and target_count <= _PAGE_SIZE:
            return await self._client.get_last_k_messages(
                session_id=session_id, k=target_count, space_id=space_id
            )

        # Paginated path: use list_messages
        first = await self._client.list_messages(
            space_id=space_id, session_id=session_id, limit=1, offset=0
        )
        total = first.total

        if target_count is None:
            need = total
            start_offset = 0
            logger.info(
                "Loading all messages for session %s (total=%d). "
                "Consider setting num_recent_events for better performance.",
                session_id,
                total,
            )
        else:
            need = min(target_count, total)
            start_offset = max(0, total - need)

        messages: list[MessageInfo] = []
        offset = start_offset
        remaining = need
        while remaining > 0:
            batch_size = min(_PAGE_SIZE, remaining)
            page = await self._client.list_messages(
                space_id=space_id,
                session_id=session_id,
                limit=batch_size,
                offset=offset,
            )
            messages.extend(page.items)
            offset += len(page.items)
            remaining -= len(page.items)
            if len(page.items) < batch_size:
                break  # reached end

        return messages

    async def list_sessions(
        self,
        *,
        app_name: str,
        user_id: str | None = None,
    ) -> ListSessionsResponse:
        """List sessions for a user in an app."""
        response = await self._client.list_sessions(
            space_id=app_name, actor_id=user_id
        )
        sessions = [
            Session(
                id=s.id,
                app_name=app_name,
                user_id=s.actor_id or "",
                state={},
                events=[],
            )
            for s in response.items
        ]
        return ListSessionsResponse(sessions=sessions)

    async def delete_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> None:
        """Delete a session from AgentArts."""
        await self._client.delete_session(
            space_id=app_name, session_id=session_id
        )

    async def append_event(self, session: Session, event: Event) -> Event:
        """Append an event to the session and persist to AgentArts.

        1. Calls the base class to update in-memory state and events.
        2. Extracts session-scoped state (excluding ``app:``/``user:``/``temp:``).
        3. Encodes the full state snapshot into ``message.meta``.
        4. Persists via ``add_messages`` with an idempotency key to
           prevent duplicates.
        """
        # 1. Base class: apply temp state, trim temp delta, update session state
        event = await super().append_event(session=session, event=event)

        # 2. Extract session-scoped state
        session_state = _extract_session_scoped_state(session.state)

        # 3. Convert event to messages with full state snapshot
        messages = event_to_messages(event, full_state=session_state)

        # 4. Persist with idempotency key (dedup via 409 fallback)
        try:
            await self._client.add_messages(
                space_id=session.app_name,
                session_id=session.id,
                messages=messages,
                idempotency_key=f"{session.id}:{event.id}",
            )
        except APIException as e:
            if e.status_code == 409:
                # Already persisted (e.g., by MemoryService), skip
                logger.debug(
                    "Event %s already persisted for session %s, skipping.",
                    event.id,
                    session.id,
                )
            else:
                raise

        return event
