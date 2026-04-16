"""
Agent Memory SDK Configuration Module
Provides SDK configuration and data class definitions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class StrategyType(Enum):
    """Memory strategy type."""
    SEMANTIC = "semantic"
    SUMMARY = "summary"
    USER_PREFERENCE = "user_preference"
    EPISODIC = "episodic"
    EVENT = "event"
    CUSTOM = "custom"


class MessageRole(Enum):
    """Message role."""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


@dataclass
class CreateMemoryRequest:
    """
    Create memory request.

    Required fields:
        - content: Memory content, length 1-10000
        - strategy_type: Strategy type (semantic, summary, user_preference, episodic, event, custom)
        - strategy_id: Source strategy ID (UUID)

    Optional fields:
        - actor_id: Actor ID, length 0-64
        - assistant_id: Assistant ID, length 0-64
        - session_id: Session ID (UUID)
        - metadata: Metadata (dict)
    """
    content: str
    strategy_type: str
    strategy_id: str

    actor_id: str | None = None
    assistant_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
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


@dataclass
class Tag:
    """Tag data class."""
    key: str
    value: str

    def to_dict(self) -> dict[str, str]:
        return {"key": self.key, "value": self.value}


@dataclass
class MemoryStrategy:
    """Memory strategy configuration data class."""
    type: str
    parameters: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"type": self.type}
        if self.parameters:
            result.update(self.parameters)
        return result


@dataclass
class SessionMetadata:
    """Session metadata data class."""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.data.copy()


@dataclass
class MemorySearchFilter:
    """Memory search filter data class - contains all search_memories API parameters."""

    query: str | None = None
    strategy_type: str | None = None
    strategy_id: str | None = None
    actor_id: str | None = None
    assistant_id: str | None = None
    session_id: str | None = None
    memory_type: Literal["memory", "episode", "reflection"] | None = None
    start_time: int | None = None
    end_time: int | None = None
    top_k: int | None = None
    min_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to API request body format, set default values."""
        result = {}

        for k, v in self.__dict__.items():
            if v is not None:
                if (k == "top_k" and v == 10) or (k == "min_score" and v == 0.5) or v is not None:
                    result[k] = v

        return result


@dataclass
class MemoryListFilter:
    """Memory list filter data class - contains all list_memories API filter parameters (except limit/offset)."""

    strategy_type: str | None = None
    strategy_id: str | None = None
    actor_id: str | None = None
    assistant_id: str | None = None
    session_id: str | None = None
    start_time: int | None = None
    end_time: int | None = None
    sort_by: Literal["created_at", "updated_at"] | None = None
    sort_order: Literal["asc", "desc"] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to API dictionary format, set default values."""
        result = {}

        for k, v in self.__dict__.items():
            if v is not None:
                if (k == "sort_by" and v == "created_at") or (k == "sort_order" and v == "desc"):
                    result[k] = v
                else:
                    result[k] = v

        return result


@dataclass
class SpaceCreateRequest:
    """
    Space creation request.

    Users only need to care about basic Space configuration,
    SDK internally handles API Key creation automatically.

    Required fields:
        - name: Space name, length 1-128
        - message_ttl_hours: Message TTL (hours), range 1-8760

    Optional fields:
        - description: Space description
        - tags: Space tags
        - public_access_enable: Enable public network access (default: True)
        - private_vpc_id: Private VPC ID (must be provided with private_subnet_id)
        - private_subnet_id: Private subnet ID (must be provided with private_vpc_id)
        - memory_extract_idle_seconds: Memory extraction idle time
        - memory_extract_max_tokens: Memory extraction max token count
        - memory_extract_max_messages: Memory extraction max message count
        - memory_strategies_builtin: Built-in memory strategy list
        - memory_strategies_customized: Custom memory strategy list
    """
    name: str
    message_ttl_hours: int = 168

    description: str | None = None
    memory_extract_idle_seconds: int | None = None
    memory_extract_max_tokens: int | None = None
    memory_extract_max_messages: int | None = None

    tags: list[dict[str, str]] | None = None

    public_access_enable: bool = True
    private_vpc_id: str | None = None
    private_subnet_id: str | None = None

    memory_strategies_builtin: list[str] | None = None
    memory_strategies_customized: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to API dictionary format.

        Returns:
            Request dictionary adapted for backend API
        """
        result = {
            "name": self.name,
            "message_ttl_hours": self.message_ttl_hours,
        }

        if self.description is not None:
            result["description"] = self.description
        if self.memory_extract_idle_seconds is not None:
            result["memory_extract_idle_seconds"] = self.memory_extract_idle_seconds
        if self.memory_extract_max_tokens is not None:
            result["memory_extract_max_tokens"] = self.memory_extract_max_tokens
        if self.memory_extract_max_messages is not None:
            result["memory_extract_max_messages"] = self.memory_extract_max_messages

        if self.memory_strategies_builtin is not None:
            result["memory_strategies_builtin"] = self.memory_strategies_builtin
        if self.memory_strategies_customized is not None:
            result["memory_strategies_customized"] = self.memory_strategies_customized

        if self.tags is not None:
            result["tags"] = self.tags

        network_access = {}
        network_access["public_access_enable"] = self.public_access_enable

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
    """Space update request."""
    name: str | None = None
    description: str | None = None
    message_ttl_hours: int | None = None

    memory_extract_enabled: bool | None = None
    memory_extract_idle_seconds: int | None = None
    memory_extract_max_tokens: int | None = None
    memory_extract_max_messages: int | None = None

    tags: list[dict[str, str]] | None = None

    memory_strategies_builtin: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, skip None values, conform to OpenAPI spec."""
        result = {}

        if self.name is not None:
            result["name"] = self.name
        if self.description is not None:
            result["description"] = self.description
        if self.message_ttl_hours is not None:
            result["message_ttl_hours"] = self.message_ttl_hours

        if self.memory_extract_enabled is not None:
            result["memory_extract_enabled"] = self.memory_extract_enabled
        if self.memory_extract_idle_seconds is not None:
            result["memory_extract_idle_seconds"] = self.memory_extract_idle_seconds
        if self.memory_extract_max_tokens is not None:
            result["memory_extract_max_tokens"] = self.memory_extract_max_tokens
        if self.memory_extract_max_messages is not None:
            result["memory_extract_max_messages"] = self.memory_extract_max_messages

        if self.memory_strategies_builtin is not None:
            result["memory_strategies_builtin"] = self.memory_strategies_builtin

        if self.tags is not None:
            result["tags"] = self.tags

        return result


@dataclass
class SessionCreateRequest:
    """Session creation request."""
    id: str | None = None
    actor_id: str | None = None
    assistant_id: str | None = None
    meta: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, skip None values."""
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


