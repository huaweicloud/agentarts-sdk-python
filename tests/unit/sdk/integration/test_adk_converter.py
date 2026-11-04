"""
Unit tests for Google ADK converter module.

Tests cover:
- _parse_meta helper
- _extract_session_scoped_state
- event_to_messages (all part types, state placement, placeholder)
- message_to_event (id/author/state recovery, timestamp conversion)
- _messages_to_events (grouping logic)
- _merge_group_to_event (single/multi message paths)
- _convert_search_response
- Round-trip fidelity tests (critical for verifying review fixes)
"""

import json

import pytest

pytest.importorskip("google.adk")

from google.adk.events.event import Event
from google.genai import types

from agentarts.sdk.integration.google_adk.converter import (
    _STATE_KEY,
    _convert_search_response,
    _extract_session_scoped_state,
    _merge_group_to_event,
    _messages_to_events,
    _parse_meta,
    event_to_messages,
    message_to_event,
)
from agentarts.sdk.memory import (
    MessageInfo,
    TextMessage,
    ToolCallMessage,
    ToolResultMessage,
)

# --- Helpers ---

def _make_text_event(event_id="evt-1", author="user", text="Hello", state=None):
    """Helper: create ADK Event with text part."""
    kwargs = {
        "id": event_id,
        "author": author,
        "content": types.Content(
            role="user" if author == "user" else "model",
            parts=[types.Part(text=text)],
        ),
    }
    if state is not None:
        kwargs["state"] = state
    return Event(**kwargs)


def _make_function_call_event(
    event_id="evt-2",
    author="agent",
    fc_id="fc-1",
    fc_name="get_weather",
    fc_args=None,
):
    """Helper: create ADK Event with function_call part."""
    if fc_args is None:
        fc_args = {"city": "Tokyo"}
    return Event(
        id=event_id,
        author=author,
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        id=fc_id, name=fc_name, args=fc_args
                    )
                )
            ],
        ),
    )


def _make_function_response_event(
    event_id="evt-3",
    author="agent",
    fr_id="fc-1",
    fr_name="get_weather",
    fr_response=None,
):
    """Helper: create ADK Event with function_response part."""
    if fr_response is None:
        fr_response = {"temp": 25, "condition": "sunny"}
    return Event(
        id=event_id,
        author=author,
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        id=fr_id, name=fr_name, response=fr_response
                    )
                )
            ],
        ),
    )


def _make_mixed_event(event_id="evt-4", author="agent"):
    """Helper: create ADK Event with text + function_call + function_response."""
    return Event(
        id=event_id,
        author=author,
        content=types.Content(
            role="model",
            parts=[
                types.Part(text="Let me check the weather"),
                types.Part(
                    function_call=types.FunctionCall(
                        id="fc-1", name="get_weather", args={"city": "Tokyo"}
                    )
                ),
                types.Part(
                    function_response=types.FunctionResponse(
                        id="fc-1",
                        name="get_weather",
                        response={"temp": 25},
                    )
                ),
            ],
        ),
    )


def _make_state_only_event(event_id="evt-5", author="agent", state=None):
    """Helper: create ADK Event with no content (state-only)."""
    kwargs = {
        "id": event_id,
        "author": author,
        "content": None,
    }
    if state is not None:
        kwargs["state"] = state
    return Event(**kwargs)


def _to_message_info(msg, idx=0):
    """Simulate backend conversion: input message type -> MessageInfo.

    event_to_messages produces TextMessage/ToolCallMessage/ToolResultMessage
    (input types with .to_dict()), but message_to_event expects MessageInfo
    (output type with .role and .parts). This helper bridges the gap by
    calling .to_dict() and constructing a MessageInfo, simulating what the
    backend would return after persisting the messages.
    """
    d = msg.to_dict()
    # Backend returns meta as dict (not str)
    meta = None
    raw_meta = d.get("meta")
    if raw_meta:
        if isinstance(raw_meta, str):
            meta = json.loads(raw_meta)
        elif isinstance(raw_meta, dict):
            meta = raw_meta
    return MessageInfo(
        id=f"msg-{idx}",
        session_id="s1",
        seq=idx,
        role=d.get("role", "user"),
        parts=d.get("parts"),
        meta=meta,
        message_time=1000 + idx,
        assistant_id=getattr(msg, "assistant_id", None),
    )


