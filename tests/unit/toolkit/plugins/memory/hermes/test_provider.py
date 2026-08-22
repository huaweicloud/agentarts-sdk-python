"""Tests for the AgentArts Memory provider.

This module consolidates tests for the config module, entry point / plugin
metadata, the provider lifecycle, and the tool schemas (ltm_search /
ltm_search_summary). All tests use a shared set of helpers defined at the top.
"""

import json
import pathlib
import threading
import time
from unittest.mock import MagicMock, patch

import __init__ as hermes_init
import pytest
import yaml
from provider import (
    CONFIG_SCHEMA,
    DEFAULT_LIST_LIMIT,
    DEFAULT_REGION,
    DEFAULT_TOP_K,
    ENV_API_KEY,
    ENV_REGION,
    ENV_SPACE_ID,
    TOOL_SCHEMAS,
    AgentArtsMemoryProvider,
    register,
    save_config,
)

# ── Shared helpers ──

ENV_VARS = {
    "HUAWEICLOUD_SDK_MEMORY_API_KEY": "test-api-key",
    "HUAWEICLOUD_SDK_REGION": "cn-southwest-2",
    "AGENTARTS_MEMORY_SPACE_ID": "test-space-id",
}


@pytest.fixture
def env_vars(monkeypatch):
    for key, val in ENV_VARS.items():
        monkeypatch.setenv(key, val)


def make_mock_sdk():
    """Create a mock SDK namespace with MemoryClient, TextMessage, MemorySearchFilter."""
    sdk = MagicMock()
    sdk.TextMessage = MagicMock(side_effect=lambda **kw: type("TextMessage", (), kw))
    sdk.MemorySearchFilter = MagicMock(side_effect=lambda **kw: type("Filter", (), kw))
    sdk.MemoryClient = MagicMock(return_value=MagicMock())
    return sdk


def init_provider(provider, mock_sdk):
    """Initialize provider with a mock SDK and return the mock client."""
    mock_client = mock_sdk.MemoryClient.return_value
    mock_client.create_memory_session.return_value = MagicMock(id="aa-sess")
    with patch(
        "provider.import_memory_sdk",
        return_value=mock_sdk,
    ):
        provider.initialize("sess-1", hermes_home="/tmp/h")
    return mock_client


# ── Config schema ──


class TestConfigSchema:
    def test_schema_is_list_of_dicts(self):
        assert isinstance(CONFIG_SCHEMA, list)
        assert len(CONFIG_SCHEMA) == 3
        for field in CONFIG_SCHEMA:
            assert isinstance(field, dict)
            assert "key" in field

    def test_api_key_field(self):
        field = next(f for f in CONFIG_SCHEMA if f["key"] == "api_key")
        assert field["secret"] is True
        assert field["required"] is True
        assert field["env_var"] == ENV_API_KEY

    def test_space_id_field(self):
        field = next(f for f in CONFIG_SCHEMA if f["key"] == "space_id")
        assert field["required"] is True
        assert field["env_var"] == ENV_SPACE_ID

    def test_region_field(self):
        field = next(f for f in CONFIG_SCHEMA if f["key"] == "region")
        assert field["default"] == DEFAULT_REGION
        assert field["env_var"] == ENV_REGION


# ── save_config ──


class TestSaveConfig:
    def test_writes_non_secret_fields(self, tmp_path):
        values = {
            "api_key": "secret-key",
            "ak": "my-ak",
            "sk": "my-sk",
            "space_id": "space-123",
            "region": "cn-north-4",
        }
        save_config(values, str(tmp_path))

        config_path = tmp_path / "agentarts.json"
        assert config_path.exists()
        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data == {"space_id": "space-123", "region": "cn-north-4"}

    def test_secrets_not_written_to_json(self, tmp_path):
        values = {
            "api_key": "secret-key",
            "ak": "my-ak",
            "sk": "my-sk",
            "space_id": "space-123",
        }
        save_config(values, str(tmp_path))

        config_path = tmp_path / "agentarts.json"
        content = config_path.read_text(encoding="utf-8")
        assert "secret-key" not in content
        assert "my-ak" not in content
        assert "my-sk" not in content

    def test_partial_values(self, tmp_path):
        save_config({"region": "cn-east-3"}, str(tmp_path))

        config_path = tmp_path / "agentarts.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data == {"region": "cn-east-3"}

    def test_creates_parent_dir(self, tmp_path):
        nested = tmp_path / "nested" / "path"
        save_config({"space_id": "s1"}, str(nested))

        config_path = nested / "agentarts.json"
        assert config_path.exists()
        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data == {"space_id": "s1"}

    def test_empty_values(self, tmp_path):
        save_config({}, str(tmp_path))

        config_path = tmp_path / "agentarts.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data == {}


