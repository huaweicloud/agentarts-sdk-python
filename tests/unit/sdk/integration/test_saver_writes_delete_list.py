"""
Unit tests for AgentArtsMemorySessionSaver behavior.

Migrated from my_simple_demo/test_saver_writes_delete_list.py (which is
git-ignored) into the formal unit test suite. Covers the actual behavior of:
- put_writes / aput_writes (storage, 404 auto-create retry, dedup)
- get_tuple / aget_tuple and list / alist (pending_writes extraction)
- delete_thread / adelete_thread (order, swallow contract, cleanup)
- context managers (sync / async close behavior)

Uses in-memory fake clients (no real API calls).
"""

import asyncio
import base64
import json
from unittest.mock import MagicMock

import pytest

pytest.importorskip("langgraph")

from agentarts.sdk.integration.langgraph import AgentArtsMemorySessionSaver
from agentarts.sdk.service.http_client import APIException


class FakeMessage:
    """Mock message for testing."""

    def __init__(self, role, content="", meta=None):
        self.role = role
        self.content = content
        self.meta = meta
        # parts is what memory_to_langgraph_message expects
        self.parts = [{"type": "text", "text": content}]


class FakeMemoryClient:
    """In-memory mock of MemoryClient for testing."""

    def __init__(self):
        self.sessions = {}  # session_id -> list of message objects
        self.add_messages_calls = []
        self.delete_session_calls = []
        self.create_memory_session_calls = []
        self.close_called = False
        self._add_messages_fail_404 = False
        self._delete_session_fail = False
        self.delete_session_attempts = 0

    def add_messages(self, space_id, session_id, messages):
        # Simulate 404 on first call if flag is set
        if self._add_messages_fail_404:
            self._add_messages_fail_404 = False
            raise APIException(404, "NotFound", "session not found")
        # Call to_dict() on each message to simulate real backend behavior
        # This catches bugs like empty content (TextMessage.to_dict validates)
        for msg in messages:
            msg.to_dict()
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].extend(messages)
        self.add_messages_calls.append({
            "space_id": space_id,
            "session_id": session_id,
            "messages": messages,
        })
        return MagicMock(items=messages)

    def create_memory_session(self, space_id, id=None, actor_id=None,
                              assistant_id=None):
        self.create_memory_session_calls.append({
            "space_id": space_id,
            "id": id,
        })

    def get_last_k_messages(self, session_id, k, space_id):
        msgs = self.sessions.get(session_id, [])
        return msgs[-k:] if len(msgs) > k else msgs

    def list_messages(self, space_id, session_id, limit, offset):
        msgs = self.sessions.get(session_id, [])
        items = msgs[offset:offset + limit]
        result = MagicMock()
        result.items = items
        return result

    def delete_session(self, space_id, session_id):
        self.delete_session_attempts += 1
        if self._delete_session_fail:
            raise APIException(500, "InternalError", "delete failed")
        self.sessions.pop(session_id, None)
        self.delete_session_calls.append({
            "space_id": space_id,
            "session_id": session_id,
        })

    def close(self):
        self.close_called = True


class FakeAsyncMemoryClient:
    """In-memory mock of AsyncMemoryClient for testing."""

    def __init__(self):
        self.sessions = {}
        self.add_messages_calls = []
        self.delete_session_calls = []
        self.create_memory_session_calls = []
        self.close_called = False
        self._add_messages_fail_404 = False
        self._delete_session_fail = False
        self.delete_session_attempts = 0

    async def add_messages(self, space_id, session_id, messages):
        # Simulate 404 on first call if flag is set
        if self._add_messages_fail_404:
            self._add_messages_fail_404 = False
            raise APIException(404, "NotFound", "session not found")
        # Call to_dict() on each message to simulate real backend behavior
        for msg in messages:
            msg.to_dict()
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].extend(messages)
        self.add_messages_calls.append({
            "space_id": space_id,
            "session_id": session_id,
            "messages": messages,
        })
        return MagicMock(items=messages)

    async def create_memory_session(self, space_id, id=None, actor_id=None,
                                    assistant_id=None):
        self.create_memory_session_calls.append({
            "space_id": space_id,
            "id": id,
        })

    async def get_last_k_messages(self, session_id, k, space_id):
        msgs = self.sessions.get(session_id, [])
        return msgs[-k:] if len(msgs) > k else msgs

    async def list_messages(self, space_id, session_id, limit, offset):
        msgs = self.sessions.get(session_id, [])
        items = msgs[offset:offset + limit]
        result = MagicMock()
        result.items = items
        return result

    async def delete_session(self, space_id, session_id):
        self.delete_session_attempts += 1
        if self._delete_session_fail:
            raise APIException(500, "InternalError", "delete failed")
        self.sessions.pop(session_id, None)
        self.delete_session_calls.append({
            "space_id": space_id,
            "session_id": session_id,
        })

    async def close(self):
        self.close_called = True


