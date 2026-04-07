"""
Agent Memory SDK 配置模块
提供SDK配置和数据类定义
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any, Literal


# ==================== 枚举类型 ====================

class StrategyType(Enum):
    """记忆策略类型"""
    SEMANTIC = "semantic"
    SUMMARY = "summary"
    USER_PREFERENCE = "user_preference"
    EPISODIC = "episodic"
    EVENT = "event"
    CUSTOM = "custom"


class MessageRole(Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


@dataclass
class CreateMemoryRequest:
    """
    创建记忆请求
    
    必填字段:
        - content: 记忆内容，长度1-10000
        - strategy_type: 策略类型 (semantic, summary, user_preference, episodic, event, custom)
        - strategy_id: 来源策略 ID (UUID)
    
    可选字段:
        - actor_id: 归属 Actor ID，长度0-64
        - assistant_id: 归属 Assistant ID，长度0-64
        - session_id: 会话 ID (UUID)
        - metadata: 元数据 (字典)
    """
    # 必填字段
    content: str
    strategy_type: str
    strategy_id: str

    # 可选字段
    actor_id: Optional[str] = None
    assistant_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "content": self.content,
            "strategy_type": self.strategy_type,
            "strategy_id": self.strategy_id,
        }

        if self.actor_id:
            result["actor_id"] = self.actor_id

        if self.assistant_id:
            result["assistant_id"] = self.assistant_id

        if self.session_id:
            result["session_id"] = self.session_id

        if self.metadata:
            result["metadata"] = self.metadata

        return result


# ==================== 类型化数据类替代Dict参数 ====================

@dataclass
class Tag:
    """标签数据类"""
    key: str
    value: str

    def to_dict(self) -> Dict[str, str]:
        return {"key": self.key, "value": self.value}


@dataclass
class MemoryStrategy:
    """记忆策略配置数据类"""
    type: str
    parameters: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"type": self.type}
        if self.parameters:
            result.update(self.parameters)
        return result


@dataclass
class SessionMetadata:
    """会话元数据数据类"""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.data.copy()


# MessageFilter已被移除，因为list_messages API没有过滤参数

@dataclass
class MemorySearchFilter:
    """记忆搜索过滤条件数据类 - 包含所有search_memories API参数"""

    # 所有API支持的过滤参数（包括top_k和min_score，它们不再是方法参数）
    query: Optional[str] = None  # 搜索查询文本
    strategy_type: Optional[str] = None  # 策略类型过滤: semantic, summary, user_preference, episodic, event, custom
    strategy_id: Optional[str] = None  # 策略实例ID过滤(UUID)
    actor_id: Optional[str] = None  # Actor ID过滤(1-64字符)
    assistant_id: Optional[str] = None  # Assistant ID过滤(1-64字符)
    session_id: Optional[str] = None  # Session ID过滤(UUID)
    memory_type: Optional[Literal["memory", "episode", "reflection"]] = None  # 记忆类型
    start_time: Optional[int] = None  # 起始时间戳（毫秒，0-253402300799999）
    end_time: Optional[int] = None  # 结束时间戳（毫秒，0-253402300799999）
    top_k: Optional[int] = None  # 返回前K个结果(1-100，默认10)
    min_score: Optional[float] = None  # 最小相似度分数阈值(0.0-1.0，默认0.5)

    def to_dict(self) -> Dict[str, Any]:
        """转换为API请求体格式，设置默认值"""
        result = {}

        # 添加所有非None的字段
        for k, v in self.__dict__.items():
            if v is not None:
                # 设置默认值
                if k == "top_k" and v == 10:
                    result[k] = v
                elif k == "min_score" and v == 0.5:
                    result[k] = v
                elif v is not None:
                    result[k] = v

        return result


@dataclass
class MemoryListFilter:
    """记忆列表过滤条件数据类 - 包含所有list_memories API过滤参数（除limit/offset）"""

    # 所有过滤参数（limit和offset已经是方法参数，不放在这里）
    strategy_type: Optional[str] = None  # 按策略类型过滤: semantic, summary, user_preference, episodic, event, custom
    strategy_id: Optional[str] = None  # 按策略实例ID过滤(UUID)
    actor_id: Optional[str] = None  # 按Actor ID过滤(1-64字符)
    assistant_id: Optional[str] = None  # 按Assistant ID过滤(1-64字符)
    session_id: Optional[str] = None  # 按Session ID过滤(UUID)
    start_time: Optional[int] = None  # 起始时间戳（毫秒，0-253402300799999）
    end_time: Optional[int] = None  # 结束时间戳（毫秒，0-253402300799999）
    sort_by: Optional[Literal["created_at", "updated_at"]] = None  # 排序字段，默认created_at
    sort_order: Optional[Literal["asc", "desc"]] = None  # 排序方向，默认desc

    def to_dict(self) -> Dict[str, Any]:
        """转换为API字典格式，设置默认值"""
        result = {}

        # 添加所有非None的字段并设置默认值
        for k, v in self.__dict__.items():
            if v is not None:
                # 处理默认值
                if k == "sort_by" and v == "created_at":
                    result[k] = v
                elif k == "sort_order" and v == "desc":
                    result[k] = v
                else:
                    result[k] = v

        return result


@dataclass
class SpaceCreateRequest:
    """
    Space 创建请求
    
    用户只需要关心Space的基本配置，SDK内部会自动处理API Key的创建

    必填字段:
        - name: Space 名称，长度1-128
        - message_ttl_hours: 消息 TTL (小时), 范围 1-8760
    
    可选字段:
        - description: Space 描述
        - tags: Space 标签
        - public_access_enable: 是否开启公网访问 (默认: True)
        - private_vpc_id: 内网VPC ID (与private_subnet_id同时提供才有效)
        - private_subnet_id: 内网子网ID (与private_subnet_id同时提供才有效)
        - memory_extract_idle_seconds: 记忆抽取idle时间
        - memory_extract_max_tokens: 记忆抽取最大token数  
        - memory_extract_max_messages: 记忆抽取最大message数
        - memory_strategies_builtin: 内置记忆策略列表
        - memory_strategies_customized: 自定义记忆策略列表,memory_strategies_builtin和memory_strategies_customized二选一必填
    """
    # 必填字段
    name: str
    message_ttl_hours: int = 168  # 默认 7 天

    # 可选字段
    description: Optional[str] = None
    memory_extract_idle_seconds: Optional[int] = None
    memory_extract_max_tokens: Optional[int] = None
    memory_extract_max_messages: Optional[int] = None

    # 标签
    tags: Optional[List[Dict[str, str]]] = None

    # 网络访问配置（平铺实现）
    public_access_enable: bool = True  # 默认为true
    private_vpc_id: Optional[str] = None  # 内网VPC ID
    private_subnet_id: Optional[str] = None  # 内网子网ID

    # 记忆策略配置
    memory_strategies_builtin: Optional[List[str]] = None
    memory_strategies_customized: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为API字典格式

        Args:
            create_api_key: 是否需要创建API Key标志，供ControlPlane使用

        Returns:
            适配后端API的请求字典
        """
        # 基础配置
        result = {
            "name": self.name,
            "message_ttl_hours": self.message_ttl_hours,
        }

        # 添加可选字段
        if self.description is not None:
            result["description"] = self.description
        if self.memory_extract_idle_seconds is not None:
            result["memory_extract_idle_seconds"] = self.memory_extract_idle_seconds
        if self.memory_extract_max_tokens is not None:
            result["memory_extract_max_tokens"] = self.memory_extract_max_tokens
        if self.memory_extract_max_messages is not None:
            result["memory_extract_max_messages"] = self.memory_extract_max_messages

        # 记忆策略配置
        if self.memory_strategies_builtin is not None:
            result["memory_strategies_builtin"] = self.memory_strategies_builtin
        if self.memory_strategies_customized is not None:
            result["memory_strategies_customized"] = self.memory_strategies_customized

        # 标签
        if self.tags is not None:
            result["tags"] = self.tags

        # 网络访问配置输出符合OpenAPI规范
        network_access = {}
        network_access["public_access_enable"] = self.public_access_enable

        # 内网访问配置：只有同时提供vpc_id和subnet_id时才创建
        if self.private_vpc_id is not None and self.private_subnet_id is not None:
            private_access = {
                "enable": True,
                "vpc_id": self.private_vpc_id,
                "subnet_id": self.private_subnet_id
            }
            network_access["private_access_config"] = private_access

        result["network_access"] = network_access

        return result


