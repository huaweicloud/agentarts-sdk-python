"""Unit tests for the MCP server tools (mcp/server.py).

Uses a mock AgentArtsMemoryClient injected via reset_client(). No network
or cloud SDK required.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agentarts.toolkit.plugins.memory.mcp import server as mcp_server


@pytest.fixture
def mock_client(monkeypatch):
    """Inject a mock AgentArtsMemoryClient into the MCP server module."""
    monkeypatch.setenv("HUAWEICLOUD_SDK_AK", "ak")
    monkeypatch.setenv("HUAWEICLOUD_SDK_SK", "sk")
    monkeypatch.setenv("AGENTARTS_MEMORY_SPACE_ID", "sp")
    monkeypatch.setenv("HUAWEICLOUD_SDK_MEMORY_API_KEY", "k")
    # Ensure platform detection returns "unknown" → user_id="__default__".
    monkeypatch.delenv("AGENTARTS_MEMORY_PLATFORM", raising=False)
    monkeypatch.delenv("AGENTARTS_MEMORY_USER_ID", raising=False)
    monkeypatch.delenv("AGENTARTS_MEMORY_PROJECT_NAME", raising=False)
    mock = MagicMock()
    mcp_server.reset_client(mock)
    yield mock
    mcp_server.reset_client(None)


# ── search_memories ───────────────────────────────────────────────


def test_search_memories_returns_results(mock_client):
    mock_client.search_memories.return_value = [
        {"content": "likes python", "score": 0.9, "type": "semantic"},
        {"content": "episodic note", "score": 0.7, "type": "episodic"},
    ]
    result = mcp_server.search_memories(query="python", num=5, threshold=0.3)
    assert result["total"] == 2
    assert result["query"] == "python"
    assert result["results"][0]["content"] == "likes python"
    assert result["results"][0]["score"] == 0.9

    kw = mock_client.search_memories.call_args.kwargs
    assert kw["query"] == "python"
    assert kw["user_id"] == "__default__"
    assert kw["scope_id"] == "default"
    assert kw["num"] == 5
    assert kw["threshold"] == 0.3


def test_search_memories_empty(mock_client):
    mock_client.search_memories.return_value = []
    result = mcp_server.search_memories(query="x")
    assert result["total"] == 0
    assert result["results"] == []


def test_search_memories_error(mock_client):
    mock_client.search_memories.side_effect = RuntimeError("boom")
    result = mcp_server.search_memories(query="x")
    assert "error" in result
    assert "boom" in result["error"]
    assert result["results"] == []
    assert result["total"] == 0


def test_search_memories_defaults(mock_client):
    mock_client.search_memories.return_value = []
    mcp_server.search_memories(query="test")
    kw = mock_client.search_memories.call_args.kwargs
    from agentarts.toolkit.plugins.memory.agentarts_client import (
        DEFAULT_MIN_SCORE,
        DEFAULT_TOP_K,
    )
    assert kw["num"] == DEFAULT_TOP_K
    assert kw["threshold"] == DEFAULT_MIN_SCORE
    assert kw["user_id"] == "__default__"
    assert kw["scope_id"] == "default"


def test_search_memories_resolves_platform_env(mock_client, monkeypatch):
    """When AGENTARTS_MEMORY_PLATFORM=opencode, user_id should be opencode-user."""
    monkeypatch.setenv("AGENTARTS_MEMORY_PLATFORM", "opencode")
    mock_client.search_memories.return_value = []
    mcp_server.search_memories(query="test")
    kw = mock_client.search_memories.call_args.kwargs
    assert kw["user_id"] == "opencode-user"


# ── add_messages ──────────────────────────────────────────────────


def test_add_messages_success(mock_client):
    mock_client.add_messages.return_value = {"session_id": "s1", "count": 2}
    result = mcp_server.add_messages(
        messages=[{"role": "user", "content": "hi"}],
    )
    assert result["session_id"] == "s1"
    assert result["count"] == 2

    args, kwargs = mock_client.add_messages.call_args
    assert args[0] == [{"role": "user", "content": "hi"}]
    assert kwargs["user_id"] == "__default__"
    assert kwargs["scope_id"] == "default"


def test_add_messages_error(mock_client):
    mock_client.add_messages.side_effect = RuntimeError("network error")
    result = mcp_server.add_messages(
        messages=[{"role": "user", "content": "x"}],
    )
    assert "error" in result
    assert "network error" in result["error"]
    assert result["count"] == 0


# ── list_memories ─────────────────────────────────────────────────


def test_list_memories_success(mock_client):
    mock_client.list_memories.return_value = [
        {"id": "m1", "content": "c1", "type": "semantic", "created_at": "t1"},
        {"id": "m2", "content": "c2", "type": "episodic", "created_at": "t2"},
    ]
    result = mcp_server.list_memories(limit=10, offset=0)
    assert result["total"] == 2
    assert result["results"][0]["id"] == "m1"

    kw = mock_client.list_memories.call_args.kwargs
    assert kw["limit"] == 10
    assert kw["offset"] == 0


def test_list_memories_error(mock_client):
    mock_client.list_memories.side_effect = RuntimeError("fail")
    result = mcp_server.list_memories()
    assert "error" in result
    assert result["total"] == 0


# ── search_summary ────────────────────────────────────────────────


def test_search_summary_filters_summary_types(mock_client):
    # search_memories returns results; filter to summary types only.
    mock_client.search_memories.return_value = [
        {"content": "summary text", "score": 0.9, "type": "episodic"},
        {"content": "other", "score": 0.7, "type": "semantic"},
    ]
    result = mcp_server.search_summary(query="x", num=3)
    types = [m["type"] for m in result["results"]]
    assert "episodic" in types
    assert "semantic" not in types


def test_search_summary_fallback_to_list_when_search_empty(mock_client):
    # search_memories returns nothing; fallback to list_memories + filter.
    mock_client.search_memories.return_value = []
    mock_client.list_memories.return_value = [
        {"id": "m1", "content": "summary text", "type": "episodic", "created_at": "t"},
        {"id": "m2", "content": "other", "type": "semantic", "created_at": "t2"},
    ]
    result = mcp_server.search_summary(query="x", num=3)
    types = [m["type"] for m in result["results"]]
    assert "episodic" in types
    assert "semantic" not in types


def test_search_summary_fallback_to_all(mock_client):
    mock_client.search_memories.return_value = []
    mock_client.list_memories.return_value = [
        {"id": "m1", "content": "c", "type": "semantic", "created_at": "t"},
    ]
    result = mcp_server.search_summary(query="x", num=5)
    assert len(result["results"]) == 1


def test_search_summary_error(mock_client):
    mock_client.search_memories.side_effect = RuntimeError("err")
    result = mcp_server.search_summary(query="x")
    assert "error" in result
    assert result["total"] == 0


# ── module structure ─────────────────────────────────────────────


def test_mcp_server_has_name():
    assert mcp_server.mcp.name == "agentarts-memory"


def test_mcp_server_has_version():
    assert mcp_server.mcp.version == "1.0.0"


def test_get_client_singleton():
    mcp_server.reset_client(None)
    assert callable(mcp_server.get_client)
    assert callable(mcp_server.reset_client)
    mcp_server.reset_client(None)
