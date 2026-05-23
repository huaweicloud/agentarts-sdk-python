"""Unit tests for download_files operation"""

from unittest.mock import MagicMock, patch

import pytest

from agentarts.sdk.service.runtime_client import StreamDownloadResult
from agentarts.toolkit.operations.runtime.download_files import DEFAULT_PATH, download_runtime_files


class TestDownloadRuntimeFiles:
    """Tests for download_runtime_files function."""

    def test_download_files_empty_path_raises_error(self):
        with pytest.raises(ValueError, match="Path is required"):
            download_runtime_files(path="", session_id="session-123")

    def test_download_files_no_session_raises_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValueError, match="Session ID is required"):
            download_runtime_files(path="/home/user/test.txt")

    def test_download_files_no_agent_raises_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValueError, match="Agent name is required"):
            download_runtime_files(path="/home/user/test.txt", session_id="session-123")

    def test_download_files_normalizes_path(self, tmp_path, monkeypatch):
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

        with patch("agentarts.toolkit.operations.runtime.download_files._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.download_files.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance

                mock_result = StreamDownloadResult(
                    success=True,
                    status_code=200,
                    content_type="application/octet-stream",
                    _raw_response=MagicMock(),
                )
                mock_result._raw_response.iter_content.return_value = iter([b"test content"])
                mock_instance.download_files.return_value = mock_result

                output_path = str(tmp_path / "output.txt")
                result = download_runtime_files(
                    path="test.txt",
                    output=output_path,
                    session_id="session-123",
                )

                assert result["saved_path"] == output_path
                call_args = mock_instance.download_files.call_args
                path_arg = call_args.kwargs["path"]
                assert path_arg.startswith(DEFAULT_PATH)

    def test_download_files_preserves_full_path(self, tmp_path, monkeypatch):
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

        with patch("agentarts.toolkit.operations.runtime.download_files._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.download_files.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance

                mock_result = StreamDownloadResult(
                    success=True,
                    status_code=200,
                    content_type="application/octet-stream",
                    _raw_response=MagicMock(),
                )
                mock_result._raw_response.iter_content.return_value = iter([b"test content"])
                mock_instance.download_files.return_value = mock_result

                output_path = str(tmp_path / "output.txt")
                download_runtime_files(
                    path="/home/user/custom/file.txt",
                    output=output_path,
                    session_id="session-123",
                )

                call_args = mock_instance.download_files.call_args
                assert call_args.kwargs["path"] == "/home/user/custom/file.txt"

    def test_download_files_recursive_tar(self, tmp_path, monkeypatch):
        import tarfile

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

        tar_path = tmp_path / "test.tar"
        with tarfile.open(str(tar_path), "w") as tar:
            test_file = tmp_path / "test_content.txt"
            test_file.write_text("test content")
            tar.add(str(test_file), arcname="test_content.txt")

        tar_bytes = tar_path.read_bytes()

        with patch("agentarts.toolkit.operations.runtime.download_files._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.download_files.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance

                mock_response = MagicMock()
                mock_response.iter_content.return_value = iter([tar_bytes])

                mock_result = StreamDownloadResult(
                    success=True,
                    status_code=200,
                    content_type="application/x-tar",
                    _raw_response=mock_response,
                )
                mock_instance.download_files.return_value = mock_result

                output_dir = str(tmp_path / "output_dir")
                result = download_runtime_files(
                    path="/home/user/data",
                    output=output_dir,
                    recursive=True,
                    session_id="session-123",
                )

                assert result["saved_path"] == output_dir
                call_args = mock_instance.download_files.call_args
                assert call_args.kwargs["recursive"] is True

    def test_download_files_with_session_id(self, tmp_path, monkeypatch):
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

        with patch("agentarts.toolkit.operations.runtime.download_files._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.download_files.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance

                mock_result = StreamDownloadResult(
                    success=True,
                    status_code=200,
                    content_type="application/octet-stream",
                    _raw_response=MagicMock(),
                )
                mock_result._raw_response.iter_content.return_value = iter([b"test"])
                mock_instance.download_files.return_value = mock_result

                output_path = str(tmp_path / "output.txt")
                download_runtime_files(
                    path="/home/user/test.txt",
                    output=output_path,
                    session_id="session-123",
                )

                call_args = mock_instance.download_files.call_args
                assert call_args.kwargs["session_id"] == "session-123"

    def test_download_files_with_bearer_token(self, tmp_path, monkeypatch):
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

        with patch("agentarts.toolkit.operations.runtime.download_files._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.download_files.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance

                mock_result = StreamDownloadResult(
                    success=True,
                    status_code=200,
                    content_type="application/octet-stream",
                    _raw_response=MagicMock(),
                )
                mock_result._raw_response.iter_content.return_value = iter([b"test"])
                mock_instance.download_files.return_value = mock_result

                output_path = str(tmp_path / "output.txt")
                download_runtime_files(
                    path="/home/user/test.txt",
                    output=output_path,
                    session_id="session-123",
                    bearer_token="test-token",
                )

                call_args = mock_instance.download_files.call_args
                assert call_args.kwargs["bearer_token"] == "test-token"

    def test_download_files_failure_raises_error(self, tmp_path, monkeypatch):
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

        with patch("agentarts.toolkit.operations.runtime.download_files._get_data_endpoint") as mock_endpoint:
            with patch("agentarts.toolkit.operations.runtime.download_files.RuntimeClient") as mock_client:
                mock_endpoint.return_value = "https://test.example.com"
                mock_instance = MagicMock()
                mock_client.return_value = mock_instance

                mock_result = StreamDownloadResult(
                    success=False,
                    status_code=404,
                    content_type="application/json",
                    error="File not found",
                )
                mock_instance.download_files.return_value = mock_result

                with pytest.raises(RuntimeError, match="Download failed"):
                    download_runtime_files(
                        path="/home/user/test.txt",
                        session_id="session-123",
                    )

    def test_download_files_no_data_endpoint_raises_error(self, tmp_path, monkeypatch):
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

        with patch("agentarts.toolkit.operations.runtime.download_files._get_data_endpoint") as mock_endpoint:
            mock_endpoint.return_value = None

            with pytest.raises(ValueError, match="No data endpoint"):
                download_runtime_files(
                    path="/home/user/test.txt",
                    session_id="session-123",
                )


class TestDownloadFilesClient:
    """Tests for RuntimeClient.download_files method."""

    def test_download_files_endpoint_path(self):
        """Test that download_files uses correct endpoint path."""
        from agentarts.sdk.service.runtime_client import RuntimeClient

        mock_data_client = MagicMock()

        with patch.object(RuntimeClient, "__init__", lambda self, *args, **kwargs: None):
            client = RuntimeClient.__new__(RuntimeClient)
            client._data_client = mock_data_client
            client._request_stream = lambda *args, **kwargs: StreamDownloadResult(
                success=True,
                status_code=200,
                content_type="application/octet-stream",
            )

            result = client.download_files(
                agent_name="myagent",
                session_id="session-123",
                path="/test.txt",
            )

            call_args = mock_data_client._session.request.call_args
            if call_args:
                url = call_args[0][1] if call_args[0] else ""
                assert "/runtimes/myagent/download-files" in url