@dataclass
class SpaceUpdateRequest:
    """Space 更新请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    message_ttl_hours: Optional[int] = None

    # 记忆抽取配置
    memory_extract_enabled: Optional[bool] = None
    memory_extract_idle_seconds: Optional[int] = None
    memory_extract_max_tokens: Optional[int] = None
    memory_extract_max_messages: Optional[int] = None

    # 标签
    tags: Optional[List[Dict[str, str]]] = None

    # 记忆策略配置
    memory_strategies_builtin: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，跳过 None 值，符合OpenAPI规范"""
        result = {}

        # 基本字段
        if self.name is not None:
            result["name"] = self.name
        if self.description is not None:
            result["description"] = self.description
        if self.message_ttl_hours is not None:
            result["message_ttl_hours"] = self.message_ttl_hours

        # 记忆抽取配置
        if self.memory_extract_enabled is not None:
            result["memory_extract_enabled"] = self.memory_extract_enabled
        if self.memory_extract_idle_seconds is not None:
            result["memory_extract_idle_seconds"] = self.memory_extract_idle_seconds
        if self.memory_extract_max_tokens is not None:
            result["memory_extract_max_tokens"] = self.memory_extract_max_tokens
        if self.memory_extract_max_messages is not None:
            result["memory_extract_max_messages"] = self.memory_extract_max_messages

        # 记忆策略配置
        if self.memory_strategies_builtin is not None:
            result["memory_strategies_builtin"] = self.memory_strategies_builtin

        # 标签
        if self.tags is not None:
            result["tags"] = self.tags

        return result


