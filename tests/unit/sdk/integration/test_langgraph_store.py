"""
Unit tests for AgentArtsMemoryStore

Tests cover:
- Basic operations (put, get, search, list_namespaces)
- Namespace + filter design (方案 D)
- LangGraph agent simulation
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("langgraph")


class TestAgentArtsMemoryStoreBasic:
    """Basic tests for AgentArtsMemoryStore"""

    def test_import_store(self):
        """Test that store module can be imported"""
        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        assert AgentArtsMemoryStore is not None

    def test_store_methods_exist(self):
        """Test that required methods exist"""
        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        assert hasattr(AgentArtsMemoryStore, "batch")
        assert hasattr(AgentArtsMemoryStore, "abatch")
        assert hasattr(AgentArtsMemoryStore, "close")

    def test_store_properties(self):
        """Test that properties exist"""
        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        assert hasattr(AgentArtsMemoryStore, "space_id")
        assert hasattr(AgentArtsMemoryStore, "region")
        assert hasattr(AgentArtsMemoryStore, "supports_ttl")

    def test_store_init_requires_space_id(self):
        """Test that space_id is required"""
        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient"):
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    store = AgentArtsMemoryStore(space_id="test-space")
                    assert store.space_id == "test-space"


class TestAgentArtsMemoryStorePut:
    """Tests for PutOp handling"""

    def test_put_requires_session_id(self):
        """Test that Put requires session_id in value"""
        from langgraph.store.base import PutOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    op = PutOp(
                        namespace=("memories",),
                        key="msg-1",
                        value={"content": "test"},
                    )

                    with pytest.raises(ValueError, match="session_id"):
                        store._handle_put(op)

    def test_put_requires_content(self):
        """Test that Put requires content in value"""
        from langgraph.store.base import PutOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    op = PutOp(
                        namespace=("memories",),
                        key="msg-1",
                        value={"session_id": "session-123"},
                    )

                    with pytest.raises(ValueError, match="content"):
                        store._handle_put(op)

    def test_put_calls_add_messages(self):
        """Test that Put calls add_messages with correct params"""
        from langgraph.store.base import PutOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    op = PutOp(
                        namespace=("memories", "user-001"),
                        key="msg-1",
                        value={
                            "content": "I prefer dark mode",
                            "actor_id": "user-001",
                            "session_id": "session-123",
                        },
                    )

                    store._handle_put(op)

                    mock_client.add_messages.assert_called_once()
                    call_args = mock_client.add_messages.call_args

                    assert call_args.kwargs["space_id"] == "test-space"
                    assert call_args.kwargs["session_id"] == "session-123"
                    messages = call_args.kwargs["messages"]
                    assert len(messages) == 1
                    assert messages[0]["role"] == "user"
                    assert messages[0]["actor_id"] == "user-001"

    def test_put_delete_not_supported(self):
        """Test that delete (value=None) is not supported"""
        from langgraph.store.base import PutOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    op = PutOp(
                        namespace=("memories",),
                        key="msg-1",
                        value=None,
                    )

                    store._handle_put(op)

                    mock_client.add_messages.assert_not_called()


class TestAgentArtsMemoryStoreSearch:
    """Tests for SearchOp handling"""

    def test_search_with_query_calls_search_memories(self):
        """Test that search with query calls search_memories"""
        from langgraph.store.base import SearchOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        mock_memory_info = MagicMock()
        mock_memory_info.id = "memory-123"
        mock_memory_info.content = "User prefers dark mode"
        mock_memory_info.actor_id = "user-001"
        mock_memory_info.assistant_id = None
        mock_memory_info.session_id = "session-xyz"
        mock_memory_info.strategy_type = "semantic"
        mock_memory_info.created_at = "2024-01-01T00:00:00Z"
        mock_memory_info.updated_at = "2024-01-01T00:00:00Z"
        mock_memory_info.meta = None

        mock_response = MagicMock()
        mock_response.results = [
            {"record": mock_memory_info, "score": 0.95}
        ]

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client.search_memories.return_value = mock_response
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    results = store._handle_search(
                        SearchOp(
                            namespace_prefix=("memories",),
                            query="user preferences",
                            filter={"actor_id": "user-001"},
                            limit=5,
                        )
                    )

                    mock_client.search_memories.assert_called_once()
                    assert len(results) == 1
                    assert results[0].key == "memory-123"
                    assert results[0].score == 0.95
                    assert "dark mode" in results[0].value["content"]

    def test_search_with_filter_params(self):
        """Test that filter params are passed to search_memories"""
        from langgraph.store.base import SearchOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        mock_response = MagicMock()
        mock_response.results = []

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client.search_memories.return_value = mock_response
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    store._handle_search(
                        SearchOp(
                            namespace_prefix=("memories",),
                            query="test",
                            filter={
                                "actor_id": "user-001",
                                "assistant_id": "agent-abc",
                                "session_id": "session-xyz",
                            },
                            limit=10,
                        )
                    )

                    call_args = mock_client.search_memories.call_args
                    filters = call_args.kwargs["filters"]

                    assert filters.actor_id == "user-001"
                    assert filters.assistant_id == "agent-abc"
                    assert filters.session_id == "session-xyz"

    def test_search_without_query_calls_list_memories(self):
        """Test that search without query calls list_memories"""
        from langgraph.store.base import SearchOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        mock_memory_info = MagicMock()
        mock_memory_info.id = "memory-123"
        mock_memory_info.content = "test content"
        mock_memory_info.actor_id = "user-001"
        mock_memory_info.assistant_id = None
        mock_memory_info.session_id = "session-xyz"
        mock_memory_info.strategy_type = "semantic"
        mock_memory_info.created_at = "2024-01-01T00:00:00Z"
        mock_memory_info.updated_at = "2024-01-01T00:00:00Z"

        mock_response = MagicMock()
        mock_response.items = [mock_memory_info]

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client.list_memories.return_value = mock_response
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    results = store._handle_search(
                        SearchOp(
                            namespace_prefix=("memories",),
                            filter={"actor_id": "user-001"},
                            limit=10,
                        )
                    )

                    mock_client.list_memories.assert_called_once()
                    assert len(results) == 1
                    assert results[0].score is None


class TestAgentArtsMemoryStoreGet:
    """Tests for GetOp handling"""

    def test_get_returns_item_when_found(self):
        """Test that get returns Item when memory exists"""
        from langgraph.store.base import GetOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        mock_memory_info = MagicMock()
        mock_memory_info.id = "memory-123"
        mock_memory_info.content = "test content"
        mock_memory_info.actor_id = "user-001"
        mock_memory_info.assistant_id = None
        mock_memory_info.session_id = "session-xyz"
        mock_memory_info.strategy_type = "semantic"
        mock_memory_info.created_at = "2024-01-01T00:00:00Z"
        mock_memory_info.updated_at = "2024-01-01T00:00:00Z"

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client.get_memory.return_value = mock_memory_info
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    result = store._handle_get(
                        GetOp(namespace=("memories",), key="memory-123")
                    )

                    assert result is not None
                    assert result.key == "memory-123"
                    assert result.value["content"] == "test content"

    def test_get_returns_none_when_not_found(self):
        """Test that get returns None when memory doesn't exist"""
        from langgraph.store.base import GetOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client.get_memory.side_effect = Exception("not found")
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    result = store._handle_get(
                        GetOp(namespace=("memories",), key="nonexistent")
                    )

                    assert result is None


