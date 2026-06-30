"""Memory SDK lifecycle tests (ALLOW_CREATE tier).

Self-contained: creates a Space (which mints its own data-plane API key), uses
that key for session/message/memory ops, then deletes the Space — which
cascades to all sessions/messages/memories. No pre-existing memory API key
required; only AK/SK for the control-plane Space CRUD.
"""

from __future__ import annotations

import pytest

from agentarts.sdk import MemoryClient
from agentarts.sdk.memory import MemorySearchFilter, TextMessage

pytestmark = pytest.mark.integration


# --------------------------------------------------------------------------- #
# Shared resources (Space is session-scoped in conftest; per-module data
# client + session + seeded messages are created once here, cleaned up via
# the Space's session-end cascade delete.)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def memory_data_client(memory_space):
    """Data-plane client authenticated with the Space's own API key."""
    return MemoryClient(api_key=memory_space.api_key)


@pytest.fixture(scope="module")
def memory_session(memory_data_client, memory_space):
    return memory_data_client.create_memory_session(
        space_id=memory_space.id, actor_id="aa-it-actor"
    )


@pytest.fixture(scope="module")
def seeded_messages(memory_data_client, memory_space, memory_session):
    """Add two text messages once; reused by read-path tests."""
    batch = memory_data_client.add_messages(
        space_id=memory_space.id,
        session_id=memory_session.id,
        messages=[
            TextMessage(role="user", content="hello from the integration suite"),
            TextMessage(role="assistant", content="echo: hello from the integration suite"),
        ],
        is_force_extract=False,
    )
    return batch


# --------------------------------------------------------------------------- #
# Space control plane
# --------------------------------------------------------------------------- #
def test_get_space(memory_control_client, memory_space):
    got = memory_control_client.get_space(memory_space.id)
    assert got.id == memory_space.id
    assert got.name == memory_space.name


def test_list_spaces_contains_created(memory_control_client, memory_space):
    # limit capped at 100 by the backend ("limit too large" above 100)
    result = memory_control_client.list_spaces(limit=100)
    ids = [s.id for s in result.items]
    assert memory_space.id in ids


def test_update_space(memory_control_client, memory_space):
    updated = memory_control_client.update_space(
        memory_space.id, description="updated by integration suite"
    )
    assert updated.id == memory_space.id


# --------------------------------------------------------------------------- #
# Session + message data plane
# --------------------------------------------------------------------------- #
def test_session_created(memory_session):
    assert memory_session.id


def test_add_messages(memory_space, memory_session, seeded_messages):
    assert len(seeded_messages.items) == 2


def test_list_messages(memory_data_client, memory_space, memory_session, seeded_messages):
    result = memory_data_client.list_messages(
        space_id=memory_space.id, session_id=memory_session.id, limit=10
    )
    assert isinstance(result.items, list)
    assert result.total >= 2


def test_get_last_k_messages(memory_data_client, memory_space, memory_session, seeded_messages):
    msgs = memory_data_client.get_last_k_messages(
        session_id=memory_session.id, k=2, space_id=memory_space.id
    )
    assert isinstance(msgs, list)
    assert len(msgs) == 2
    roles = [m.role for m in msgs]
    assert "user" in roles and "assistant" in roles


def test_get_message(memory_data_client, memory_space, memory_session, seeded_messages):
    msg_id = seeded_messages.items[0].id
    msg = memory_data_client.get_message(
        message_id=msg_id, space_id=memory_space.id, session_id=memory_session.id
    )
    assert msg.id == msg_id
    assert msg.role in ("user", "assistant", "system", "tool")


# --------------------------------------------------------------------------- #
# Memory data plane (search / list / get / delete)
# --------------------------------------------------------------------------- #
def test_search_memories(memory_data_client, memory_space, seeded_messages):
    result = memory_data_client.search_memories(
        space_id=memory_space.id,
        filters=MemorySearchFilter(query="hello", top_k=3),
    )
    assert isinstance(result.results, list)
    assert result.total >= 0


def test_list_memories(memory_data_client, memory_space, seeded_messages):
    result = memory_data_client.list_memories(space_id=memory_space.id, limit=10)
    assert isinstance(result.items, list)
    assert result.total >= 0


def test_delete_memory_if_any(memory_data_client, memory_space, seeded_messages):
    """Memories are backend-extracted; if none exist yet, this is a soft skip."""
    result = memory_data_client.list_memories(space_id=memory_space.id, limit=10)
    if not result.items:
        pytest.skip(
            "no extracted memories to delete — enable memory_strategies_builtin "
            "+ is_force_extract=True to exercise the extraction+delete path"
        )
    target = result.items[0]
    memory_data_client.delete_memory(space_id=memory_space.id, memory_id=target.id)


# --------------------------------------------------------------------------- #
# MemorySession wrapper (bound space+session, auto-creates session on init)
# --------------------------------------------------------------------------- #
def test_memory_session_wrapper(memory_space):
    from agentarts.sdk.memory import MemorySession
    from agentarts.sdk.utils.constant import get_region

    session = MemorySession(
        space_id=memory_space.id,
        actor_id="aa-it-wrap",
        api_key=memory_space.api_key,
        region_name=get_region(),
    )
    session.add_messages([TextMessage(role="user", content="wrap sync")])
    last = session.get_last_k_messages(k=1)
    assert len(last) == 1
    listed = session.list_messages(limit=5)
    assert listed.total >= 1
