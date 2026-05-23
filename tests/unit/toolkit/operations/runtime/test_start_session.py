"""
Unit tests for start-session CLI command
"""

from unittest.mock import MagicMock, patch

import pytest


class TestStartRuntimeSession:
    """Tests for start_runtime_session operation"""

    def test_start_session_calls_client(self):
        """Test that start_session calls RuntimeClient.start_session"""
        from agentarts.toolkit.operations.runtime.start_session import start_runtime_session

        mock_response = {"data": {"session_id": "session-123"}}

        with patch(
            "agentarts.toolkit.operations.runtime.start_session._resolve_agent_info"
        ) as mock_resolve:
            with patch(
                "agentarts.toolkit.operations.runtime.start_session._get_data_endpoint"
            ) as mock_endpoint:
                with patch(
                    "agentarts.toolkit.operations.runtime.start_session.RuntimeClient"
                ) as mock_client_cls:
                    mock_resolve.return_value = ("myagent", "cn-southwest-2", "agent-id", "IAM")
                    mock_endpoint.return_value = "https://data.example.com"

                    mock_client = MagicMock()
                    mock_client.start_session.return_value = mock_response
                    mock_client_cls.return_value = mock_client

                    result = start_runtime_session(agent_name="myagent")

                    mock_client.start_session.assert_called_once_with(
                        agent_name="myagent",
                        bearer_token=None,
                        endpoint=None,
                        user_id=None,
                    )
                    assert result == mock_response

    def test_start_session_with_bearer_token(self):
        """Test that start_session passes bearer_token"""
        from agentarts.toolkit.operations.runtime.start_session import start_runtime_session

        mock_response = {"data": {"session_id": "session-abc"}}

        with patch(
            "agentarts.toolkit.operations.runtime.start_session._resolve_agent_info"
        ) as mock_resolve:
            with patch(
                "agentarts.toolkit.operations.runtime.start_session._get_data_endpoint"
            ) as mock_endpoint:
                with patch(
                    "agentarts.toolkit.operations.runtime.start_session.RuntimeClient"
                ) as mock_client_cls:
                    mock_resolve.return_value = ("myagent", "cn-southwest-2", "agent-id", "IAM")
                    mock_endpoint.return_value = "https://data.example.com"

                    mock_client = MagicMock()
                    mock_client.start_session.return_value = mock_response
                    mock_client_cls.return_value = mock_client

                    result = start_runtime_session(
                        agent_name="myagent",
                        bearer_token="test-token",
                    )

                    mock_client.start_session.assert_called_once_with(
                        agent_name="myagent",
                        bearer_token="test-token",
                        endpoint=None,
                        user_id=None,
                    )

    def test_start_session_no_agent_raises(self):
        """Test that missing agent raises ValueError"""
        from agentarts.toolkit.operations.runtime.start_session import start_runtime_session

        with patch(
            "agentarts.toolkit.operations.runtime.start_session._resolve_agent_info"
        ) as mock_resolve:
            with patch(
                "agentarts.toolkit.operations.runtime.start_session.echo_error"
            ):
                mock_resolve.return_value = (None, None, None, None)

                with pytest.raises(ValueError, match="Agent name is required"):
                    start_runtime_session()

    def test_start_session_no_endpoint_raises(self):
        """Test that missing endpoint raises ValueError"""
        from agentarts.toolkit.operations.runtime.start_session import start_runtime_session

        with patch(
            "agentarts.toolkit.operations.runtime.start_session._resolve_agent_info"
        ) as mock_resolve:
            with patch(
                "agentarts.toolkit.operations.runtime.start_session._get_data_endpoint"
            ) as mock_endpoint:
                mock_resolve.return_value = ("myagent", "cn-southwest-2", "agent-id", "IAM")
                mock_endpoint.return_value = None

                with pytest.raises(ValueError, match="No data endpoint"):
                    start_runtime_session(agent_name="myagent")