# ==================== Session 相关请求类 ====================

@dataclass
class SessionCreateRequest:
    """Session 创建请求"""
    id: Optional[str] = None
    actor_id: Optional[str] = None
    assistant_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，跳过 None 值"""
        result = {}
        if self.id is not None:
            result["id"] = self.id
        if self.actor_id is not None:
            result["actor_id"] = self.actor_id
        if self.assistant_id is not None:
            result["assistant_id"] = self.assistant_id
        if self.meta is not None:
            result["meta"] = self.meta
        return result


# ==================== Message 相关请求类 ====================

@dataclass
class AssetRef:
    """资源引用（文件、图片、音频）"""
    asset_id: str = ""
    uri: str = ""
    mime: str = ""
    size: int = 0
    filename: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "asset_id": self.asset_id,
            "uri": self.uri,
            "mime": self.mime,
            "size": self.size
        }
        if self.filename:
            result["filename"] = self.filename
        if self.meta:
            result["meta"] = self.meta
        return result


@dataclass
class DataMessage:
    """数据消息部分（摘要、卸载索引、自定义数据）"""
    type: str = "data"
    kind: str = "custom"  # summary, offload_index, custom
    covers: Optional[List[str]] = None  # 被摘要/卸载的 message ids
    content: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"type": self.type, "kind": self.kind}
        if self.covers:
            result["covers"] = self.covers
        if self.content:
            result["content"] = self.content
        if self.meta:
            result["meta"] = self.meta
        return result


@dataclass
class ToolCallMessage:
    """工具调用消息部分（符合OpenAPI规范）"""
    type: str = "tool_call"
    id: str = ""
    name: str = ""
    arguments: str = ""  # JSON string, 符合OpenAPI规范

    def __post_init__(self):
        # 如果传入的是字典，自动序列化为JSON字符串
        if self.arguments is None:
            self.arguments = ""
        elif isinstance(self.arguments, dict):
            import json
            self.arguments = json.dumps(self.arguments, ensure_ascii=False)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments
        }

        return {
            "role": "tool",
            "parts": [{"type": "tool_call", "tool_call": result}]
        }


@dataclass
class ToolResultMessage:
    """工具结果消息部分（符合OpenAPI规范）"""
    type: str = "tool_result"
    tool_call_id: str = ""
    content: str = ""
    asset_ref: Optional[AssetRef] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "tool_call_id": self.tool_call_id,
            "content": self.content,
            "asset_ref": self.asset_ref
        }

        return {
            "role": "tool",
            "parts": [{"type": "tool_result", "tool_result": result}]
        }


@dataclass
class MessageRequest:
    """
    消息请求
    
    使用 parts 格式，支持多种消息类型:
    - TextPart: 文本消息
    - ImagePart: 图片消息
    - FilePart: 文件消息
    - AudioPart: 音频消息
    - ToolCallPart: 工具调用
    - ToolResultPart: 工具结果
    - DataPart: 数据消息（摘要、卸载索引、自定义数据）
    - AssetPart: 资源消息
    """
    role: str  # user, assistant, tool, system
    parts: List[Any] = field(default_factory=list)  # Message parts
    actor_id: Optional[str] = None
    assistant_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        # 验证消息数量
        if not self.parts:
            raise ValueError("必须包含至少一个消息部分")

        if len(self.parts) > 5:
            raise ValueError("消息最多包含5个部分")

        # 验证消息部分
        for part in self.parts:
            if not hasattr(part, 'to_dict'):
                raise ValueError(f"消息部分必须支持to_dict方法，实际类型: {type(part)}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，兼容OpenAPI规范"""
        result = {
            "role": self.role,
            "parts": [part.to_dict() for part in self.parts]
        }
        if self.actor_id is not None:
            result["actor_id"] = self.actor_id
        if self.assistant_id is not None:
            result["assistant_id"] = self.assistant_id
        if self.meta is not None:
            result["meta"] = self.meta
        return result


