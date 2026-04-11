"""
Unit tests for AgentArts LangGraph Integration

Tests are designed to work with mocked dependencies.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys


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
        
        with pytest.raises(ValueError, match="thread_id is required"):
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
        assert hasattr(AgentArtsMemorySessionSaver, 'get_tuple')
        assert hasattr(AgentArtsMemorySessionSaver, 'put')
        assert hasattr(AgentArtsMemorySessionSaver, 'list')
        assert hasattr(AgentArtsMemorySessionSaver, 'delete')
        assert hasattr(AgentArtsMemorySessionSaver, 'put_writes')
        
        # Check async methods
        assert hasattr(AgentArtsMemorySessionSaver, 'aget_tuple')
        assert hasattr(AgentArtsMemorySessionSaver, 'aput')
        assert hasattr(AgentArtsMemorySessionSaver, 'alist')
        assert hasattr(AgentArtsMemorySessionSaver, 'adelete')
        assert hasattr(AgentArtsMemorySessionSaver, 'aput_writes')

    def test_saver_properties(self):
        """Test that properties exist"""
        from agentarts.sdk.integration.langgraph.saver import AgentArtsMemorySessionSaver
        
        assert hasattr(AgentArtsMemorySessionSaver, 'space_id')
        assert hasattr(AgentArtsMemorySessionSaver, 'region')
        assert hasattr(AgentArtsMemorySessionSaver, 'max_messages')


class TestIntegrationModule:
    """Tests for integration module exports"""

    def test_module_exports(self):
        """Test that module exports expected classes and functions"""
        from agentarts.sdk.integration.langgraph import (
            AgentArtsMemorySessionSaver,
            CheckpointerConfig,
            langgraph_to_memory_message,
            memory_to_langgraph_message,
            langgraph_messages_to_memory,
            memory_messages_to_langgraph,
        )
        
        assert AgentArtsMemorySessionSaver is not None
        assert CheckpointerConfig is not None
        assert langgraph_to_memory_message is not None
        assert memory_to_langgraph_message is not None
        assert langgraph_messages_to_memory is not None
        assert memory_messages_to_langgraph is not None