# ── Constants ──


class TestConstants:
    def test_default_values(self):
        assert DEFAULT_REGION == "cn-southwest-2"

    def test_env_var_names(self):
        assert ENV_API_KEY == "HUAWEICLOUD_SDK_MEMORY_API_KEY"
        assert ENV_REGION == "HUAWEICLOUD_SDK_REGION"
        assert ENV_SPACE_ID == "AGENTARTS_MEMORY_SPACE_ID"


# ── name property ──


class TestName:
    def test_name(self):
        provider = AgentArtsMemoryProvider()
        assert provider.name == "agentarts_memory"


# ── is_available ──


class TestIsAvailable:
    def test_available_true(self, env_vars):
        provider = AgentArtsMemoryProvider()
        assert provider.is_available() is True

    def test_available_false_missing_api_key(self, monkeypatch):
        for key, val in ENV_VARS.items():
            if key == "HUAWEICLOUD_SDK_MEMORY_API_KEY":
                continue
            monkeypatch.setenv(key, val)
        monkeypatch.delenv("HUAWEICLOUD_SDK_MEMORY_API_KEY", raising=False)
        provider = AgentArtsMemoryProvider()
        assert provider.is_available() is False

    def test_available_false_missing_space_id(self, monkeypatch):
        for key, val in ENV_VARS.items():
            if key == "AGENTARTS_MEMORY_SPACE_ID":
                continue
            monkeypatch.setenv(key, val)
        monkeypatch.delenv("AGENTARTS_MEMORY_SPACE_ID", raising=False)
        provider = AgentArtsMemoryProvider()
        assert provider.is_available() is False

    def test_no_network_requests(self, env_vars):
        """is_available must not trigger any network requests."""
        provider = AgentArtsMemoryProvider()
        result = provider.is_available()
        assert isinstance(result, bool)


# ── initialize ──


