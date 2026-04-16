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
# Internal classes (for advanced users)
from agentarts.sdk.service.memory_service import MemoryHttpService

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
    MemoryListResponse,
    MemorySearchResponse,
    MessageBatchResponse,
    MessageInfo,
    MessageListResponse,
    MessageRequest,
    SessionCreateRequest,
    SessionInfo,
    SessionListResponse,
    # ==================== Request types ====================
    SpaceCreateRequest,
    # ==================== Response types ====================
    SpaceInfo,
    SpaceListResponse,
    SpaceUpdateRequest,
    TextMessage,
    ToolCallMessage,
    ToolResultMessage,
)

__all__ = [
    "AddMessagesRequest",
    "ApiKeyInfo",
    "AssetRef",
    "ContextChainResponse",
    "ContextCompressionResponse",
    "DataMessage",
    # ==================== Main entry point ====================
    "MemoryClient",
    # ==================== Internal classes (for advanced users) ====================
    "MemoryHttpService",
    "MemoryInfo",
    "MemoryListResponse",
    "MemorySearchResponse",
    "MessageBatchResponse",
    "MessageInfo",
    "MessageListResponse",
    "MessageRequest",
    "SessionCreateRequest",
    "SessionInfo",
    "SessionListResponse",
    # ==================== Request types ====================
    "SpaceCreateRequest",
    # ==================== Response types ====================
    "SpaceInfo",
    "SpaceListResponse",
    "SpaceUpdateRequest",
    # ==================== SDK-specific message types ====================
    "TextMessage",
    "ToolCallMessage",
    "ToolResultMessage"
]