def _messages_to_message_infos(messages):
    """Convert a list of input message types to MessageInfo list."""
    return [_to_message_info(msg, i) for i, msg in enumerate(messages)]


# ============================================================================
# TestParseMeta
# ============================================================================


class TestParseMeta:
    """Tests for _parse_meta helper."""

    def test_none(self):
        assert _parse_meta(None) == {}

    def test_empty_string(self):
        assert _parse_meta("") == {}

    def test_json_string(self):
        assert _parse_meta('{"key": "value"}') == {"key": "value"}

    def test_dict(self):
        original = {"key": "value"}
        result = _parse_meta(original)
        assert result == original
        # Should return a copy
        assert result is not original

    def test_non_json_string(self):
        assert _parse_meta("not json") == {}

    def test_json_array_string(self):
        """JSON array is valid JSON but not a dict."""
        assert _parse_meta("[1, 2, 3]") == {}

    def test_empty_json_string(self):
        assert _parse_meta("{}") == {}


# ============================================================================
# TestExtractSessionScopedState
# ============================================================================


class TestExtractSessionScopedState:
    """Tests for _extract_session_scoped_state."""

    def test_filters_app_prefix(self):
        state = {"app:config": "value", "session_key": "keep"}
        result = _extract_session_scoped_state(state)
        assert result == {"session_key": "keep"}

    def test_filters_user_prefix(self):
        state = {"user:preference": "dark", "session_key": "keep"}
        result = _extract_session_scoped_state(state)
        assert result == {"session_key": "keep"}

    def test_filters_temp_prefix(self):
        state = {"temp:cache": "data", "session_key": "keep"}
        result = _extract_session_scoped_state(state)
        assert result == {"session_key": "keep"}

    def test_keeps_session_keys(self):
        state = {"step": 1, "counter": 5, "data": "value"}
        result = _extract_session_scoped_state(state)
        assert result == state

    def test_empty_dict(self):
        assert _extract_session_scoped_state({}) == {}

    def test_mixed_state(self):
        state = {
            "current_step": 1,
            "app:config": "value",
            "user:preference": "dark",
            "temp:cache": "data",
            "session_data": "keep",
        }
        result = _extract_session_scoped_state(state)
        assert result == {"current_step": 1, "session_data": "keep"}


# ============================================================================
# TestEventToMessages
# ============================================================================


