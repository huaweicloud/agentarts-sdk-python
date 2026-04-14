"""
Message Converters for LangGraph Integration

Provides bidirectional conversion between LangGraph messages and 
AgentArts Memory service messages.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union, Literal

from agentarts.sdk.memory import TextMessage, ToolCallMessage, ToolResultMessage, MessageInfo

try:
    from langchain_core.messages import (
        BaseMessage,
        HumanMessage,
        AIMessage,
        SystemMessage,
        ToolMessage,
        FunctionMessage,
    ChatMessage,
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


def langgraph_to_memory_message(
    message: BaseMessage,
    actor_id: Optional[str] = None,
    assistant_id: Optional[str] = None,
    meta: Optional[str] = None,
) -> Union[TextMessage, ToolCallMessage, ToolResultMessage]:
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
        raise ImportError(
            "langchain-core is required for message conversion. "
            "Install it with: pip install langchain-core"
        )
    
    if isinstance(message, HumanMessage):
        return TextMessage(
            role="user",
            content=message.content,
            actor_id=actor_id,
            assistant_id=assistant_id,
            meta=meta,
        )
    
    elif isinstance(message, AIMessage):
        if hasattr(message, 'tool_calls') and message.tool_calls:
            return ToolCallMessage(
                id=message.tool_calls[0].get("id", ""),
                name=message.tool_calls[0].get("name", ""),
                arguments=json.dumps(message.tool_calls[0].get("args", {}), ensure_ascii=False),
                meta=meta,
            )
        
        return TextMessage(
            role="assistant",
            content=message.content,
            actor_id=actor_id,
            assistant_id=assistant_id,
            meta=meta,
        )
    
    elif isinstance(message, SystemMessage):
        return TextMessage(
            role="system",
            content=message.content,
            actor_id=actor_id,
            assistant_id=assistant_id,
            meta=meta,
        )
    
    elif isinstance(message, ToolMessage):
        return ToolResultMessage(
            tool_call_id=message.tool_call_id,
            content=str(message.content),
            meta=meta,
        )
    
    elif isinstance(message, FunctionMessage):
        return ToolResultMessage(
            tool_call_id=message.name,
            content=str(message.content),
            meta=meta,
        )
    elif isinstance(message, ChatMessage):
        role = message.role
        if role not in("user", "assistant", "system"):
            if role in ("ai", "model"):
                role = "assistant"
            elif role in ("human"):
                role = "user"
            else:
                role = "user"
        return TextMessage(
            role=role,
            content=str(message.content),
            actor_id=actor_id,
            assistant_id=assistant_id,
            meta=meta,
        )
    else:
        return TextMessage(
            role="user",
            content=str(message.content),
            actor_id=actor_id,
            assistant_id=assistant_id,
            meta=meta,
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
        raise ImportError(
            "langchain-core is required for message conversion. "
            "Install it with: pip install langchain-core"
        )
    
    role = message.role
    parts = message.parts or []
    
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
        )
    
    if tool_call_data:
        return AIMessage(
            content=text_content,
            tool_calls=[{
                "id": tool_call_data.get("id", ""),
                "name": tool_call_data.get("name", ""),
                "args": json.loads(tool_call_data.get("arguments", "{}")),
            }],
        )
    
    if role == "user":
        return HumanMessage(content=text_content)
    elif role == "assistant":
        return AIMessage(content=text_content)
    elif role == "system":
        return SystemMessage(content=text_content)
    elif role == "tool":
        return ToolMessage(
            content=text_content,
            tool_call_id="",
        )
    else:
        return HumanMessage(content=text_content)


def langgraph_messages_to_memory(
    messages: List[BaseMessage],
    actor_id: Optional[str] = None,
    assistant_id: Optional[str] = None,
    meta: Optional[str] = None,
) -> List[Union[TextMessage, ToolCallMessage, ToolResultMessage]]:
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
    messages: List[MessageInfo],
) -> List[BaseMessage]:
    """
    Convert a list of AgentArts Memory messages to LangGraph messages.
    
    Args:
        messages: List of AgentArts Memory MessageInfo objects
        
    Returns:
        List of LangGraph messages
    """
    return [memory_to_langgraph_message(msg) for msg in messages]