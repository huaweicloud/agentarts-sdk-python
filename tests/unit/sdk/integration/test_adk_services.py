"""
Unit tests for Google ADK session and memory services.

Tests cover:
- AgentArtsSessionService (create/get/append/list/delete/fetch)
- AgentArtsMemoryService (try_add_event/add_session/add_events/search)
- Module exports
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("google.adk")

from google.adk.events.event import Event
from google.adk.sessions.session import Session
from google.genai import types

from agentarts.sdk.integration.google_adk.converter import _STATE_KEY
from agentarts.sdk.integration.google_adk.memory_service import AgentArtsMemoryService
from agentarts.sdk.integration.google_adk.session_service import (
    AgentArtsSessionService,
)
from agentarts.sdk.memory import MessageInfo

# --- Helpers ---


def _make_mock_client():
    """Create a mock AsyncMemoryClient."""
    client = AsyncMock()
    client.create_memory_session = AsyncMock()
    client.get_session = AsyncMock()
    client.get_last_k_messages = AsyncMock(return_value=[])
    client.list_messages = AsyncMock()
    client.add_messages = AsyncMock()
    client.delete_session = AsyncMock()
    client.list_sessions = AsyncMock()
    client.search_memories = AsyncMock()
    return client


def _make_session_info(session_id="session-123"):
    """Create a mock SessionInfo."""
    info = MagicMock()
    info.id = session_id
    return info


def _make_message_with_state(state=None, event_id="evt-1"):
    """Create a MessageInfo with optional state in meta."""
    meta_dict = {"_adk_event_id": event_id, "_adk_author": "agent"}
    if state is not None:
        meta_dict[_STATE_KEY] = state
    return MessageInfo(
        id="msg-1",
        session_id="session-123",
        seq=0,
        role="assistant",
        parts=[{"type": "text", "text": "Hello"}],
        meta=json.dumps(meta_dict),
    )


def _make_message_list_response(items, total=None):
    """Create a mock MessageListResponse."""
    response = MagicMock()
    response.items = items
    response.total = total if total is not None else len(items)
    return response


def _make_text_event(event_id="evt-1", author="user", text="Hello"):
    """Create ADK Event with text part."""
    return Event(
        id=event_id,
        author=author,
        content=types.Content(
            role="user" if author == "user" else "model",
            parts=[types.Part(text=text)],
        ),
    )


def _make_api_exception(status_code, message="Error"):
    """Create a real APIException for use as side_effect."""
    from agentarts.sdk.service import APIException

    return APIException(
        status_code=status_code,
        error_code=f"ERR_{status_code}",
        error_msg=message,
    )


# ============================================================================
# TestSessionServiceInit
# ============================================================================


class TestSessionServiceInit:
    """Tests for AgentArtsSessionService initialization."""

    def test_init(self):
        client = _make_mock_client()
        service = AgentArtsSessionService(client)
        assert service._client is client


# ============================================================================
# TestCreateSession
# ============================================================================


class TestCreateSession:
    """Tests for create_session."""

    @pytest.mark.asyncio
    async def test_create_session_basic(self):
        client = _make_mock_client()
        session_info = _make_session_info("new-session")
        client.create_memory_session.return_value = session_info

        service = AgentArtsSessionService(client)
        session = await service.create_session(
            app_name="test-app",
            user_id="user-123",
            state={"key": "value"},
            session_id="new-session",
        )

        assert session.id == "new-session"
        assert session.app_name == "test-app"
        assert session.user_id == "user-123"
        assert session.state == {"key": "value"}
        assert session.events == []
        client.create_memory_session.assert_called_once_with(
            space_id="test-app",
            id="new-session",
            actor_id="user-123",
        )

    @pytest.mark.asyncio
    async def test_create_session_no_state(self):
        client = _make_mock_client()
        session_info = _make_session_info()
        client.create_memory_session.return_value = session_info

        service = AgentArtsSessionService(client)
        session = await service.create_session(
            app_name="test-app",
            user_id="user-123",
        )

        assert session.state == {}


# ============================================================================
# TestGetSession
# ============================================================================


class TestGetSession:
    """Tests for get_session."""

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        client = _make_mock_client()
        client.get_session.side_effect = _make_api_exception(404, "Not found")

        service = AgentArtsSessionService(client)
        session = await service.get_session(
            app_name="test-app",
            user_id="user-123",
            session_id="nonexistent",
        )

        assert session is None

    @pytest.mark.asyncio
    async def test_get_session_exists(self):
        client = _make_mock_client()
        client.get_session.return_value = _make_session_info()
        client.get_last_k_messages.return_value = []
        client.list_messages.return_value = _make_message_list_response([])

        service = AgentArtsSessionService(client)
        session = await service.get_session(
            app_name="test-app",
            user_id="user-123",
            session_id="session-123",
        )

        assert session is not None
        assert session.id == "session-123"
        assert session.app_name == "test-app"
        assert session.user_id == "user-123"

    @pytest.mark.asyncio
    async def test_get_session_state_read(self):
        client = _make_mock_client()
        client.get_session.return_value = _make_session_info()

        state = {"step": 1, "counter": 5}
        msg_with_state = _make_message_with_state(state=state)
        client.get_last_k_messages.return_value = [msg_with_state]
        client.list_messages.return_value = _make_message_list_response([])

        service = AgentArtsSessionService(client)
        session = await service.get_session(
            app_name="test-app",
            user_id="user-123",
            session_id="session-123",
        )

        assert session.state == state

    @pytest.mark.asyncio
    async def test_get_session_state_as_string(self):
        """State stored as JSON string should be parsed."""
        client = _make_mock_client()
        client.get_session.return_value = _make_session_info()

        state = {"step": 1}
        msg = MessageInfo(
            id="msg-1",
            session_id="session-123",
            seq=0,
            role="assistant",
            parts=[{"type": "text", "text": "Hello"}],
            meta=json.dumps(
                {
                    "_adk_event_id": "evt-1",
                    "_adk_author": "agent",
                    _STATE_KEY: json.dumps(state),
                }
            ),
        )
        client.get_last_k_messages.return_value = [msg]
        client.list_messages.return_value = _make_message_list_response([])

        service = AgentArtsSessionService(client)
        session = await service.get_session(
            app_name="test-app",
            user_id="user-123",
            session_id="session-123",
        )

        assert session.state == state

    @pytest.mark.asyncio
    async def test_get_session_num_recent_events_zero(self):
        client = _make_mock_client()
        client.get_session.return_value = _make_session_info()
        client.get_last_k_messages.return_value = []

        service = AgentArtsSessionService(client)
        from google.adk.sessions.base_session_service import GetSessionConfig

        config = GetSessionConfig(num_recent_events=0)
        session = await service.get_session(
            app_name="test-app",
            user_id="user-123",
            session_id="session-123",
            config=config,
        )

        assert session.events == []

    @pytest.mark.asyncio
    async def test_get_session_num_recent_events_positive(self):
        """num_recent_events should over-fetch and trim."""
        client = _make_mock_client()
        client.get_session.return_value = _make_session_info()

        # Create 3 events worth of messages (3 events x 2 parts each = 6 messages)
        messages = []
        for i in range(3):
            for j in range(2):
                messages.append(
                    MessageInfo(
                        id=f"msg-{i}-{j}",
                        session_id="session-123",
                        seq=i * 2 + j,
                        role="assistant",
                        parts=[{"type": "text", "text": f"Event {i} part {j}"}],
                        meta=json.dumps(
                            {"_adk_event_id": f"evt-{i}", "_adk_author": "agent"}
                        ),
                    )
                )

        # get_last_k_messages is called twice:
        # 1. k=1 for state read -> return [] (no state)
        # 2. k=20 for event loading (fetch_count = 2 * _MAX_PARTS_PER_EVENT = 20)
        client.get_last_k_messages.side_effect = [[], messages]

        service = AgentArtsSessionService(client)
        from google.adk.sessions.base_session_service import GetSessionConfig

        config = GetSessionConfig(num_recent_events=2)
        session = await service.get_session(
            app_name="test-app",
            user_id="user-123",
            session_id="session-123",
            config=config,
        )

        # Should return last 2 events
        assert len(session.events) == 2
        assert session.events[0].id == "evt-1"
        assert session.events[1].id == "evt-2"

    @pytest.mark.asyncio
    async def test_get_session_after_timestamp(self):
        client = _make_mock_client()
        client.get_session.return_value = _make_session_info()
        client.get_last_k_messages.return_value = []

        # Create messages with different timestamps
        messages = [
            MessageInfo(
                id="msg-1",
                session_id="session-123",
                seq=0,
                role="user",
                parts=[{"type": "text", "text": "Old"}],
                meta=json.dumps({"_adk_event_id": "evt-1", "_adk_author": "user"}),
                message_time=1000000,  # Old timestamp
            ),
            MessageInfo(
                id="msg-2",
                session_id="session-123",
                seq=1,
                role="assistant",
                parts=[{"type": "text", "text": "New"}],
                meta=json.dumps({"_adk_event_id": "evt-2", "_adk_author": "agent"}),
                message_time=2000000,  # New timestamp
            ),
        ]
        client.list_messages.return_value = _make_message_list_response(messages)

        service = AgentArtsSessionService(client)
        from google.adk.sessions.base_session_service import GetSessionConfig

        config = GetSessionConfig(after_timestamp=1500.0)  # 1500 seconds
        session = await service.get_session(
            app_name="test-app",
            user_id="user-123",
            session_id="session-123",
            config=config,
        )

        # Only event after timestamp should be included
        assert len(session.events) == 1
        assert session.events[0].id == "evt-2"


# ============================================================================
# TestAppendEvent
# ============================================================================


class TestAppendEvent:
    """Tests for append_event."""

    @pytest.mark.asyncio
    async def test_append_event_basic(self):
        client = _make_mock_client()
        service = AgentArtsSessionService(client)

        session = Session(
            id="session-123",
            app_name="test-app",
            user_id="user-123",
            state={"step": 1},
            events=[],
        )
        event = _make_text_event(event_id="evt-1")

        result = await service.append_event(session, event)

        assert result is not None
        client.add_messages.assert_called_once()
        call_kwargs = client.add_messages.call_args.kwargs
        assert call_kwargs["space_id"] == "test-app"
        assert call_kwargs["session_id"] == "session-123"
        assert call_kwargs["idempotency_key"] == "session-123:evt-1"

    @pytest.mark.asyncio
    async def test_append_event_state_snapshot(self):
        """State should be snapshot in messages."""
        client = _make_mock_client()
        service = AgentArtsSessionService(client)

        session = Session(
            id="session-123",
            app_name="test-app",
            user_id="user-123",
            state={"step": 1, "counter": 5},
            events=[],
        )
        event = _make_text_event(event_id="evt-1")

        await service.append_event(session, event)

        messages = client.add_messages.call_args.kwargs["messages"]
        assert len(messages) > 0
        # Last message should have state
        last_meta = json.loads(messages[-1].meta)
        assert _STATE_KEY in last_meta
        # State should be session-scoped only (no app:/user:/temp: prefixes)
        state = last_meta[_STATE_KEY]
        assert state == {"step": 1, "counter": 5}

    @pytest.mark.asyncio
    async def test_append_event_409_fallback(self):
        """409 Conflict should be silently caught."""
        client = _make_mock_client()
        client.add_messages.side_effect = _make_api_exception(409, "Conflict")

        service = AgentArtsSessionService(client)
        session = Session(
            id="session-123",
            app_name="test-app",
            user_id="user-123",
            state={},
            events=[],
        )
        event = _make_text_event()

        # Should not raise
        result = await service.append_event(session, event)
        assert result is not None

    @pytest.mark.asyncio
    async def test_append_event_non_409_raises(self):
        """Non-409 errors should be re-raised."""
        client = _make_mock_client()
        client.add_messages.side_effect = _make_api_exception(500, "Internal error")

        service = AgentArtsSessionService(client)
        session = Session(
            id="session-123",
            app_name="test-app",
            user_id="user-123",
            state={},
            events=[],
        )
        event = _make_text_event()

        with pytest.raises(Exception):
            await service.append_event(session, event)


# ============================================================================
# TestFetchMessages
# ============================================================================


class TestFetchMessages:
    """Tests for _fetch_messages."""

    @pytest.mark.asyncio
    async def test_fetch_messages_simple_path(self):
        """target_count <= 20 should use get_last_k_messages."""
        client = _make_mock_client()
        messages = [
            MessageInfo(
                id="msg-1",
                session_id="session-123",
                seq=0,
                role="user",
                parts=[{"type": "text", "text": "Hello"}],
            )
        ]
        client.get_last_k_messages.return_value = messages

        service = AgentArtsSessionService(client)
        result = await service._fetch_messages("test-app", "session-123", 10)

        assert result == messages
        client.get_last_k_messages.assert_called_once_with(
            session_id="session-123", k=10, space_id="test-app"
        )

    @pytest.mark.asyncio
    async def test_fetch_messages_paginated_path(self):
        """target_count > 20 should use list_messages with pagination."""
        client = _make_mock_client()

        # Full dataset of 50 messages; pagination starts at offset 25
        all_messages = [
            MessageInfo(
                id=f"msg-{i}",
                session_id="session-123",
                seq=i,
                role="user",
                parts=[{"type": "text", "text": f"Message {i}"}],
            )
            for i in range(50)
        ]

        # Mock list_messages to return different pages
        call_count = [0]

        async def mock_list_messages(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call to get total
                return _make_message_list_response([], total=50)
            # Subsequent calls to get pages
            limit = kwargs.get("limit", 20)
            offset = kwargs.get("offset", 0)
            page = all_messages[offset : offset + limit]
            return _make_message_list_response(page, total=50)

        client.list_messages.side_effect = mock_list_messages

        service = AgentArtsSessionService(client)
        result = await service._fetch_messages("test-app", "session-123", 25)

        assert len(result) == 25

    @pytest.mark.asyncio
    async def test_fetch_messages_total_zero(self):
        """total=0 should return empty list."""
        client = _make_mock_client()
        client.list_messages.return_value = _make_message_list_response([], total=0)

        service = AgentArtsSessionService(client)
        result = await service._fetch_messages("test-app", "session-123", None)

        assert result == []


# ============================================================================
# TestListSessions
# ============================================================================


class TestListSessions:
    """Tests for list_sessions."""

    @pytest.mark.asyncio
    async def test_list_sessions(self):
        client = _make_mock_client()

        session1 = MagicMock()
        session1.id = "session-1"
        session1.actor_id = "user-1"

        session2 = MagicMock()
        session2.id = "session-2"
        session2.actor_id = "user-1"

        response = MagicMock()
        response.items = [session1, session2]
        client.list_sessions.return_value = response

        service = AgentArtsSessionService(client)
        result = await service.list_sessions(
            app_name="test-app", user_id="user-1"
        )

        assert len(result.sessions) == 2
        assert result.sessions[0].id == "session-1"
        assert result.sessions[1].id == "session-2"


# ============================================================================
# TestDeleteSession
# ============================================================================


class TestDeleteSession:
    """Tests for delete_session."""

    @pytest.mark.asyncio
    async def test_delete_session(self):
        client = _make_mock_client()
        service = AgentArtsSessionService(client)

        await service.delete_session(
            app_name="test-app",
            user_id="user-123",
            session_id="session-123",
        )

        client.delete_session.assert_called_once_with(
            space_id="test-app", session_id="session-123"
        )


# ============================================================================
# TestMemoryServiceInit
# ============================================================================


class TestMemoryServiceInit:
    """Tests for AgentArtsMemoryService initialization."""

    def test_init(self):
        client = _make_mock_client()
        service = AgentArtsMemoryService(client)
        assert service._client is client


# ============================================================================
# TestTryAddEvent
# ============================================================================


class TestTryAddEvent:
    """Tests for _try_add_event."""

    @pytest.mark.asyncio
    async def test_try_add_event_success(self):
        client = _make_mock_client()
        service = AgentArtsMemoryService(client)

        event = _make_text_event(event_id="evt-1")
        await service._try_add_event(event, "session-123", "test-app")

        client.add_messages.assert_called_once()
        call_kwargs = client.add_messages.call_args.kwargs
        assert call_kwargs["space_id"] == "test-app"
        assert call_kwargs["session_id"] == "session-123"
        assert call_kwargs["idempotency_key"] == "session-123:evt-1"
        assert call_kwargs["is_force_extract"] is True

    @pytest.mark.asyncio
    async def test_try_add_event_no_id(self):
        """Event with empty id should be assigned a UUID."""
        client = _make_mock_client()
        service = AgentArtsMemoryService(client)

        event = Event(
            author="user",
            content=types.Content(
                role="user", parts=[types.Part(text="Hello")]
            ),
        )
        # Simulate externally constructed Event with no id
        event.id = ""
        await service._try_add_event(event, "session-123", "test-app")

        # Should have an id now
        assert event.id != ""
        assert event.id is not None
        client.add_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_try_add_event_no_content_skips(self):
        """Event with no content should be skipped."""
        client = _make_mock_client()
        service = AgentArtsMemoryService(client)

        event = Event(id="evt-1", author="agent", content=None)
        await service._try_add_event(event, "session-123", "test-app")

        client.add_messages.assert_not_called()

    @pytest.mark.asyncio
    async def test_try_add_event_409_fallback(self):
        """409 Conflict should be silently caught."""
        client = _make_mock_client()
        client.add_messages.side_effect = _make_api_exception(409, "Conflict")

        service = AgentArtsMemoryService(client)
        event = _make_text_event(event_id="evt-1")

        # Should not raise
        await service._try_add_event(event, "session-123", "test-app")

    @pytest.mark.asyncio
    async def test_try_add_event_non_409_raises(self):
        """Non-409 errors should be re-raised."""
        client = _make_mock_client()
        client.add_messages.side_effect = _make_api_exception(500, "Internal error")

        service = AgentArtsMemoryService(client)
        event = _make_text_event(event_id="evt-1")

        with pytest.raises(Exception):
            await service._try_add_event(event, "session-123", "test-app")


# ============================================================================
# TestAddSessionToMemory
# ============================================================================


class TestAddSessionToMemory:
    """Tests for add_session_to_memory."""

    @pytest.mark.asyncio
    async def test_add_session_to_memory(self):
        client = _make_mock_client()
        service = AgentArtsMemoryService(client)

        session = Session(
            id="session-123",
            app_name="test-app",
            user_id="user-123",
            state={},
            events=[
                _make_text_event(event_id="evt-1"),
                _make_text_event(event_id="evt-2"),
            ],
        )

        await service.add_session_to_memory(session)

        # Should be called once per event
        assert client.add_messages.call_count == 2


# ============================================================================
# TestAddEventsToMemory
# ============================================================================


class TestAddEventsToMemory:
    """Tests for add_events_to_memory."""

    @pytest.mark.asyncio
    async def test_add_events_to_memory(self):
        client = _make_mock_client()
        service = AgentArtsMemoryService(client)

        events = [
            _make_text_event(event_id="evt-1"),
            _make_text_event(event_id="evt-2"),
        ]

        await service.add_events_to_memory(
            app_name="test-app",
            user_id="user-123",
            events=events,
            session_id="session-123",
        )

        assert client.add_messages.call_count == 2

    @pytest.mark.asyncio
    async def test_add_events_to_memory_default_session_id(self):
        """Default session_id should be '__unknown_session_id__'."""
        client = _make_mock_client()
        service = AgentArtsMemoryService(client)

        events = [_make_text_event(event_id="evt-1")]

        await service.add_events_to_memory(
            app_name="test-app",
            user_id="user-123",
            events=events,
        )

        call_kwargs = client.add_messages.call_args.kwargs
        assert call_kwargs["session_id"] == "__unknown_session_id__"


# ============================================================================
# TestSearchMemory
# ============================================================================


class TestSearchMemory:
    """Tests for search_memory."""

    @pytest.mark.asyncio
    async def test_search_memory(self):
        client = _make_mock_client()

        mock_response = MagicMock()
        mock_response.results = [
            {
                "record": {"content": "User prefers dark mode", "id": "mem-1"},
                "score": 0.95,
            }
        ]
        client.search_memories.return_value = mock_response

        service = AgentArtsMemoryService(client)
        result = await service.search_memory(
            app_name="test-app",
            user_id="user-123",
            query="user preferences",
        )

        assert len(result.memories) == 1
        assert result.memories[0].id == "mem-1"
        client.search_memories.assert_called_once()

        # Check filter parameters
        call_kwargs = client.search_memories.call_args.kwargs
        assert call_kwargs["space_id"] == "test-app"
        filters = call_kwargs["filters"]
        assert filters.query == "user preferences"
        assert filters.actor_id == "user-123"


# ============================================================================
# TestModuleExports
# ============================================================================


class TestModuleExports:
    """Tests for module exports."""

    def test_import_session_service(self):
        from agentarts.sdk.integration.google_adk import AgentArtsSessionService

        assert AgentArtsSessionService is not None

    def test_import_memory_service(self):
        from agentarts.sdk.integration.google_adk import AgentArtsMemoryService

        assert AgentArtsMemoryService is not None

    def test_import_converter_functions(self):
        from agentarts.sdk.integration.google_adk import (
            event_to_messages,
            message_to_event,
        )

        assert event_to_messages is not None
        assert message_to_event is not None

    def test_all_exports(self):
        from agentarts.sdk.integration.google_adk import __all__

        assert "AgentArtsSessionService" in __all__
        assert "AgentArtsMemoryService" in __all__
        assert "event_to_messages" in __all__
        assert "message_to_event" in __all__
