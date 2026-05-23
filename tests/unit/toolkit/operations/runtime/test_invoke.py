"""Unit tests for invoke.py module"""

from unittest.mock import MagicMock, patch

import pytest

from agentarts.sdk.utils.constant import _ensure_https
from agentarts.toolkit.operations.runtime.invoke import (
    InvokeMode,
    _resolve_agent_info,
    _validate_and_normalize_custom_path,
    invoke_agent,
)


class TestInvokeMode:
    """Tests for InvokeMode enum."""

    def test_has_local_mode(self):
        """Has LOCAL mode."""
        assert InvokeMode.LOCAL.value == "local"

    def test_has_cloud_mode(self):
        """Has CLOUD mode."""
        assert InvokeMode.CLOUD.value == "cloud"


class TestEnsureHttps:
    """Tests for _ensure_https() function."""

    def test_adds_https_prefix(self):
        """Adds https:// prefix when missing."""
        result = _ensure_https("example.com")
        assert result == "https://example.com"

    def test_preserves_existing_https(self):
        """Preserves existing https:// prefix."""
        result = _ensure_https("https://example.com")
        assert result == "https://example.com"

    def test_preserves_existing_http(self):
        """Preserves existing http:// prefix."""
        result = _ensure_https("http://example.com")
        assert result == "http://example.com"

    def test_returns_empty_string_unchanged(self):
        """Returns empty string unchanged."""
        result = _ensure_https("")
        assert result == ""

    def test_returns_none_unchanged(self):
        """Returns None unchanged."""
        result = _ensure_https(None)
        assert result is None


class TestResolveAgentInfo:
    """Tests for _resolve_agent_info() function."""

    def test_returns_none_when_no_config(self, tmp_path, monkeypatch):
        """Returns None values when no config exists."""
        monkeypatch.chdir(tmp_path)

        name, region, _agent_id, _auth_type = _resolve_agent_info(None, None)

        assert name is None
        assert region is None

    def test_resolves_from_config(self, tmp_path, monkeypatch):
        """Resolves agent info from config file."""
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
      region: cn-north-4
    runtime:
      agent_id: agent-123
      identity_configuration:
        authorizer_type: IAM
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        monkeypatch.chdir(tmp_path)

        name, region, agent_id, auth_type = _resolve_agent_info(None, None)

        assert name == "test-agent"
        assert region == "cn-north-4"
        assert agent_id == "agent-123"
        assert auth_type == "IAM"


class TestInvokeAgent:
    """Tests for invoke_agent() function."""

    def test_returns_false_for_invalid_json(self, tmp_path, monkeypatch):
        """Returns False for invalid JSON payload."""
        monkeypatch.chdir(tmp_path)

        result = invoke_agent(payload="not valid json")

        assert result is False

    @patch("agentarts.toolkit.operations.runtime.invoke.LocalRuntimeClient")
    def test_local_mode_invokes_local_client(self, mock_client, tmp_path, monkeypatch):
        """Local mode invokes LocalRuntimeClient."""
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.invoke_agent.return_value = {"status": "ok"}

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

        result = invoke_agent(
            payload='{"message": "hello"}',
            mode=InvokeMode.LOCAL,
        )

        assert result is True
        mock_client_instance.invoke_agent.assert_called()

    def test_uses_bearer_token_from_env(self, tmp_path, monkeypatch):
        """Uses BEARER_TOKEN from environment variable."""
        monkeypatch.setenv("BEARER_TOKEN", "env-token")

        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
      region: cn-north-4
    runtime:
      identity_configuration:
        authorizer_type: CUSTOM_JWT
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        monkeypatch.chdir(tmp_path)

        with patch("agentarts.toolkit.operations.runtime.invoke.RuntimeClient") as mock_runtime:
            mock_instance = MagicMock()
            mock_runtime.return_value = mock_instance
            mock_instance.invoke_agent.return_value = {"status": "ok"}

            with patch("agentarts.toolkit.operations.runtime.invoke._get_data_endpoint") as mock_endpoint:
                mock_endpoint.return_value = "https://example.com"

                invoke_agent(
                    payload='{"message": "hello"}',
                    mode=InvokeMode.CLOUD,
                )

                call_args = mock_instance.invoke_agent.call_args
                assert call_args.kwargs["bearer_token"] == "env-token"

    def test_cli_bearer_token_overrides_env(self, tmp_path, monkeypatch):
        """CLI bearer_token overrides environment variable."""
        monkeypatch.setenv("BEARER_TOKEN", "env-token")

        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
      region: cn-north-4
    runtime:
      identity_configuration:
        authorizer_type: CUSTOM_JWT
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        monkeypatch.chdir(tmp_path)

        with patch("agentarts.toolkit.operations.runtime.invoke.RuntimeClient") as mock_runtime:
            mock_instance = MagicMock()
            mock_runtime.return_value = mock_instance
            mock_instance.invoke_agent.return_value = {"status": "ok"}

            with patch("agentarts.toolkit.operations.runtime.invoke._get_data_endpoint") as mock_endpoint:
                mock_endpoint.return_value = "https://example.com"

                invoke_agent(
                    payload='{"message": "hello"}',
                    mode=InvokeMode.CLOUD,
                    bearer_token="cli-token",
                )

                call_args = mock_instance.invoke_agent.call_args
                assert call_args.kwargs["bearer_token"] == "cli-token"


