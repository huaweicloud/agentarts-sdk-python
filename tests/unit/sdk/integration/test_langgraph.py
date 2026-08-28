"""
Unit tests for AgentArts LangGraph Integration

Tests are designed to work with mocked dependencies.
"""


import pytest


class TestCheckpointerConfig:
    """Tests for CheckpointerConfig"""

    def test_from_runnable_config_basic(self):
        """Test creating CheckpointerConfig from RunnableConfig"""
        from agentarts.sdk.integration.langgraph.config import CheckpointerConfig

        runnable_config = {
            "configurable": {
                "thread_id": "conv-123",
                "actor_id": "user-456",
                "checkpoint_id": "cp-789",
            }
        }

        config = CheckpointerConfig.from_runnable_config(runnable_config)

        assert config.thread_id == "conv-123"
        assert config.actor_id == "user-456"
        assert config.checkpoint_id == "cp-789"

    def test_from_runnable_config_missing_thread_id(self):
        """Test that missing thread_id raises ValueError"""
        from agentarts.sdk.integration.langgraph.config import CheckpointerConfig

        runnable_config = {"configurable": {}}

        with pytest.raises(ValueError):
            CheckpointerConfig.from_runnable_config(runnable_config)

    def test_from_runnable_config_empty_configurable(self):
        """Test with empty configurable dict"""
        from agentarts.sdk.integration.langgraph.config import CheckpointerConfig

        runnable_config = {}

        with pytest.raises(ValueError):
            CheckpointerConfig.from_runnable_config(runnable_config)

    def test_session_id_property(self):
        """Test that session_id returns thread_id"""
        from agentarts.sdk.integration.langgraph.config import CheckpointerConfig

        config = CheckpointerConfig(
            thread_id="test-thread",
            actor_id="test-actor",
        )

        assert config.session_id == "test-thread"

    def test_to_runnable_config(self):
        """Test converting back to RunnableConfig"""
        from agentarts.sdk.integration.langgraph.config import CheckpointerConfig

        config = CheckpointerConfig(
            thread_id="conv-123",
            actor_id="user-456",
            checkpoint_id="cp-789",
            checkpoint_ns="ns-1",
        )

        result = config.to_runnable_config()

        assert result["configurable"]["thread_id"] == "conv-123"
        assert result["configurable"]["actor_id"] == "user-456"
        assert result["configurable"]["checkpoint_id"] == "cp-789"
        assert result["configurable"]["checkpoint_ns"] == "ns-1"

    def test_to_runnable_config_minimal(self):
        """Test converting minimal config to RunnableConfig"""
        from agentarts.sdk.integration.langgraph.config import CheckpointerConfig

        config = CheckpointerConfig(thread_id="test-thread")

        result = config.to_runnable_config()

        assert result["configurable"]["thread_id"] == "test-thread"


