"""Agent Memory SDK - v2.0
根据实际 API 规范整改，与华为云 Memory 服务对接

推荐使用：
- MemoryClient: 统一入口，提供所有方法

示例：
    from hw_agentrun_wrapper.memory import (
        MemoryClient,
        SpaceCreateRequest,
        SpaceUpdateRequest,
        SessionCreateRequest,
        MessageRequest,
        TextPart,
        ImagePart,
        FilePart,
    )

    # 创建客户端（需要 IAM Token）
    client = MemoryClient(iam_token="your-token", region_name="cn-north-4")

    # 创建 Space
    space_request = SpaceCreateRequest(
        name="my-space",
        message_ttl_hours=168,
        api_key_id="your-api-key-id"
    )
    space = client.create_space(space_request)
"""

# 公共接口
from .client import MemoryClient

# 数据类型（新版）
from .inner.config import (
    # ==================== 请求类型 ====================
    SpaceCreateRequest,  # 面向用户的版本
    SpaceUpdateRequest,
    SessionCreateRequest,
    AddMessagesRequest,
    MessageRequest,
    AssetRef,
    ToolCallMessage,
    ToolResultMessage,
    DataMessage,
    TextMessage,

    # ==================== 响应类型 ====================
    SpaceInfo,  # Space返回信息
    SpaceListResponse,  # Space列表响应
    SessionInfo,  # Session返回信息
    SessionListResponse,  # Session列表响应
    MessageInfo,  # Message返回信息
    MessageListResponse,  # Message列表响应
    MessageBatchResponse,  # Message批量响应
    MemoryInfo,  # Memory返回信息
    MemoryListResponse,  # Memory列表响应
    MemorySearchResponse,  # Memory搜索响应
    ContextChainResponse,  # 上下文链响应
    ContextCompressionResponse,  # 上下文压缩响应
    ApiKeyInfo,  # API Key返回信息
)

# 内部类（高级用户）
from ..services.memory_http import MemoryHttpService

__all__ = [
    # ==================== 主入口 ====================
    "MemoryClient",

    # ==================== 请求类型 ====================
    "SpaceCreateRequest",  # 面向用户的版本
    "SpaceUpdateRequest",
    "SessionCreateRequest",
    "AddMessagesRequest",
    "MessageRequest",
    "AssetRef",
    "DataMessage",

    # ==================== SDK专用消息类型 ====================
    "TextMessage",  # SDK文本消息 - 便于使用和扩展
    "ToolCallMessage",
    "ToolResultMessage",

    # ==================== 响应类型 ====================
    "SpaceInfo",  # Space返回信息
    "SpaceListResponse",  # Space列表响应
    "SessionInfo",  # Session返回信息
    "SessionListResponse",  # Session列表响应
    "MessageInfo",  # Message返回信息
    "MessageListResponse",  # Message列表响应
    "MessageBatchResponse",  # Message批量响应
    "MemoryInfo",  # Memory返回信息
    "MemoryListResponse",  # Memory列表响应
    "MemorySearchResponse",  # Memory搜索响应
    "ContextChainResponse",  # 上下文链响应
    "ContextCompressionResponse",  # 上下文压缩响应
    "ApiKeyInfo",  # API Key返回信息

    # ==================== 内部类（高级用户）====================
    "MemoryHttpService"
]
