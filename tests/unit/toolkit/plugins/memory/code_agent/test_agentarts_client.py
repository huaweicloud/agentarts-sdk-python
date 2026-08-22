"""Unit tests for AgentArtsMemoryClient (agentarts_client.py).

Uses a fake SDK namespace so no cloud SDK or network is required.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from agentarts.toolkit.plugins.memory import agentarts_client as ac
from agentarts.toolkit.plugins.memory.agentarts_client import AgentArtsMemoryClient


# ── fake SDK ───────────────────────────────────────────────────────
class FakeTextMessage:
    def __init__(self, role, content, actor_id=None, assistant_id=None):
        self.role = role
        self.content = content
        self.actor_id = actor_id
        self.assistant_id = assistant_id


class FakeSearchFilter:
    def __init__(self, query=None, top_k=5, min_score=0.3, actor_id=None, **kw):
        self.query = query
        self.top_k = top_k
        self.min_score = min_score
        self.actor_id = actor_id


def _fake_sdk():
    return SimpleNamespace(
        TextMessage=FakeTextMessage,
        MemorySearchFilter=FakeSearchFilter,
    )


def _make_client(monkeypatch, space_id="space-1", ak="ak1", sk="sk1", api_key="key1"):
    monkeypatch.setenv("HUAWEICLOUD_SDK_AK", ak)
    monkeypatch.setenv("HUAWEICLOUD_SDK_SK", sk)
    monkeypatch.setenv("AGENTARTS_MEMORY_SPACE_ID", space_id)
    monkeypatch.setenv("HUAWEICLOUD_SDK_MEMORY_API_KEY", api_key)
    sdk = _fake_sdk()
    client = AgentArtsMemoryClient(sdk=sdk)
    # Disable file-based cache for unit tests — only test in-memory logic.
    monkeypatch.setattr(AgentArtsMemoryClient, "_get_cached_sid_from_file", staticmethod(lambda _: None))
    monkeypatch.setattr(AgentArtsMemoryClient, "_put_cached_sid_to_file", staticmethod(lambda *a: None))
    monkeypatch.setattr(AgentArtsMemoryClient, "_invalidate_cached_sid", staticmethod(lambda *a: None))
    return client


# ── availability ──────────────────────────────────────────────────
def test_is_configured_true(monkeypatch):
    c = _make_client(monkeypatch)
    assert c.is_configured() is True


def test_is_configured_false_when_missing_space(monkeypatch):
    monkeypatch.setenv("HUAWEICLOUD_SDK_AK", "ak")
    monkeypatch.setenv("HUAWEICLOUD_SDK_SK", "sk")
    monkeypatch.delenv("AGENTARTS_MEMORY_SPACE_ID", raising=False)
    c = AgentArtsMemoryClient(sdk=_fake_sdk())
    assert c.is_configured() is False


def test_health_reports_flags(monkeypatch):
    c = _make_client(monkeypatch)
    h = c.health()
    assert h["space_id"] is True
    assert h["api_key"] is True
    assert h["status"] == "healthy"


# ── session caching ───────────────────────────────────────────────
def test_session_cached_per_scope(monkeypatch):
    c = _make_client(monkeypatch)
    c._client = MagicMock()
    c._client.create_memory_session.return_value = SimpleNamespace(id="sess-1")
    sid1 = c._get_or_create_session("proj-a", "user-1")
    sid2 = c._get_or_create_session("proj-a", "user-1")
    assert sid1 == sid2 == "sess-1"
    # create called only once for the same scope
    assert c._client.create_memory_session.call_count == 1
    # different scope -> new session
    c._client.create_memory_session.return_value = SimpleNamespace(id="sess-2")
    sid3 = c._get_or_create_session("proj-b", "user-1")
    assert sid3 == "sess-2"
    assert c._client.create_memory_session.call_count == 2


def test_session_not_shared_across_users(monkeypatch):
    """Same scope but different actor_id must create separate sessions."""
    c = _make_client(monkeypatch)
    c._client = MagicMock()
    c._client.create_memory_session.return_value = SimpleNamespace(id="sess-1")
    sid1 = c._get_or_create_session("proj-a", "codex-user")
    # same scope, different user -> new session
    c._client.create_memory_session.return_value = SimpleNamespace(id="sess-2")
    sid2 = c._get_or_create_session("proj-a", "cc-user")
    assert sid1 != sid2
    assert sid1 == "sess-1"
    assert sid2 == "sess-2"
    assert c._client.create_memory_session.call_count == 2
    # same scope + same user still cached
    sid3 = c._get_or_create_session("proj-a", "codex-user")
    assert sid3 == sid1
    assert c._client.create_memory_session.call_count == 2


def test_session_uses_actor_and_assistant(monkeypatch):
    c = _make_client(monkeypatch, space_id="sp")
    c._client = MagicMock()
    c._client.create_memory_session.return_value = SimpleNamespace(id="s-x")
    c._get_or_create_session("scope", "the-actor")
    call = c._client.create_memory_session.call_args
    assert call.kwargs["space_id"] == "sp"
    assert call.kwargs["actor_id"] == "the-actor"
    assert call.kwargs["assistant_id"] == ac.DEFAULT_ASSISTANT_ID


# ── add_messages ──────────────────────────────────────────────────
def test_add_messages_maps_role_content(monkeypatch):
    c = _make_client(monkeypatch)
    c._client = MagicMock()
    c._client.create_memory_session.return_value = SimpleNamespace(id="sess-9")
    c._client.add_messages.return_value = SimpleNamespace()
    res = c.add_messages(
        [{"role": "user", "content": "hello"}],
        user_id="u1",
        scope_id="proj",
    )
    assert res["session_id"] == "sess-9"
    assert res["count"] == 1
    sent = c._client.add_messages.call_args
    msgs = sent.kwargs["messages"]
    assert msgs[0].role == "user"
    assert msgs[0].content == "hello"
    assert msgs[0].actor_id == "u1"
    assert sent.kwargs["space_id"] == "space-1"
    assert sent.kwargs["session_id"] == "sess-9"


# ── search_memories ───────────────────────────────────────────────
def test_search_memories_normalizes_results(monkeypatch):
    c = _make_client(monkeypatch)
    c._client = MagicMock()
    # MemorySearchResponse.results = [{"record": <dict>, "score": 0.9}, ...]
    c._client.search_memories.return_value = SimpleNamespace(
        results=[
            {"record": {"content": "likes python", "strategy_type": "semantic"}, "score": 0.9},
            {"record": {"content": "episodic note", "strategy_type": "episodic"}, "score": 0.7},
        ],
        total=2,
    )
    out = c.search_memories(query="python", user_id="u1", scope_id="proj")
    assert len(out) == 2
    assert out[0]["content"] == "likes python"
    assert out[0]["score"] == pytest.approx(0.9)
    assert out[0]["type"] == "semantic"
    # filter passed through
    f = c._client.search_memories.call_args.kwargs["filters"]
    assert f.query == "python"
    assert f.top_k == ac.DEFAULT_TOP_K
    assert f.min_score == ac.DEFAULT_MIN_SCORE
    assert f.actor_id == "u1"


def test_search_memories_empty(monkeypatch):
    c = _make_client(monkeypatch)
    c._client = MagicMock()
    c._client.search_memories.return_value = SimpleNamespace(results=[], total=0)
    assert c.search_memories(query="x", user_id="u", scope_id="s") == []


# ── list_memories ─────────────────────────────────────────────────
def test_list_memories_normalizes(monkeypatch):
    c = _make_client(monkeypatch)
    c._client = MagicMock()
    c._client.list_memories.return_value = SimpleNamespace(
        items=[
            SimpleNamespace(id="m1", content="c1", strategy_type="semantic", created_at="t1"),
        ],
        total=1,
    )
    out = c.list_memories(user_id="u", scope_id="s")
    assert out[0]["id"] == "m1"
    assert out[0]["content"] == "c1"
    assert out[0]["type"] == "semantic"
    assert out[0]["created_at"] == "t1"