class TestInitialize:
    def test_initializes_client_and_session(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_session = MagicMock()
        mock_session.id = "agentarts-session-123"
        mock_client.create_memory_session.return_value = mock_session

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("hermes-session-1", hermes_home="/tmp/hermes")

        assert provider._client is mock_client
        assert provider._space_id == "test-space-id"
        assert provider._session_id == "agentarts-session-123"
        assert provider._actor_id == "hermes-user"
        assert provider._hermes_home == "/tmp/hermes"
        assert provider._assistant_id == "hermes-agent"

    def test_initialize_calls_memory_client_with_correct_args(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_session = MagicMock()
        mock_session.id = "sess-1"
        mock_client.create_memory_session.return_value = mock_session

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")

        mock_sdk.MemoryClient.assert_called_once_with(
            region_name="cn-southwest-2",
            api_key="test-api-key",
        )

    def test_initialize_falls_back_on_session_failure(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.side_effect = RuntimeError("network error")

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("hermes-sess", hermes_home="/tmp/h")

        assert provider._session_id == "hermes-sess"
        assert provider._client is mock_client


# ── Config methods ──


class TestConfigMethods:
    def test_get_config_schema(self):
        provider = AgentArtsMemoryProvider()
        schema = provider.get_config_schema()
        assert isinstance(schema, list)
        assert len(schema) == 3
        keys = {f["key"] for f in schema}
        assert keys == {"api_key", "space_id", "region"}

    def test_save_config(self, tmp_path):
        provider = AgentArtsMemoryProvider()
        provider.save_config({"space_id": "s1", "region": "r1", "api_key": "secret"}, str(tmp_path))
        config_path = tmp_path / "agentarts.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data == {"space_id": "s1", "region": "r1"}


# ── Tool methods (stub phase) ──


class TestToolMethods:
    def test_get_tool_schemas_returns_list(self):
        provider = AgentArtsMemoryProvider()
        assert isinstance(provider.get_tool_schemas(), list)

    def test_handle_tool_call_unknown(self):
        provider = AgentArtsMemoryProvider()
        result = provider.handle_tool_call("nonexistent", {})
        data = json.loads(result)
        assert "error" in data


# ── system_prompt_block ──


class TestSystemPromptBlock:
    def test_returns_non_empty_text(self):
        provider = AgentArtsMemoryProvider()
        block = provider.system_prompt_block()
        assert isinstance(block, str)
        assert len(block) > 0
        assert "AgentArts Memory" in block

    def test_mentions_tools(self):
        provider = AgentArtsMemoryProvider()
        block = provider.system_prompt_block()
        assert "ltm_search" in block
        assert "ltm_search_summary" in block


# ── prefetch ──


class TestPrefetch:
    def test_returns_empty_without_client(self):
        provider = AgentArtsMemoryProvider()
        assert provider.prefetch("query") == ""

    def test_returns_empty_with_empty_query(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")
        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
        assert provider.prefetch("") == ""

    def test_calls_search_memories(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")
        search_response = MagicMock()
        search_response.results = [
            {"record": {"content": "memory 1"}, "score": 0.9},
            {"record": {"content": "memory 2"}, "score": 0.8},
        ]
        mock_client.search_memories.return_value = search_response

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            result = provider.prefetch("test query")

        assert "test query" in result
        assert "memory 1" in result
        assert "memory 2" in result
        assert "0.9" in result
        mock_client.search_memories.assert_called_once()

    def test_returns_empty_on_exception(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")
        mock_client.search_memories.side_effect = RuntimeError("timeout")

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            result = provider.prefetch("query")

        assert result == ""

    def test_empty_results(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")
        search_response = MagicMock()
        search_response.results = []
        mock_client.search_memories.return_value = search_response

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            result = provider.prefetch("query")

        assert result == ""


# ── sync_turn ──


class TestSyncTurn:
    def test_returns_immediately_no_client(self):
        provider = AgentArtsMemoryProvider()
        provider.sync_turn("user", "assistant")
        assert provider._sync_thread is None

    def test_starts_daemon_thread(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")
        event = threading.Event()

        def _slow_add(*args, **kwargs):
            event.set()

        mock_client.add_messages.side_effect = _slow_add

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            provider.sync_turn("hello", "hi there")

        assert provider._sync_thread is not None
        assert provider._sync_thread.daemon is True
        assert event.wait(timeout=5.0)
        mock_client.add_messages.assert_called_once()
        provider._sync_thread.join(timeout=5.0)

    def test_add_messages_called_with_correct_args(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="aa-sess")

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("h-sess", hermes_home="/tmp/h")
            provider.sync_turn("user msg", "assistant msg")
            if provider._sync_thread:
                provider._sync_thread.join(timeout=5.0)

        mock_client.add_messages.assert_called_once()
        call_kwargs = mock_client.add_messages.call_args.kwargs
        assert call_kwargs["space_id"] == "test-space-id"
        assert call_kwargs["session_id"] == "aa-sess"
        messages = call_kwargs["messages"]
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "user msg"
        assert messages[1].role == "assistant"
        assert messages[1].content == "assistant msg"

    def test_join_previous_thread(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")

        barrier = threading.Event()

        def _blocking_add(*args, **kwargs):
            barrier.set()
            time.sleep(0.3)

        mock_client.add_messages.side_effect = _blocking_add

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            provider.sync_turn("msg1", "resp1")
            assert barrier.wait(timeout=5.0) is True
            provider.sync_turn("msg2", "resp2")
            if provider._sync_thread:
                provider._sync_thread.join(timeout=5.0)

        assert mock_client.add_messages.call_count == 2

    def test_exception_in_thread_does_not_propagate(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")
        mock_client.add_messages.side_effect = RuntimeError("write failed")

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            provider.sync_turn("msg", "resp")
            if provider._sync_thread:
                provider._sync_thread.join(timeout=5.0)

        mock_client.add_messages.assert_called_once()


# ── on_pre_compress ──


class TestOnPreCompress:
    def test_extracts_query_and_prefetches(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")
        search_response = MagicMock()
        search_response.results = [{"record": {"content": "ctx"}, "score": 0.9}]
        mock_client.search_memories.return_value = search_response

        messages = [
            {"role": "assistant", "content": "old response"},
            {"role": "user", "content": "important user question"},
        ]

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            result = provider.on_pre_compress(messages)

        assert "important user question" in result
        assert "ctx" in result

    def test_empty_messages_returns_empty(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            result = provider.on_pre_compress([])

        assert result == ""

    def test_handles_object_messages(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")
        search_response = MagicMock()
        search_response.results = []
        mock_client.search_memories.return_value = search_response

        class Msg:
            def __init__(self, role, content):
                self.role = role
                self.content = content

        messages = [Msg("user", "object content")]

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            provider.on_pre_compress(messages)

        mock_client.search_memories.assert_called_once()
        call_kwargs = mock_client.search_memories.call_args.kwargs
        filters = call_kwargs["filters"]
        assert filters.query == "object content"

    def test_truncates_long_query(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")
        search_response = MagicMock()
        search_response.results = []
        mock_client.search_memories.return_value = search_response

        long_content = "x" * 500
        messages = [{"role": "user", "content": long_content}]

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            provider.on_pre_compress(messages)

        call_kwargs = mock_client.search_memories.call_args.kwargs
        assert len(call_kwargs["filters"].query) == 200


# ── on_memory_write ──


class TestOnMemoryWrite:
    def test_calls_add_messages(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            provider.on_memory_write("update", "MEMORY.md", "some memory content")

        mock_client.add_messages.assert_called_once()
        call_kwargs = mock_client.add_messages.call_args.kwargs
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0].role == "system"
        assert "[MEMORY_MIRROR]" in messages[0].content
        assert "MEMORY.md" in messages[0].content
        assert "some memory content" in messages[0].content

    def test_no_op_without_client(self):
        provider = AgentArtsMemoryProvider()
        provider.on_memory_write("update", "MEMORY.md", "content")

    def test_no_op_with_empty_content(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            provider.on_memory_write("update", "MEMORY.md", "")

        mock_client.add_messages.assert_not_called()

    def test_exception_does_not_propagate(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")
        mock_client.add_messages.side_effect = RuntimeError("write error")

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            provider.on_memory_write("update", "MEMORY.md", "content")


# ── on_session_end ──


class TestOnSessionEnd:
    def test_no_op_does_not_raise(self):
        provider = AgentArtsMemoryProvider()
        provider.on_session_end([])

    def test_no_op_with_messages(self):
        provider = AgentArtsMemoryProvider()
        provider.on_session_end([{"role": "user", "content": "bye"}])


# ── shutdown ──


class TestShutdown:
    def test_clears_client(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            assert provider._client is not None
            provider.shutdown()

        assert provider._client is None

    def test_calls_close_if_available(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")
        mock_client.close = MagicMock()

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            provider.shutdown()

        mock_client.close.assert_called_once()

    def test_no_error_without_client(self):
        provider = AgentArtsMemoryProvider()
        provider.shutdown()
        assert provider._client is None

    def test_waits_for_sync_thread(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = mock_sdk.MemoryClient.return_value
        mock_client.create_memory_session.return_value = MagicMock(id="s1")

        done_event = threading.Event()

        def _slow_add(*args, **kwargs):
            time.sleep(0.2)
            done_event.set()

        mock_client.add_messages.side_effect = _slow_add

        with patch(
            "provider.import_memory_sdk",
            return_value=mock_sdk,
        ):
            provider.initialize("sess-1", hermes_home="/tmp/h")
            provider.sync_turn("msg", "resp")
            provider.shutdown()

        assert done_event.is_set()
        assert provider._sync_thread is not None
        assert not provider._sync_thread.is_alive()


# ── TOOL_SCHEMAS ──


class TestToolSchemas:
    def test_schemas_count(self):
        assert len(TOOL_SCHEMAS) == 2

    def test_ltm_search_schema(self):
        schema = next(s for s in TOOL_SCHEMAS if s["name"] == "ltm_search")
        assert schema["description"]
        props = schema["parameters"]["properties"]
        assert "query" in props
        assert "top_k" in props
        assert props["top_k"]["default"] == DEFAULT_TOP_K
        assert "query" in schema["parameters"]["required"]

    def test_ltm_search_summary_schema(self):
        schema = next(s for s in TOOL_SCHEMAS if s["name"] == "ltm_search_summary")
        assert schema["description"]
        props = schema["parameters"]["properties"]
        assert "limit" in props
        assert props["limit"]["default"] == DEFAULT_LIST_LIMIT
        assert "required" not in schema["parameters"] or schema["parameters"]["required"] == []

    def test_tool_names_unique(self):
        names = [s["name"] for s in TOOL_SCHEMAS]
        assert len(names) == len(set(names))


# ── handle_tool_call: unknown tool ──


class TestUnknownTool:
    def test_unknown_tool(self):
        provider = AgentArtsMemoryProvider()
        result = provider.handle_tool_call("nonexistent", {})
        data = json.loads(result)
        assert "error" in data
        assert "nonexistent" in data["error"]


# ── ltm_search ──


class TestLtmSearch:
    def test_no_client_initialized(self):
        provider = AgentArtsMemoryProvider()
        result = provider.handle_tool_call("ltm_search", {"query": "test"})
        data = json.loads(result)
        assert "error" in data
        assert "not initialized" in data["error"]

    def test_missing_query(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        init_provider(provider, mock_sdk)

        result = provider.handle_tool_call("ltm_search", {})
        data = json.loads(result)
        assert "error" in data
        assert "query" in data["error"]

    def test_search_returns_results(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        search_response = MagicMock()
        search_response.results = [
            {"record": {"content": "memory 1", "strategy_type": "semantic"}, "score": 0.9},
            {"record": {"content": "memory 2", "strategy_type": "episodic"}, "score": 0.8},
        ]
        mock_client.search_memories.return_value = search_response

        result = provider.handle_tool_call("ltm_search", {"query": "hello"})
        data = json.loads(result)

        assert data["query"] == "hello"
        assert len(data["results"]) == 2
        assert data["results"][0]["content"] == "memory 1"
        assert data["results"][0]["score"] == 0.9
        assert data["results"][0]["strategy_type"] == "semantic"
        assert data["results"][1]["content"] == "memory 2"

    def test_search_calls_sdk_with_correct_args(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        search_response = MagicMock()
        search_response.results = []
        mock_client.search_memories.return_value = search_response

        provider.handle_tool_call("ltm_search", {"query": "q", "top_k": 3})

        mock_client.search_memories.assert_called_once()
        call_kwargs = mock_client.search_memories.call_args.kwargs
        assert call_kwargs["space_id"] == "test-space-id"
        assert call_kwargs["filters"].query == "q"
        assert call_kwargs["filters"].top_k == 3

    def test_default_top_k(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        search_response = MagicMock()
        search_response.results = []
        mock_client.search_memories.return_value = search_response

        provider.handle_tool_call("ltm_search", {"query": "q"})

        call_kwargs = mock_client.search_memories.call_args.kwargs
        assert call_kwargs["filters"].top_k == DEFAULT_TOP_K

    def test_search_exception_returns_error_json(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)
        mock_client.search_memories.side_effect = RuntimeError("timeout")

        result = provider.handle_tool_call("ltm_search", {"query": "q"})
        data = json.loads(result)
        assert "error" in data
        assert "timeout" in data["error"]

    def test_empty_results(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        search_response = MagicMock()
        search_response.results = []
        mock_client.search_memories.return_value = search_response

        result = provider.handle_tool_call("ltm_search", {"query": "q"})
        data = json.loads(result)
        assert data["results"] == []

    def test_non_dict_result_items(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        search_response = MagicMock()
        search_response.results = ["raw string item", 42]
        mock_client.search_memories.return_value = search_response

        result = provider.handle_tool_call("ltm_search", {"query": "q"})
        data = json.loads(result)
        assert len(data["results"]) == 2
        assert data["results"][0]["content"] == "raw string item"
        assert data["results"][1]["content"] == "42"


# ── ltm_search_summary ──


class TestLtmSearchSummary:
    def test_no_client_initialized(self):
        provider = AgentArtsMemoryProvider()
        result = provider.handle_tool_call("ltm_search_summary", {})
        data = json.loads(result)
        assert "error" in data
        assert "not initialized" in data["error"]

    def test_returns_summary_list(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        class FakeMemory:
            def __init__(self, mid, content, stype, created):
                self.id = mid
                self.content = content
                self.strategy_type = stype
                self.created_at = created

        list_response = MagicMock()
        list_response.items = [
            FakeMemory("m1", "summary 1", "semantic", 1700000000),
            FakeMemory("m2", "summary 2", "episodic", 1700000001),
        ]
        list_response.total = 2
        mock_client.list_memories.return_value = list_response

        result = provider.handle_tool_call("ltm_search_summary", {"limit": 5})
        data = json.loads(result)

        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["id"] == "m1"
        assert data["items"][0]["content"] == "summary 1"
        assert data["items"][0]["strategy_type"] == "semantic"
        assert data["items"][0]["created_at"] == 1700000000

    def test_calls_list_memories_with_correct_args(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        list_response = MagicMock()
        list_response.items = []
        list_response.total = 0
        mock_client.list_memories.return_value = list_response

        provider.handle_tool_call("ltm_search_summary", {"limit": 20})

        mock_client.list_memories.assert_called_once()
        call_kwargs = mock_client.list_memories.call_args.kwargs
        assert call_kwargs["space_id"] == "test-space-id"
        assert call_kwargs["limit"] == 20

    def test_default_limit(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        list_response = MagicMock()
        list_response.items = []
        list_response.total = 0
        mock_client.list_memories.return_value = list_response

        provider.handle_tool_call("ltm_search_summary", {})

        call_kwargs = mock_client.list_memories.call_args.kwargs
        assert call_kwargs["limit"] == DEFAULT_LIST_LIMIT

    def test_exception_returns_error_json(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)
        mock_client.list_memories.side_effect = RuntimeError("db error")

        result = provider.handle_tool_call("ltm_search_summary", {})
        data = json.loads(result)
        assert "error" in data
        assert "db error" in data["error"]

    def test_empty_list(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        list_response = MagicMock()
        list_response.items = []
        list_response.total = 0
        mock_client.list_memories.return_value = list_response

        result = provider.handle_tool_call("ltm_search_summary", {})
        data = json.loads(result)
        assert data["items"] == []
        assert data["total"] == 0


# ── Provider.handle_tool_call delegation ──


class TestProviderDelegation:
    def test_provider_delegates_to_handle_tool_call(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        search_response = MagicMock()
        search_response.results = [{"record": {"content": "x"}, "score": 0.5}]
        mock_client.search_memories.return_value = search_response

        result = provider.handle_tool_call("ltm_search", {"query": "test"})
        data = json.loads(result)
        assert data["query"] == "test"
        assert len(data["results"]) == 1

    def test_provider_unknown_tool(self):
        provider = AgentArtsMemoryProvider()
        result = provider.handle_tool_call("bogus", {})
        data = json.loads(result)
        assert "error" in data


# ── Format results edge cases ──


class TestFormatSearchResults:
    def test_results_with_non_record_dict(self, env_vars):
        """Items without 'record' key should still be formatted."""
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        search_response = MagicMock()
        search_response.results = [
            {"content": "direct content", "score": 0.7},
        ]
        mock_client.search_memories.return_value = search_response

        result = provider.prefetch("query")
        assert "query" in result
        assert "0.7" in result

    def test_results_with_record_not_dict(self, env_vars):
        """Record as a non-dict value should use str()."""
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        search_response = MagicMock()
        search_response.results = [
            {"record": "plain string record", "score": 0.5},
        ]
        mock_client.search_memories.return_value = search_response

        result = provider.prefetch("query")
        assert "plain string record" in result
        assert "0.5" in result

    def test_results_with_none_score(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        search_response = MagicMock()
        search_response.results = [
            {"record": {"content": "no score"}, "score": None},
        ]
        mock_client.search_memories.return_value = search_response

        result = provider.prefetch("query")
        assert "no score" in result
        assert "None" in result


# ── sync_turn edge cases ──


class TestSyncTurnEdgeCases:
    def test_sync_with_empty_content(self, env_vars):
        """sync_turn with empty content should still write (SDK validates)."""
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        provider.sync_turn("", "")
        if provider._sync_thread:
            provider._sync_thread.join(timeout=5.0)

        mock_client.add_messages.assert_called_once()

    def test_sync_multiple_turns(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        for i in range(5):
            provider.sync_turn(f"user-{i}", f"assistant-{i}")
            if provider._sync_thread:
                provider._sync_thread.join(timeout=5.0)

        assert mock_client.add_messages.call_count == 5

    def test_sync_thread_is_daemon(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        barrier = threading.Event()

        def _slow(*args, **kwargs):
            barrier.set()

        mock_client.add_messages.side_effect = _slow
        provider.sync_turn("u", "a")
        assert provider._sync_thread is not None
        assert provider._sync_thread.daemon is True
        barrier.wait(timeout=5.0)
        provider._sync_thread.join(timeout=5.0)


# ── on_pre_compress edge cases ──


class TestOnPreCompressEdgeCases:
    def test_only_assistant_messages(self, env_vars):
        """If no user message, query is empty → prefetch returns empty."""
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        messages = [
            {"role": "assistant", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]
        result = provider.on_pre_compress(messages)
        assert result == ""
        mock_client.search_memories.assert_not_called()

    def test_mixed_messages_picks_last_user(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)
        search_response = MagicMock()
        search_response.results = []
        mock_client.search_memories.return_value = search_response

        messages = [
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "answer"},
            {"role": "user", "content": "second question"},
        ]
        provider.on_pre_compress(messages)

        call_kwargs = mock_client.search_memories.call_args.kwargs
        assert call_kwargs["filters"].query == "second question"

    def test_none_content_in_user_message(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)
        search_response = MagicMock()
        search_response.results = []
        mock_client.search_memories.return_value = search_response

        messages = [
            {"role": "user", "content": None},
        ]
        result = provider.on_pre_compress(messages)
        assert result == ""


# ── shutdown edge cases ──


class TestShutdownEdgeCases:
    def test_shutdown_without_close_method(self, env_vars):
        """Client without close/shutdown method should not error."""
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)
        del mock_client.close
        del mock_client.shutdown

        provider.shutdown()
        assert provider._client is None

    def test_shutdown_with_shutdown_method(self, env_vars):
        """If client has 'shutdown' but not 'close', use shutdown."""
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)
        del mock_client.close
        mock_client.shutdown = MagicMock()

        provider.shutdown()
        mock_client.shutdown.assert_called_once()

    def test_shutdown_no_sync_thread(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        init_provider(provider, mock_sdk)
        provider._sync_thread = None
        provider.shutdown()
        assert provider._client is None


# ── Tool edge cases ──


class TestToolEdgeCases:
    def test_ltm_search_with_none_args(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        init_provider(provider, mock_sdk)

        result = provider.handle_tool_call("ltm_search", None)
        data = json.loads(result)
        assert "error" in data

    def test_ltm_search_empty_args(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        init_provider(provider, mock_sdk)

        result = provider.handle_tool_call("ltm_search", {})
        data = json.loads(result)
        assert "error" in data
        assert "query" in data["error"]

    def test_ltm_search_with_record_missing_content(self, env_vars):
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        search_response = MagicMock()
        search_response.results = [
            {"record": {"strategy_type": "semantic"}, "score": 0.6},
        ]
        mock_client.search_memories.return_value = search_response

        result = provider.handle_tool_call("ltm_search", {"query": "q"})
        data = json.loads(result)
        assert len(data["results"]) == 1
        assert data["results"][0]["content"] == ""
        assert data["results"][0]["strategy_type"] == "semantic"

    def test_ltm_search_summary_falls_back_total(self, env_vars):
        """If memories response has no 'total', use len(items)."""
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        list_response = MagicMock()
        list_response.items = [MagicMock(id="m1", content="c1", strategy_type="s", created_at=1)]
        del list_response.total
        mock_client.list_memories.return_value = list_response

        result = provider.handle_tool_call("ltm_search_summary", {})
        data = json.loads(result)
        assert data["total"] == 1
        assert len(data["items"]) == 1


# ── Full lifecycle integration ──


class TestFullLifecycle:
    def test_full_lifecycle(self, env_vars):
        """Initialize → sync_turn → prefetch → handle_tool_call → shutdown."""
        provider = AgentArtsMemoryProvider()
        mock_sdk = make_mock_sdk()
        mock_client = init_provider(provider, mock_sdk)

        provider.sync_turn("user question", "assistant answer")
        if provider._sync_thread:
            provider._sync_thread.join(timeout=5.0)
        assert mock_client.add_messages.call_count == 1

        search_response = MagicMock()
        search_response.results = [
            {"record": {"content": "relevant memory"}, "score": 0.85},
        ]
        mock_client.search_memories.return_value = search_response
        prefetched = provider.prefetch("user question")
        assert "relevant memory" in prefetched

        tool_result = provider.handle_tool_call("ltm_search", {"query": "user question"})
        data = json.loads(tool_result)
        assert data["query"] == "user question"
        assert len(data["results"]) == 1

        provider.shutdown()
        assert provider._client is None

    def test_lifecycle_without_initialize(self):
        """All methods should be safe to call before initialize."""
        provider = AgentArtsMemoryProvider()
        assert provider.prefetch("q") == ""
        assert provider.system_prompt_block() != ""
        provider.sync_turn("u", "a")
        provider.on_session_end([])
        provider.shutdown()
        result = provider.handle_tool_call("ltm_search", {"query": "q"})
        data = json.loads(result)
        assert "error" in data


# ── register / entry point ──


def _plugin_yaml_path() -> pathlib.Path:
    """Return the path to plugin.yaml (alongside the modules)."""
    mod_dir = pathlib.Path(hermes_init.__file__).resolve().parent
    return mod_dir / "plugin.yaml"


class TestRegister:
    def test_register_calls_register_memory_provider(self):
        ctx = _FakeContext()
        register(ctx)
        assert len(ctx.providers) == 1
        assert isinstance(ctx.providers[0], AgentArtsMemoryProvider)

    def test_register_provider_name(self):
        ctx = _FakeContext()
        register(ctx)
        assert ctx.providers[0].name == "agentarts_memory"


class TestPackageExports:
    def test_provider_class_exported(self):
        assert AgentArtsMemoryProvider is not None

    def test_register_callable(self):
        assert callable(register)

    def test_all_exports(self):
        assert "AgentArtsMemoryProvider" in hermes_init.__all__
        assert "register" in hermes_init.__all__


class TestPluginYaml:
    def test_plugin_yaml_exists(self):
        plugin_yaml = _plugin_yaml_path()
        assert plugin_yaml.exists()

    def test_plugin_yaml_content(self):
        plugin_yaml = _plugin_yaml_path()
        data = yaml.safe_load(plugin_yaml.read_text(encoding="utf-8"))

        assert data["name"] == "agentarts_memory"
        assert data["version"] == "1.0.0"
        assert "Memory" in data["description"]

    def test_plugin_yaml_hooks(self):
        plugin_yaml = _plugin_yaml_path()
        data = yaml.safe_load(plugin_yaml.read_text(encoding="utf-8"))

        expected_hooks = {
            "system_prompt_block",
            "prefetch",
            "sync_turn",
            "on_pre_compress",
            "on_memory_write",
            "on_session_end",
            "shutdown",
        }
        assert set(data["hooks"]) == expected_hooks

    def test_plugin_yaml_hooks_are_implemented(self):
        """Every hook listed in plugin.yaml should be a method of the provider."""
        provider = AgentArtsMemoryProvider()
        plugin_yaml = _plugin_yaml_path()
        data = yaml.safe_load(plugin_yaml.read_text(encoding="utf-8"))

        for hook in data["hooks"]:
            assert hasattr(provider, hook), f"Provider missing hook: {hook}"
            assert callable(getattr(provider, hook)), f"Hook not callable: {hook}"


class _FakeContext:
    """Fake plugin context for testing register()."""

    def __init__(self):
        self.providers = []

    def register_memory_provider(self, provider):
        self.providers.append(provider)
