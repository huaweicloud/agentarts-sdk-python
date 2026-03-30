"""Tests for core module"""

import pytest


def test_import():
    """Test that core module can be imported"""
    from agentarts.wrapper.runtime import AgentRuntime
    from agentarts.wrapper.runtime.context import Context
    from agentarts.wrapper.runtime.config import Config
    
    assert AgentRuntime is not None
    assert Context is not None
    assert Config is not None


@pytest.mark.asyncio
async def test_context():
    """Test Context creation and operations"""
    from agentarts.wrapper.runtime.context import Context
    
    context = Context()
    assert context.session_id is not None
    
    context.set("key", "value")
    assert context.get("key") == "value"
    assert context.get("nonexistent", "default") == "default"


def test_config():
    """Test Config creation"""
    from agentarts.wrapper.runtime.config import Config
    
    config = Config()
    assert config is not None