def create_saver():
    """Create a saver with fake clients."""
    saver = AgentArtsMemorySessionSaver(
        space_id="test-space",
        region="cn-southwest-1",
        api_key="test-api-key",
    )
    fake_sync = FakeMemoryClient()
    fake_async = FakeAsyncMemoryClient()
    saver._client = fake_sync
    saver._async_client = fake_async
    return saver, fake_sync, fake_async


def make_config(thread_id, checkpoint_id=None):
    """Create a RunnableConfig."""
    config = {"configurable": {"thread_id": thread_id}}
    if checkpoint_id:
        config["configurable"]["checkpoint_id"] = checkpoint_id
    return config


def serialize_write(saver, value):
    """Serialize a value the same way put_writes does."""
    value_type, value_bytes = saver.serde.dumps_typed(value)
    return {
        "value_type": value_type,
        "value_data": base64.b64encode(value_bytes).decode("ascii"),
    }


def _seed_main_session(fake, thread_id, checkpoint_id, content="Hello"):
    """Seed the main session with one checkpoint message."""
    fake.sessions[thread_id] = [FakeMessage(
        role="user",
        content=content,
        meta=json.dumps({
            "step": 0,
            "source": "loop",
            "checkpoint_id": checkpoint_id,
            "checkpoint_ts": "2024-01-01T00:00:00Z",
        }),
    )]


class TestPutWrites:
    """put_writes behavior."""

    def test_put_writes_stores_in_writes_session(self):
        saver, fake_sync, _ = create_saver()
        thread_id = "test-thread-1"
        checkpoint_id = "cp-123"
        config = make_config(thread_id, checkpoint_id)

        writes = [("channel1", "value1"), ("channel2", {"key": "val"})]
        task_id = "task-001"
        saver.put_writes(config, writes, task_id)

        assert len(fake_sync.add_messages_calls) == 1
        call = fake_sync.add_messages_calls[0]
        expected_writes_session = AgentArtsMemorySessionSaver._writes_session_id(thread_id)
        assert call["session_id"] == expected_writes_session

        assert len(call["messages"]) == 1
        msg = call["messages"][0]
        assert msg.role == "system"
        assert msg.content == "pending_writes"

        meta = json.loads(msg.meta)
        assert meta["type"] == "pending_writes"
        assert meta["checkpoint_id"] == checkpoint_id
        assert len(meta["writes"]) == 2
        assert meta["writes"][0]["task_id"] == task_id
        assert meta["writes"][0]["channel"] == "channel1"
        assert "value_type" in meta["writes"][0]
        assert "value_data" in meta["writes"][0]

    def test_put_writes_empty_is_noop(self):
        saver, fake_sync, _ = create_saver()
        thread_id = "test-thread-5"
        config = make_config(thread_id, "cp-000")

        saver.put_writes(config, [], "task-005")

        assert len(fake_sync.add_messages_calls) == 0

    def test_put_writes_dedup_first_occurrence_wins(self):
        saver, fake_sync, _ = create_saver()
        thread_id = "test-thread-6"
        checkpoint_id = "cp-dedup"
        _seed_main_session(fake_sync, thread_id, checkpoint_id)

        config = make_config(thread_id, checkpoint_id)
        saver.put_writes(config, [("output", "first")], "task-A")
        saver.put_writes(config, [("output", "second")], "task-A")

        result = saver.get_tuple(config)
        assert result.pending_writes is not None
        assert len(result.pending_writes) == 1
        assert result.pending_writes[0][2] == "first"

    def test_put_writes_404_auto_creates_and_retries(self):
        saver, fake_sync, _ = create_saver()
        thread_id = "test-thread-404"
        checkpoint_id = "cp-404"
        config = make_config(thread_id, checkpoint_id)

        fake_sync._add_messages_fail_404 = True
        saver.put_writes(config, [("channel404", "value404")], "task-404")

        assert len(fake_sync.create_memory_session_calls) == 1
        create_call = fake_sync.create_memory_session_calls[0]
        expected_writes_session = saver._writes_session_id(thread_id)
        assert create_call["id"] == expected_writes_session

        assert len(fake_sync.add_messages_calls) == 1
        assert expected_writes_session in fake_sync.sessions
        assert len(fake_sync.sessions[expected_writes_session]) == 1