@dataclass
class AddMessagesRequest:
    """批量添加消息请求"""
    messages: List[MessageRequest] = field(default_factory=list)
    timestamp: Optional[int] = None  # 毫秒时间戳
    idempotency_key: Optional[str] = None
    is_force_extract: bool = False

    # 验证消息列表
    def __post_init__(self):
        if not self.messages:
            raise ValueError("必须包含至少一条消息")

        if len(self.messages) > 100:
            raise ValueError("批量消息最多100条")

        for message in self.messages:
            if not isinstance(message, MessageRequest):
                raise ValueError(f"消息必须是MessageRequest类型，实际类型: {type(message)}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，兼容OpenAPI规范"""
        result = {
            "messages": [m.to_dict() for m in self.messages],
            "is_force_extract": self.is_force_extract
        }
        if self.timestamp is not None:
            result["timestamp"] = self.timestamp
        if self.idempotency_key is not None:
            result["idempotency_key"] = self.idempotency_key
        return result


# ==================== Memory 相关请求类 ====================

@dataclass
class MemorySearchRequest:
    """记忆搜索请求"""
    query: Optional[str] = None  # 改为可选，支持纯过滤搜索
    top_k: int = 10
    min_score: float = 0.5  # API默认是0.5，不是0.0
    strategy_type: Optional[str] = None
    strategy_id: Optional[str] = None
    actor_id: Optional[str] = None
    assistant_id: Optional[str] = None
    session_id: Optional[str] = None
    memory_type: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，跳过 None 值，使用API默认值"""
        result = {}

        # 只添加非默认值的字段，符合API规范
        if self.query is not None and self.query != '':
            result["query"] = self.query
        if self.top_k != 10:
            result["top_k"] = self.top_k
        if self.min_score != 0.5:
            result["min_score"] = self.min_score
        if self.strategy_type is not None:
            result["strategy_type"] = self.strategy_type
        if self.strategy_id is not None:
            result["strategy_id"] = self.strategy_id
        if self.actor_id is not None:
            result["actor_id"] = self.actor_id
        if self.assistant_id is not None:
            result["assistant_id"] = self.assistant_id
        if self.session_id is not None:
            result["session_id"] = self.session_id
        if self.memory_type is not None:
            result["memory_type"] = self.memory_type
        if self.start_time is not None:
            result["start_time"] = self.start_time
        if self.end_time is not None:
            result["end_time"] = self.end_time

        # 确保至少有默认值，符合API要求
        if not result:
            result = {"top_k": 10, "min_score": 0.5}

        return result


@dataclass
class MemoryCreateRequest:
    """记忆创建请求"""
    content: str
    actor_id: Optional[str] = None
    assistant_id: Optional[str] = None
    session_id: Optional[str] = None
    extraction_meta: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        # 验证内容长度
        if len(self.content) > 10000:
            raise ValueError("记忆内容不能超过10000个字符")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，兼容OpenAPI规范"""
        result = {
            "content": self.content
        }
        if self.actor_id is not None:
            result["actor_id"] = self.actor_id
        if self.assistant_id is not None:
            result["assistant_id"] = self.assistant_id
        if self.session_id is not None:
            result["session_id"] = self.session_id
        if self.extraction_meta is not None:
            result["extraction_meta"] = self.extraction_meta
        return result


@dataclass
class MemoryUpdateRequest:
    """记忆更新请求"""
    content: Optional[str] = None
    extraction_meta: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        # 验证内容长度
        if self.content is not None and len(self.content) > 10000:
            raise ValueError("记忆内容不能超过10000个字符")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，兼容OpenAPI规范"""
        result = {}
        if self.content is not None:
            result["content"] = self.content
        if self.extraction_meta is not None:
            result["extraction_meta"] = self.extraction_meta
        return result


# ==================== Context 压缩配置 ====================

@dataclass
class CompressConfig:
    """上下文压缩配置"""
    msg_threshold: int = 100
    max_token: int = 131072
    token_ratio: float = 0.75
    last_keep: int = 50
    large_payload_threshold: int = 5000
    custom_prompt: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，跳过 None 值"""
        result = {
            "msg_threshold": self.msg_threshold,
            "max_token": self.max_token,
            "token_ratio": self.token_ratio,
            "last_keep": self.last_keep,
            "large_payload_threshold": self.large_payload_threshold
        }
        if self.custom_prompt is not None:
            result["custom_prompt"] = self.custom_prompt
        return result


# ==================== 类型化返回值数据类 ====================

@dataclass
class SpaceInfo:
    """Space详细信息（返回值用）"""
    # 基本信息
    id: str
    name: str
    description: Optional[str] = None
    message_ttl_hours: int = 168
    status: Optional[str] = None  # creating/running/deleted/create_failed
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # 记忆提取配置
    memory_extract_enabled: bool = False
    memory_extract_idle_seconds: Optional[int] = None
    memory_extract_max_tokens: Optional[int] = None
    memory_extract_max_messages: Optional[int] = None

    # 记忆策略
    memory_strategies_builtin: Optional[List[str]] = None  # 内置策略类型列表
    memory_strategies_customized: Optional[List[Dict[str, Any]]] = None  # 自定义记忆策略列表

    # 网络配置
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    public_access: Optional[Dict[str, Any]] = None  # 公网访问配置对象
    private_access: Optional[Dict[str, Any]] = None  # 内网访问配置对象

    # API Key
    api_key: Optional[str] = None
    api_key_id: Optional[str] = None

    # 兼容性字段（保持向后兼容）
    public_domain: Optional[str] = None  # 从public_access兼容提取
    private_domain: Optional[str] = None  # 从private_access兼容提取
    private_ip: Optional[str] = None  # 从private_access兼容提取

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpaceInfo":
        """从OpenAPI响应字典创建SpaceInfo"""
        # 提取网络访问配置
        public_access = data.get("public_access") or {}
        private_access = data.get("private_access") or {}

        return cls(
            # 基本信息
            id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            message_ttl_hours=data.get("message_ttl_hours", 168),
            status=data.get("status"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),

            # 记忆提取配置
            memory_extract_enabled=data.get("memory_extract_enabled", False),
            memory_extract_idle_seconds=data.get("memory_extract_idle_seconds"),
            memory_extract_max_tokens=data.get("memory_extract_max_tokens"),
            memory_extract_max_messages=data.get("memory_extract_max_messages"),

            # 记忆策略
            memory_strategies_builtin=data.get("memory_strategies_builtin"),
            memory_strategies_customized=data.get("memory_strategies_customized"),

            # 网络配置
            public_access=public_access,
            private_access=private_access,

            # API Key
            api_key=data.get("api_key"),
            api_key_id=data.get("api_key_id"),

            # 兼容性字段（自动从新的网络配置字段提取）
            public_domain=public_access.get("domain") if public_access else None,
            private_domain=private_access.get("domain") if private_access else None,
            private_ip=private_access.get("ip") if private_access else None
        )


@dataclass
class SpaceListResponse:
    """Space列表响应"""
    items: List[SpaceInfo]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpaceListResponse":
        """从OpenAPI响应字典创建SpaceListResponse"""
        return cls(
            items=[SpaceInfo.from_dict(item) for item in data.get("spaces", [])],
            total=data.get("total", 0),
            limit=data.get("limit", 20),
            offset=data.get("offset", 0)
        )


@dataclass
class SessionInfo:
    """会话详细信息（返回值用）"""
    id: str
    space_id: str
    actor_id: Optional[str] = None
    assistant_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionInfo":
        """从OpenAPI响应字典创建SessionInfo"""
        return cls(
            id=data.get("id"),
            space_id=data.get("space_id"),
            actor_id=data.get("actor_id"),
            assistant_id=data.get("assistant_id"),
            meta=data.get("meta"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class SessionListResponse:
    """会话列表响应"""
    items: List[SessionInfo]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionListResponse":
        """从OpenAPI响应字典创建SessionListResponse"""
        return cls(
            items=[SessionInfo.from_dict(item) for item in data.get("items", [])],
            total=data.get("total", 0),
            limit=data.get("limit", 20),
            offset=data.get("offset", 0)
        )


@dataclass
class MessageInfo:
    """消息详细信息（返回值用）"""
    id: str
    session_id: str
    seq: int
    actor_id: Optional[str] = None
    assistant_id: Optional[str] = None
    role: str = "user"  # user/assistant/tool/system
    parts: Optional[List[Dict[str, Any]]] = None
    idempotency_key: Optional[str] = None  # 幂等键
    meta: Optional[Dict[str, Any]] = None  # 扩展元数据
    message_time: Optional[int] = None  # 消息实际发生时间（毫秒时间戳）
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageInfo":
        """从OpenAPI响应字典创建MessageInfo"""
        return cls(
            id=data.get("id"),
            session_id=data.get("session_id"),
            seq=data.get("seq", 0),
            actor_id=data.get("actor_id"),
            assistant_id=data.get("assistant_id"),
            role=data.get("role", "user"),
            parts=data.get("parts"),
            idempotency_key=data.get("idempotency_key"),
            meta=data.get("meta"),
            message_time=data.get("message_time"),
            created_at=data.get("created_at")
        )


@dataclass
class MessageListResponse:
    """消息列表响应"""
    items: List[MessageInfo]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageListResponse":
        """从OpenAPI响应字典创建MessageListResponse"""
        return cls(
            items=[MessageInfo.from_dict(item) for item in data.get("items", [])],
            total=data.get("total", 0),
            limit=data.get("limit", 20),
            offset=data.get("offset", 0)
        )


@dataclass
class MessageBatchResponse:
    """消息批量响应"""
    items: List[MessageInfo]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageBatchResponse":
        """从OpenAPI响应字典创建MessageBatchResponse"""
        return cls(
            items=[MessageInfo.from_dict(item) for item in data.get("messages", [])]
        )


@dataclass
class MemoryInfo:
    """记忆记录详细信息（返回值用）"""
    id: str
    space_id: str
    strategy_id: str
    strategy_type: Optional[str] = None
    actor_id: Optional[str] = None
    assistant_id: Optional[str] = None
    session_id: Optional[str] = None
    content: str = ""
    memory_type: str = "memory"  # memory/episode/reflection
    isolation_level: str = "actor"  # actor/session
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryInfo":
        """从OpenAPI响应字典创建MemoryInfo"""
        return cls(
            id=data.get("id"),
            space_id=data.get("space_id"),
            strategy_id=data.get("strategy_id"),
            strategy_type=data.get("strategy_type"),
            actor_id=data.get("actor_id"),
            assistant_id=data.get("assistant_id"),
            session_id=data.get("session_id"),
            content=data.get("content", ""),
            memory_type=data.get("memory_type", "memory"),
            isolation_level=data.get("isolation_level", "actor"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class MemoryListResponse:
    """记忆列表响应"""
    items: List[MemoryInfo]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryListResponse":
        """从OpenAPI响应字典创建MemoryListResponse"""
        return cls(
            items=[MemoryInfo.from_dict(item) for item in data.get("items", [])],
            total=data.get("total", 0),
            limit=data.get("limit", 20),
            offset=data.get("offset", 0)
        )


@dataclass
class MemorySearchResponse:
    """记忆搜索响应"""
    results: List[Dict[str, Any]]  # 搜索结果列表，包含record和score信息
    total: int = 0  # 总结果数
    query: Optional[str] = None  # 原始查询

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemorySearchResponse":
        """从OpenAPI响应字典创建MemorySearchResponse"""
        # 兼容性处理：API返回records，但这个类名是results，为了统一命名
        # 将records映射为results以符合OpenAPI规范
        search_results = []
        if "records" in data:
            # 老格式：records包含record和score
            for record in data.get("records", []):
                if isinstance(record, dict):
                    new_record = {
                        "record": record.get("record"),
                        "score": record.get("score")
                    }
                    search_results.append(new_record)
        # 或者使用新格式：results直接包含record和score
        elif "results" in data:
            search_results = data.get("results", [])

        return cls(
            results=search_results,
            query=data.get("query"),
            total=data.get("total", 0)
        )


# ==================== SDK专用消息类型 ====================

@dataclass
class TextMessage:
    """SDK文本消息 - 最常用的消息类型，便于使用和后续扩展"""
    role: Literal["user", "assistant", "system"] = "user"
    content: str = ""
    actor_id: Optional[str] = None
    assistant_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为OpenAPI格式的消息请求"""
        if not self.content:
            raise ValueError("文本消息内容不能为空")

        return {
            "role": self.role,
            "parts": [{"type": "text", "text": self.content}]
        }


@dataclass
class ContextChainResponse:
    """上下文链响应"""
    messages: List[MessageInfo]
    total_token_count: int
    compressed: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextChainResponse":
        """从OpenAPI响应字典创建ContextChainResponse"""
        return cls(
            messages=[MessageInfo.from_dict(item) for item in data.get("messages", [])],
            total_token_count=data.get("total_token_count", 0),
            compressed=data.get("compressed", False)
        )


@dataclass
class ContextCompressionResponse:
    """上下文压缩响应"""
    compression_id: Optional[str] = None
    status: Optional[str] = None
    compressed_messages: Optional[List[MessageInfo]] = None
    compression_ratio: Optional[float] = None
    original_token_count: Optional[int] = None
    compressed_token_count: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextCompressionResponse":
        """从OpenAPI响应字典创建ContextCompressionResponse"""
        return cls(
            compression_id=data.get("compression_id"),
            status=data.get("status"),
            compressed_messages=[MessageInfo.from_dict(item) for item in data.get("compressed_messages", [])],
            compression_ratio=data.get("compression_ratio"),
            original_token_count=data.get("original_token_count"),
            compressed_token_count=data.get("compressed_token_count")
        )


@dataclass
class ApiKeyInfo:
    """API Key信息（返回值用）"""
    id: str
    api_key: str  # 仅创建时可见

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApiKeyInfo":
        """从OpenAPI响应字典创建ApiKeyInfo"""
        return cls(
            id=data.get("id"),
            api_key=data.get("api_key", ""),
        )