class TestEventToMessages:
    """Tests for event_to_messages."""

    def test_text_event(self):
        event = _make_text_event()
        messages = event_to_messages(event)
        assert len(messages) == 1
        assert isinstance(messages[0], TextMessage)
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"

    def test_function_call_event(self):
        event = _make_function_call_event()
        messages = event_to_messages(event)
        assert len(messages) == 1
        assert isinstance(messages[0], ToolCallMessage)
        assert messages[0].id == "fc-1"
        assert messages[0].name == "get_weather"
        assert json.loads(messages[0].arguments) == {"city": "Tokyo"}

    def test_function_response_event(self):
        event = _make_function_response_event()
        messages = event_to_messages(event)
        assert len(messages) == 1
        assert isinstance(messages[0], ToolResultMessage)
        assert messages[0].tool_call_id == "fc-1"
        assert json.loads(messages[0].content) == {"temp": 25, "condition": "sunny"}

    def test_mixed_event(self):
        event = _make_mixed_event()
        messages = event_to_messages(event)
        assert len(messages) == 3
        assert isinstance(messages[0], TextMessage)
        assert isinstance(messages[1], ToolCallMessage)
        assert isinstance(messages[2], ToolResultMessage)

    def test_state_only_event_placeholder(self):
        event = _make_state_only_event()
        messages = event_to_messages(event)
        assert len(messages) == 1
        assert isinstance(messages[0], TextMessage)
        assert messages[0].content == "[state_update]"

    def test_state_meta_on_last_message(self):
        """State snapshot should be on the last message."""
        event = _make_mixed_event()
        state = {"step": 1, "counter": 5}
        messages = event_to_messages(event, full_state=state)
        assert len(messages) == 3
        # Last message should have state
        last_meta = json.loads(messages[2].meta)
        assert _STATE_KEY in last_meta
        assert last_meta[_STATE_KEY] == state
        # First two messages should not have state
        first_meta = json.loads(messages[0].meta)
        assert _STATE_KEY not in first_meta
        second_meta = json.loads(messages[1].meta)
        assert _STATE_KEY not in second_meta

    def test_state_meta_single_message(self):
        """State snapshot on single message event."""
        event = _make_text_event()
        state = {"step": 1}
        messages = event_to_messages(event, full_state=state)
        assert len(messages) == 1
        meta = json.loads(messages[0].meta)
        assert _STATE_KEY in meta
        assert meta[_STATE_KEY] == state

    def test_no_state_meta(self):
        """full_state=None should not add state to meta."""
        event = _make_text_event()
        messages = event_to_messages(event, full_state=None)
        assert len(messages) == 1
        meta = json.loads(messages[0].meta)
        assert _STATE_KEY not in meta

    def test_all_messages_carry_event_id(self):
        """All messages should carry _adk_event_id."""
        event = _make_mixed_event(event_id="evt-test")
        messages = event_to_messages(event)
        for msg in messages:
            meta = json.loads(msg.meta)
            assert meta["_adk_event_id"] == "evt-test"

    def test_all_messages_carry_author(self):
        """All messages should carry _adk_author."""
        event = _make_mixed_event(author="weather_agent")
        messages = event_to_messages(event)
        for msg in messages:
            meta = json.loads(msg.meta)
            assert meta["_adk_author"] == "weather_agent"

    def test_tool_result_carry_function_response_name(self):
        """ToolResultMessage should carry _adk_function_response_name."""
        event = _make_function_response_event(fr_name="get_weather")
        messages = event_to_messages(event)
        assert len(messages) == 1
        meta = json.loads(messages[0].meta)
        assert meta["_adk_function_response_name"] == "get_weather"

    def test_to_dict_roundtrip(self):
        """All message types should serialize via to_dict()."""
        event = _make_mixed_event()
        messages = event_to_messages(event)
        for msg in messages:
            msg_dict = msg.to_dict()
            assert isinstance(msg_dict, dict)
            assert "parts" in msg_dict
            assert "role" in msg_dict

    def test_state_only_event_carries_author(self):
        """Placeholder event should also carry _adk_author."""
        event = _make_state_only_event(author="system_agent")
        messages = event_to_messages(event)
        assert len(messages) == 1
        meta = json.loads(messages[0].meta)
        assert meta["_adk_author"] == "system_agent"

    def test_user_event_role(self):
        """User events should have role='user'."""
        event = _make_text_event(author="user")
        messages = event_to_messages(event)
        assert messages[0].role == "user"

    def test_agent_event_role(self):
        """Agent events should have role='assistant'."""
        event = _make_text_event(author="agent")
        messages = event_to_messages(event)
        assert messages[0].role == "assistant"


# ============================================================================
# TestMessageToEvent
# ============================================================================