class TestMessageConverter:
    """Tests for message conversion between LangGraph and Memory"""

    def test_langchain_available_check(self):
        """Test that LANGCHAIN_AVAILABLE is properly set"""
        from agentarts.sdk.integration.langgraph.converter import LANGCHAIN_AVAILABLE

        # Just check it's a boolean
        assert isinstance(LANGCHAIN_AVAILABLE, bool)

    def test_text_message_creation(self):
        """Test creating TextMessage"""
        from agentarts.sdk.memory import TextMessage

        msg = TextMessage(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_tool_call_message_creation(self):
        """Test creating ToolCallMessage"""
        from agentarts.sdk.memory import ToolCallMessage

        msg = ToolCallMessage(id="call-123", name="search", arguments='{"query": "test"}')

        assert msg.id == "call-123"
        assert msg.name == "search"

    def test_tool_result_message_creation(self):
        """Test creating ToolResultMessage"""
        from agentarts.sdk.memory import ToolResultMessage

        msg = ToolResultMessage(tool_call_id="call-123", content="Result")

        assert msg.tool_call_id == "call-123"
        assert msg.content == "Result"


class TestAgentArtsMemorySessionSaver:
    """Tests for AgentArtsMemorySessionSaver"""

    def test_import_saver(self):
        """Test that saver module can be imported"""
        from agentarts.sdk.integration.langgraph.saver import AgentArtsMemorySessionSaver

        assert AgentArtsMemorySessionSaver is not None

    def test_saver_methods_exist(self):
        """Test that required methods exist"""
        from agentarts.sdk.integration.langgraph.saver import AgentArtsMemorySessionSaver

        # Check sync methods
        assert hasattr(AgentArtsMemorySessionSaver, "get_tuple")
        assert hasattr(AgentArtsMemorySessionSaver, "put")
        assert hasattr(AgentArtsMemorySessionSaver, "list")
        assert hasattr(AgentArtsMemorySessionSaver, "delete_thread")
        assert hasattr(AgentArtsMemorySessionSaver, "put_writes")

        # Check async methods
        assert hasattr(AgentArtsMemorySessionSaver, "aget_tuple")
        assert hasattr(AgentArtsMemorySessionSaver, "aput")
        assert hasattr(AgentArtsMemorySessionSaver, "alist")
        assert hasattr(AgentArtsMemorySessionSaver, "adelete_thread")
        assert hasattr(AgentArtsMemorySessionSaver, "aput_writes")

    def test_saver_properties(self):
        """Test that properties exist"""
        from agentarts.sdk.integration.langgraph.saver import AgentArtsMemorySessionSaver

        assert hasattr(AgentArtsMemorySessionSaver, "space_id")
        assert hasattr(AgentArtsMemorySessionSaver, "region")
        assert hasattr(AgentArtsMemorySessionSaver, "max_messages")


class TestIntegrationModule:
    """Tests for integration module exports"""

    def test_module_exports(self):
        """Test that module exports expected classes and functions"""
        from agentarts.sdk.integration.langgraph import (
            AgentArtsMemorySessionSaver,
            CheckpointerConfig,
            langgraph_messages_to_memory,
            langgraph_to_memory_message,
            memory_messages_to_langgraph,
            memory_to_langgraph_message,
        )

        assert AgentArtsMemorySessionSaver is not None
        assert CheckpointerConfig is not None
        assert langgraph_to_memory_message is not None
        assert memory_to_langgraph_message is not None
        assert langgraph_messages_to_memory is not None
        assert memory_messages_to_langgraph is not None


class TestMessageMetaField:
    """Tests for message meta field support."""

    def test_text_message_with_meta(self):
        """Test creating TextMessage with meta field."""
        from agentarts.sdk.memory import TextMessage

        msg = TextMessage(role="user", content="Hello", meta='{"key": "value"}')

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.meta == '{"key": "value"}'

    def test_tool_call_message_with_meta(self):
        """Test creating ToolCallMessage with meta field."""
        from agentarts.sdk.memory import ToolCallMessage

        msg = ToolCallMessage(
            id="call-123",
            name="search",
            arguments='{"query": "test"}',
            meta='{"checkpoint_id": "cp-456"}',
        )

        assert msg.id == "call-123"
        assert msg.name == "search"
        assert msg.meta == '{"checkpoint_id": "cp-456"}'

    def test_tool_result_message_with_meta(self):
        """Test creating ToolResultMessage with meta field."""
        from agentarts.sdk.memory import ToolResultMessage

        msg = ToolResultMessage(
            tool_call_id="call-123",
            content="Result",
            meta='{"checkpoint_ts": "2024-01-01T00:00:00"}',
        )

        assert msg.tool_call_id == "call-123"
        assert msg.content == "Result"
        assert msg.meta == '{"checkpoint_ts": "2024-01-01T00:00:00"}'

    def test_text_message_to_dict_includes_meta(self):
        """Test that to_dict includes meta field."""
        from agentarts.sdk.memory import TextMessage

        msg = TextMessage(role="user", content="Hello", meta='{"key": "value"}')
        result = msg.to_dict()

        assert "meta" in result
        assert result["meta"] == '{"key": "value"}'

    def test_text_message_to_dict_excludes_none_meta(self):
        """Test that to_dict excludes meta when None."""
        from agentarts.sdk.memory import TextMessage

        msg = TextMessage(role="user", content="Hello")
        result = msg.to_dict()

        assert "meta" not in result


class TestAdditionalKwargsPreservation:
    """Tests for additional_kwargs / response_metadata preservation in converter."""

    # --- _parse_meta helper ---

    def test_parse_meta_none(self):
        from agentarts.sdk.integration.langgraph.converter import _parse_meta

        assert _parse_meta(None) == {}

    def test_parse_meta_empty_string(self):
        from agentarts.sdk.integration.langgraph.converter import _parse_meta

        assert _parse_meta("") == {}

    def test_parse_meta_json_string(self):
        from agentarts.sdk.integration.langgraph.converter import _parse_meta

        assert _parse_meta('{"step":1}') == {"step": 1}

    def test_parse_meta_empty_json_string(self):
        from agentarts.sdk.integration.langgraph.converter import _parse_meta

        assert _parse_meta("{}") == {}

    def test_parse_meta_dict(self):
        from agentarts.sdk.integration.langgraph.converter import _parse_meta

        assert _parse_meta({"step": 1}) == {"step": 1}

    def test_parse_meta_non_json_string(self):
        from agentarts.sdk.integration.langgraph.converter import _parse_meta

        assert _parse_meta("not json") == {}

    def test_parse_meta_json_array_string(self):
        """JSON array is valid JSON but not a dict -- should return {}."""
        from agentarts.sdk.integration.langgraph.converter import _parse_meta

        assert _parse_meta("[1, 2, 3]") == {}

    # --- _build_meta helper ---

    def test_build_meta_none_caller_no_kwargs(self):
        from agentarts.sdk.integration.langgraph.converter import _build_meta

        assert _build_meta(None) is None

    def test_build_meta_caller_only(self):
        """Caller meta without LangChain fields is re-serialized unchanged."""
        import json

        from agentarts.sdk.integration.langgraph.converter import _build_meta

        result = _build_meta('{"step":1}')
        assert json.loads(result) == {"step": 1}

    def test_build_meta_with_additional_kwargs(self):
        import json

        from agentarts.sdk.integration.langgraph.converter import _build_meta

        result = _build_meta(
            '{"step":1}',
            additional_kwargs={"reasoning_content": "thinking"},
        )
        parsed = json.loads(result)
        assert parsed["step"] == 1
        assert parsed["_lc_additional_kwargs"] == {"reasoning_content": "thinking"}

    def test_build_meta_with_response_metadata(self):
        import json

        from agentarts.sdk.integration.langgraph.converter import _build_meta

        result = _build_meta(
            None,
            response_metadata={"model_name": "deepseek-v3.2"},
        )
        parsed = json.loads(result)
        assert parsed["_lc_response_metadata"] == {"model_name": "deepseek-v3.2"}

    def test_build_meta_with_extra(self):
        import json

        from agentarts.sdk.integration.langgraph.converter import _build_meta

        result = _build_meta(
            None,
            extra={"_lc_content": "some text"},
        )
        parsed = json.loads(result)
        assert parsed["_lc_content"] == "some text"

    def test_build_meta_empty_additional_kwargs_not_stored(self):
        """Empty dict additional_kwargs should not be stored (falsy)."""
        import json

        from agentarts.sdk.integration.langgraph.converter import _build_meta

        result = _build_meta('{"step":1}', additional_kwargs={})
        parsed = json.loads(result)
        assert "_lc_additional_kwargs" not in parsed

    # --- AIMessage round-trip ---

    def test_ai_message_round_trip_additional_kwargs(self):
        """AIMessage with reasoning_content survives a full round-trip."""
        from langchain_core.messages import AIMessage

        from agentarts.sdk.integration.langgraph.converter import (
            langgraph_to_memory_message,
            memory_to_langgraph_message,
        )
        from agentarts.sdk.memory import MessageInfo

        original = AIMessage(
            content="Hello",
            additional_kwargs={"reasoning_content": "user is greeting"},
        )
        mem_msg = langgraph_to_memory_message(original, meta='{"step":1}')

        msg_info = MessageInfo(
            id="1", session_id="s1", seq=0, role="assistant",
            parts=[{"type": "text", "text": "Hello"}],
            meta=mem_msg.meta,
        )
        restored = memory_to_langgraph_message(msg_info)

        assert restored.content == "Hello"
        assert restored.additional_kwargs == {"reasoning_content": "user is greeting"}

    def test_ai_message_round_trip_response_metadata(self):
        """AIMessage response_metadata (model_name, finish_reason) survives round-trip."""
        from langchain_core.messages import AIMessage

        from agentarts.sdk.integration.langgraph.converter import (
            langgraph_to_memory_message,
            memory_to_langgraph_message,
        )
        from agentarts.sdk.memory import MessageInfo

        original = AIMessage(
            content="Answer",
            response_metadata={"model_name": "deepseek-v3.2", "finish_reason": "stop"},
        )
        mem_msg = langgraph_to_memory_message(original)

        msg_info = MessageInfo(
            id="1", session_id="s1", seq=0, role="assistant",
            parts=[{"type": "text", "text": "Answer"}],
            meta=mem_msg.meta,
        )
        restored = memory_to_langgraph_message(msg_info)

        assert restored.response_metadata == {"model_name": "deepseek-v3.2", "finish_reason": "stop"}

    def test_ai_message_with_tool_calls_preserves_content(self):
        """AIMessage with both text and tool_calls preserves content in _lc_content."""
        import json

        from langchain_core.messages import AIMessage

        from agentarts.sdk.integration.langgraph.converter import (
            langgraph_to_memory_message,
            memory_to_langgraph_message,
        )
        from agentarts.sdk.memory import MessageInfo

        original = AIMessage(
            content="Let me check the weather",
            tool_calls=[{"id": "tc1", "name": "get_weather", "args": {"city": "Tokyo"}}],
            additional_kwargs={"reasoning_content": "user wants weather"},
        )
        mem_msg = langgraph_to_memory_message(original, meta='{"step":2}')

        # Verify content stored in meta
        parsed = json.loads(mem_msg.meta)
        assert parsed["_lc_content"] == "Let me check the weather"

        # Simulate backend round-trip
        msg_info = MessageInfo(
            id="2", session_id="s1", seq=1, role="tool",
            parts=[{
                "type": "tool_call",
                "tool_call": {
                    "id": "tc1",
                    "name": "get_weather",
                    "arguments": json.dumps({"city": "Tokyo"}),
                },
            }],
            meta=mem_msg.meta,
        )
        restored = memory_to_langgraph_message(msg_info)

        assert restored.content == "Let me check the weather"
        assert restored.additional_kwargs == {"reasoning_content": "user wants weather"}
        assert restored.tool_calls[0]["name"] == "get_weather"

    def test_ai_message_with_tool_calls_no_content(self):
        """AIMessage with tool_calls but empty content -- _lc_content not stored."""
        from langchain_core.messages import AIMessage

        from agentarts.sdk.integration.langgraph.converter import langgraph_to_memory_message

        original = AIMessage(
            content="",
            tool_calls=[{"id": "tc1", "name": "search", "args": {"q": "test"}}],
        )
        mem_msg = langgraph_to_memory_message(original)

        # No content, no additional_kwargs, no response_metadata, no caller_meta
        # -> _build_meta returns None (nothing to store) -- correct behavior
        assert mem_msg.meta is None

    # --- Other message types round-trip ---

    def test_human_message_round_trip_additional_kwargs(self):
        from langchain_core.messages import HumanMessage

        from agentarts.sdk.integration.langgraph.converter import (
            langgraph_to_memory_message,
            memory_to_langgraph_message,
        )
        from agentarts.sdk.memory import MessageInfo

        original = HumanMessage(content="Question", additional_kwargs={"custom": "data"})
        mem_msg = langgraph_to_memory_message(original)

        msg_info = MessageInfo(
            id="1", session_id="s1", seq=0, role="user",
            parts=[{"type": "text", "text": "Question"}],
            meta=mem_msg.meta,
        )
        restored = memory_to_langgraph_message(msg_info)

        assert restored.content == "Question"
        assert restored.additional_kwargs == {"custom": "data"}

    def test_system_message_round_trip_additional_kwargs(self):
        from langchain_core.messages import SystemMessage

        from agentarts.sdk.integration.langgraph.converter import (
            langgraph_to_memory_message,
            memory_to_langgraph_message,
        )
        from agentarts.sdk.memory import MessageInfo

        original = SystemMessage(content="You are helpful", additional_kwargs={"key": "val"})
        mem_msg = langgraph_to_memory_message(original)

        msg_info = MessageInfo(
            id="1", session_id="s1", seq=0, role="system",
            parts=[{"type": "text", "text": "You are helpful"}],
            meta=mem_msg.meta,
        )
        restored = memory_to_langgraph_message(msg_info)

        assert restored.content == "You are helpful"
        assert restored.additional_kwargs == {"key": "val"}

    def test_tool_message_round_trip_additional_kwargs(self):
        from langchain_core.messages import ToolMessage

        from agentarts.sdk.integration.langgraph.converter import (
            langgraph_to_memory_message,
            memory_to_langgraph_message,
        )
        from agentarts.sdk.memory import MessageInfo

        original = ToolMessage(
            content="Result data",
            tool_call_id="tc1",
            additional_kwargs={"name": "get_weather"},
        )
        mem_msg = langgraph_to_memory_message(original)

        msg_info = MessageInfo(
            id="1", session_id="s1", seq=0, role="tool",
            parts=[{
                "type": "tool_result",
                "tool_result": {"tool_call_id": "tc1", "content": "Result data"},
            }],
            meta=mem_msg.meta,
        )
        restored = memory_to_langgraph_message(msg_info)

        assert restored.content == "Result data"
        assert restored.tool_call_id == "tc1"
        assert restored.additional_kwargs == {"name": "get_weather"}

    # --- Backward compatibility ---

    def test_old_message_without_lc_keys(self):
        """Old messages without _lc_* keys restore with empty additional_kwargs."""
        from agentarts.sdk.integration.langgraph.converter import memory_to_langgraph_message
        from agentarts.sdk.memory import MessageInfo

        msg_info = MessageInfo(
            id="1", session_id="s1", seq=0, role="assistant",
            parts=[{"type": "text", "text": "old message"}],
            meta='{"step":1,"source":"loop"}',
        )
        restored = memory_to_langgraph_message(msg_info)

        assert restored.content == "old message"
        assert restored.additional_kwargs == {}
        assert restored.response_metadata == {}

    def test_old_message_meta_none(self):
        """Message with meta=None restores with empty additional_kwargs."""
        from agentarts.sdk.integration.langgraph.converter import memory_to_langgraph_message
        from agentarts.sdk.memory import MessageInfo

        msg_info = MessageInfo(
            id="1", session_id="s1", seq=0, role="user",
            parts=[{"type": "text", "text": "no meta"}],
            meta=None,
        )
        restored = memory_to_langgraph_message(msg_info)

        assert restored.additional_kwargs == {}

    def test_old_message_meta_non_json(self):
        """Message with non-JSON meta string does not crash."""
        from agentarts.sdk.integration.langgraph.converter import memory_to_langgraph_message
        from agentarts.sdk.memory import MessageInfo

        msg_info = MessageInfo(
            id="1", session_id="s1", seq=0, role="user",
            parts=[{"type": "text", "text": "bad meta"}],
            meta="not a json string",
        )
        restored = memory_to_langgraph_message(msg_info)

        assert restored.additional_kwargs == {}

    # --- Backend returning meta as dict ---

    def test_meta_returned_as_dict(self):
        """Backend may return meta as dict -- should work."""
        from agentarts.sdk.integration.langgraph.converter import memory_to_langgraph_message
        from agentarts.sdk.memory import MessageInfo

        msg_info = MessageInfo(
            id="1", session_id="s1", seq=0, role="assistant",
            parts=[{"type": "text", "text": "dict meta"}],
            meta={"step": 1, "_lc_additional_kwargs": {"reasoning_content": "from dict"}},
        )
        restored = memory_to_langgraph_message(msg_info)

        assert restored.content == "dict meta"
        assert restored.additional_kwargs == {"reasoning_content": "from dict"}

    # --- Saver checkpoint_meta coexistence ---

    def test_saver_checkpoint_meta_coexists_with_lc_keys(self):
        """Saver's checkpoint_meta keys and _lc_* keys coexist in the same JSON."""
        import json

        from langchain_core.messages import AIMessage

        from agentarts.sdk.integration.langgraph.converter import langgraph_to_memory_message

        checkpoint_meta = json.dumps({
            "step": 3,
            "source": "loop",
            "checkpoint_id": "cp-abc",
            "checkpoint_ts": "2026-01-01T00:00:00Z",
        })
        ai_msg = AIMessage(
            content="Response",
            additional_kwargs={"reasoning_content": "thinking"},
        )
        mem_msg = langgraph_to_memory_message(ai_msg, meta=checkpoint_meta)

        parsed = json.loads(mem_msg.meta)
        # Saver keys preserved
        assert parsed["step"] == 3
        assert parsed["source"] == "loop"
        assert parsed["checkpoint_id"] == "cp-abc"
        # LangChain keys added
        assert parsed["_lc_additional_kwargs"] == {"reasoning_content": "thinking"}

    def test_saver_reads_checkpoint_meta_from_merged(self):
        """Saver's reading logic (step/source) works on merged meta."""
        import json

        from langchain_core.messages import AIMessage

        from agentarts.sdk.integration.langgraph.converter import langgraph_to_memory_message

        checkpoint_meta = json.dumps({
            "step": 5,
            "source": "update",
            "checkpoint_id": "cp-xyz",
            "checkpoint_ts": "2026-01-01T12:00:00Z",
        })
        ai_msg = AIMessage(
            content="Hi",
            additional_kwargs={"reasoning_content": "reasoning"},
            response_metadata={"model_name": "test-model"},
        )
        mem_msg = langgraph_to_memory_message(ai_msg, meta=checkpoint_meta)

        # Simulate saver's get_tuple() reading logic
        meta = json.loads(mem_msg.meta)
        assert meta.get("step", 0) == 5
        assert meta.get("source", "loop") == "update"
        assert meta.get("checkpoint_id") == "cp-xyz"
        assert meta.get("checkpoint_ts") == "2026-01-01T12:00:00Z"

    # --- Empty additional_kwargs not stored ---

    def test_empty_additional_kwargs_not_stored(self):
        """Messages with empty additional_kwargs should not add _lc_additional_kwargs to meta."""
        import json

        from langchain_core.messages import AIMessage

        from agentarts.sdk.integration.langgraph.converter import langgraph_to_memory_message

        ai_msg = AIMessage(content="Hello")  # no additional_kwargs
        mem_msg = langgraph_to_memory_message(ai_msg, meta='{"step":1}')

        parsed = json.loads(mem_msg.meta)
        assert "_lc_additional_kwargs" not in parsed
        assert "_lc_response_metadata" not in parsed

    # --- No caller_meta with additional_kwargs ---

    def test_no_caller_meta_with_additional_kwargs(self):
        """When caller_meta is None but message has additional_kwargs, meta is created."""
        import json

        from langchain_core.messages import AIMessage

        from agentarts.sdk.integration.langgraph.converter import langgraph_to_memory_message

        ai_msg = AIMessage(
            content="Hello",
            additional_kwargs={"reasoning_content": "standalone"},
        )
        mem_msg = langgraph_to_memory_message(ai_msg, meta=None)

        assert mem_msg.meta is not None
        parsed = json.loads(mem_msg.meta)
        assert parsed["_lc_additional_kwargs"] == {"reasoning_content": "standalone"}


class TestConfigIsEmptyMethods:
    """Tests for is_empty() methods in config models."""

    def test_custom_jwt_auth_config_is_empty(self):
        """Test CustomJWTAuthConfig.is_empty() method."""
        from agentarts.toolkit.utils.runtime.config import CustomJWTAuthConfig

        config = CustomJWTAuthConfig()
        assert config.is_empty() is True

        config_with_url = CustomJWTAuthConfig(discovery_url="https://example.com")
        assert config_with_url.is_empty() is False

        config_with_audience = CustomJWTAuthConfig(allowed_audience=["aud1"])
        assert config_with_audience.is_empty() is False

    def test_auth_config_is_empty(self):
        """Test AuthConfig.is_empty() method."""
        from agentarts.toolkit.utils.runtime.config import (
            APIKeyAuthConfig,
            APIKeyPair,
            AuthConfig,
            CustomJWTAuthConfig,
        )

        config = AuthConfig()
        assert config.is_empty() is True

        config_with_jwt = AuthConfig(
            custom_jwt=CustomJWTAuthConfig(discovery_url="https://example.com")
        )
        assert config_with_jwt.is_empty() is False

        config_with_key = AuthConfig(
            key_auth=APIKeyAuthConfig(api_keys=[APIKeyPair(api_key="key1")])
        )
        assert config_with_key.is_empty() is False

    def test_inbound_identity_config_to_dict_excludes_empty(self):
        """Test InboundIdentityConfig.to_dict() excludes empty config."""
        from agentarts.toolkit.utils.runtime.config import (
            AuthConfig,
            InboundIdentityConfig,
        )

        config = InboundIdentityConfig(
            authorizer_type="IAM",
            authorizer_configuration=AuthConfig(),
        )

        result = config.to_dict()

        assert result["authorizer_type"] == "IAM"
        assert "authorizer_configuration" not in result

    def test_inbound_identity_config_to_dict_includes_non_empty(self):
        """Test InboundIdentityConfig.to_dict() includes non-empty config."""
        from agentarts.toolkit.utils.runtime.config import (
            AuthConfig,
            CustomJWTAuthConfig,
            InboundIdentityConfig,
        )

        config = InboundIdentityConfig(
            authorizer_type="CUSTOM_JWT",
            authorizer_configuration=AuthConfig(
                custom_jwt=CustomJWTAuthConfig(discovery_url="https://example.com")
            ),
        )

        result = config.to_dict()

        assert result["authorizer_type"] == "CUSTOM_JWT"
        assert "authorizer_configuration" in result
        assert "custom_jwt" in result["authorizer_configuration"]