@dataclass
class AssetRef:
    """Asset reference (file, image, audio)."""
    asset_id: str = ""
    uri: str = ""
    mime: str = ""
    size: int = 0
    filename: str | None = None
    meta: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
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
    """Data message part (summary, offload index, custom data)."""
    type: str = "data"
    kind: str = "custom"
    covers: list[str] | None = None
    content: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
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
    """Tool call message part (conforms to OpenAPI spec)."""
    type: str = "tool_call"
    id: str = ""
    name: str = ""
    arguments: str = ""
    meta: str | None = None

    def __post_init__(self):
        if self.arguments is None:
            self.arguments = ""
        elif isinstance(self.arguments, dict):
            import json
            self.arguments = json.dumps(self.arguments, ensure_ascii=False)

    def to_dict(self) -> dict[str, Any]:
        tool_call = {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments
        }
        result = {
            "role": "tool",
            "parts": [{"type": "tool_call", "tool_call": tool_call}]
        }
        if self.meta:
            result["meta"] = self.meta
        return result


@dataclass
class ToolResultMessage:
    """Tool result message part (conforms to OpenAPI spec)."""
    type: str = "tool_result"
    tool_call_id: str = ""
    content: str = ""
    asset_ref: AssetRef | None = None
    meta: str | None = None

    def to_dict(self) -> dict[str, Any]:
        tool_result = {
            "tool_call_id": self.tool_call_id,
            "content": self.content,
            "asset_ref": self.asset_ref
        }
        result = {
            "role": "tool",
            "parts": [{"type": "tool_result", "tool_result": tool_result}]
        }
        if self.meta:
            result["meta"] = self.meta
        return result


@dataclass
class MessageRequest:
    """
    Message request.

    Uses parts format, supports multiple message types:
    - TextPart: Text message
    - ImagePart: Image message
    - FilePart: File message
    - AudioPart: Audio message
    - ToolCallPart: Tool call
    - ToolResultPart: Tool result
    - DataPart: Data message (summary, offload index, custom data)
    - AssetPart: Asset message
    """
    role: str
    parts: list[Any] = field(default_factory=list)
    actor_id: str | None = None
    assistant_id: str | None = None
    meta: dict[str, Any] | None = None

    def __post_init__(self):
        if not self.parts:
            msg = "Must contain at least one message part"
            raise ValueError(msg)

        if len(self.parts) > 5:
            msg = "Message can contain at most 5 parts"
            raise ValueError(msg)

        for part in self.parts:
            if not hasattr(part, "to_dict"):
                msg = f"Message part must support to_dict method, actual type: {type(part)}"
                raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, compatible with OpenAPI spec."""
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
    """Batch add messages request."""
    messages: list[MessageRequest] = field(default_factory=list)
    timestamp: int | None = None
    idempotency_key: str | None = None
    is_force_extract: bool = False

    def __post_init__(self):
        if not self.messages:
            msg = "Must contain at least one message"
            raise ValueError(msg)

        if len(self.messages) > 100:
            msg = "Batch messages can contain at most 100"
            raise ValueError(msg)

        for message in self.messages:
            if not isinstance(message, MessageRequest):
                msg = f"Message must be MessageRequest type, actual type: {type(message)}"
                raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, compatible with OpenAPI spec."""
        result = {
            "messages": [m.to_dict() for m in self.messages],
            "is_force_extract": self.is_force_extract
        }
        if self.timestamp is not None:
            result["timestamp"] = self.timestamp
        if self.idempotency_key is not None:
            result["idempotency_key"] = self.idempotency_key
        return result


