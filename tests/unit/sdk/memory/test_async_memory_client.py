"""Unit tests for AsyncMemoryClient"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agentarts.sdk.memory import (
    AsyncMemoryClient,
    AsyncMemorySession,
    MemorySearchFilter,
    MemorySearchResponse,
    MessageBatchResponse,
    MessageInfo,
    MessageListResponse,
    SessionInfo,
    TextMessage,
)


class TestAsyncMemoryClient:
    """Tests for AsyncMemoryClient."""

    def test_init_with_api_key(self):
        client = AsyncMemoryClient(api_key="test-api-key")
        assert client._async_data_plane is not None
        assert client._control_plane is None

    def test_init_with_region(self):
        client = AsyncMemoryClient(region_name="cn-north-4", api_key="test-key")
        assert client.region_name == "cn-north-4"

    @pytest.mark.asyncio
    async def test_close_async(self):
        client = AsyncMemoryClient(api_key="test-key")

        mock_close = AsyncMock()
        client._async_data_plane.close = mock_close

        await client.close()

        mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        mock_close = AsyncMock()

        async with AsyncMemoryClient(api_key="test-key") as client:
            client._async_data_plane.close = mock_close

        mock_close.assert_called_once()


class TestAsyncMemoryClientDataPlane:
    """Tests for AsyncMemoryClient data plane methods."""

    @pytest.mark.asyncio
    async def test_add_messages_success(self):
        client = AsyncMemoryClient(api_key="test-key")

        mock_result = {
            "messages": [{"id": "msg-1", "session_id": "session-456", "seq": 1, "role": "user", "parts": [{"text": "hello"}]}],
        }
        mock_add = AsyncMock(return_value=MessageBatchResponse.from_dict(mock_result))
        client._async_data_plane.add_messages = mock_add

        result = await client.add_messages(
            space_id="space-123",
            session_id="session-456",
            messages=[TextMessage(role="user", content="hello")],
        )

        assert len(result.items) == 1
        mock_add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_messages_with_options(self):
        client = AsyncMemoryClient(api_key="test-key")

        mock_result = {"messages": []}
        mock_add = AsyncMock(return_value=MessageBatchResponse.from_dict(mock_result))
        client._async_data_plane.add_messages = mock_add

        await client.add_messages(
            space_id="space-123",
            session_id="session-456",
            messages=[TextMessage(role="user", content="test")],
            timestamp=123456789,
            idempotency_key="key-123",
            is_force_extract=True,
        )

        call_kwargs = mock_add.call_args.kwargs
        assert call_kwargs["timestamp"] == 123456789
        assert call_kwargs["idempotency_key"] == "key-123"
        assert call_kwargs["is_force_extract"] is True

    @pytest.mark.asyncio
    async def test_search_memories_success(self):
        client = AsyncMemoryClient(api_key="test-key")

        mock_result = {
            "records": [{"id": "mem-1", "space_id": "space-123", "strategy_id": "str-1", "content": "test", "score": 0.9}],
            "total": 1,
        }
        mock_search = AsyncMock(return_value=MemorySearchResponse.from_dict(mock_result))
        client._async_data_plane.search_memories = mock_search

        filters = MemorySearchFilter(query="test query", top_k=5)
        result = await client.search_memories(space_id="space-123", filters=filters)

        assert result.total == 1
        mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_last_k_messages_success(self):
        client = AsyncMemoryClient(api_key="test-key")

        mock_messages = [
            MessageInfo(id="msg-1", session_id="session-456", seq=1, role="user", parts=[{"text": "hello"}]),
            MessageInfo(id="msg-2", session_id="session-456", seq=2, role="assistant", parts=[{"text": "response"}]),
        ]
        mock_get = AsyncMock(return_value=mock_messages)
        client._async_data_plane.get_last_k_messages = mock_get

        result = await client.get_last_k_messages(
            session_id="session-456",
            k=10,
            space_id="space-123",
        )

        assert len(result) == 2
        mock_get.assert_called_once_with("session-456", 10, "space-123")

    @pytest.mark.asyncio
    async def test_list_messages_success(self):
        client = AsyncMemoryClient(api_key="test-key")

        mock_result = {
            "items": [{"id": "msg-1", "session_id": "session-456", "seq": 1, "role": "user", "parts": []}],
            "total": 1,
        }
        mock_list = AsyncMock(return_value=MessageListResponse.from_dict(mock_result))
        client._async_data_plane.list_messages = mock_list

        result = await client.list_messages(
            space_id="space-123",
            session_id="session-456",
            limit=10,
            offset=0,
        )

        assert result.total == 1
        mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_memory_success(self):
        client = AsyncMemoryClient(api_key="test-key")

        mock_result = {"id": "mem-1", "space_id": "space-123", "strategy_id": "str-1", "content": "test memory"}
        from agentarts.sdk.memory.inner.config import MemoryInfo
        mock_get = AsyncMock(return_value=MemoryInfo.from_dict(mock_result))
        client._async_data_plane.get_memory = mock_get

        result = await client.get_memory(space_id="space-123", memory_id="mem-1")

        assert result.id == "mem-1"
        mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_memory_success(self):
        client = AsyncMemoryClient(api_key="test-key")

        mock_delete = AsyncMock()
        client._async_data_plane.delete_memory = mock_delete

        await client.delete_memory(space_id="space-123", memory_id="mem-1")

        mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_memory_session_success(self):
        client = AsyncMemoryClient(api_key="test-key")

        mock_result = {"id": "session-123", "space_id": "space-123", "actor_id": "user-1"}
        mock_create = AsyncMock(return_value=SessionInfo.from_dict(mock_result))
        client._async_data_plane.create_memory_session = mock_create

        result = await client.create_memory_session(
            space_id="space-123",
            actor_id="user-1",
        )

        assert result.id == "session-123"
        mock_create.assert_called_once()


class TestAsyncMemoryClientUnsupportedMessage:
    """Tests for unsupported message types."""

    @pytest.mark.asyncio
    async def test_add_messages_unsupported_type_raises_error(self):
        client = AsyncMemoryClient(api_key="test-key")

        with pytest.raises(ValueError, match="Unsupported message type"):
            await client.add_messages(
                space_id="space-123",
                session_id="session-456",
                messages=[{"invalid": "message"}],
            )


class TestAsyncMemorySession:
    """Tests for AsyncMemorySession."""

    @pytest.mark.asyncio
    async def test_session_with_existing_session_id(self):
        mock_data_plane = MagicMock()
        mock_data_plane.close = AsyncMock()

        session = AsyncMemorySession(
            space_id="space-123",
            actor_id="user-1",
            session_id="session-456",
            api_key="test-key",
        )
        session._async_data_plane = mock_data_plane

        await session._ensure_initialized()

        assert session.session_id == "session-456"
        assert session._initialized is True

    @pytest.mark.asyncio
    async def test_session_auto_create(self):
        mock_data_plane = MagicMock()
        mock_data_plane.create_memory_session = AsyncMock(
            return_value=SessionInfo(id="new-session-123", space_id="space-123", actor_id="user-1")
        )
        mock_data_plane.close = AsyncMock()

        session = AsyncMemorySession(
            space_id="space-123",
            actor_id="user-1",
            api_key="test-key",
        )
        session._async_data_plane = mock_data_plane

        await session._ensure_initialized()

        assert session.session_id == "new-session-123"
        mock_data_plane.create_memory_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_add_messages(self):
        mock_data_plane = MagicMock()
        mock_data_plane.create_memory_session = AsyncMock(
            return_value=SessionInfo(id="session-123", space_id="space-123", actor_id="user-1")
        )
        mock_data_plane.add_messages = AsyncMock(
            return_value=MessageBatchResponse(items=[])
        )
        mock_data_plane.close = AsyncMock()

        session = AsyncMemorySession(
            space_id="space-123",
            actor_id="user-1",
            api_key="test-key",
        )
        session._async_data_plane = mock_data_plane

        await session.add_messages([TextMessage(role="user", content="hello")])

        mock_data_plane.add_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        mock_data_plane = MagicMock()
        mock_data_plane.create_memory_session = AsyncMock(
            return_value=SessionInfo(id="session-123", space_id="space-123", actor_id="user-1")
        )
        mock_data_plane.close = AsyncMock()

        async with AsyncMemorySession(
            space_id="space-123",
            actor_id="user-1",
            session_id="session-456",
            api_key="test-key",
        ) as session:
            session._async_data_plane = mock_data_plane

        mock_data_plane.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_factory_method(self):
        session = AsyncMemorySession.of(
            space_id="space-123",
            actor_id="user-1",
            session_id="session-456",
            api_key="test-key",
        )

        assert session.space_id == "space-123"
        assert session.actor_id == "user-1"


class TestAsyncDataPlaneValidation:
    """Tests for AsyncDataPlane validation."""

    @pytest.mark.asyncio
    async def test_add_messages_empty_space_id_raises_error(self):
        from agentarts.sdk.memory.inner.dataplane_async import _AsyncDataPlane

        data_plane = _AsyncDataPlane(api_key="test-key")

        with pytest.raises(ValueError, match="space_id is required"):
            await data_plane.add_messages(
                space_id="",
                session_id="session-456",
                messages=[{"role": "user"}],
            )

    @pytest.mark.asyncio
    async def test_get_last_k_messages_empty_space_id_raises_error(self):
        from agentarts.sdk.memory.inner.dataplane_async import _AsyncDataPlane

        data_plane = _AsyncDataPlane(api_key="test-key")

        with pytest.raises(ValueError, match="space_id is required"):
            await data_plane.get_last_k_messages(
                session_id="session-456",
                k=10,
                space_id="",
            )
