"""Agent Memory SDK - v2.0
Refactored according to actual API specifications, integrates with Huawei Cloud Memory Service.

Recommended usage:
- MemoryClient: Unified entry point, provides all methods.

Example:
    from agentarts.sdk.memory import (
        MemoryClient,
        SpaceCreateRequest,
        SpaceUpdateRequest,
        SessionCreateRequest,
        MessageRequest,
        TextPart,
        ImagePart,
        FilePart,
    )

    # Create client (requires IAM Token)
    client = MemoryClient(iam_token="your-token", region_name="cn-southwest-2")

    # Create Space
    space_request = SpaceCreateRequest(
        name="my-space",
        message_ttl_hours=168,
        api_key_id="your-api-key-id"
    )
    space = client.create_space(space_request)
"""

# Public interface
from .client import MemoryClient

# Data types
from .inner.config import (
    # ==================== Request types ====================
    SpaceCreateRequest,
    SpaceUpdateRequest,
    SessionCreateRequest,
    AddMessagesRequest,
    MessageRequest,
    AssetRef,
    ToolCallMessage,
    ToolResultMessage,
    DataMessage,
    TextMessage,

    # ==================== Response types ====================
    SpaceInfo,
    SpaceListResponse,
    SessionInfo,
    SessionListResponse,
    MessageInfo,
    MessageListResponse,
    MessageBatchResponse,
    MemoryInfo,
    MemoryListResponse,
    MemorySearchResponse,
    ContextChainResponse,
    ContextCompressionResponse,
    ApiKeyInfo,
)

# Internal classes (for advanced users)
from ..service.memory_service import MemoryHttpService

__all__ = [
    # ==================== Main entry point ====================
    "MemoryClient",

    # ==================== Request types ====================
    "SpaceCreateRequest",
    "SpaceUpdateRequest",
    "SessionCreateRequest",
    "AddMessagesRequest",
    "MessageRequest",
    "AssetRef",
    "DataMessage",

    # ==================== SDK-specific message types ====================
    "TextMessage",
    "ToolCallMessage",
    "ToolResultMessage",

    # ==================== Response types ====================
    "SpaceInfo",
    "SpaceListResponse",
    "SessionInfo",
    "SessionListResponse",
    "MessageInfo",
    "MessageListResponse",
    "MessageBatchResponse",
    "MemoryInfo",
    "MemoryListResponse",
    "MemorySearchResponse",
    "ContextChainResponse",
    "ContextCompressionResponse",
    "ApiKeyInfo",

    # ==================== Internal classes (for advanced users) ====================
    "MemoryHttpService"
]
