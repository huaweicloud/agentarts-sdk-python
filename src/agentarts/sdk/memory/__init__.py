"""Agent Memory SDK - v2.0
Refactored according to actual API specifications, integrates with Huawei Cloud Memory Service.

Recommended usage:
- MemoryClient: Unified entry point, provides all methods (synchronous).
- AsyncMemoryClient: Async version for non-blocking operations.

Example:
    from agentarts.sdk.memory import (
        MemoryClient,
        AsyncMemoryClient,
        SpaceCreateRequest,
        SpaceUpdateRequest,
        SessionCreateRequest,
        MessageRequest,
        TextPart,
        ImagePart,
        FilePart,
    )

    # Create sync client
    client = MemoryClient(api_key="your-api-key", region_name="cn-southwest-2")

    # Create async client
    async_client = AsyncMemoryClient(api_key="your-api-key", region_name="cn-southwest-2")

    # Create Space
    space_request = SpaceCreateRequest(
        name="my-space",
        message_ttl_hours=168,
    )
    space = client.create_space(space_request)
"""

# Public interface
# Internal classes (for advanced users)
from agentarts.sdk.service.memory_service import MemoryHttpService

from .async_client import AsyncMemoryClient
from .async_session import AsyncMemorySession
from .client import MemoryClient

# Data types
from .inner.config import (
    AddMessagesRequest,
    ApiKeyInfo,
    AssetRef,
    ContextChainResponse,
    ContextCompressionResponse,
    DataMessage,
    MemoryInfo,
    MemoryListFilter,
    MemoryListResponse,
    MemorySearchFilter,
    MemorySearchResponse,
    MessageBatchResponse,
    MessageInfo,
    MessageListResponse,
    MessageRequest,
    SessionCreateRequest,
    SessionInfo,
    SessionListResponse,
    SpaceCreateRequest,
    SpaceInfo,
    SpaceListResponse,
    SpaceUpdateRequest,
    TextMessage,
    ToolCallMessage,
    ToolResultMessage,
)
from .session import MemorySession

__all__ = [
    "AddMessagesRequest",
    "ApiKeyInfo",
    "AssetRef",
    "AsyncMemoryClient",
    "AsyncMemorySession",
    "ContextChainResponse",
    "ContextCompressionResponse",
    "DataMessage",
    "MemoryClient",
    "MemoryHttpService",
    "MemoryInfo",
    "MemoryListFilter",
    "MemoryListResponse",
    "MemorySearchFilter",
    "MemorySearchResponse",
    "MemorySession",
    "MessageBatchResponse",
    "MessageInfo",
    "MessageListResponse",
    "MessageRequest",
    "SessionCreateRequest",
    "SessionInfo",
    "SessionListResponse",
    "SpaceCreateRequest",
    "SpaceInfo",
    "SpaceListResponse",
    "SpaceUpdateRequest",
    "TextMessage",
    "ToolCallMessage",
    "ToolResultMessage",
]