class TestMessageToEvent:
    """Tests for message_to_event."""

    def test_event_id_recovery_from_meta(self):
        """Event.id should be recovered from _adk_event_id (priority)."""
        msg = MessageInfo(
            id="backend-msg-id",
            session_id="s1",
            seq=0,
            role="user",
            parts=[{"type": "text", "text": "Hello"}],
            meta=json.dumps({"_adk_event_id": "original-evt-id", "_adk_author": "user"}),
        )
        event = message_to_event(msg)
        assert event.id == "original-evt-id"

    def test_event_id_fallback_to_message_id(self):
        """Event.id should fallback to message.id if no _adk_event_id."""
        msg = MessageInfo(
            id="backend-msg-id",
            session_id="s1",
            seq=0,
            role="user",
            parts=[{"type": "text", "text": "Hello"}],
            meta=json.dumps({"_adk_author": "user"}),
        )
        event = message_to_event(msg)
        assert event.id == "backend-msg-id"

    def test_author_recovery_user_role(self):
        """User role should always have author='user'."""
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="user",
            parts=[{"type": "text", "text": "Hello"}],
            meta=json.dumps({"_adk_event_id": "evt-1"}),
        )
        event = message_to_event(msg)
        assert event.author == "user"

    def test_author_recovery_from_meta(self):
        """Assistant/agent author should be recovered from _adk_author."""
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="assistant",
            parts=[{"type": "text", "text": "Hello"}],
            meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "weather_agent"}),
        )
        event = message_to_event(msg)
        assert event.author == "weather_agent"

    def test_author_fallback_to_assistant_id(self):
        """Author should fallback to assistant_id if no _adk_author."""
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="assistant",
            assistant_id="fallback_agent",
            parts=[{"type": "text", "text": "Hello"}],
            meta=json.dumps({"_adk_event_id": "evt-1"}),
        )
        event = message_to_event(msg)
        assert event.author == "fallback_agent"

    def test_text_part_reconstruction(self):
        """Text part should be reconstructed correctly."""
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="user",
            parts=[{"type": "text", "text": "Hello world"}],
            meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "user"}),
        )
        event = message_to_event(msg)
        assert event.content is not None
        assert len(event.content.parts) == 1
        assert event.content.parts[0].text == "Hello world"

    def test_function_call_reconstruction(self):
        """FunctionCall should be reconstructed correctly."""
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="assistant",
            parts=[
                {
                    "type": "tool_call",
                    "tool_call": {
                        "id": "fc-1",
                        "name": "get_weather",
                        "arguments": json.dumps({"city": "Tokyo"}),
                    },
                }
            ],
            meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "agent"}),
        )
        event = message_to_event(msg)
        assert event.content is not None
        assert len(event.content.parts) == 1
        fc = event.content.parts[0].function_call
        assert fc.id == "fc-1"
        assert fc.name == "get_weather"
        assert fc.args == {"city": "Tokyo"}

    def test_function_response_reconstruction(self):
        """FunctionResponse should be reconstructed correctly (no double encoding)."""
        response_data = {"temp": 25, "condition": "sunny"}
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="assistant",
            parts=[
                {
                    "type": "tool_result",
                    "tool_result": {
                        "tool_call_id": "fc-1",
                        "content": json.dumps(response_data),
                    },
                }
            ],
            meta=json.dumps(
                {
                    "_adk_event_id": "evt-1",
                    "_adk_author": "agent",
                    "_adk_function_response_name": "get_weather",
                }
            ),
        )
        event = message_to_event(msg)
        assert event.content is not None
        assert len(event.content.parts) == 1
        fr = event.content.parts[0].function_response
        assert fr.id == "fc-1"
        assert fr.name == "get_weather"
        assert fr.response == response_data  # No double encoding

    def test_function_response_name_recovery(self):
        """FunctionResponse.name should be recovered from _adk_function_response_name."""
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="assistant",
            parts=[
                {
                    "type": "tool_result",
                    "tool_result": {
                        "tool_call_id": "fc-1",
                        "content": json.dumps({"result": "ok"}),
                    },
                }
            ],
            meta=json.dumps(
                {
                    "_adk_event_id": "evt-1",
                    "_adk_author": "agent",
                    "_adk_function_response_name": "custom_tool",
                }
            ),
        )
        event = message_to_event(msg)
        fr = event.content.parts[0].function_response
        assert fr.name == "custom_tool"

    def test_state_extraction(self):
        """State should be extracted from _STATE_KEY in meta."""
        state = {"step": 1, "counter": 5}
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="assistant",
            parts=[{"type": "text", "text": "Hello"}],
            meta=json.dumps(
                {
                    "_adk_event_id": "evt-1",
                    "_adk_author": "agent",
                    _STATE_KEY: state,
                }
            ),
        )
        event = message_to_event(msg)
        # State is routed to actions.state_delta via Event model_validator
        assert event.actions is not None
        assert event.actions.state_delta == state

    def test_timestamp_conversion(self):
        """Timestamp should be converted from ms to s."""
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="user",
            parts=[{"type": "text", "text": "Hello"}],
            meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "user"}),
            message_time=1609459200000,  # 2021-01-01 00:00:00 UTC in ms
        )
        event = message_to_event(msg)
        assert event.timestamp == 1609459200.0  # Converted to seconds

    def test_content_none_when_no_parts(self):
        """Content should be None when no parts."""
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="user",
            parts=[],
            meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "user"}),
        )
        event = message_to_event(msg)
        assert event.content is None

    def test_meta_none_handling(self):
        """Message with meta=None should not crash."""
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="user",
            parts=[{"type": "text", "text": "Hello"}],
            meta=None,
        )
        event = message_to_event(msg)
        assert event.id == "msg-1"  # Fallback to message.id
        assert event.author == "user"  # User role

    def test_meta_empty_handling(self):
        """Message with meta='' should not crash."""
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="user",
            parts=[{"type": "text", "text": "Hello"}],
            meta="",
        )
        event = message_to_event(msg)
        assert event.id == "msg-1"

    def test_meta_non_json_handling(self):
        """Message with non-JSON meta should not crash."""
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="user",
            parts=[{"type": "text", "text": "Hello"}],
            meta="not json",
        )
        event = message_to_event(msg)
        assert event.id == "msg-1"


