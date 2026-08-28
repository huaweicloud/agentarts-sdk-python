"""
AgentArts Memory Service for Google ADK

Implements ``BaseMemoryService`` by ingesting conversation events into
the AgentArts Memory backend for semantic search and memory extraction.

Deduplication strategy (idempotency_key + 409 fallback):
    When ``SessionService.append_event`` has already persisted an event,
    ``MemoryService.add_session_to_memory`` would re-ingest it. To prevent
    duplicates, every ``add_messages`` call uses
    ``idempotency_key=f"{session_id}:{event.id}"``. The backend rejects
    duplicates with 409 Conflict before any DB write, so the overhead is
    negligible.

Asynchronous extraction:
    The AgentArts backend performs memory extraction asynchronously.
    ``is_force_extract=True`` is safe and triggers extraction, but is not
    required for correctness.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence

from agentarts.sdk.memory import AsyncMemoryClient, MemorySearchFilter
from agentarts.sdk.service import APIException

try:
    from google.adk.events.event import Event
    from google.adk.memory.base_memory_service import (
        BaseMemoryService,
        SearchMemoryResponse,
    )
    from google.adk.sessions.session import Session

    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    BaseMemoryService = object  # type: ignore[assignment,misc]
    SearchMemoryResponse = None  # type: ignore[assignment,misc]
    Session = None  # type: ignore[assignment,misc]
    Event = None  # type: ignore[assignment,misc]

from agentarts.sdk.integration.google_adk.converter import (
    _convert_search_response,
    event_to_messages,
)

logger = logging.getLogger(__name__)


class AgentArtsMemoryService(BaseMemoryService):
    """ADK MemoryService backed by AgentArts Memory.

    Provides:
        - ``add_session_to_memory``: Ingest all session events (with dedup).
        - ``add_events_to_memory``: Ingest a subset of events (incremental).
        - ``search_memory``: Semantic search over stored memories.
    """

    def __init__(self, client: AsyncMemoryClient):
        self._client = client

    async def _try_add_event(
        self,
        event: Event,
        session_id: str,
        space_id: str,
    ) -> None:
        """Add a single event as a message, with idempotency-key dedup.

        Skips events with no content parts (pure state updates).
        Catches 409 Conflict silently - the message is already persisted.

        Guards against ``event.id`` being None (e.g., externally
        constructed Events) by assigning a UUID so the idempotency key
        does not collapse to ``"session_id:None"``.
        """
        if not event.id:
            import uuid
            event.id = str(uuid.uuid4())

        if not (event.content and event.content.parts):
            return

        messages = event_to_messages(event)
        try:
            await self._client.add_messages(
                space_id=space_id,
                session_id=session_id,
                messages=messages,
                idempotency_key=f"{session_id}:{event.id}",
                is_force_extract=True,
            )
        except APIException as e:
            if e.status_code == 409:
                logger.debug(
                    "Event %s already ingested for session %s, skipping.",
                    event.id,
                    session_id,
                )
            else:
                raise

    async def add_session_to_memory(self, session: Session) -> None:
        """Ingest all session events into memory.

        A session may be added multiple times; idempotency keys ensure
        no duplicates are created.
        """
        for event in session.events:
            await self._try_add_event(event, session.id, session.app_name)

    async def add_events_to_memory(
        self,
        *,
        app_name: str,
        user_id: str,
        events: Sequence[Event],
        session_id: str | None = None,
        custom_metadata: Mapping[str, object] | None = None,
    ) -> None:
        """Ingest an incremental list of events (delta) into memory.

        Prefer this over ``add_session_to_memory`` when you only need
        to persist the latest turn - it avoids iterating the full
        session history and issuing unnecessary 409s.
        """
        sid = session_id or "__unknown_session_id__"
        for event in events:
            await self._try_add_event(event, sid, app_name)

    async def search_memory(
        self,
        *,
        app_name: str,
        user_id: str,
        query: str,
    ) -> SearchMemoryResponse:
        """Semantic search over stored memories.

        Args:
            app_name: AgentArts space ID.
            user_id: AgentArts actor ID (used as filter).
            query: Natural-language search query.

        Returns:
            ADK SearchMemoryResponse with matching memory entries.
        """
        response = await self._client.search_memories(
            space_id=app_name,
            filters=MemorySearchFilter(query=query, actor_id=user_id),
        )
        return _convert_search_response(response)
