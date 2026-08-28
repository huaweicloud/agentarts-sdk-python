"""Unit tests for exec_command operation"""

import uuid
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from agentarts.toolkit.operations.runtime.exec_command import (
    _needs_shell,
    build_command_array,
    exec_runtime_command,
)


class TestNeedsShell:
    """Quote-aware detection of shell-only constructs."""

    @pytest.mark.parametrize("cmd", [
        "echo '1214' > test1.txt",   # redirection outside quotes
        "cat f | grep x",            # pipe
        "cd /tmp && pwd",           # &&
        "cd /tmp || pwd",           # ||
        "echo a;b",                 # ;
        "sleep 1 &",                # background &
        "echo hi $(date)",          # command substitution
        "echo hi `date`",           # backtick
        "echo a>>f",                # >> redirection
    ])
    def test_shell_constructs_detected(self, cmd):
        assert _needs_shell(cmd) is True

    @pytest.mark.parametrize("cmd", [
        "ls -la",
        "echo 1214",
        'echo "a > b"',             # > inside double quotes -> literal
        "echo 'a;b'",               # ; inside single quotes -> literal
        "find . -name '*.py'",      # glob not in operator set; * quoted anyway
        'grep ">" f',               # > quoted -> literal
        "curl 'http://x?a=1&b=2'",  # & inside quotes -> literal
    ])
    def test_no_shell_construct(self, cmd):
        assert _needs_shell(cmd) is False


class TestBuildCommandArray:
    """Docker exec-form vs auto sh -c wrapping."""

    def test_plain_command_exec_form(self):
        assert build_command_array("ls -la /home") == ["ls", "-la", "/home"]

    def test_shell_construct_wraps_with_sh_c(self):
        cmd = "echo 1214 > test1.txt"
        assert build_command_array(cmd) == ["sh", "-c", cmd]

    def test_wrap_uses_original_string_not_shlex_joined(self):
        # sh -c only uses its first arg as the script; the array must be exactly
        # ["sh","-c",<original>] so sh re-parses quotes/operators consistently.
        cmd = "echo '1214' > test1.txt"
        arr = build_command_array(cmd)
        assert arr[0] == "sh"
        assert arr[1] == "-c"
        assert arr[2] is cmd  # original string, not shlex-joined

    def test_quoted_metacharacter_stays_exec_form(self):
        arr = build_command_array('echo "a > b"')
        assert arr == ["echo", "a > b"]

    def test_explicit_sh_c_wrapper_is_passed_through(self):
        # No shell operators outside quotes -> stays exec-form as-is, which
        # already runs sh -c on the backend. Users can force a shell this way.
        cmd = 'sh -c "echo 1214 > f.txt"'
        assert build_command_array(cmd) == ["sh", "-c", "echo 1214 > f.txt"]

    def test_empty_after_split_raises(self):
        with pytest.raises(ValueError, match="empty"):
            build_command_array("   ")


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

    def test_exec_command_auto_generates_session_id(self, tmp_path, monkeypatch):
        """When no session id is given, one is auto-generated (valid uuid),
        mirroring `invoke` — instead of crashing in the signer on a None header.
        """
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

                exec_runtime_command(command="pwd")

                call_args = mock_instance.exec_command.call_args
                generated = call_args.kwargs["session_id"]
                # must be a real, non-empty uuid (not None)
                assert generated is not None
                uuid.UUID(generated)  # raises ValueError if not a valid uuid

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
        """Test that timeout exceeding max (3600) raises ValueError."""
        with pytest.raises(ValueError, match="Timeout exceeds maximum allowed value"):
            exec_runtime_command(command="ls", timeout=4000)

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