# ============================================================================
# TestMessagesToEvents
# ============================================================================


class TestMessagesToEvents:
    """Tests for _messages_to_events."""

    def test_consecutive_same_id_grouped(self):
        """Consecutive messages with same _adk_event_id should be grouped."""
        msgs = [
            MessageInfo(
                id="msg-1",
                session_id="s1",
                seq=0,
                role="assistant",
                parts=[{"type": "text", "text": "Text"}],
                meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "agent"}),
            ),
            MessageInfo(
                id="msg-2",
                session_id="s1",
                seq=1,
                role="assistant",
                parts=[
                    {
                        "type": "tool_call",
                        "tool_call": {
                            "id": "fc-1",
                            "name": "get_weather",
                            "arguments": json.dumps({"city": "Tokyo"}),
                        },
                    }
                ],
                meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "agent"}),
            ),
        ]
        events = _messages_to_events(msgs)
        assert len(events) == 1
        assert events[0].id == "evt-1"
        assert len(events[0].content.parts) == 2

    def test_different_id_split(self):
        """Messages with different _adk_event_id should be split."""
        msgs = [
            MessageInfo(
                id="msg-1",
                session_id="s1",
                seq=0,
                role="user",
                parts=[{"type": "text", "text": "Hello"}],
                meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "user"}),
            ),
            MessageInfo(
                id="msg-2",
                session_id="s1",
                seq=1,
                role="assistant",
                parts=[{"type": "text", "text": "Hi"}],
                meta=json.dumps({"_adk_event_id": "evt-2", "_adk_author": "agent"}),
            ),
        ]
        events = _messages_to_events(msgs)
        assert len(events) == 2
        assert events[0].id == "evt-1"
        assert events[1].id == "evt-2"

    def test_no_event_id_backward_compat(self):
        """Messages without _adk_event_id should be treated as individual events."""
        msgs = [
            MessageInfo(
                id="msg-1",
                session_id="s1",
                seq=0,
                role="user",
                parts=[{"type": "text", "text": "Hello"}],
                meta=json.dumps({"_adk_author": "user"}),
            ),
        ]
        events = _messages_to_events(msgs)
        assert len(events) == 1
        assert events[0].id == "msg-1"  # Fallback to message.id

    def test_empty_list(self):
        """Empty message list should return empty events list."""
        events = _messages_to_events([])
        assert events == []

    def test_trailing_group_flush(self):
        """Last group should be flushed correctly."""
        msgs = [
            MessageInfo(
                id="msg-1",
                session_id="s1",
                seq=0,
                role="assistant",
                parts=[{"type": "text", "text": "Text"}],
                meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "agent"}),
            ),
            MessageInfo(
                id="msg-2",
                session_id="s1",
                seq=1,
                role="assistant",
                parts=[
                    {
                        "type": "tool_call",
                        "tool_call": {
                            "id": "fc-1",
                            "name": "tool",
                            "arguments": json.dumps({}),
                        },
                    }
                ],
                meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "agent"}),
            ),
        ]
        events = _messages_to_events(msgs)
        assert len(events) == 1
        assert len(events[0].content.parts) == 2


