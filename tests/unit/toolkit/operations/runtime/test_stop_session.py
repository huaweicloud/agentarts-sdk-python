"""Unit tests for stop_session operation"""

from unittest.mock import MagicMock, patch

import pytest

from agentarts.toolkit.operations.runtime.stop_session import stop_runtime_session


class TestStopRuntimeSession:
    """Tests for stop_runtime_session function."""

    def test_stop_session_no_agent_raises_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValueError, match="Agent name is required"):
            stop_runtime_session(session_id="session-123")

    def test_stop_session_no_session_id_raises_error(self, tmp_path, monkeypatch):
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

        with pytest.raises(ValueError, match="Session ID is required"):
            stop_runtime_session()

    def test_stop_session_success(self, tmp_path, monkeypatch):
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

        with patch("agentarts.toolkit.operations.runtime.stop_session._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.stop_session.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                mock_instance.stop_session.return_value = {"status": "stopped"}

                result = stop_runtime_session(session_id="session-123")

                assert result["status"] == "stopped"
                call_args = mock_instance.stop_session.call_args
                assert call_args.kwargs["agent_name"] == "test-agent"
                assert call_args.kwargs["session_id"] == "session-123"

    def test_stop_session_with_specific_agent(self, tmp_path, monkeypatch):
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

        with patch("agentarts.toolkit.operations.runtime.stop_session._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.stop_session.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                mock_instance.stop_session.return_value = {"status": "stopped"}

                stop_runtime_session(agent_name="custom-agent", session_id="session-123")

                call_args = mock_instance.stop_session.call_args
                assert call_args.kwargs["agent_name"] == "custom-agent"

    def test_stop_session_with_region(self, tmp_path, monkeypatch):
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

        with patch("agentarts.toolkit.operations.runtime.stop_session._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.stop_session.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance
                mock_instance.stop_session.return_value = {"status": "stopped"}

                stop_runtime_session(session_id="session-123", region="cn-north-7")

                call_args = mock_client.call_args
                assert call_args.kwargs["region_id"] == "cn-north-7"

    def test_stop_session_no_data_endpoint_raises_error(self, tmp_path, monkeypatch):
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

        with patch("agentarts.toolkit.operations.runtime.stop_session._get_data_endpoint") as mock_endpoint:
            mock_endpoint.return_value = None

            with pytest.raises(ValueError, match="No data endpoint"):
                stop_runtime_session(session_id="session-123")
