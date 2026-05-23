"""Unit tests for upload_files operation"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentarts.toolkit.operations.runtime.upload_files import DEFAULT_PATH, upload_runtime_files


class TestUploadRuntimeFiles:
    """Tests for upload_runtime_files function."""

    def test_upload_files_empty_files_raises_error(self):
        with pytest.raises(ValueError, match="Files are required"):
            upload_runtime_files(files=[], session_id="session-123")

    def test_upload_files_no_agent_raises_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValueError, match="Agent name is required"):
            upload_runtime_files(
                files=[{"path": "/test.txt", "local_file": "/tmp/test.txt"}],
                session_id="session-123",
            )

    def test_upload_files_no_session_raises_error(self, tmp_path, monkeypatch):
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
            upload_runtime_files(files=[{"path": "/test.txt", "local_file": "/tmp/test.txt"}])

    def test_upload_files_normalizes_path(self, tmp_path, monkeypatch):
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

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path_file = tmp.name

        try:
            with patch("agentarts.toolkit.operations.runtime.upload_files._get_data_endpoint") as mock_endpoint:
                with patch("agentarts.toolkit.operations.runtime.upload_files.RuntimeClient") as mock_client:
                    mock_endpoint.return_value = "https://test.example.com"
                    mock_instance = MagicMock()
                    mock_client.return_value = mock_instance
                    mock_instance.upload_files.return_value = {"status": "uploaded"}

                    result = upload_runtime_files(
                        files=[{"path": "test.txt", "local_file": tmp_path_file}],
                        session_id="session-123",
                    )

                    assert result["status"] == "uploaded"
                    call_args = mock_instance.upload_files.call_args
                    files_arg = call_args.kwargs["files"]
                    assert files_arg[0]["path"].startswith(DEFAULT_PATH)
        finally:
            Path(tmp_path_file).unlink()

    def test_upload_files_preserves_full_path(self, tmp_path, monkeypatch):
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

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path_file = tmp.name

        try:
            with patch("agentarts.toolkit.operations.runtime.upload_files._get_data_endpoint") as mock_endpoint:
                with patch("agentarts.toolkit.operations.runtime.upload_files.RuntimeClient") as mock_client:
                    mock_endpoint.return_value = "https://test.example.com"
                    mock_instance = MagicMock()
                    mock_client.return_value = mock_instance
                    mock_instance.upload_files.return_value = {"status": "uploaded"}

                    result = upload_runtime_files(
                        files=[{"path": "/home/user/custom/path.txt", "local_file": tmp_path_file}],
                        session_id="session-123",
                    )

                    call_args = mock_instance.upload_files.call_args
                    files_arg = call_args.kwargs["files"]
                    assert files_arg[0]["path"] == "/home/user/custom/path.txt"
        finally:
            Path(tmp_path_file).unlink()

    def test_upload_files_multiple_files(self, tmp_path, monkeypatch):
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

        with tempfile.NamedTemporaryFile(delete=False) as tmp1:
            tmp1.write(b"content1")
            tmp1_path = tmp1.name
        with tempfile.NamedTemporaryFile(delete=False) as tmp2:
            tmp2.write(b"content2")
            tmp2_path = tmp2.name

        try:
            with patch("agentarts.toolkit.operations.runtime.upload_files._get_data_endpoint") as mock_endpoint:
                with patch("agentarts.toolkit.operations.runtime.upload_files.RuntimeClient") as mock_client:
                    mock_endpoint.return_value = "https://test.example.com"
                    mock_instance = MagicMock()
                    mock_client.return_value = mock_instance
                    mock_instance.upload_files.return_value = {"status": "uploaded", "files": 2}

                    result = upload_runtime_files(
                        files=[
                            {"path": "/home/user/file1.txt", "local_file": tmp1_path},
                            {"path": "/home/user/file2.txt", "local_file": tmp2_path},
                        ],
                        session_id="session-123",
                    )

                    assert result["files"] == 2
                    call_args = mock_instance.upload_files.call_args
                    files_arg = call_args.kwargs["files"]
                    assert len(files_arg) == 2
        finally:
            Path(tmp1_path).unlink()
            Path(tmp2_path).unlink()

    def test_upload_files_with_metadata(self, tmp_path, monkeypatch):
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

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test")
            tmp_path_file = tmp.name

        try:
            with patch("agentarts.toolkit.operations.runtime.upload_files._get_data_endpoint") as mock_endpoint:
                with patch("agentarts.toolkit.operations.runtime.upload_files.RuntimeClient") as mock_client:
                    mock_endpoint.return_value = "https://test.example.com"
                    mock_instance = MagicMock()
                    mock_client.return_value = mock_instance
                    mock_instance.upload_files.return_value = {"status": "uploaded"}

                    upload_runtime_files(
                        files=[{"path": "/home/user/test.txt", "local_file": tmp_path_file}],
                        session_id="session-123",
                        user_id=1001,
                        group_id=1001,
                        file_mode="0755",
                    )

                    call_args = mock_instance.upload_files.call_args
                    assert call_args.kwargs["user_id"] == 1001
                    assert call_args.kwargs["group_id"] == 1001
                    assert call_args.kwargs["file_mode"] == "0755"
        finally:
            Path(tmp_path_file).unlink()

    def test_upload_files_default_metadata(self, tmp_path, monkeypatch):
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

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test")
            tmp_path_file = tmp.name

        try:
            with patch("agentarts.toolkit.operations.runtime.upload_files._get_data_endpoint") as mock_endpoint:
                with patch("agentarts.toolkit.operations.runtime.upload_files.RuntimeClient") as mock_client:
                    mock_endpoint.return_value = "https://test.example.com"
                    mock_instance = MagicMock()
                    mock_client.return_value = mock_instance
                    mock_instance.upload_files.return_value = {"status": "uploaded"}

                    upload_runtime_files(
                        files=[{"path": "/home/user/test.txt", "local_file": tmp_path_file}],
                        session_id="session-123",
                    )

                    call_args = mock_instance.upload_files.call_args
                    assert call_args.kwargs["user_id"] == 1000
                    assert call_args.kwargs["group_id"] == 1000
                    assert call_args.kwargs["file_mode"] == "0644"
        finally:
            Path(tmp_path_file).unlink()

    def test_upload_files_with_bearer_token(self, tmp_path, monkeypatch):
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

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test")
            tmp_path_file = tmp.name

        try:
            with patch("agentarts.toolkit.operations.runtime.upload_files._get_data_endpoint") as mock_endpoint:
                with patch("agentarts.toolkit.operations.runtime.upload_files.RuntimeClient") as mock_client:
                    mock_endpoint.return_value = "https://test.example.com"
                    mock_instance = MagicMock()
                    mock_client.return_value = mock_instance
                    mock_instance.upload_files.return_value = {"status": "uploaded"}

                    upload_runtime_files(
                        files=[{"path": "/home/user/test.txt", "local_file": tmp_path_file}],
                        session_id="session-123",
                        bearer_token="test-token",
                    )

                    call_args = mock_instance.upload_files.call_args
                    assert call_args.kwargs["bearer_token"] == "test-token"
        finally:
            Path(tmp_path_file).unlink()

    def test_upload_files_no_data_endpoint_raises_error(self, tmp_path, monkeypatch):
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

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test")
            tmp_path_file = tmp.name

        try:
            with patch("agentarts.toolkit.operations.runtime.upload_files._get_data_endpoint") as mock_endpoint:
                mock_endpoint.return_value = None

                with pytest.raises(ValueError, match="No data endpoint"):
                    upload_runtime_files(
                        files=[{"path": "/test.txt", "local_file": tmp_path_file}],
                        session_id="session-123",
                    )
        finally:
            Path(tmp_path_file).unlink()


class TestUploadFilesClient:
    """Tests for RuntimeClient.upload_files method."""

    def test_upload_files_endpoint_path(self):
        """Test that upload_files uses correct endpoint path."""
        from agentarts.sdk.service.runtime_client import RuntimeClient

        mock_data_client = MagicMock()
        mock_data_client._request.return_value = MagicMock(
            success=True,
            data={"status": "uploaded"},
        )

        with patch.object(RuntimeClient, "__init__", lambda self, *args, **kwargs: None):
            client = RuntimeClient.__new__(RuntimeClient)
            client._data_client = mock_data_client
            client._data = lambda method, path, **kwargs: mock_data_client._request(method, path, **kwargs)

            with patch("builtins.open", MagicMock()):
                result = client.upload_files(
                    agent_name="myagent",
                    session_id="session-123",
                    files=[{"path": "/test.txt", "content": b"test"}],
                )

                call_args = mock_data_client._request.call_args
                assert "/runtimes/myagent/upload-files" in call_args[0][1]

    def test_upload_files_includes_user_group_params(self):
        """Test that user_id and group_id are included in params."""
        from agentarts.sdk.service.runtime_client import RuntimeClient

        mock_data_client = MagicMock()
        mock_data_client._request.return_value = MagicMock(
            success=True,
            data={"status": "uploaded"},
        )

        with patch.object(RuntimeClient, "__init__", lambda self, *args, **kwargs: None):
            client = RuntimeClient.__new__(RuntimeClient)
            client._data_client = mock_data_client
            client._data = lambda method, path, **kwargs: mock_data_client._request(method, path, **kwargs)

            result = client.upload_files(
                agent_name="myagent",
                session_id="session-123",
                files=[{"path": "/test.txt", "content": b"test"}],
                user_id=1001,
                group_id=1002,
                file_mode="0755",
            )

            call_args = mock_data_client._request.call_args
            params = call_args.kwargs.get("params", {})
            assert params["user_id"] == 1001
            assert params["group_id"] == 1002
            assert params["file_mode"] == "0755"
