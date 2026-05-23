"""Unit tests for exec_command operation"""

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from agentarts.toolkit.operations.runtime.exec_command import exec_runtime_command


class TestExecRuntimeCommand:
    """Tests for exec_runtime_command function."""

    def test_exec_command_empty_raises_error(self):
        with pytest.raises(ValueError, match="Command is required"):
            exec_runtime_command(command="")

    def test_exec_command_whitespace_only_raises_error(self):
        with pytest.raises(ValueError, match="Command cannot be empty"):
            exec_runtime_command(command="   ")

    def test_exec_command_parses_command_string(self, tmp_path, monkeypatch):
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
      region: cn-north-4
    runtime:
      agent_id: agent-123
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        monkeypatch.chdir(tmp_path)

        with patch("agentarts.toolkit.operations.runtime.exec_command._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.exec_command.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                mock_instance.exec_command.return_value = {"stdout": "output"}

                result = exec_runtime_command(command="ls -la /home")

                assert result == {"stdout": "output"}
                call_args = mock_instance.exec_command.call_args
                assert call_args.kwargs["command"] == ["ls", "-la", "/home"]

    def test_exec_command_with_chunked_mode(self, tmp_path, monkeypatch):
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
      region: cn-north-4
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        monkeypatch.chdir(tmp_path)

        with patch("agentarts.toolkit.operations.runtime.exec_command._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.exec_command.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                mock_instance.exec_command.return_value = iter(["line1", "line2"])

                result = exec_runtime_command(command="echo hello", chunked=True)

                assert isinstance(result, Iterator)
                call_args = mock_instance.exec_command.call_args
                assert call_args.kwargs["chunked"] is True

    def test_exec_command_no_agent_raises_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValueError, match="Agent name is required"):
            exec_runtime_command(command="ls")

    def test_exec_command_no_data_endpoint_raises_error(self, tmp_path, monkeypatch):
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
      region: cn-north-4
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        monkeypatch.chdir(tmp_path)

        with patch("agentarts.toolkit.operations.runtime.exec_command._get_data_endpoint") as mock_endpoint:
            mock_endpoint.return_value = None

            with pytest.raises(ValueError, match="No data endpoint"):
                exec_runtime_command(command="ls")

    def test_exec_command_with_session_id(self, tmp_path, monkeypatch):
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
      region: cn-north-4
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        monkeypatch.chdir(tmp_path)

        with patch("agentarts.toolkit.operations.runtime.exec_command._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.exec_command.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                mock_instance.exec_command.return_value = {"stdout": ""}

                exec_runtime_command(command="pwd", session_id="session-123")

                call_args = mock_instance.exec_command.call_args
                assert call_args.kwargs["session_id"] == "session-123"

    def test_exec_command_with_specific_agent(self, tmp_path, monkeypatch):
        config_content = """
default_agent: default-agent
agents:
  default-agent:
    base:
      name: default-agent
      region: cn-north-4
  custom-agent:
    base:
      name: custom-agent
      region: cn-north-7
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        monkeypatch.chdir(tmp_path)

        with patch("agentarts.toolkit.operations.runtime.exec_command._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.exec_command.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                mock_instance.exec_command.return_value = {"stdout": ""}

                exec_runtime_command(command="ls", agent_name="custom-agent")

                call_args = mock_instance.exec_command.call_args
                assert call_args.kwargs["agent_name"] == "custom-agent"

    def test_exec_command_timeout_zero_raises_error(self):
        """Test that timeout=0 raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be a positive number"):
            exec_runtime_command(command="ls", timeout=0)

    def test_exec_command_timeout_negative_raises_error(self):
        """Test that negative timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be a positive number"):
            exec_runtime_command(command="ls", timeout=-10)

    def test_exec_command_timeout_exceeds_max_raises_error(self):
        """Test that timeout exceeding max (300) raises ValueError."""
        with pytest.raises(ValueError, match="Timeout exceeds maximum allowed value"):
            exec_runtime_command(command="ls", timeout=500)

    def test_exec_command_timeout_valid_passes(self, tmp_path, monkeypatch):
        """Test that valid timeout passes validation."""
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
      region: cn-north-4
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        monkeypatch.chdir(tmp_path)

        with patch("agentarts.toolkit.operations.runtime.exec_command._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.exec_command.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                mock_instance.exec_command.return_value = {"stdout": ""}

                exec_runtime_command(command="ls", timeout=120)

                call_args = mock_instance.exec_command.call_args
                assert call_args.kwargs["timeout"] == 120