class TestAPutWrites:
    """aput_writes behavior (async)."""

    @pytest.mark.asyncio
    async def test_aput_writes_stores_in_writes_session(self):
        saver, _, fake_async = create_saver()
        thread_id = "test-thread-7"
        checkpoint_id = "cp-async-1"
        config = make_config(thread_id, checkpoint_id)

        await saver.aput_writes(config, [("channelA", "valueA")], "task-007")

        assert len(fake_async.add_messages_calls) == 1
        call = fake_async.add_messages_calls[0]
        assert call["session_id"] == saver._writes_session_id(thread_id)
        meta = json.loads(call["messages"][0].meta)
        assert meta["type"] == "pending_writes"
        assert len(meta["writes"]) == 1

    @pytest.mark.asyncio
    async def test_aput_writes_404_auto_creates_and_retries(self):
        saver, _, fake_async = create_saver()
        thread_id = "test-thread-404-async"
        checkpoint_id = "cp-404-async"
        config = make_config(thread_id, checkpoint_id)

        fake_async._add_messages_fail_404 = True
        await saver.aput_writes(config, [("channelA404", "valueA404")], "task-404-async")

        assert len(fake_async.create_memory_session_calls) == 1
        create_call = fake_async.create_memory_session_calls[0]
        expected_writes_session = saver._writes_session_id(thread_id)
        assert create_call["id"] == expected_writes_session

        assert len(fake_async.add_messages_calls) == 1
        assert expected_writes_session in fake_async.sessions
        assert len(fake_async.sessions[expected_writes_session]) == 1


class TestGetTuplePendingWrites:
    """get_tuple pending_writes roundtrip."""

    def test_roundtrip(self):
        saver, fake_sync, _ = create_saver()
        thread_id = "test-thread-2"
        checkpoint_id = "cp-456"
        _seed_main_session(fake_sync, thread_id, checkpoint_id)

        config = make_config(thread_id, checkpoint_id)
        saver.put_writes(config, [("output", "result-value")], "task-002")

        result = saver.get_tuple(config)
        assert result is not None
        assert result.pending_writes is not None
        assert len(result.pending_writes) == 1
        pw = result.pending_writes[0]
        assert pw[0] == "task-002"
        assert pw[1] == "output"
        assert pw[2] == "result-value"

    @pytest.mark.asyncio
    async def test_async_roundtrip(self):
        saver, _, fake_async = create_saver()
        thread_id = "test-thread-8"
        checkpoint_id = "cp-async-2"
        _seed_main_session(fake_async, thread_id, checkpoint_id, content="Async test")

        config = make_config(thread_id, checkpoint_id)
        await saver.aput_writes(config, [("result", {"data": "async-value"})], "task-008")

        result = await saver.aget_tuple(config)
        assert result is not None
        assert result.pending_writes is not None
        assert len(result.pending_writes) == 1
        pw = result.pending_writes[0]
        assert pw[0] == "task-008"
        assert pw[1] == "result"
        assert pw[2] == {"data": "async-value"}


class TestListPendingWrites:
    """list / alist pending_writes extraction."""

    def _seed_writes_session(self, saver, fake, thread_id, checkpoint_id,
                             task_id, channel, value):
        writes_data = [{
            "task_id": task_id,
            "task_path": "",
            "channel": channel,
            "write_idx": 0,
            **serialize_write(saver, value),
        }]
        fake.sessions[saver._writes_session_id(thread_id)] = [FakeMessage(
            role="system",
            content="",
            meta=json.dumps({
                "type": "pending_writes",
                "checkpoint_id": checkpoint_id,
                "writes": writes_data,
            }),
        )]

    def test_list_retrieves_pending_writes(self):
        saver, fake_sync, _ = create_saver()
        thread_id = "test-thread-3"
        checkpoint_id = "cp-789"
        _seed_main_session(fake_sync, thread_id, checkpoint_id, content="Test")
        self._seed_writes_session(
            saver, fake_sync, thread_id, checkpoint_id, "task-003", "data", "test-data"
        )

        result = saver.list(make_config(thread_id))
        assert len(result) == 1
        checkpoint_tuple = result[0]
        assert checkpoint_tuple.pending_writes is not None
        assert len(checkpoint_tuple.pending_writes) == 1
        pw = checkpoint_tuple.pending_writes[0]
        assert pw[0] == "task-003"
        assert pw[1] == "data"
        assert pw[2] == "test-data"

    @pytest.mark.asyncio
    async def test_alist_retrieves_pending_writes(self):
        saver, _, fake_async = create_saver()
        thread_id = "test-thread-9"
        checkpoint_id = "cp-async-3"
        _seed_main_session(fake_async, thread_id, checkpoint_id, content="Async list test")
        self._seed_writes_session(
            saver, fake_async, thread_id, checkpoint_id, "task-009", "async-channel", "async-data"
        )

        result = await saver.alist(make_config(thread_id))
        assert len(result) == 1
        checkpoint_tuple = result[0]
        assert checkpoint_tuple.pending_writes is not None
        assert len(checkpoint_tuple.pending_writes) == 1
        pw = checkpoint_tuple.pending_writes[0]
        assert pw[0] == "task-009"
        assert pw[1] == "async-channel"
        assert pw[2] == "async-data"