class TestRuntimeClientStartSession:
    """Tests for RuntimeClient.start_session method"""

    def test_start_session_method_exists(self):
        """Test that RuntimeClient has start_session method"""
        from agentarts.sdk.service.runtime_client import RuntimeClient

        assert hasattr(RuntimeClient, "start_session")

    def test_start_session_calls_correct_path(self):
        """Test that start_session calls correct API path with POST"""
        from agentarts.sdk.service.runtime_client import RuntimeClient

        mock_data_client = MagicMock()
        mock_data_client._request.return_value = MagicMock(
            success=True,
            data={"data": {"session_id": "session-abc"}},
        )

        with patch.object(
            RuntimeClient, "__init__", lambda self, *args, **kwargs: None
        ):
            client = RuntimeClient.__new__(RuntimeClient)
            client._data_client = mock_data_client
            client._data = lambda method, path, **kwargs: mock_data_client._request(
                method, path, **kwargs
            )

            result = client.start_session(agent_name="myagent")

            call_args = mock_data_client._request.call_args
            assert call_args[0][0] == "POST"
            assert "sessions-start" in call_args[0][1]
            assert "myagent" in call_args[0][1]

    def test_start_session_with_bearer_token(self):
        """Test that start_session includes Authorization header"""
        from agentarts.sdk.service.runtime_client import RuntimeClient

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {"data": {"session_id": "session-xyz"}}

        mock_data_client = MagicMock()
        mock_data_client._request.return_value = mock_result

        with patch.object(
            RuntimeClient, "__init__", lambda self, *args, **kwargs: None
        ):
            client = RuntimeClient.__new__(RuntimeClient)
            client._data_client = mock_data_client
            client._data = lambda method, path, **kwargs: mock_data_client._request(
                method, path, **kwargs
            )

            result = client.start_session(
                agent_name="myagent",
                bearer_token="test-token"
            )

            call_args = mock_data_client._request.call_args
            headers = call_args.kwargs.get("headers", {})
            assert headers.get("Authorization") == "Bearer test-token"

    def test_start_session_failure_raises(self):
        """Test that start_session raises on failure"""
        from agentarts.sdk.service.runtime_client import RuntimeClient

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.status_code = 500
        mock_result.error = "Internal error"

        mock_data_client = MagicMock()
        mock_data_client._request.return_value = mock_result

        with patch.object(
            RuntimeClient, "__init__", lambda self, *args, **kwargs: None
        ):
            client = RuntimeClient.__new__(RuntimeClient)
            client._data_client = mock_data_client
            client._data = lambda method, path, **kwargs: mock_data_client._request(
                method, path, **kwargs
            )

            with pytest.raises(RuntimeError, match="start_session failed"):
                client.start_session(agent_name="myagent")


class TestStartSessionCli:
    """Tests for start_session_cmd CLI"""

    def test_cli_imports_successfully(self):
        """Test that CLI module imports"""
        from agentarts.toolkit.cli.runtime.start_session import start_session_cmd

        assert start_session_cmd is not None

    def test_cli_registered_in_runtime_app(self):
        """Test that start-session is registered in runtime_app"""
        from agentarts.toolkit.cli.runtime.commands import runtime_app

        registered_commands = [cmd.name for cmd in runtime_app.registered_commands]
        assert "start-session" in registered_commands

    def test_cli_outputs_raw_response(self):
        """Test that CLI outputs raw JSON response"""
        from agentarts.toolkit.cli.runtime.start_session import start_session_cmd

        mock_response = {"data": {"session_id": "session-abc-123"}}

        with patch(
            "agentarts.toolkit.cli.runtime.start_session.start_runtime_session"
        ) as mock_op:
            with patch(
                "agentarts.toolkit.cli.runtime.start_session.echo_success"
            ):
                with patch("agentarts.toolkit.cli.runtime.start_session.console") as mock_console:
                    mock_op.return_value = mock_response

                    start_session_cmd(agent="myagent")

                    mock_op.assert_called_once_with(
                        agent_name="myagent",
                        region=None,
                        bearer_token=None,
                        endpoint=None,
                        skip_ssl_verification=False,
                        user_id=None,
                    )
                    assert mock_console.print.called

    def test_cli_with_bearer_token(self):
        """Test that CLI passes bearer_token"""
        from agentarts.toolkit.cli.runtime.start_session import start_session_cmd

        mock_response = {"data": {"session_id": "session-xyz"}}

        with patch(
            "agentarts.toolkit.cli.runtime.start_session.start_runtime_session"
        ) as mock_op:
            with patch(
                "agentarts.toolkit.cli.runtime.start_session.echo_success"
            ):
                with patch("agentarts.toolkit.cli.runtime.start_session.console"):
                    mock_op.return_value = mock_response

                    start_session_cmd(agent="myagent", bearer_token="test-token")

                    mock_op.assert_called_once_with(
                        agent_name="myagent",
                        region=None,
                        bearer_token="test-token",
                        endpoint=None,
                        skip_ssl_verification=False,
                        user_id=None,
                    )