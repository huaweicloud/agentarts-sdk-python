"""
Message Converters for Google ADK Integration

Provides bidirectional conversion between ADK Events and
AgentArts Memory service messages.

State encoding strategy (Plan B - full snapshot):
    Each append_event stores the complete session-scoped state in
    message.meta under the ``_STATE_KEY``. Reading state only requires
    fetching the last message (k=1), avoiding full history replay.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agentarts.sdk.memory import (
    MessageInfo,
    TextMessage,
    ToolCallMessage,
    ToolResultMessage,
)

try:
    from google.adk.events.event import Event
    from google.adk.memory.base_memory_service import SearchMemoryResponse
    from google.adk.memory.memory_entry import MemoryEntry
    from google.adk.sessions.state import State
    from google.genai import types

    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    Event = None  # type: ignore[assignment,misc]
    SearchMemoryResponse = None  # type: ignore[assignment,misc]
    MemoryEntry = None  # type: ignore[assignment,misc]
    State = None  # type: ignore[assignment,misc]
    types = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

# Key under which the full session-scoped state snapshot is stored in message.meta.
_STATE_KEY = "_adk_state"


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


def _extract_session_scoped_state(state: dict[str, Any]) -> dict[str, Any]:
    """Filter state to only session-scoped keys.

    Excludes ``app:``, ``user:``, and ``temp:`` prefixed keys.
    Temp-scoped state is already trimmed by the base class's
    ``_trim_temp_delta_state`` before reaching here, but we filter
    defensively.
    """
    return {
        key: value
        for key, value in state.items()
        if not key.startswith(State.APP_PREFIX)
        and not key.startswith(State.USER_PREFIX)
        and not key.startswith(State.TEMP_PREFIX)
    }


def event_to_messages(
    event: Event,
    full_state: dict[str, Any] | None = None,
) -> list[TextMessage | ToolCallMessage | ToolResultMessage]:
    """Convert an ADK Event to a list of AgentArts messages.

    Each part of the Event's content becomes a separate message:
        - text parts            -> TextMessage
        - function_call parts   -> ToolCallMessage
        - function_response parts -> ToolResultMessage

    Metadata encoding for round-trip fidelity:
        - ``_adk_event_id``: original Event.id (for grouping on read)
        - ``_adk_author``: original Event.author (for tool messages)
        - ``_adk_function_response_name``: FunctionResponse.name (for tool_result)
        - ``_adk_state``: full session state snapshot (last message only)

    Args:
        event: ADK Event object.
        full_state: If provided, the complete session-scoped state is
            encoded into ``message.meta`` under ``_STATE_KEY`` on the
            **last** message in the list. This lets readers recover the
            latest state via ``get_last_k_messages(k=1)`` without
            replaying full history. Used by SessionService.append_event
            for state persistence.

    Returns:
        List of AgentArts messages. For pure state-update events
        (no content parts), returns a single TextMessage with a
        ``[state_update]`` placeholder so that ``TextMessage.to_dict()``
        does not raise on empty content.

    Raises:
        ImportError: If google-adk is not installed.
    """
    if not ADK_AVAILABLE:
        msg = (
            "google-adk is required for event conversion. "
            "Install it with: pip install google-adk"
        )
        raise ImportError(msg)

    author = event.author or "user"
    role = "user" if author == "user" else "assistant"

    # Base metadata for all messages from this event (for grouping on read)
    base_meta = {"_adk_event_id": event.id}

    messages: list[TextMessage | ToolCallMessage | ToolResultMessage] = []

    if event.content and event.content.parts:
        for part in event.content.parts:
            if part.text:
                msg_meta = {**base_meta, "_adk_author": author}
                messages.append(TextMessage(
                    role=role,
                    content=part.text,
                    meta=json.dumps(msg_meta, ensure_ascii=False),
                ))
            elif part.function_call:
                fc = part.function_call
                msg_meta = {**base_meta, "_adk_author": author}
                messages.append(ToolCallMessage(
                    id=fc.id or "",
                    name=fc.name or "",
                    arguments=json.dumps(fc.args or {}, ensure_ascii=False),
                    meta=json.dumps(msg_meta, ensure_ascii=False),
                ))
            elif part.function_response:
                fr = part.function_response
                msg_meta = {
                    **base_meta,
                    "_adk_author": author,
                    "_adk_function_response_name": fr.name or "",
                }
                messages.append(ToolResultMessage(
                    tool_call_id=fr.id or "",
                    content=json.dumps(fr.response or {}, ensure_ascii=False),
                    meta=json.dumps(msg_meta, ensure_ascii=False),
                ))

    # Pure state-update events (no content) use placeholder text,
    # because TextMessage.to_dict() requires content to be non-empty.
    if not messages:
        placeholder_meta = {**base_meta, "_adk_author": author}
        messages.append(TextMessage(
            role=role,
            content="[state_update]",
            meta=json.dumps(placeholder_meta, ensure_ascii=False),
        ))

    # Attach state snapshot to the last message so that
    # get_last_k_messages(k=1) retrieves the latest state.
    if full_state is not None:
        last_meta = _parse_meta(messages[-1].meta)
        last_meta[_STATE_KEY] = full_state
        messages[-1].meta = json.dumps(last_meta, ensure_ascii=False)

    return messages


def message_to_event(message: MessageInfo) -> Event:
    """Convert an AgentArts MessageInfo to an ADK Event.

    Reconstructs the Event with content parts and state_delta (if
    ``_STATE_KEY`` is present in message.meta).

    Metadata extraction for round-trip fidelity:
        - ``_adk_author``: restores original Event.author for tool messages
        - ``_adk_function_response_name``: restores FunctionResponse.name

    Args:
        message: AgentArts Memory MessageInfo.

    Returns:
        ADK Event.

    Raises:
        ImportError: If google-adk is not installed.
    """
    if not ADK_AVAILABLE:
        msg = (
            "google-adk is required for event conversion. "
            "Install it with: pip install google-adk"
        )
        raise ImportError(msg)

    # Extract metadata for round-trip fidelity
    meta_dict = _parse_meta(getattr(message, "meta", None))

    # Restore author from meta for tool and assistant messages.
    # For user messages, author is always "user".
    if message.role == "user":
        author = "user"
    else:
        author = meta_dict.get("_adk_author", message.assistant_id or "assistant")

    content_role = "user" if message.role == "user" else "model"

    # Build Content parts from message parts
    parts: list[types.Part] = []
    if message.parts:
        for part in message.parts:
            if not isinstance(part, dict):
                continue
            part_type = part.get("type", "")

            if part_type == "text":
                text = part.get("text", "")
                if text:
                    parts.append(types.Part(text=text))
            elif part_type == "tool_call":
                tool_call = part.get("tool_call", {})
                if tool_call:
                    fc = types.FunctionCall(
                        id=tool_call.get("id", ""),
                        name=tool_call.get("name", ""),
                        args=json.loads(tool_call.get("arguments", "{}")),
                    )
                    parts.append(types.Part(function_call=fc))
            elif part_type == "tool_result":
                tool_result = part.get("tool_result", {})
                if tool_result:
                    # Fix: decode response from JSON string instead of wrapping
                    raw_content = tool_result.get("content", "")
                    try:
                        response = json.loads(raw_content) if raw_content else {}
                    except json.JSONDecodeError:
                        response = {"result": raw_content}

                    # Restore FunctionResponse.name from meta
                    fr_name = meta_dict.get("_adk_function_response_name", "")

                    fr = types.FunctionResponse(
                        id=tool_result.get("tool_call_id", ""),
                        name=fr_name,
                        response=response,
                    )
                    parts.append(types.Part(function_response=fr))

    content = types.Content(role=content_role, parts=parts) if parts else None

    # Extract state from meta if present
    state_delta = None
    if _STATE_KEY in meta_dict:
        state_delta = meta_dict[_STATE_KEY]
        if isinstance(state_delta, str):
            state_delta = json.loads(state_delta)

    # Convert timestamp: backend uses milliseconds (int), ADK uses seconds (float)
    timestamp = 0.0
    if message.message_time:
        timestamp = float(message.message_time) / 1000.0

    # Build Event
    # Restore original Event.id from meta (preferred over backend message ID)
    event_id = meta_dict.get("_adk_event_id") or message.id
    event_kwargs: dict[str, Any] = {
        "id": event_id,
        "author": author,
        "timestamp": timestamp,
        "content": content,
    }
    if state_delta is not None:
        event_kwargs["state"] = state_delta

    return Event(**event_kwargs)


def _messages_to_events(messages: list[MessageInfo]) -> list[Event]:
    """Group consecutive messages by _adk_event_id and merge into Events.

    Messages with the same consecutive ``_adk_event_id`` are merged into
    a single Event with multiple parts. Messages without ``_adk_event_id``
    (backward compatibility) are treated as individual Events.

    This restores the original Event structure after persistence, since
    ``event_to_messages`` splits one Event with N parts into N messages.

    Args:
        messages: List of AgentArts MessageInfo objects.

    Returns:
        List of ADK Events with parts merged from consecutive messages.
    """
    if not messages:
        return []

    events: list[Event] = []
    current_group: list[MessageInfo] = []
    current_event_id: str | None = None

    for msg in messages:
        meta = _parse_meta(getattr(msg, "meta", None))
        event_id = meta.get("_adk_event_id")

        # Group consecutive messages with the same event_id
        if event_id and event_id == current_event_id:
            current_group.append(msg)
        else:
            # Flush previous group
            if current_group:
                events.append(_merge_group_to_event(current_group))
            current_group = [msg]
            current_event_id = event_id

    # Flush last group
    if current_group:
        events.append(_merge_group_to_event(current_group))

    return events


def _merge_group_to_event(messages: list[MessageInfo]) -> Event:
    """Merge a group of messages into a single Event with multiple parts.

    Args:
        messages: List of consecutive MessageInfo objects with the same
            ``_adk_event_id``.

    Returns:
        ADK Event with parts merged from all messages. The Event.id is
        restored from ``_adk_event_id`` in meta (not the backend message ID).
    """
    if len(messages) == 1:
        return message_to_event(messages[0])

    # Convert all messages to Events
    events = [message_to_event(msg) for msg in messages]

    # Merge parts from all Events into the first one
    merged = events[0]
    for event in events[1:]:
        if event.content and event.content.parts:
            if merged.content is None:
                merged.content = event.content
            else:
                merged.content.parts.extend(event.content.parts)
        # State from later events overrides earlier ones
        event_state = getattr(getattr(event, "actions", None), "state_delta", None)
        if event_state:
            if merged.actions is None:
                # Create actions if it doesn't exist
                from google.adk.events.event import EventActions
                merged.actions = EventActions(state_delta=event_state)
            else:
                merged.actions.state_delta = event_state

    # Restore original Event.id from meta (not the backend message ID)
    first_meta = _parse_meta(getattr(messages[0], "meta", None))
    original_id = first_meta.get("_adk_event_id")
    if original_id:
        merged.id = original_id

    return merged


def _convert_search_response(response) -> SearchMemoryResponse:
    """Convert SDK MemorySearchResponse to ADK SearchMemoryResponse.

    Backend returns results as ``[{"record": {...}, "score": float}]``.
    Each record contains fields like ``content``, ``id``, etc.

    Args:
        response: AgentArts SDK MemorySearchResponse.

    Returns:
        ADK SearchMemoryResponse.
    """
    if not ADK_AVAILABLE:
        msg = (
            "google-adk is required for search response conversion. "
            "Install it with: pip install google-adk"
        )
        raise ImportError(msg)

    memories: list[MemoryEntry] = []
    for result in response.results:
        record = result.get("record", {})
        score = result.get("score", 0.0)

        content_text = record.get("content", "")
        memory_id = record.get("id")

        entry = MemoryEntry(
            content=types.Content(
                parts=[types.Part(text=content_text)]
            ),
            id=memory_id,
            custom_metadata={"score": score},
        )
        memories.append(entry)

    return SearchMemoryResponse(memories=memories)
