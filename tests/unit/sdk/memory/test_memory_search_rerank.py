"""Verify rerank kwargs reach the search HTTP request in every public entry point."""

import inspect
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agentarts.sdk.memory import (
    AsyncMemoryClient,
    AsyncMemorySession,
    MemoryClient,
    MemorySearchFilter,
    MemorySession,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "client_type", [MemoryClient, MemorySession, AsyncMemoryClient, AsyncMemorySession]
)
@pytest.mark.parametrize(
    "filter_kwargs",
    [{}, {"rerank": None}, {"rerank": True}, {"rerank": False}],
    ids=["omitted", "none", "enabled", "disabled"],
)
async def test_rerank_in_search_request(client_type, filter_kwargs):
    session_mode = client_type in (MemorySession, AsyncMemorySession)
    asynchronous = client_type in (AsyncMemoryClient, AsyncMemorySession)
    options = {"api_key": "test-key", "region_name": "cn-southwest-2"}
    if session_mode:
        options.update(space_id="space-1", session_id="session-1", actor_id="actor-1")
    client = client_type(**options)
    plane = client._async_data_plane if asynchronous else client._data_plane
    try:
        with patch.object(
            plane.client, "_make_request", new_callable=AsyncMock if asynchronous else Mock
        ) as request:
            request.return_value = {"records": [], "total": 0}
            filters = MemorySearchFilter(query="user preferences", top_k=5, **filter_kwargs)
            scope = {} if session_mode else {"space_id": "space-1"}
            result = client.search_memories(filters=filters, **scope)
            if inspect.isawaitable(result):
                result = await result

            expected = {"query": "user preferences", "top_k": 5, "only_actived": False}
            if filter_kwargs.get("rerank") is not None:
                expected["rerank"] = filter_kwargs["rerank"]
            request.assert_called_once_with(
                method="POST",
                path="/v1/core/spaces/space-1/memories/search",
                data=expected,
                space_id="space-1",
            )
            payload = request.call_args.kwargs["data"]
            if "rerank" in expected:
                assert payload["rerank"] is filter_kwargs["rerank"]
            assert result.total == 0
            assert result.results == []
    finally:
        closed = client.close()
        if inspect.isawaitable(closed):
            await closed