@dataclass
class MemorySearchRequest:
    """Memory search request."""
    query: str | None = None
    top_k: int = 10
    min_score: float = 0.5
    strategy_type: str | None = None
    strategy_id: str | None = None
    actor_id: str | None = None
    assistant_id: str | None = None
    session_id: str | None = None
    memory_type: str | None = None
    start_time: int | None = None
    end_time: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, skip None values, use API default values."""
        result = {}

        if self.query is not None and self.query != "":
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

        if not result:
            result = {"top_k": 10, "min_score": 0.5}

        return result


@dataclass
class MemoryCreateRequest:
    """Memory creation request."""
    content: str
    actor_id: str | None = None
    assistant_id: str | None = None
    session_id: str | None = None
    extraction_meta: dict[str, Any] | None = None

    def __post_init__(self):
        if len(self.content) > 10000:
            msg = "Memory content cannot exceed 10000 characters"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, compatible with OpenAPI spec."""
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
    """Memory update request."""
    content: str | None = None
    extraction_meta: dict[str, Any] | None = None

    def __post_init__(self):
        if self.content is not None and len(self.content) > 10000:
            msg = "Memory content cannot exceed 10000 characters"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, compatible with OpenAPI spec."""
        result = {}
        if self.content is not None:
            result["content"] = self.content
        if self.extraction_meta is not None:
            result["extraction_meta"] = self.extraction_meta
        return result


@dataclass
class CompressConfig:
    """Context compression configuration."""
    msg_threshold: int = 100
    max_token: int = 131072
    token_ratio: float = 0.75
    last_keep: int = 50
    large_payload_threshold: int = 5000
    custom_prompt: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, skip None values."""
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


@dataclass
class SpaceInfo:
    """Space detailed information (for return values)."""
    id: str
    name: str
    description: str | None = None
    message_ttl_hours: int = 168
    status: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    memory_extract_enabled: bool = False
    memory_extract_idle_seconds: int | None = None
    memory_extract_max_tokens: int | None = None
    memory_extract_max_messages: int | None = None

    memory_strategies_builtin: list[str] | None = None
    memory_strategies_customized: list[dict[str, Any]] | None = None

    vpc_id: str | None = None
    subnet_id: str | None = None
    public_access: dict[str, Any] | None = None
    private_access: dict[str, Any] | None = None

    api_key: str | None = None
    api_key_id: str | None = None

    public_domain: str | None = None
    private_domain: str | None = None
    private_ip: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpaceInfo":
        """Create SpaceInfo from OpenAPI response dictionary."""
        public_access = data.get("public_access") or {}
        private_access = data.get("private_access") or {}

        return cls(
            id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            message_ttl_hours=data.get("message_ttl_hours", 168),
            status=data.get("status"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),

            memory_extract_enabled=data.get("memory_extract_enabled", False),
            memory_extract_idle_seconds=data.get("memory_extract_idle_seconds"),
            memory_extract_max_tokens=data.get("memory_extract_max_tokens"),
            memory_extract_max_messages=data.get("memory_extract_max_messages"),

            memory_strategies_builtin=data.get("memory_strategies_builtin"),
            memory_strategies_customized=data.get("memory_strategies_customized"),

            public_access=public_access,
            private_access=private_access,

            api_key=data.get("api_key"),
            api_key_id=data.get("api_key_id"),

            public_domain=public_access.get("domain") if public_access else None,
            private_domain=private_access.get("domain") if private_access else None,
            private_ip=private_access.get("ip") if private_access else None
        )


@dataclass
class SpaceListResponse:
    """Space list response."""
    items: list[SpaceInfo]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpaceListResponse":
        """Create SpaceListResponse from OpenAPI response dictionary."""
        return cls(
            items=[SpaceInfo.from_dict(item) for item in data.get("spaces", [])],
            total=data.get("total", 0),
            limit=data.get("limit", 20),
            offset=data.get("offset", 0)
        )


