"""
Agent Memory SDK - Async MemorySession

Async version of MemorySession for non-blocking operations.

All request parameters and response handling identical to MemorySession.
"""

import logging

from .inner.config import (
    MemoryInfo,
    MemoryListFilter,
    MemoryListResponse,
    MemorySearchFilter,
    MemorySearchResponse,
    MessageBatchResponse,
    MessageInfo,
    MessageListResponse,
    SessionCreateRequest,
    TextMessage,
    ToolCallMessage,
    ToolResultMessage,
)
from .inner.dataplane_async import _AsyncDataPlane

logger = logging.getLogger(__name__)


class AsyncRetrievalConfig:
    """
    Async Retrieval configuration class - identical to RetrievalConfig.
    """

    user_id: str | None = None
    max_tokens: int = 0
    top_k: int = 2
    score_threshold: float = 0.6

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return f"AsyncRetrievalConfig(user_id={self.user_id}, max_tokens={self.max_tokens}, top_k={self.top_k}, score_threshold={self.score_threshold})"


class AsyncMemorySession:
    """
    Async Memory session wrapper class - Non-blocking version of MemorySession.

    All request parameters identical to MemorySession.

    Usage:
        1. Specify space_id and actor_id when creating AsyncMemorySession, automatically creates a new Session
        2. Or specify an existing session_id to reuse an existing Session
    """

    def __init__(
            self,
            space_id: str,
            actor_id: str,
            session_id: str | None = None,
            region_name: str | None = None,
            api_key: str | None = None
    ):
        """
        Initialize AsyncMemorySession - identical parameters to MemorySession.

        Args:
            space_id: Space ID, required
            actor_id: Participant ID, required
            session_id: Session ID, optional
            region_name: Huawei Cloud region name, optional
            api_key: API Key for data plane authentication, optional
        """
        if region_name is None:
            region_name = "cn-southwest-2"

        self.space_id = space_id
        self.actor_id = actor_id
        self._region_name = region_name

        self._async_data_plane = _AsyncDataPlane(region_name=region_name, api_key=api_key)

        self._initialized = False
        self._pending_session_id = session_id

    async def _ensure_initialized(self) -> None:
        """Ensure session is initialized."""
        if self._initialized:
            return

        if self._pending_session_id is None:
            session_config = SessionCreateRequest(actor_id=self.actor_id)
            session_info = await self._async_data_plane.create_memory_session(self.space_id, session_config.to_dict())
            self.session_id = session_info.id
            if not self.session_id:
                msg = f"Failed to create session: {session_info}"
                raise ValueError(msg)
            logger.info(f"Session created via API: {self.session_id}")
        else:
            self.session_id = self._pending_session_id

        self._initialized = True

    @classmethod
    def of(
            cls,
            space_id: str,
            actor_id: str,
            session_id: str | None = None,
            region_name: str | None = None,
            api_key: str | None = None
    ) -> "AsyncMemorySession":
        """Factory method: Create AsyncMemorySession - identical to sync version."""
        return cls(
            space_id=space_id,
            actor_id=actor_id,
            session_id=session_id,
            region_name=region_name,
            api_key=api_key
        )

    def __repr__(self) -> str:
        """Return string representation - identical to sync version."""
        session_id = getattr(self, "session_id", "<pending>")
        return f"AsyncMemorySession(space_id='{self.space_id}', session_id='{session_id}', region_name='{self._region_name}')"

    @property
    def region_name(self) -> str:
        """Get region name."""
        return self._region_name

    # ==================== Message Management (Async) ====================

    async def get_last_k_messages(
            self,
            k: int
    ) -> list[MessageInfo]:
        """Get the last K messages - identical to sync version."""
        await self._ensure_initialized()
        logger.info(f"Getting last {k} messages for session: {self.session_id}")
        return await self._async_data_plane.get_last_k_messages(self.session_id, k, self.space_id)

    async def add_messages(
            self,
            messages: list[TextMessage | ToolCallMessage | ToolResultMessage],
            *,
            timestamp: int | None = None,
            idempotency_key: str | None = None,
            is_force_extract: bool = False
    ) -> MessageBatchResponse:
        """Add messages - identical to sync version."""
        await self._ensure_initialized()
        logger.info(f"Adding {len(messages)} messages to session: {self.session_id}")

        message_requests = []

        for msg in messages:
            if isinstance(msg, (TextMessage, ToolCallMessage, ToolResultMessage)):
                message_requests.append(msg.to_dict())
            else:
                msg = f"Unsupported message type: {type(msg)}"
                raise ValueError(msg)

        return await self._async_data_plane.add_messages(
            space_id=self.space_id,
            session_id=self.session_id,
            messages=message_requests,
            timestamp=timestamp,
            idempotency_key=idempotency_key,
            is_force_extract=is_force_extract
        )

    async def list_messages(
            self,
            limit: int = 10,
            offset: int = 0
    ) -> MessageListResponse:
        """List messages - identical to sync version."""
        await self._ensure_initialized()
        logger.info(f"Listing messages for session: {self.session_id}")
        return await self._async_data_plane.list_messages(
            space_id=self.space_id,
            session_id=self.session_id,
            limit=limit,
            offset=offset
        )

    async def get_message(self, message_id: str) -> MessageInfo:
        """Get a specific message - identical to sync version."""
        await self._ensure_initialized()
        logger.info(f"Getting message: {message_id}")
        return await self._async_data_plane.get_message(self.space_id, self.session_id, message_id)

    async def search_memories(
            self,
            filters: MemorySearchFilter | None = None
    ) -> MemorySearchResponse:
        """Search memories - identical to sync version."""
        await self._ensure_initialized()
        logger.info(f"Searching memories with filter: {filters}")

        return await self._async_data_plane.search_memories(
            space_id=self.space_id,
            filters=filters
        )

    async def list_memories(
            self,
            limit: int = 10,
            offset: int = 0,
            filters: MemoryListFilter | None = None
    ) -> MemoryListResponse:
        """List memory records - identical to sync version."""
        await self._ensure_initialized()
        logger.info(f"Listing memory records: limit={limit}, offset={offset}")

        return await self._async_data_plane.list_memories(
            space_id=self.space_id,
            limit=limit,
            offset=offset,
            filters=filters
        )

    async def get_memory(self, memory_id: str) -> MemoryInfo:
        """Get a specific memory record - identical to sync version."""
        await self._ensure_initialized()
        logger.info(f"Getting memory record: {memory_id}")
        return await self._async_data_plane.get_memory(self.space_id, memory_id)

    async def delete_memory(self, memory_id: str) -> None:
        """Delete a specific memory record - identical to sync version."""
        await self._ensure_initialized()
        logger.info(f"Deleting memory record: {memory_id}")
        await self._async_data_plane.delete_memory(self.space_id, memory_id)

    async def close(self) -> None:
        """Close the async session and release resources."""
        if hasattr(self, "_async_data_plane") and self._async_data_plane is not None:
            await self._async_data_plane.close()
            logger.info("AsyncMemorySession closed")

    async def __aenter__(self) -> "AsyncMemorySession":
        """Async context manager entry."""
        await self._ensure_initialized()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
