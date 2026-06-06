"""
Agent Memory SDK - AsyncMemoryClient

Async version of MemoryClient for non-blocking operations.

All request parameters and response handling identical to MemoryClient.
Control plane operations remain synchronous (low-frequency operations).
"""

import threading
from typing import Any

from agentarts.sdk.utils.constant import get_region

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
    SessionInfo,
    SpaceCreateRequest,
    SpaceInfo,
    SpaceListResponse,
    SpaceUpdateRequest,
    TextMessage,
    ToolCallMessage,
    ToolResultMessage,
)
from .inner.controlplane import _ControlPlane
from .inner.dataplane_async import _AsyncDataPlane


class AsyncMemoryClient:
    """
    Async Memory Client - Non-blocking version of MemoryClient.

    All request parameters identical to MemoryClient.

    Control plane operations (Space management) remain synchronous:
    - These are low-frequency operations (create, update, delete Space)
    - No significant performance impact

    Data plane operations are asynchronous:
    - High-frequency operations (add_messages, search_memories, etc.)
    - Non-blocking for runtime performance
    """

    def __init__(
            self,
            region_name: str | None = None,
            api_key: str | None = None,
            verify_ssl: bool | str = True,
    ):
        """
        Initialize Async Memory Client - identical parameters to MemoryClient.

        Args:
            region_name: Huawei Cloud region name, auto-detected from environment if not provided
            api_key: API Key for data plane authentication (optional, falls back to environment variable)
            verify_ssl: SSL verification setting.
                - True: Verify SSL certificates using system CA bundle (default)
                - False: Skip SSL verification (not recommended for production)
                - str: Path to custom CA certificate file
        """
        self.region_name = region_name or get_region()
        self._verify_ssl = verify_ssl

        self._control_plane = None
        self._async_data_plane = _AsyncDataPlane(
            region_name=region_name,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )
        self._control_plane_init_lock = threading.Lock()

    def _ensure_control_plane_initialized(self, region_name: str):
        """Ensure control plane is initialized - identical to sync version."""
        with self._control_plane_init_lock:
            if self._control_plane is None:
                self._control_plane = _ControlPlane(
                    region_name=region_name,
                    verify_ssl=self._verify_ssl,
                )

    # ==================== Control Plane - Space Management (Synchronous) ====================

    def create_space(
            self,
            name: str,
            message_ttl_hours: int = 168,
            description: str | None = None,
            tags: list[dict[str, str]] | None = None,
            memory_extract_idle_seconds: int | None = None,
            memory_extract_max_tokens: int | None = None,
            memory_extract_max_messages: int | None = None,
            public_access_enable: bool = True,
            private_vpc_id: str | None = None,
            private_subnet_id: str | None = None,
            memory_strategies_builtin: list[str] | None = None,
            memory_strategies_customized: list[dict[str, Any]] | None = None
    ) -> SpaceInfo:
        """Create Space - identical to sync version."""
        request = SpaceCreateRequest(
            name=name,
            message_ttl_hours=message_ttl_hours,
            description=description,
            tags=tags,
            memory_extract_idle_seconds=memory_extract_idle_seconds,
            memory_extract_max_tokens=memory_extract_max_tokens,
            memory_extract_max_messages=memory_extract_max_messages,
            public_access_enable=public_access_enable,
            private_vpc_id=private_vpc_id,
            private_subnet_id=private_subnet_id,
            memory_strategies_builtin=memory_strategies_builtin,
            memory_strategies_customized=memory_strategies_customized
        )

        self._ensure_control_plane_initialized(self.region_name)

        return self._control_plane.create_space(request)

    def get_space(self, space_id: str) -> SpaceInfo:
        """Get Space details - identical to sync version."""
        self._ensure_control_plane_initialized(self._async_data_plane.client.region_name)
        return self._control_plane.get_space(space_id)

    def list_spaces(
            self,
            limit: int = 20,
            offset: int = 0
    ) -> SpaceListResponse:
        """List all Spaces - identical to sync version."""
        self._ensure_control_plane_initialized(self._async_data_plane.client.region_name)
        return self._control_plane.list_spaces(limit, offset)

    def update_space(
            self,
            space_id: str,
            name: str | None = None,
            description: str | None = None,
            message_ttl_hours: int | None = None,
            memory_extract_enabled: bool | None = None,
            memory_extract_idle_seconds: int | None = None,
            memory_extract_max_tokens: int | None = None,
            memory_extract_max_messages: int | None = None,
            tags: list[dict[str, str]] | None = None,
            memory_strategies_builtin: list[str] | None = None
    ) -> SpaceInfo:
        """Update Space configuration - identical to sync version."""
        request = SpaceUpdateRequest(
            name=name,
            description=description,
            message_ttl_hours=message_ttl_hours,
            memory_extract_enabled=memory_extract_enabled,
            memory_extract_idle_seconds=memory_extract_idle_seconds,
            memory_extract_max_tokens=memory_extract_max_tokens,
            memory_extract_max_messages=memory_extract_max_messages,
            tags=tags,
            memory_strategies_builtin=memory_strategies_builtin
        )

        self._ensure_control_plane_initialized(self._async_data_plane.client.region_name)
        return self._control_plane.update_space(space_id, request)

    def delete_space(self, space_id: str) -> None:
        """Delete Space - identical to sync version."""
        self._ensure_control_plane_initialized(self._async_data_plane.client.region_name)
        return self._control_plane.delete_space(space_id)

    # ==================== Data Plane - Session Management (Async) ====================

    async def create_memory_session(
            self,
            space_id: str,
            id: str | None = None,
            actor_id: str | None = None,
            assistant_id: str | None = None,
            meta: dict[str, Any] | None = None
    ) -> SessionInfo:
        """Create Memory Session - identical to sync version."""
        session_request = SessionCreateRequest(
            id=id,
            actor_id=actor_id,
            assistant_id=assistant_id,
            meta=meta
        )

        return await self._async_data_plane.create_memory_session(space_id, session_request)

    # ==================== Data Plane - Message Management (Async) ====================

    async def get_last_k_messages(
            self,
            session_id: str,
            k: int,
            space_id: str
    ) -> list[MessageInfo]:
        """Get last K messages - identical to sync version."""
        return await self._async_data_plane.get_last_k_messages(session_id, k, space_id)

    async def get_message(self, message_id: str, space_id: str, session_id: str) -> MessageInfo:
        """Get single message - identical to sync version."""
        return await self._async_data_plane.get_message(message_id, space_id, session_id)

    async def add_messages(
            self,
            space_id: str,
            session_id: str,
            messages: list[TextMessage | ToolCallMessage | ToolResultMessage],
            *,
            timestamp: int | None = None,
            idempotency_key: str | None = None,
            is_force_extract: bool = False
    ) -> MessageBatchResponse:
        """Add messages - identical to sync version."""
        message_requests = []

        for msg in messages:
            if isinstance(msg, (TextMessage, ToolCallMessage, ToolResultMessage)):
                message_requests.append(msg.to_dict())
            else:
                msg = f"Unsupported message type: {type(msg)}"
                raise ValueError(msg)
        return await self._async_data_plane.add_messages(
            space_id,
            session_id,
            message_requests,
            timestamp=timestamp,
            idempotency_key=idempotency_key,
            is_force_extract=is_force_extract
        )

    async def list_messages(
            self,
            space_id: str,
            session_id: str | None = None,
            limit: int = 10,
            offset: int = 0
    ) -> MessageListResponse:
        """List messages - identical to sync version."""
        return await self._async_data_plane.list_messages(space_id, session_id, limit, offset)

    # ==================== Data Plane - Memory Management (Async) ====================

    async def search_memories(
            self,
            space_id: str,
            filters: MemorySearchFilter | None = None
    ) -> MemorySearchResponse:
        """Search memories - identical to sync version."""
        return await self._async_data_plane.search_memories(space_id, filters)

    async def list_memories(
            self,
            space_id: str,
            limit: int = 10,
            offset: int = 0,
            filters: MemoryListFilter | None = None
    ) -> MemoryListResponse:
        """List memory records - identical to sync version."""
        return await self._async_data_plane.list_memories(space_id, limit, offset, filters)

    async def get_memory(self, space_id: str, memory_id: str) -> MemoryInfo:
        """Get memory record - identical to sync version."""
        return await self._async_data_plane.get_memory(space_id, memory_id)

    async def delete_memory(self, space_id: str, memory_id: str) -> None:
        """Delete memory record - identical to sync version."""
        return await self._async_data_plane.delete_memory(space_id, memory_id)

    # ==================== Resource Management ====================

    async def close(self) -> None:
        """Close Client connection - async version."""
        if self._control_plane is not None:
            self._control_plane.close()
        await self._async_data_plane.close()

    async def __aenter__(self) -> "AsyncMemoryClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
