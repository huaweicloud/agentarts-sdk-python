"""Async Memory SDK tests (ALLOW_CREATE tier).

Exercises ``AsyncMemoryClient``'s async data-plane methods against the shared
session Space. Setup (session + seeded messages) is done once via the *sync*
client to avoid async-fixture/event-loop-scope complexity; the async tests
then only read — cheap and isolated.
"""

from __future__ import annotations

import pytest

from agentarts.sdk import AsyncMemoryClient, MemoryClient
from agentarts.sdk.memory import MemorySearchFilter, TextMessage

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def async_setup(memory_space):
    """Seed a session + two messages via the sync client (one-time, module scope)."""
    sync = MemoryClient(api_key=memory_space.api_key)
    session = sync.create_memory_session(
        space_id=memory_space.id, actor_id="aa-it-async-actor"
    )
    batch = sync.add_messages(
        space_id=memory_space.id,
        session_id=session.id,
        messages=[
            TextMessage(role="user", content="async hello"),
            TextMessage(role="assistant", content="async echo: hello"),
        ],
        is_force_extract=False,
    )
    return {
        "space_id": memory_space.id,
        "session_id": session.id,
        "msg_ids": [m.id for m in batch.items],
    }


def _client(memory_space) -> AsyncMemoryClient:
    return AsyncMemoryClient(api_key=memory_space.api_key)


@pytest.mark.asyncio
async def test_async_get_last_k_messages(memory_space, async_setup):
    client = _client(memory_space)
    try:
        msgs = await client.get_last_k_messages(
            session_id=async_setup["session_id"], k=2, space_id=async_setup["space_id"]
        )
    finally:
        await client.close()
    assert len(msgs) == 2


@pytest.mark.asyncio
async def test_async_list_messages(memory_space, async_setup):
    client = _client(memory_space)
    try:
        result = await client.list_messages(
            space_id=async_setup["space_id"],
            session_id=async_setup["session_id"],
            limit=10,
        )
    finally:
        await client.close()
    assert result.total >= 2


@pytest.mark.asyncio
async def test_async_get_message(memory_space, async_setup):
    client = _client(memory_space)
    try:
        msg = await client.get_message(
            message_id=async_setup["msg_ids"][0],
            space_id=async_setup["space_id"],
            session_id=async_setup["session_id"],
        )
    finally:
        await client.close()
    assert msg.id == async_setup["msg_ids"][0]


@pytest.mark.asyncio
async def test_async_search_memories(memory_space, async_setup):
    client = _client(memory_space)
    try:
        result = await client.search_memories(
            space_id=async_setup["space_id"],
            filters=MemorySearchFilter(query="hello", top_k=3),
        )
    finally:
        await client.close()
    assert isinstance(result.results, list)
    assert result.total >= 0


@pytest.mark.asyncio
async def test_async_list_memories(memory_space, async_setup):
    client = _client(memory_space)
    try:
        result = await client.list_memories(space_id=async_setup["space_id"], limit=10)
    finally:
        await client.close()
    assert isinstance(result.items, list)
    assert result.total >= 0


@pytest.mark.asyncio
async def test_async_delete_memory_if_any(memory_space, async_setup):
    client = _client(memory_space)
    try:
        result = await client.list_memories(space_id=async_setup["space_id"], limit=10)
        if not result.items:
            pytest.skip("no extracted memories to delete in async path")
        await client.delete_memory(
            space_id=async_setup["space_id"], memory_id=result.items[0].id
        )
    finally:
        await client.close()