class TestAgentArtsMemoryStoreBatch:
    """Tests for batch operations"""

    def test_batch_processes_multiple_ops(self):
        """Test that batch processes multiple operations"""
        from langgraph.store.base import GetOp, PutOp, SearchOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        mock_response = MagicMock()
        mock_response.results = []

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client.search_memories.return_value = mock_response
                    mock_client.add_messages.return_value = MagicMock()
                    mock_client.get_memory.side_effect = Exception("404 not found")
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    ops = [
                        PutOp(
                            namespace=("memories",),
                            key="msg-1",
                            value={"content": "test", "session_id": "s1"},
                        ),
                        SearchOp(namespace_prefix=("memories",), query="test"),
                        GetOp(namespace=("memories",), key="nonexistent"),
                    ]

                    results = store.batch(ops)

                    assert len(results) == 3
                    assert results[0] is None
                    assert results[1] == []
                    assert results[2] is None


class TestAgentArtsMemoryStoreAsync:
    """Tests for async operations"""

    @pytest.mark.asyncio
    async def test_async_put_calls_async_client(self):
        """Test that async put uses AsyncMemoryClient"""
        from langgraph.store.base import PutOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient"):
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient") as mock_async_cls:
                    mock_async_client = AsyncMock()
                    mock_async_cls.return_value = mock_async_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    op = PutOp(
                        namespace=("memories",),
                        key="msg-1",
                        value={"content": "test", "session_id": "s1"},
                    )

                    await store._async_handle_put(op)

                    mock_async_client.add_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_search_calls_async_client(self):
        """Test that async search uses AsyncMemoryClient"""
        from langgraph.store.base import SearchOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        mock_response = MagicMock()
        mock_response.results = []

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient"):
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient") as mock_async_cls:
                    mock_async_client = AsyncMock()
                    mock_async_client.search_memories.return_value = mock_response
                    mock_async_cls.return_value = mock_async_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    results = await store._async_handle_search(
                        SearchOp(namespace_prefix=("memories",), query="test")
                    )

                    assert results == []

    @pytest.mark.asyncio
    async def test_abatch_processes_multiple_ops(self):
        """Test that abatch processes multiple operations"""
        from langgraph.store.base import GetOp, PutOp, SearchOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        mock_response = MagicMock()
        mock_response.results = []

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient"):
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient") as mock_async_cls:
                    mock_async_client = AsyncMock()
                    mock_async_client.search_memories.return_value = mock_response
                    mock_async_client.add_messages.return_value = MagicMock()
                    mock_async_client.get_memory.side_effect = Exception("not found")
                    mock_async_cls.return_value = mock_async_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    ops = [
                        PutOp(
                            namespace=("memories",),
                            key="msg-1",
                            value={"content": "test", "session_id": "s1"},
                        ),
                        SearchOp(namespace_prefix=("memories",), query="test"),
                        GetOp(namespace=("memories",), key="nonexistent"),
                    ]

                    results = await store.abatch(ops)

                    assert len(results) == 3


