"""Tests for memory module"""

import pytest


@pytest.mark.asyncio
async def test_short_term_memory():
    """Test ShortTermMemory"""
    from agentarts.wrapper.memory import ShortTermMemory
    
    memory = ShortTermMemory(max_size=10)
    
    memory_id = await memory.save("test_key", "test_value")
    assert memory_id is not None
    
    results = await memory.retrieve("test")
    assert len(results) > 0
    assert results[0]["value"] == "test_value"


@pytest.mark.asyncio
async def test_memory_clear():
    """Test memory clear"""
    from agentarts.wrapper.memory import ShortTermMemory
    
    memory = ShortTermMemory(max_size=10)
    
    await memory.save("key1", "value1")
    await memory.save("key2", "value2")
    
    all_memories = await memory.get_all()
    assert len(all_memories) == 2
    
    await memory.clear()
    all_memories = await memory.get_all()
    assert len(all_memories) == 0