# ============================================================================
# TestMergeGroupToEvent
# ============================================================================


class TestMergeGroupToEvent:
    """Tests for _merge_group_to_event."""

    def test_single_message_path(self):
        """Single message should go through message_to_event."""
        msg = MessageInfo(
            id="msg-1",
            session_id="s1",
            seq=0,
            role="user",
            parts=[{"type": "text", "text": "Hello"}],
            meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "user"}),
        )
        event = _merge_group_to_event([msg])
        assert event.id == "evt-1"
        assert event.author == "user"

    def test_multi_message_path_parts_merge(self):
        """Multiple messages should merge parts."""
        msgs = [
            MessageInfo(
                id="msg-1",
                session_id="s1",
                seq=0,
                role="assistant",
                parts=[{"type": "text", "text": "Text"}],
                meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "agent"}),
            ),
            MessageInfo(
                id="msg-2",
                session_id="s1",
                seq=1,
                role="assistant",
                parts=[
                    {
                        "type": "tool_call",
                        "tool_call": {
                            "id": "fc-1",
                            "name": "tool",
                            "arguments": json.dumps({}),
                        },
                    }
                ],
                meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "agent"}),
            ),
        ]
        event = _merge_group_to_event(msgs)
        assert event.id == "evt-1"
        assert len(event.content.parts) == 2

    def test_multi_message_path_state_override(self):
        """Later state should override earlier state."""
        msgs = [
            MessageInfo(
                id="msg-1",
                session_id="s1",
                seq=0,
                role="assistant",
                parts=[{"type": "text", "text": "Text"}],
                meta=json.dumps(
                    {
                        "_adk_event_id": "evt-1",
                        "_adk_author": "agent",
                        _STATE_KEY: {"step": 1},
                    }
                ),
            ),
            MessageInfo(
                id="msg-2",
                session_id="s1",
                seq=1,
                role="assistant",
                parts=[{"type": "text", "text": "More"}],
                meta=json.dumps(
                    {
                        "_adk_event_id": "evt-1",
                        "_adk_author": "agent",
                        _STATE_KEY: {"step": 2},
                    }
                ),
            ),
        ]
        event = _merge_group_to_event(msgs)
        assert event.actions.state_delta == {"step": 2}


# ============================================================================
# TestConvertSearchResponse
# ============================================================================


