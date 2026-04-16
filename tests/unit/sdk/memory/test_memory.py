"""Tests for memory module"""



def test_memory_client_import():
    """Test that MemoryClient can be imported"""
    from agentarts.sdk import MemoryClient

    assert MemoryClient is not None


def test_memory_client_creation():
    """Test MemoryClient creation"""
    from agentarts.sdk import MemoryClient

    client = MemoryClient(region_name="cn-north-4", api_key="test-api-key")

    assert client is not None


def test_memory_types_import():
    """Test that memory types can be imported"""
    from agentarts.sdk.memory import (
        MessageRequest,
        SessionCreateRequest,
        SpaceCreateRequest,
        SpaceUpdateRequest,
    )

    assert SpaceCreateRequest is not None
    assert SpaceUpdateRequest is not None
    assert SessionCreateRequest is not None
    assert MessageRequest is not None
