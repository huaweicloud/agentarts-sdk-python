"""In-process tests for the MCP server and ltm_search tool."""

import logging
from types import SimpleNamespace
from typing import Any

import pytest
from agentarts.sdk.memory import MemorySearchFilter
from mcp import Client

from agentarts_memory_mcp.config import ServerSettings
from agentarts_memory_mcp.server import DEFAULT_TOP_K, MAX_TOP_K, create_server


class FakeMemoryClient:
    def __init__(self, *, results: list[object] | None = None, error: Exception | None = None):
        self.results = [] if results is None else results
        self.error = error
        self.calls: list[tuple[str, MemorySearchFilter | None]] = []
        self.closed = False

    async def search_memories(
        self,
        space_id: str,
        filters: MemorySearchFilter | None = None,
    ) -> Any:
        self.calls.append((space_id, filters))
        if self.error is not None:
            raise self.error
        return SimpleNamespace(results=self.results)

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
    )
    return create_server(settings, client_factory=factory), factory_arguments


@pytest.mark.asyncio
async def test_server_exposes_only_read_only_ltm_search() -> None:
    server, _ = server_with_fake(FakeMemoryClient())

    async with Client(server) as client:
        tools = await client.list_tools()

    assert [tool.name for tool in tools.tools] == ["ltm_search"]
    tool = tools.tools[0]
    assert tool.input_schema["required"] == ["query"]
    assert tool.input_schema["properties"]["top_k"]["default"] == DEFAULT_TOP_K
    assert tool.input_schema["properties"]["top_k"]["maximum"] == MAX_TOP_K
    assert tool.annotations is not None
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.destructive_hint is False
    assert tool.output_schema is not None


@pytest.mark.asyncio
async def test_ltm_search_delegates_to_bound_space_and_normalizes_results() -> None:
    fake = FakeMemoryClient(
        results=[
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
            "ltm_search",
            {"query": "  travel preferences  ", "top_k": 2},
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
            {
                "content": "plain record",
                "score": 1.0,
                "strategy_type": None,
            },
        ],
    }
    assert factory_arguments == {
        "region_name": "cn-north-4",
        "api_key": "secret-api-key",
    }
    assert len(fake.calls) == 1
    space_id, filters = fake.calls[0]
    assert space_id == "space-123"
    assert filters is not None
    assert filters.query == "travel preferences"
    assert filters.actor_id == "actor-123"
    assert filters.assistant_id == "assistant-123"
    assert filters.top_k == 2
    assert fake.closed is True


@pytest.mark.asyncio
async def test_ltm_search_uses_default_top_k() -> None:
    fake = FakeMemoryClient()
    server, _ = server_with_fake(fake)

    async with Client(server) as client:
        await client.call_tool("ltm_search", {"query": "preferences"})

    _, filters = fake.calls[0]
    assert filters is not None
    assert filters.top_k == DEFAULT_TOP_K


@pytest.mark.asyncio
async def test_ltm_search_does_not_filter_by_optional_ids_when_absent() -> None:
    fake = FakeMemoryClient()
    server, _ = server_with_fake(fake, actor_id=None, assistant_id=None)

    async with Client(server) as client:
        await client.call_tool("ltm_search", {"query": "preferences"})

    _, filters = fake.calls[0]
    assert filters is not None
    assert filters.actor_id is None
    assert filters.assistant_id is None


def test_server_warns_when_actor_id_is_absent(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="agentarts_memory_mcp.server"):
        server_with_fake(FakeMemoryClient(), actor_id=None)

    assert "AGENTARTS_MEMORY_ACTOR_ID is not set" in caplog.text
    assert "searches will include all actors" in caplog.text


@pytest.mark.asyncio
async def test_ltm_search_rejects_whitespace_query() -> None:
    server, _ = server_with_fake(FakeMemoryClient())

    async with Client(server) as client:
        result = await client.call_tool("ltm_search", {"query": "   "})

    assert result.is_error is True
    assert "non-whitespace" in result.content[0].text


@pytest.mark.asyncio
async def test_ltm_search_sanitizes_upstream_errors() -> None:
    server, _ = server_with_fake(
        FakeMemoryClient(error=RuntimeError("upstream included secret-api-key"))
    )

    async with Client(server) as client:
        result = await client.call_tool("ltm_search", {"query": "preferences"})

    assert result.is_error is True
    assert "check the server logs" in result.content[0].text
    assert "secret-api-key" not in result.content[0].text