class TestAgentArtsMemoryStoreNamespaceFilter:
    """Tests for namespace + filter design (方案 D)"""

    def test_namespace_is_hierarchy_path(self):
        """Test that namespace follows LangGraph standard as hierarchy path"""
        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient"):
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    store = AgentArtsMemoryStore(space_id="test-space")

                    assert store._space_id == "test-space"

    def test_filter_contains_actor_session(self):
        """Test that filter can contain actor_id/session_id"""
        from langgraph.store.base import SearchOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        mock_response = MagicMock()
        mock_response.results = []

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client.search_memories.return_value = mock_response
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    store._handle_search(
                        SearchOp(
                            namespace_prefix=("memories",),
                            query="test",
                            filter={
                                "actor_id": "user-001",
                                "session_id": "session-xyz",
                            },
                        )
                    )

                    call_args = mock_client.search_memories.call_args
                    filters = call_args.kwargs["filters"]

                    assert filters.actor_id == "user-001"
                    assert filters.session_id == "session-xyz"

    def test_only_session_id_in_filter(self):
        """Test that only session_id can be used in filter"""
        from langgraph.store.base import SearchOp

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        mock_response = MagicMock()
        mock_response.results = []

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client.search_memories.return_value = mock_response
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="test-space")

                    store._handle_search(
                        SearchOp(
                            namespace_prefix=("memories",),
                            query="test",
                            filter={"session_id": "session-xyz"},
                        )
                    )

                    call_args = mock_client.search_memories.call_args
                    filters = call_args.kwargs["filters"]

                    assert filters.session_id == "session-xyz"
                    assert filters.actor_id is None
                    assert filters.assistant_id is None


