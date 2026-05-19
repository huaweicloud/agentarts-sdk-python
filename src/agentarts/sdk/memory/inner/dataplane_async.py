"""
Agent Memory SDK - Async Data Plane

Async data plane: handles messages, memories and other operations.

All request parameters and response handling logic identical to _DataPlane.
"""

import logging
from dataclasses import dataclass
from typing import Any

from agentarts.sdk.service.memory_service_async import AsyncMemoryHttpService

from .config import (
    MemoryInfo,
    MemoryListFilter,
    MemoryListResponse,
    MemorySearchFilter,
    MemorySearchResponse,
    MessageBatchResponse,
    MessageInfo,
    MessageListResponse,
    SessionCreateRequest,
    SessionInfo,
)

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Message data class."""
    role: str
    content: str


class _AsyncDataPlane:
    """
    Async Data Plane API - All parameters identical to _DataPlane.
    """

    def __init__(
            self,
            region_name: str | None = None,
            api_key: str | None = None,
            verify_ssl: bool | str = True,
    ):
        """
        Initialize async data plane - identical to sync version.

        Args:
            region_name: Huawei Cloud region name, auto-detected from environment if not provided
            api_key: API Key for data plane authentication (optional, falls back to environment variable)
            verify_ssl: SSL verification setting (default: True).
        """
        self.client = AsyncMemoryHttpService(
            region_name=region_name,
            endpoint_type="data",
            api_key=api_key,
            verify_ssl=verify_ssl,
        )
        logger.info("AsyncDataPlane initialized")

    async def create_memory_session(
            self,
            space_id: str,
            request: SessionCreateRequest
    ) -> SessionInfo:
        """
        Create Memory Session - identical to sync version.

        Args:
            space_id: Space ID
            request: Session configuration

        Returns:
            Session info, including id field
        """
        logger.info(f"Creating memory session in space: {space_id}")

        result = await self.client.create_session(space_id, request.to_dict())

        logger.info(f"Memory session created: {result.get('id')}")
        return SessionInfo.from_dict(result)

    async def add_messages(
            self,
            space_id: str,
            session_id: str,
            messages: list[dict[str, Any]],
            timestamp: int | None = None,
            idempotency_key: str | None = None,
            is_force_extract: bool = False
    ) -> MessageBatchResponse:
        """
        Add messages - identical to sync version.

        Args:
            space_id: Space ID (required)
            session_id: Session ID
            messages: Message list (already in OpenAPI format dictionary)
            timestamp: Client API call time (milliseconds timestamp, optional)
            idempotency_key: Idempotency key for batch operations (prevents retry duplicates)
            is_force_extract: Whether to force trigger memory extraction

        Returns:
            MessageBatchResponse: List of successfully added messages
        """
        if not space_id:
            msg = "space_id is required for data plane operations"
            raise ValueError(msg)

        logger.info(f"Adding {len(messages)} messages to session: {session_id}")

        request_data = {
            "messages": messages,
            "is_force_extract": is_force_extract
        }
        if timestamp is not None:
            request_data["timestamp"] = timestamp
        if idempotency_key is not None:
            request_data["idempotency_key"] = idempotency_key

        result = await self.client.add_messages(space_id, session_id, request_data)
        logger.info(f"Messages added to session: {session_id}")
        return MessageBatchResponse.from_dict(result)

    async def get_last_k_messages(
            self,
            session_id: str,
            k: int,
            space_id: str
    ) -> list[MessageInfo]:
        """
        Get last K messages - identical to sync version.

        Args:
            session_id: Session ID
            k: Number of messages to retrieve
            space_id: Space ID (required)

        Returns:
            List[MessageInfo]: Message list
        """
        if not space_id:
            msg = "space_id is required"
            raise ValueError(msg)

        logger.info(f"Getting last {k} messages from session: {session_id}")

        result = await self.client.list_messages(space_id, session_id, limit=1, offset=0)
        total = result.get("total", 0)

        offset = max(0, total - k)

        result = await self.client.list_messages(space_id, session_id, limit=k, offset=offset)
        return [MessageInfo.from_dict(msg) for msg in result.get("items", [])]

    async def get_message(
            self,
            message_id: str,
            space_id: str,
            session_id: str
    ) -> MessageInfo:
        """
        Get single message - identical to sync version.

        Args:
            message_id: Message ID
            space_id: Space ID
            session_id: Session ID

        Returns:
            Message details
        """
        logger.info(f"Getting message: {message_id}")
        result = await self.client.get_message(space_id, session_id, message_id)
        return MessageInfo.from_dict(result)

    async def list_messages(
            self,
            space_id: str,
            session_id: str | None = None,
            limit: int = 10,
            offset: int = 0
    ) -> MessageListResponse:
        """
        List messages - identical to sync version.

        Args:
            space_id: Space ID
            session_id: Session ID (optional, for getting messages from a specific session)
            limit: Number per page, default 10
            offset: Offset, default 0

        Returns:
            MessageListResponse: Message list response, including items and total
        """
        logger.info(f"Listing messages in space: {space_id}, session: {session_id}")
        result = await self.client.list_messages(space_id, session_id, limit=limit, offset=offset)
        return MessageListResponse.from_dict(result)

    async def search_memories(
            self,
            space_id: str,
            filters: MemorySearchFilter | None = None
    ) -> MemorySearchResponse:
        """
        Search memories - identical to sync version.

        Args:
            space_id: Space ID
            filters: Filter conditions (optional)

        Returns:
            Search results
        """
        logger.info(f"Searching memories in space: {space_id}")

        filters_dict = filters.to_dict() if filters else {}
        result = await self.client.search_memories(space_id, filters_dict)
        return MemorySearchResponse.from_dict(result)

    async def list_memories(
            self,
            space_id: str,
            limit: int = 10,
            offset: int = 0,
            filters: MemoryListFilter | None = None
    ) -> MemoryListResponse:
        """
        List memory records - identical to sync version.

        Args:
            space_id: Space ID
            limit: Number per page, default 10
            offset: Offset, default 0
            filters: Filter conditions

        Returns:
            MemoryListResponse: Memory record list response, including items and total
        """
        logger.info(f"Listing memories in space: {space_id}")
        filters_dict = filters.to_dict() if filters else {}
        result = await self.client.list_memories(
            space_id,
            limit=limit,
            offset=offset,
            filters=filters_dict
        )
        return MemoryListResponse.from_dict(result)

    async def get_memory(self, space_id: str, memory_id: str) -> MemoryInfo:
        """
        Get memory record - identical to sync version.

        Args:
            space_id: Space ID
            memory_id: Memory ID

        Returns:
            MemoryInfo: Record details
        """
        logger.info(f"Getting memory: {memory_id}")
        result = await self.client.get_memory(space_id, memory_id)
        return MemoryInfo.from_dict(result)

    async def delete_memory(self, space_id: str, memory_id: str) -> None:
        """
        Delete memory record - identical to sync version.

        Args:
            space_id: Space ID
            memory_id: Memory ID
        """
        logger.info(f"Deleting memory: {memory_id}")
        await self.client.delete_memory(space_id, memory_id)

    async def close(self) -> None:
        """Close the async data plane and release resources."""
        if hasattr(self, "client") and self.client is not None:
            await self.client.close()
            logger.info("AsyncDataPlane closed")