@dataclass
class SessionInfo:
    """Session detailed information (for return values)."""
    id: str
    space_id: str
    actor_id: str | None = None
    assistant_id: str | None = None
    meta: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionInfo":
        """Create SessionInfo from OpenAPI response dictionary."""
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
    """Session list response."""
    items: list[SessionInfo]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionListResponse":
        """Create SessionListResponse from OpenAPI response dictionary."""
        return cls(
            items=[SessionInfo.from_dict(item) for item in data.get("items", [])],
            total=data.get("total", 0),
            limit=data.get("limit", 20),
            offset=data.get("offset", 0)
        )


@dataclass
class MessageInfo:
    """Message detailed information (for return values)."""
    id: str
    session_id: str
    seq: int
    actor_id: str | None = None
    assistant_id: str | None = None
    role: str = "user"
    parts: list[dict[str, Any]] | None = None
    idempotency_key: str | None = None
    meta: dict[str, Any] | None = None
    message_time: int | None = None
    created_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageInfo":
        """Create MessageInfo from OpenAPI response dictionary."""
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
    """Message list response."""
    items: list[MessageInfo]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageListResponse":
        """Create MessageListResponse from OpenAPI response dictionary."""
        return cls(
            items=[MessageInfo.from_dict(item) for item in data.get("items", [])],
            total=data.get("total", 0),
            limit=data.get("limit", 20),
            offset=data.get("offset", 0)
        )


@dataclass
class MessageBatchResponse:
    """Message batch response."""
    items: list[MessageInfo]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageBatchResponse":
        """Create MessageBatchResponse from OpenAPI response dictionary."""
        return cls(
            items=[MessageInfo.from_dict(item) for item in data.get("messages", [])]
        )


@dataclass
class MemoryInfo:
    """Memory record detailed information (for return values)."""
    id: str
    space_id: str
    strategy_id: str
    strategy_type: str | None = None
    actor_id: str | None = None
    assistant_id: str | None = None
    session_id: str | None = None
    content: str = ""
    memory_type: str = "memory"
    isolation_level: str = "actor"
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryInfo":
        """Create MemoryInfo from OpenAPI response dictionary."""
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
    """Memory list response."""
    items: list[MemoryInfo]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryListResponse":
        """Create MemoryListResponse from OpenAPI response dictionary."""
        return cls(
            items=[MemoryInfo.from_dict(item) for item in data.get("items", [])],
            total=data.get("total", 0),
            limit=data.get("limit", 20),
            offset=data.get("offset", 0)
        )


@dataclass
class MemorySearchResponse:
    """Memory search response."""
    results: list[dict[str, Any]]
    total: int = 0
    query: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemorySearchResponse":
        """Create MemorySearchResponse from OpenAPI response dictionary."""
        search_results = []
        if "records" in data:
            for record in data.get("records", []):
                if isinstance(record, dict):
                    new_record = {
                        "record": record.get("record"),
                        "score": record.get("score")
                    }
                    search_results.append(new_record)
        elif "results" in data:
            search_results = data.get("results", [])

        return cls(
            results=search_results,
            query=data.get("query"),
            total=data.get("total", 0)
        )


@dataclass
class TextMessage:
    """SDK text message - most commonly used message type, easy to use and extend."""
    role: Literal["user", "assistant", "system"] = "user"
    content: str = ""
    actor_id: str | None = None
    assistant_id: str | None = None
    meta: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to OpenAPI format message request."""
        if not self.content:
            msg = "Text message content cannot be empty"
            raise ValueError(msg)

        result = {
            "role": self.role,
            "parts": [{"type": "text", "text": self.content}]
        }
        if self.meta:
            result["meta"] = self.meta
        return result


@dataclass
class ContextChainResponse:
    """Context chain response."""
    messages: list[MessageInfo]
    total_token_count: int
    compressed: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextChainResponse":
        """Create ContextChainResponse from OpenAPI response dictionary."""
        return cls(
            messages=[MessageInfo.from_dict(item) for item in data.get("messages", [])],
            total_token_count=data.get("total_token_count", 0),
            compressed=data.get("compressed", False)
        )


@dataclass
class ContextCompressionResponse:
    """Context compression response."""
    compression_id: str | None = None
    status: str | None = None
    compressed_messages: list[MessageInfo] | None = None
    compression_ratio: float | None = None
    original_token_count: int | None = None
    compressed_token_count: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextCompressionResponse":
        """Create ContextCompressionResponse from OpenAPI response dictionary."""
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
    """API Key information (for return values)."""
    id: str
    api_key: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApiKeyInfo":
        """Create ApiKeyInfo from OpenAPI response dictionary."""
        return cls(
            id=data.get("id"),
            api_key=data.get("api_key", ""),
        )
