"""Tests for core module"""



def test_import_sdk():
    """Test that SDK can be imported"""
    import agentarts.sdk

    assert hasattr(agentarts.sdk, "__version__")
    assert hasattr(agentarts.sdk, "__author__")


def test_import_memory_client():
    """Test that MemoryClient can be imported"""
    from agentarts.sdk import MemoryClient

    assert MemoryClient is not None


def test_import_code_interpreter():
    """Test that CodeInterpreter can be imported"""
    from agentarts.sdk import CodeInterpreter

    assert CodeInterpreter is not None


def test_import_identity_client():
    """Test that IdentityClient can be imported"""
    from agentarts.sdk import IdentityClient

    assert IdentityClient is not None