class TestValidateAndNormalizeCustomPath:
    """Tests for _validate_and_normalize_custom_path() function."""

    def test_returns_none_for_none_input(self):
        assert _validate_and_normalize_custom_path(None) is None

    def test_returns_none_for_empty_string(self):
        assert _validate_and_normalize_custom_path("") is None

    def test_returns_none_for_whitespace_only(self):
        assert _validate_and_normalize_custom_path("   ") is None

    def test_strips_leading_slash(self):
        result = _validate_and_normalize_custom_path("/stream")
        assert result == "stream"

    def test_strips_trailing_slash(self):
        result = _validate_and_normalize_custom_path("stream/")
        assert result == "stream"

    def test_strips_both_slashes(self):
        result = _validate_and_normalize_custom_path("/stream/")
        assert result == "stream"

    def test_validates_simple_custom_path(self):
        result = _validate_and_normalize_custom_path("stream")
        assert result == "stream"

    def test_validates_nested_path(self):
        result = _validate_and_normalize_custom_path("api/v2/stream")
        assert result == "api/v2/stream"

    def test_validates_with_hyphens(self):
        result = _validate_and_normalize_custom_path("custom-endpoint")
        assert result == "custom-endpoint"

    def test_validates_with_underscores(self):
        result = _validate_and_normalize_custom_path("custom_endpoint")
        assert result == "custom_endpoint"

    def test_validates_with_dots(self):
        result = _validate_and_normalize_custom_path("api.v2.endpoint")
        assert result == "api.v2.endpoint"

    def test_validates_complex_custom_path(self):
        result = _validate_and_normalize_custom_path("api/v2/custom-endpoint_stream.json")
        assert result == "api/v2/custom-endpoint_stream.json"

    def test_rejects_special_characters(self):
        with pytest.raises(ValueError, match="Invalid custom path"):
            _validate_and_normalize_custom_path("stream!test")

    def test_rejects_at_symbol(self):
        with pytest.raises(ValueError, match="Invalid custom path"):
            _validate_and_normalize_custom_path("stream@test")

    def test_rejects_hash_symbol(self):
        with pytest.raises(ValueError, match="Invalid custom path"):
            _validate_and_normalize_custom_path("stream#test")

    def test_rejects_dollar_symbol(self):
        with pytest.raises(ValueError, match="Invalid custom path"):
            _validate_and_normalize_custom_path("stream$test")

    def test_rejects_percent_symbol(self):
        with pytest.raises(ValueError, match="Invalid custom path"):
            _validate_and_normalize_custom_path("stream%test")

    def test_rejects_ampersand_symbol(self):
        with pytest.raises(ValueError, match="Invalid custom path"):
            _validate_and_normalize_custom_path("stream&test")

    def test_rejects_star_symbol(self):
        with pytest.raises(ValueError, match="Invalid custom path"):
            _validate_and_normalize_custom_path("stream*test")

    def test_rejects_parentheses(self):
        with pytest.raises(ValueError, match="Invalid custom path"):
            _validate_and_normalize_custom_path("stream(test)")

    def test_rejects_spaces(self):
        with pytest.raises(ValueError, match="Invalid custom path"):
            _validate_and_normalize_custom_path("stream test")

    def test_rejects_path_traversal(self):
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_and_normalize_custom_path("../etc/passwd")

    def test_rejects_path_traversal_in_middle(self):
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_and_normalize_custom_path("api/../secret")

    def test_rejects_path_traversal_complex(self):
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_and_normalize_custom_path("api/..../endpoint")


class TestInvokeAgentCustomPath:
    """Tests for invoke_agent() with custom_path parameter."""

    def test_custom_path_passed_to_local_client(self, tmp_path, monkeypatch):
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        monkeypatch.chdir(tmp_path)

        with patch("agentarts.toolkit.operations.runtime.invoke.LocalRuntimeClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            mock_instance.invoke_agent.return_value = {"status": "ok"}

            invoke_agent(
                payload='{"message": "hello"}',
                mode=InvokeMode.LOCAL,
                custom_path="stream",
            )

            call_args = mock_instance.invoke_agent.call_args
            assert call_args.kwargs["custom_path"] == "stream"

    def test_invalid_custom_path_raises_error(self, tmp_path, monkeypatch):
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValueError, match="Invalid custom path"):
            invoke_agent(
                payload='{"message": "hello"}',
                mode=InvokeMode.LOCAL,
                custom_path="invalid!path",
            )

    def test_custom_path_passed_to_cloud_client(self, tmp_path, monkeypatch):
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
      region: cn-north-4
    runtime:
      identity_configuration:
        authorizer_type: CUSTOM_JWT
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("BEARER_TOKEN", "test-token")

        with patch("agentarts.toolkit.operations.runtime.invoke.RuntimeClient") as mock_runtime:
            mock_instance = MagicMock()
            mock_runtime.return_value = mock_instance
            mock_instance.invoke_agent.return_value = {"status": "ok"}

            with patch("agentarts.toolkit.operations.runtime.invoke._get_data_endpoint") as mock_endpoint:
                mock_endpoint.return_value = "https://example.com"

                invoke_agent(
                    payload='{"message": "hello"}',
                    mode=InvokeMode.CLOUD,
                    custom_path="api/v2/stream",
                )

                call_args = mock_instance.invoke_agent.call_args
                assert call_args.kwargs["custom_path"] == "api/v2/stream"
