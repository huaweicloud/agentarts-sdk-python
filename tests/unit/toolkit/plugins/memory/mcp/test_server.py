"""In-process protocol tests for the canonical AgentArts Memory MCP server."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from mcp import Client

from agentarts.toolkit.plugins.memory.agentarts_client import AgentArtsMemoryClient
from agentarts.toolkit.plugins.memory.mcp.config import ServerSettings
from agentarts.toolkit.plugins.memory.mcp.server import (
    DEFAULT_MIN_SCORE,
    DEFAULT_TOP_K,
    MAX_RESULTS,
    create_server,
)

if TYPE_CHECKING:
    from agentarts.sdk.memory import MemoryListFilter, MemorySearchFilter


class FakeMemoryClient:
    def __init__(
        self,
        *,
        search_results: list[object] | None = None,
        list_items: list[object] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.search_results = [] if search_results is None else search_results
        self.list_items = [] if list_items is None else list_items
        self.error = error
        self.search_calls: list[tuple[str, MemorySearchFilter | None]] = []
        self.list_calls: list[tuple[str, int, int, MemoryListFilter | None]] = []
        self.created_sessions: list[tuple[str, str, str]] = []
        self.message_calls: list[tuple[str, str, list[object]]] = []
        self.closed = False

    async def search_memories(
        self, space_id: str, filters: MemorySearchFilter | None = None
    ) -> Any:
        self.search_calls.append((space_id, filters))
        if self.error is not None:
            raise self.error
        return SimpleNamespace(results=self.search_results)

    async def list_memories(
        self,
        space_id: str,
        limit: int = 10,
        offset: int = 0,
        filters: MemoryListFilter | None = None,
    ) -> Any:
        self.list_calls.append((space_id, limit, offset, filters))
        if self.error is not None:
            raise self.error
        return SimpleNamespace(items=self.list_items)

    async def create_memory_session(
        self,
        space_id: str,
        actor_id: str,
        assistant_id: str,
        **_kwargs: Any,
    ) -> Any:
        self.created_sessions.append((space_id, actor_id, assistant_id))
        if self.error is not None:
            raise self.error
        return SimpleNamespace(id="session-123")

    async def add_messages(
        self,
        space_id: str,
        session_id: str,
        messages: list[object],
        **_kwargs: Any,
    ) -> Any:
        self.message_calls.append((space_id, session_id, messages))
        if self.error is not None:
            raise self.error
        return SimpleNamespace()

    async def close(self) -> None:
        self.closed = True


def server_with_fake(
    fake: FakeMemoryClient,
    *,
    actor_id: str | None = "actor-123",
    assistant_id: str | None = "assistant-123",
) -> tuple[Any, dict[str, object]]:
    factory_arguments: dict[str, object] = {}

    def factory(**kwargs: object) -> FakeMemoryClient:
        factory_arguments.update(kwargs)
        return fake

    settings = ServerSettings(
        api_key="secret-api-key",
        space_id="space-123",
        region="cn-north-4",
        actor_id=actor_id,
        assistant_id=assistant_id,
        scope_id="project-a",
        write_assistant_id=assistant_id or "agentarts-memory-agent",
    )
    return create_server(settings, client_factory=factory), factory_arguments


@pytest.mark.asyncio
async def test_server_preserves_existing_tools_and_adds_ltm_search() -> None:
    server, _ = server_with_fake(FakeMemoryClient())

    async with Client(server) as client:
        tools = await client.list_tools()

    assert {tool.name for tool in tools.tools} == {
        "search_memories",
        "add_messages",
        "list_memories",
        "search_summary",
        "ltm_search",
    }
    by_name = {tool.name: tool for tool in tools.tools}
    assert by_name["ltm_search"].input_schema["required"] == ["query"]
    assert by_name["ltm_search"].input_schema["properties"]["top_k"]["default"] == DEFAULT_TOP_K
    assert by_name["ltm_search"].input_schema["properties"]["top_k"]["maximum"] == MAX_RESULTS
    assert by_name["ltm_search"].annotations.read_only_hint is True
    assert by_name["add_messages"].annotations.read_only_hint is False
    assert by_name["add_messages"].annotations.idempotent_hint is False
    assert all(tool.output_schema is not None for tool in tools.tools)


@pytest.mark.asyncio
async def test_ltm_search_delegates_to_bound_scope_and_normalizes() -> None:
    fake = FakeMemoryClient(
        search_results=[
            {
                "record": {
                    "content": "The user prefers window seats.",
                    "strategy_type": "user_preference",
                },
                "score": 0.91,
            },
            {"record": "plain record", "score": 1},
        ]
    )
    server, factory_arguments = server_with_fake(fake)

    async with Client(server) as client:
        result = await client.call_tool(
            "ltm_search", {"query": "  travel preferences  ", "top_k": 2}
        )

    assert result.is_error is False
    assert result.structured_content == {
        "query": "travel preferences",
        "results": [
            {
                "content": "The user prefers window seats.",
                "score": 0.91,
                "strategy_type": "user_preference",
            },
            {"content": "plain record", "score": 1.0, "strategy_type": None},
        ],
    }
    assert factory_arguments == {"region_name": "cn-north-4", "api_key": "secret-api-key"}
    space_id, filters = fake.search_calls[0]
    assert space_id == "space-123"
    assert filters is not None
    assert filters.query == "travel preferences"
    assert filters.actor_id == "actor-123"
    assert filters.assistant_id == "assistant-123"
    assert filters.top_k == 2
    assert filters.min_score is None
    assert fake.closed is True


@pytest.mark.asyncio
async def test_search_memories_preserves_parameters_and_response_shape() -> None:
    fake = FakeMemoryClient(
        search_results=[
            {
                "record": {"content": "likes python", "strategy_type": "semantic"},
                "score": 0.9,
            }
        ]
    )
    server, _ = server_with_fake(fake)

    async with Client(server) as client:
        result = await client.call_tool(
            "search_memories",
            {"query": " python ", "num": 7, "threshold": 0.3},
        )

    assert result.structured_content == {
        "query": "python",
        "results": [{"content": "likes python", "score": 0.9, "type": "semantic"}],
        "total": 1,
    }
    _, filters = fake.search_calls[0]
    assert filters is not None
    assert filters.top_k == 7
    assert filters.min_score == 0.3


@pytest.mark.asyncio
async def test_add_messages_reuses_session_and_preserves_actor_assignment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        AgentArtsMemoryClient,
        "_get_cached_sid_from_file",
        staticmethod(lambda _key: None),
    )
    monkeypatch.setattr(
        AgentArtsMemoryClient,
        "_put_cached_sid_to_file",
        staticmethod(lambda _key, _session_id: None),
    )
    fake = FakeMemoryClient()
    server, _ = server_with_fake(fake)

    async with Client(server) as client:
        first = await client.call_tool(
            "add_messages", {"messages": [{"role": "user", "content": "hello"}]}
        )
        second = await client.call_tool(
            "add_messages", {"messages": [{"role": "assistant", "content": "hi"}]}
        )

    assert first.structured_content == {"session_id": "session-123", "count": 1}
    assert second.structured_content == {"session_id": "session-123", "count": 1}
    assert fake.created_sessions == [("space-123", "actor-123", "assistant-123")]
    assert len(fake.message_calls) == 2
    first_message = fake.message_calls[0][2][0]
    assert first_message.actor_id == "actor-123"
    assert first_message.assistant_id == "assistant-123"


@pytest.mark.asyncio
async def test_list_memories_preserves_shape_and_applies_identity_filter() -> None:
    fake = FakeMemoryClient(
        list_items=[
            SimpleNamespace(
                id="memory-1",
                content="remembered",
                strategy_type="episodic",
                created_at="2026-08-30T00:00:00Z",
            )
        ]
    )
    server, _ = server_with_fake(fake)

    async with Client(server) as client:
        result = await client.call_tool("list_memories", {"limit": 10, "offset": 2})

    assert result.structured_content == {
        "results": [
            {
                "id": "memory-1",
                "content": "remembered",
                "type": "episodic",
                "created_at": "2026-08-30T00:00:00Z",
            }
        ],
        "total": 1,
    }
    space_id, limit, offset, filters = fake.list_calls[0]
    assert (space_id, limit, offset) == ("space-123", 10, 2)
    assert filters is not None
    assert filters.actor_id == "actor-123"
    assert filters.assistant_id == "assistant-123"


@pytest.mark.asyncio
async def test_search_summary_preserves_filter_and_fallback_behavior() -> None:
    fake = FakeMemoryClient(
        search_results=[
            {"record": {"content": "ordinary", "strategy_type": "semantic"}, "score": 0.8}
        ],
        list_items=[
            SimpleNamespace(
                id="memory-1",
                content="summary",
                strategy_type="episodic",
                created_at="now",
            )
        ],
    )
    server, _ = server_with_fake(fake)

    async with Client(server) as client:
        result = await client.call_tool("search_summary", {"query": "context", "num": 3})

    assert result.structured_content == {
        "query": "context",
        "results": [
            {
                "id": "memory-1",
                "content": "summary",
                "score": None,
                "type": "episodic",
                "created_at": "now",
            }
        ],
        "total": 1,
    }
    assert fake.search_calls[0][1].top_k == 9
    assert fake.search_calls[0][1].min_score == DEFAULT_MIN_SCORE
    assert len(fake.list_calls) == 1


@pytest.mark.asyncio
async def test_whitespace_query_and_upstream_errors_are_sanitized() -> None:
    whitespace_server, _ = server_with_fake(FakeMemoryClient())
    async with Client(whitespace_server) as client:
        whitespace = await client.call_tool("ltm_search", {"query": "   "})

    assert whitespace.is_error is True
    assert "non-whitespace" in whitespace.content[0].text

    error_server, _ = server_with_fake(
        FakeMemoryClient(error=RuntimeError("upstream included secret-api-key"))
    )
    async with Client(error_server) as client:
        failure = await client.call_tool("search_memories", {"query": "preferences"})

    assert failure.is_error is True
    assert "check the server logs" in failure.content[0].text
    assert "secret-api-key" not in failure.content[0].text


def test_server_warns_when_actor_is_absent(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(
        logging.WARNING,
        logger="agentarts.toolkit.plugins.memory.mcp.server",
    ):
        server_with_fake(FakeMemoryClient(), actor_id=None)

    assert "AGENTARTS_MEMORY_ACTOR_ID is not set" in caplog.text
    assert "searches will include all actors" in caplog.text