class TestDeleteThread:
    """delete_thread / adelete_thread behavior."""

    def test_delete_thread_deletes_both_sessions(self):
        saver, fake_sync, _ = create_saver()
        thread_id = "test-thread-4"

        fake_sync.sessions[thread_id] = [FakeMessage(role="user", content="main")]
        fake_sync.sessions[saver._writes_session_id(thread_id)] = [FakeMessage(role="system", content="writes")]
        saver._persisted_count[thread_id] = 5

        saver.delete_thread(thread_id)

        assert len(fake_sync.delete_session_calls) == 2
        deleted_sessions = [call["session_id"] for call in fake_sync.delete_session_calls]
        assert thread_id in deleted_sessions
        assert saver._writes_session_id(thread_id) in deleted_sessions
        assert thread_id not in saver._persisted_count
        assert thread_id not in fake_sync.sessions
        assert saver._writes_session_id(thread_id) not in fake_sync.sessions

    def test_delete_thread_writes_session_deleted_first(self):
        saver, fake_sync, _ = create_saver()
        thread_id = "test-thread-order"

        saver.delete_thread(thread_id)

        assert len(fake_sync.delete_session_calls) == 2
        deleted_sessions = [call["session_id"] for call in fake_sync.delete_session_calls]
        writes_sid = saver._writes_session_id(thread_id)
        assert deleted_sessions[0] == writes_sid
        assert deleted_sessions[1] == thread_id

    def test_delete_thread_swallows_failures_and_cleans_up(self):
        saver, fake_sync, _ = create_saver()
        thread_id = "test-thread-swallow"
        saver._persisted_count[thread_id] = 5
        fake_sync._delete_session_fail = True

        saver.delete_thread(thread_id)  # must NOT raise

        assert fake_sync.delete_session_attempts == 2
        assert thread_id not in saver._persisted_count

    @pytest.mark.asyncio
    async def test_adelete_thread_deletes_both_sessions(self):
        saver, _, fake_async = create_saver()
        thread_id = "test-thread-10"

        fake_async.sessions[thread_id] = [FakeMessage(role="user", content="main")]
        fake_async.sessions[saver._writes_session_id(thread_id)] = [FakeMessage(role="system", content="writes")]
        saver._persisted_count[thread_id] = 10

        await saver.adelete_thread(thread_id)

        assert len(fake_async.delete_session_calls) == 2
        deleted_sessions = [call["session_id"] for call in fake_async.delete_session_calls]
        assert thread_id in deleted_sessions
        assert saver._writes_session_id(thread_id) in deleted_sessions
        assert thread_id not in saver._persisted_count

    @pytest.mark.asyncio
    async def test_adelete_thread_order_and_swallow(self):
        saver, _, fake_async = create_saver()
        thread_id = "test-thread-async-order"

        # Normal path: verify order
        await saver.adelete_thread(thread_id)
        deleted_sessions = [call["session_id"] for call in fake_async.delete_session_calls]
        writes_sid = saver._writes_session_id(thread_id)
        assert len(deleted_sessions) == 2
        assert deleted_sessions[0] == writes_sid
        assert deleted_sessions[1] == thread_id
        assert thread_id not in saver._persisted_count

        # Failure path: no raise + cleanup
        saver._persisted_count[thread_id] = 7
        fake_async._delete_session_fail = True
        await saver.adelete_thread(thread_id)  # must not raise
        assert fake_async.delete_session_attempts == 4
        assert thread_id not in saver._persisted_count


class TestContextManager:
    """Sync / async context manager close behavior."""

    def test_sync_context_manager_closes_sync_client_only(self):
        saver, fake_sync, fake_async = create_saver()

        with saver as s:
            assert s is saver

        assert fake_sync.close_called
        assert not fake_async.close_called

    @pytest.mark.asyncio
    async def test_async_context_manager_closes_both(self):
        saver, fake_sync, fake_async = create_saver()

        async with saver as s:
            assert s is saver

        assert fake_sync.close_called
        assert fake_async.close_called
