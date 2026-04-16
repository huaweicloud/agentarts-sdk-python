"""
Unit tests for MCP Gateway CLI commands
"""


import pytest

from agentarts.toolkit.cli.mcp_gateway.mcp_gateway import _format_output, _parse_json


class TestMCPGatewayCLI:
    """Test MCP Gateway CLI commands"""

    def test_parse_json_valid(self):
        """Test _parse_json with valid JSON"""
        json_str = '{"key": "value"}'
        result = _parse_json(json_str)
        assert result == {"key": "value"}

    def test_parse_json_invalid(self):
        """Test _parse_json with invalid JSON"""
        invalid_json = '{"key": "value"'
        with pytest.raises(ValueError, match="Invalid JSON format"):
            _parse_json(invalid_json)

    def test_parse_json_empty(self):
        """Test _parse_json with empty string"""
        result = _parse_json("")
        assert result is None

    def test_parse_json_none(self):
        """Test _parse_json with None"""
        result = _parse_json(None)
        assert result is None

    def test_format_output_json(self):
        """Test _format_output with JSON serializable data"""
        data = {"key": "value"}
        result = _format_output(data)
        assert isinstance(result, str)
        assert "key" in result
        assert "value" in result

    def test_format_output_non_json(self):
        """Test _format_output with non-JSON serializable data"""
        # Create a non-serializable object
        class NonSerializable:
            def __str__(self):
                return "NonSerializable object"

        data = NonSerializable()
        result = _format_output(data)
        assert isinstance(result, str)
        assert "NonSerializable object" in result