class TestConvertSearchResponse:
    """Tests for _convert_search_response."""

    def test_results_to_memory_entries(self):
        """Search results should be converted to MemoryEntry list."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.results = [
            {
                "record": {"content": "User prefers dark mode", "id": "mem-1"},
                "score": 0.95,
            },
            {
                "record": {"content": "User likes Python", "id": "mem-2"},
                "score": 0.88,
            },
        ]

        result = _convert_search_response(mock_response)
        assert len(result.memories) == 2
        assert result.memories[0].id == "mem-1"
        assert result.memories[1].id == "mem-2"

    def test_score_to_custom_metadata(self):
        """Score should be stored in custom_metadata."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.results = [
            {
                "record": {"content": "Test", "id": "mem-1"},
                "score": 0.95,
            }
        ]

        result = _convert_search_response(mock_response)
        assert result.memories[0].custom_metadata["score"] == 0.95


# ============================================================================
# TestRoundTrip
# ============================================================================


class TestRoundTrip:
    """Round-trip fidelity tests (Event -> messages -> Event)."""

    def test_multi_part_event_round_trip(self):
        """Multi-part Event should survive round-trip."""
        original = _make_mixed_event(event_id="evt-rt", author="weather_agent")
        messages = event_to_messages(original)
        infos = _messages_to_message_infos(messages)
        events = _messages_to_events(infos)

        assert len(events) == 1
        restored = events[0]
        assert restored.id == "evt-rt"
        assert restored.author == "weather_agent"
        assert len(restored.content.parts) == 3

    def test_function_response_name_round_trip(self):
        """FunctionResponse.name should survive round-trip."""
        original = _make_function_response_event(fr_name="custom_tool")
        messages = event_to_messages(original)
        infos = _messages_to_message_infos(messages)
        events = _messages_to_events(infos)

        assert len(events) == 1
        fr = events[0].content.parts[0].function_response
        assert fr.name == "custom_tool"

    def test_function_response_response_round_trip(self):
        """FunctionResponse.response should survive round-trip (no double encoding)."""
        response_data = {"temp": 25, "condition": "sunny", "nested": {"key": "value"}}
        original = _make_function_response_event(fr_response=response_data)
        messages = event_to_messages(original)
        infos = _messages_to_message_infos(messages)
        events = _messages_to_events(infos)

        assert len(events) == 1
        fr = events[0].content.parts[0].function_response
        assert fr.response == response_data

    def test_tool_author_round_trip(self):
        """Tool message author should survive round-trip."""
        original = _make_mixed_event(author="custom_agent")
        messages = event_to_messages(original)
        infos = _messages_to_message_infos(messages)
        events = _messages_to_events(infos)

        assert len(events) == 1
        assert events[0].author == "custom_agent"

    def test_single_part_event_id_round_trip(self):
        """Single-part Event.id should survive round-trip."""
        original = _make_text_event(event_id="single-evt")
        messages = event_to_messages(original)
        infos = _messages_to_message_infos(messages)
        events = _messages_to_events(infos)

        assert len(events) == 1
        assert events[0].id == "single-evt"

    def test_state_only_event_author_round_trip(self):
        """State-only event author should survive round-trip."""
        original = _make_state_only_event(author="system")
        messages = event_to_messages(original)
        infos = _messages_to_message_infos(messages)
        events = _messages_to_events(infos)

        assert len(events) == 1
        assert events[0].author == "system"

    def test_user_text_author_round_trip(self):
        """User text author should survive round-trip."""
        original = _make_text_event(author="user")
        messages = event_to_messages(original)
        infos = _messages_to_message_infos(messages)
        events = _messages_to_events(infos)

        assert len(events) == 1
        assert events[0].author == "user"

    def test_backward_compat_no_event_id(self):
        """Messages without _adk_event_id should be handled correctly."""
        msg = MessageInfo(
            id="old-msg-id",
            session_id="s1",
            seq=0,
            role="user",
            parts=[{"type": "text", "text": "Old message"}],
            meta=None,
        )
        events = _messages_to_events([msg])
        assert len(events) == 1
        assert events[0].id == "old-msg-id"
        assert events[0].author == "user"
