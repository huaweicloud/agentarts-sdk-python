"""Tests for tools module"""

from unittest.mock import MagicMock, patch


def test_code_interpreter_import():
    """Test that CodeInterpreter can be imported"""
    from agentarts.sdk.tools import CodeInterpreter

    assert CodeInterpreter is not None


def test_code_interpreter_create():
    """Test CodeInterpreter creation"""
    from agentarts.sdk.tools import CodeInterpreter

    with patch("agentarts.sdk.tools.code_interpreter.code_interpreter_client.ControlToolsHttpClient"):
        with patch("agentarts.sdk.tools.code_interpreter.code_interpreter_client.DataToolsHttpClient"):
            interpreter = CodeInterpreter(region="cn-north-4")

            assert interpreter is not None


def test_code_interpreter_list():
    """Test CodeInterpreter list_code_interpreters method"""
    from agentarts.sdk.tools import CodeInterpreter

    with patch("agentarts.sdk.tools.code_interpreter.code_interpreter_client.ControlToolsHttpClient") as mock_control:
        mock_instance = MagicMock()
        mock_control.return_value = mock_instance
        mock_instance.list_code_interpreters.return_value = {"code_interpreters": [], "total": 0}

        with patch("agentarts.sdk.tools.code_interpreter.code_interpreter_client.DataToolsHttpClient"):
            interpreter = CodeInterpreter(region="cn-north-4")
            result = interpreter.list_code_interpreters()

            assert result is not None
