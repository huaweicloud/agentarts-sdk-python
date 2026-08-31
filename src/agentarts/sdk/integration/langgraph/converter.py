"""
Message Converters for LangGraph Integration

Provides bidirectional conversion between LangGraph messages and
AgentArts Memory service messages.
"""

from __future__ import annotations

import json

from agentarts.sdk.memory import MessageInfo, TextMessage, ToolCallMessage, ToolResultMessage

try:
    from langchain_core.messages import (
        AIMessage,
        BaseMessage,
        ChatMessage,
        FunctionMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseMessage = object
    HumanMessage = None
    AIMessage = None
    SystemMessage = None
    ToolMessage = None
    FunctionMessage = None


def _parse_meta(meta: str | dict | None) -> dict:
    """Parse meta from backend response.

    Handles both str (JSON string) and dict (already parsed) formats.
    Returns empty dict if meta is None or unparseable.
    """
    if not meta:
        return {}
    if isinstance(meta, dict):
        return dict(meta)
    if isinstance(meta, str):
        try:
            result = json.loads(meta)
            return result if isinstance(result, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _build_meta(
    caller_meta: str | None,
    additional_kwargs: dict | None = None,
    response_metadata: dict | None = None,
    extra: dict | None = None,
) -> str | None:
    """Merge caller's meta with LangChain-specific fields.

    Args:
        caller_meta: JSON string from caller (e.g., saver's checkpoint_meta)
        additional_kwargs: LangChain message's additional_kwargs
        response_metadata: LangChain message's response_metadata
        extra: Additional key-value pairs to merge (e.g., _lc_content)

    Returns:
        Merged JSON string, or None if nothing to store.
    """
    merged = _parse_meta(caller_meta)

    if additional_kwargs:
        merged["_lc_additional_kwargs"] = additional_kwargs
    if response_metadata:
        merged["_lc_response_metadata"] = response_metadata
    if extra:
        merged.update(extra)

    # NOTE: non-JSON-serializable metadata (e.g. datetime/custom objects) is not handled and may raise TypeError here.
    return json.dumps(merged, ensure_ascii=False) if merged else caller_meta


def langgraph_to_memory_message(
    message: BaseMessage,
    actor_id: str | None = None,
    assistant_id: str | None = None,
    meta: str | None = None,
) -> TextMessage | ToolCallMessage | ToolResultMessage:
    """
    Convert a LangGraph message to an AgentArts Memory message.

    Mapping:
        - HumanMessage -> TextMessage(role="user")
        - AIMessage -> TextMessage(role="assistant")
        - SystemMessage -> TextMessage(role="system")
        - ToolMessage -> ToolResultMessage
        - FunctionMessage -> ToolResultMessage

    Args:
        message: LangGraph message (HumanMessage, AIMessage, etc.)
        actor_id: Actor ID for the message
        assistant_id: Assistant ID for the message
        meta: Optional metadata string to attach to the message

    Returns:
        AgentArts Memory message (TextMessage, ToolCallMessage, ToolResultMessage)

    Raises:
        ImportError: If langchain-core is not installed
        ValueError: If message type is not supported
    """
    if not LANGCHAIN_AVAILABLE:
        msg = (
            "langchain-core is required for message conversion. "
            "Install it with: pip install langchain-core"
        )
        raise ImportError(
            msg
        )

    if isinstance(message, HumanMessage):
        merged_meta = _build_meta(
            meta,
            additional_kwargs=getattr(message, "additional_kwargs", None),
        )
        return TextMessage(
            role="user",
            content=message.content,
            actor_id=actor_id,
            assistant_id=assistant_id,
            meta=merged_meta,
        )

    if isinstance(message, AIMessage):
        if hasattr(message, "tool_calls") and message.tool_calls:
            extra = {}
            if message.content:
                extra["_lc_content"] = message.content

            merged_meta = _build_meta(
                meta,
                additional_kwargs=getattr(message, "additional_kwargs", None),
                response_metadata=getattr(message, "response_metadata", None),
                extra=extra if extra else None,
            )

            return ToolCallMessage(
                id=message.tool_calls[0].get("id", ""),
                name=message.tool_calls[0].get("name", ""),
                arguments=json.dumps(message.tool_calls[0].get("args", {}), ensure_ascii=False),
                meta=merged_meta,
            )

        merged_meta = _build_meta(
            meta,
            additional_kwargs=getattr(message, "additional_kwargs", None),
            response_metadata=getattr(message, "response_metadata", None),
        )

        return TextMessage(
            role="assistant",
            content=message.content,
            actor_id=actor_id,
            assistant_id=assistant_id,
            meta=merged_meta,
        )

    if isinstance(message, SystemMessage):
        merged_meta = _build_meta(
            meta,
            additional_kwargs=getattr(message, "additional_kwargs", None),
        )
        return TextMessage(
            role="system",
            content=message.content,
            actor_id=actor_id,
            assistant_id=assistant_id,
            meta=merged_meta,
        )

    if isinstance(message, ToolMessage):
        merged_meta = _build_meta(
            meta,
            additional_kwargs=getattr(message, "additional_kwargs", None),
        )
        return ToolResultMessage(
            tool_call_id=message.tool_call_id,
            content=str(message.content),
            meta=merged_meta,
        )

    if isinstance(message, FunctionMessage):
        merged_meta = _build_meta(
            meta,
            additional_kwargs=getattr(message, "additional_kwargs", None),
        )
        return ToolResultMessage(
            tool_call_id=message.name,
            content=str(message.content),
            meta=merged_meta,
        )
    if isinstance(message, ChatMessage):
        role = message.role
        if role not in("user", "assistant", "system"):
            if role in ("ai", "model"):
                role = "assistant"
            elif role in ("human"):
                role = "user"
            else:
                role = "user"
        merged_meta = _build_meta(
            meta,
            additional_kwargs=getattr(message, "additional_kwargs", None),
        )
        return TextMessage(
            role=role,
            content=str(message.content),
            actor_id=actor_id,
            assistant_id=assistant_id,
            meta=merged_meta,
        )
    merged_meta = _build_meta(
        meta,
        additional_kwargs=getattr(message, "additional_kwargs", None),
    )
    return TextMessage(
        role="user",
        content=str(message.content),
        actor_id=actor_id,
        assistant_id=assistant_id,
        meta=merged_meta,
    )


def memory_to_langgraph_message(
    message: MessageInfo,
) -> BaseMessage:
    """
    Convert an AgentArts Memory message to a LangGraph message.

    Mapping:
        - TextMessage (role="user") -> HumanMessage
        - TextMessage (role="assistant") -> AIMessage
        - TextMessage (role="system") -> SystemMessage
        - ToolResultMessage -> ToolMessage

    Args:
        message: AgentArts Memory MessageInfo

    Returns:
        LangGraph message (HumanMessage, AIMessage, etc.)

    Raises:
        ImportError: If langchain-core is not installed
    """
    if not LANGCHAIN_AVAILABLE:
        msg = (
            "langchain-core is required for message conversion. "
            "Install it with: pip install langchain-core"
        )
        raise ImportError(
            msg
        )

    role = message.role
    parts = message.parts or []

    # Parse meta to extract LangChain-specific fields
    meta_dict = _parse_meta(getattr(message, "meta", None))
    additional_kwargs = meta_dict.get("_lc_additional_kwargs", {})
    response_metadata = meta_dict.get("_lc_response_metadata", {})
    preserved_content = meta_dict.get("_lc_content")

    text_content = ""
    tool_call_data = None
    tool_result_data = None

    for part in parts:
        if isinstance(part, dict):
            part_type = part.get("type", "")

            if part_type == "text":
                text_content = part.get("text", "")
            elif part_type == "tool_call":
                tool_call_data = part.get("tool_call", {})
            elif part_type == "tool_result":
                tool_result_data = part.get("tool_result", {})

    if tool_result_data:
        return ToolMessage(
            content=tool_result_data.get("content", ""),
            tool_call_id=tool_result_data.get("tool_call_id", ""),
            additional_kwargs=additional_kwargs,
        )

    if tool_call_data:
        content = preserved_content if preserved_content is not None else text_content
        return AIMessage(
            content=content,
            tool_calls=[{
                "id": tool_call_data.get("id", ""),
                "name": tool_call_data.get("name", ""),
                "args": json.loads(tool_call_data.get("arguments", "{}")),
            }],
            additional_kwargs=additional_kwargs,
            response_metadata=response_metadata,
        )

    if role == "user":
        return HumanMessage(
            content=text_content,
            additional_kwargs=additional_kwargs,
        )
    if role == "assistant":
        return AIMessage(
            content=text_content,
            additional_kwargs=additional_kwargs,
            response_metadata=response_metadata,
        )
    if role == "system":
        return SystemMessage(
            content=text_content,
            additional_kwargs=additional_kwargs,
        )
    if role == "tool":
        return ToolMessage(
            content=text_content,
            tool_call_id="",
            additional_kwargs=additional_kwargs,
        )
    return HumanMessage(
        content=text_content,
        additional_kwargs=additional_kwargs,
    )


def langgraph_messages_to_memory(
    messages: list[BaseMessage],
    actor_id: str | None = None,
    assistant_id: str | None = None,
    meta: str | None = None,
) -> list[TextMessage | ToolCallMessage | ToolResultMessage]:
    """
    Convert a list of LangGraph messages to AgentArts Memory messages.

    Args:
        messages: List of LangGraph messages
        actor_id: Actor ID for the messages
        assistant_id: Assistant ID for the messages
        meta: Optional metadata string to attach to each message

    Returns:
        List of AgentArts Memory message objects
    """
    return [
        langgraph_to_memory_message(msg, actor_id, assistant_id, meta=meta)
        for msg in messages
    ]


def memory_messages_to_langgraph(
    messages: list[MessageInfo],
) -> list[BaseMessage]:
    """
    Convert a list of AgentArts Memory messages to LangGraph messages.

    Args:
        messages: List of AgentArts Memory MessageInfo objects

    Returns:
        List of LangGraph messages
    """
    return [memory_to_langgraph_message(msg) for msg in messages]
