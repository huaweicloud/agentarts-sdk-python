"""Tests for tools module"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_code_interpreter_tool_definition():
    """Test CodeInterpreter tool definition"""
    from agentarts.wrapper.tools import CodeInterpreter
    
    interpreter = CodeInterpreter()
    tool_def = interpreter.to_tool_definition()
    
    assert tool_def["name"] == "code_interpreter"
    assert "parameters" in tool_def
    assert "code" in tool_def["parameters"]["properties"]


@pytest.mark.asyncio
async def test_code_interpreter_unsupported_language():
    """Test CodeInterpreter with unsupported language"""
    from agentarts.wrapper.tools import CodeInterpreter
    
    interpreter = CodeInterpreter()
    
    with pytest.raises(ValueError) as exc_info:
        await interpreter.execute(code="print('hello')", language="unsupported")
    
    assert "Unsupported language" in str(exc_info.value)


@pytest.mark.asyncio
async def test_code_interpreter_mock_execution():
    """Test CodeInterpreter with mocked sandbox"""
    from agentarts.wrapper.tools import CodeInterpreter
    from agentarts.wrapper.tools.code_interpreter.sandbox import CodeSandbox
    
    mock_sandbox = MagicMock(spec=CodeSandbox)
    mock_sandbox.execute = AsyncMock(return_value={
        "success": True,
        "output": "Hello, World!",
        "error": None,
        "exit_code": 0,
        "execution_time": 0.1
    })
    
    interpreter = CodeInterpreter(sandbox=mock_sandbox)
    result = await interpreter.execute(code="print('Hello, World!')", language="python")
    
    assert result["success"] is True
    assert result["output"] == "Hello, World!"