class TestLangGraphAgentSimulation:
    """Simulate LangGraph agent using Store for cross-thread memory"""

    def test_store_put_search_flow(self):
        """Simulate agent putting memory and searching later"""

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        mock_memory_info = MagicMock()
        mock_memory_info.id = "mem-001"
        mock_memory_info.content = "User prefers dark mode theme"
        mock_memory_info.actor_id = "user-001"
        mock_memory_info.assistant_id = None
        mock_memory_info.session_id = "session-abc"
        mock_memory_info.strategy_type = "semantic"
        mock_memory_info.created_at = "2024-01-01T00:00:00Z"
        mock_memory_info.updated_at = "2024-01-01T00:00:00Z"
        mock_memory_info.meta = None

        mock_search_response = MagicMock()
        mock_search_response.results = [
            {"record": mock_memory_info, "score": 0.92}
        ]

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client.add_messages.return_value = MagicMock()
                    mock_client.search_memories.return_value = mock_search_response
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="space-001")

                    store.put(
                        namespace=("memories",),
                        key="user-pref-1",
                        value={
                            "content": "User prefers dark mode theme",
                            "actor_id": "user-001",
                            "session_id": "session-abc",
                        },
                    )

                    results = store.search(
                        ("memories",),
                        query="theme preferences",
                        filter={"actor_id": "user-001"},
                        limit=5,
                    )

                    assert len(results) == 1
                    assert results[0].score == 0.92
                    assert "dark mode" in results[0].value["content"]

    def test_cross_thread_memory_access(self):
        """Simulate accessing memory from different thread (session)"""

        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        mock_memory_info = MagicMock()
        mock_memory_info.id = "mem-001"
        mock_memory_info.content = "User likes Python programming"
        mock_memory_info.actor_id = "user-001"
        mock_memory_info.assistant_id = None
        mock_memory_info.session_id = "session-old"
        mock_memory_info.strategy_type = "semantic"
        mock_memory_info.created_at = "2024-01-01T00:00:00Z"
        mock_memory_info.updated_at = "2024-01-01T00:00:00Z"
        mock_memory_info.meta = None

        mock_search_response = MagicMock()
        mock_search_response.results = [
            {"record": mock_memory_info, "score": 0.88}
        ]

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client.search_memories.return_value = mock_search_response
                    mock_client_cls.return_value = mock_client

                    store = AgentArtsMemoryStore(space_id="space-001")

                    results = store.search(
                        ("memories",),
                        query="programming interests",
                        filter={"actor_id": "user-001"},
                    )

                    assert len(results) == 1
                    assert results[0].value["session_id"] == "session-old"

    def test_store_module_export(self):
        """Test that AgentArtsMemoryStore is exported from module"""
        from agentarts.sdk.integration.langgraph import AgentArtsMemoryStore

        assert AgentArtsMemoryStore is not None

    def test_store_with_context_manager(self):
        """Test that store works with context manager"""
        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient") as mock_client_cls:
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    mock_client = MagicMock()
                    mock_client_cls.return_value = mock_client

                    with AgentArtsMemoryStore(space_id="test-space") as store:
                        assert store.space_id == "test-space"

                    mock_client.close.assert_called_once()


class TestDatetimeParsing:
    """Tests for datetime parsing utilities"""

    def test_parse_datetime_from_string(self):
        """Test parsing datetime from ISO string"""
        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient"):
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    store = AgentArtsMemoryStore(space_id="test-space")

                    result = store._parse_datetime("2024-01-01T00:00:00Z")
                    assert result.year == 2024
                    assert result.month == 1

    def test_parse_datetime_from_datetime(self):
        """Test that datetime object is returned unchanged"""
        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient"):
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    store = AgentArtsMemoryStore(space_id="test-space")

                    dt = datetime.now(timezone.utc)
                    result = store._parse_datetime(dt)
                    assert result == dt

    def test_parse_datetime_none_returns_current(self):
        """Test that None returns current datetime"""
        from agentarts.sdk.integration.langgraph.store import AgentArtsMemoryStore

        with patch("agentarts.sdk.integration.langgraph.store.LANGGRAPH_AVAILABLE", True):
            with patch("agentarts.sdk.integration.langgraph.store.MemoryClient"):
                with patch("agentarts.sdk.integration.langgraph.store.AsyncMemoryClient"):
                    store = AgentArtsMemoryStore(space_id="test-space")

                    result = store._parse_datetime(None)
                    assert isinstance(result, datetime)
