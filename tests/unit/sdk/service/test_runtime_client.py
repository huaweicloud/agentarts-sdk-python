"""Unit tests for RuntimeClient new methods"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentarts.sdk.service.runtime_client import RuntimeClient, StreamDownloadResult


class TestRuntimeClientExecCommand:
    """Tests for RuntimeClient.exec_command method."""

    def _mock_response(self, status_code=200, json_data=None, streaming=False, content_type="application/json"):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.ok = 200 <= status_code < 300
        mock_resp.headers = {"Content-Type": content_type}
        if json_data is not None:
            mock_resp.json.return_value = json_data
        else:
            mock_resp.json.side_effect = ValueError("Not JSON")
        mock_resp.content = b""
        mock_resp.text = ""
        return mock_resp

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_exec_command_basic(self, mock_data):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.status_code = 200
        mock_result.data = {"stdout": "file1.txt\nfile2.txt", "stderr": ""}
        mock_result.headers = {"Content-Type": "application/json"}
        mock_result.streaming = False
        mock_data.return_value = mock_result

        client = RuntimeClient(data_endpoint="https://test.example.com")
        result = client.exec_command(
            agent_name="test-agent",
            session_id="session-123",
            command=["ls", "-la"],
        )

        assert isinstance(result, dict)
        assert result["stdout"] == "file1.txt\nfile2.txt"

        call_args = mock_data.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/runtimes/test-agent/commands"

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_exec_command_with_chunked_header(self, mock_data):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.status_code = 200
        mock_result.data = {"result": "ok"}
        mock_result.headers = {"Content-Type": "application/json"}
        mock_result.streaming = False
        mock_data.return_value = mock_result

        client = RuntimeClient(data_endpoint="https://test.example.com")
        client.exec_command(
            agent_name="test-agent",
            session_id="session-123",
            command=["echo", "hello"],
            chunked=True,
        )

        call_kwargs = mock_data.call_args.kwargs
        headers = call_kwargs.get("headers", {})
        assert headers.get("Command-Type") == "chunked"

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_exec_command_command_as_array(self, mock_data):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.status_code = 200
        mock_result.data = {"stdout": ""}
        mock_result.headers = {"Content-Type": "application/json"}
        mock_result.streaming = False
        mock_data.return_value = mock_result

        client = RuntimeClient(data_endpoint="https://test.example.com")
        client.exec_command(
            agent_name="test-agent",
            session_id="session-123",
            command=["ls", "-la", "/home"],
        )

        call_kwargs = mock_data.call_args.kwargs
        payload = call_kwargs.get("json", {})
        assert payload["command"] == ["ls", "-la", "/home"]

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_exec_command_with_bearer_token(self, mock_data):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.status_code = 200
        mock_result.data = {"stdout": ""}
        mock_result.headers = {"Content-Type": "application/json"}
        mock_result.streaming = False
        mock_data.return_value = mock_result

        client = RuntimeClient(data_endpoint="https://test.example.com")
        client.exec_command(
            agent_name="test-agent",
            session_id="session-123",
            command=["pwd"],
            bearer_token="test-token",
        )

        call_kwargs = mock_data.call_args.kwargs
        headers = call_kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer test-token"

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_exec_command_failure_raises_error(self, mock_data):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.status_code = 500
        mock_result.error = "Internal Server Error"
        mock_result.data = None
        mock_data.return_value = mock_result

        client = RuntimeClient(data_endpoint="https://test.example.com")

        with pytest.raises(RuntimeError, match="exec_command failed"):
            client.exec_command(
                agent_name="test-agent",
                session_id="session-123",
                command=["ls"],
            )


class TestRuntimeClientUploadFiles:
    """Tests for RuntimeClient.upload_files method."""

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_upload_files_single_file_streaming(self, mock_data):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name

        try:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.status_code = 200
            mock_result.data = {"status": "uploaded"}
            mock_data.return_value = mock_result

            client = RuntimeClient(data_endpoint="https://test.example.com")
            result = client.upload_files(
                agent_name="test-agent",
                session_id="session-123",
                files=[{"path": "/home/user/test.txt", "local_file": tmp_path}],
            )

            assert result["status"] == "uploaded"

            call_kwargs = mock_data.call_args.kwargs
            headers = call_kwargs.get("headers", {})
            assert headers.get("Content-Type") == "application/octet-stream"
            params = call_kwargs.get("params", {})
            assert params.get("path") == "/home/user/test.txt"
        finally:
            Path(tmp_path).unlink()

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_upload_files_multiple_files_multipart(self, mock_data):
        with tempfile.NamedTemporaryFile(delete=False) as tmp1:
            tmp1.write(b"content1")
            tmp1_path = tmp1.name
        with tempfile.NamedTemporaryFile(delete=False) as tmp2:
            tmp2.write(b"content2")
            tmp2_path = tmp2.name

        try:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.status_code = 200
            mock_result.data = {"status": "uploaded", "files": 2}
            mock_data.return_value = mock_result

            client = RuntimeClient(data_endpoint="https://test.example.com")
            result = client.upload_files(
                agent_name="test-agent",
                session_id="session-123",
                files=[
                    {"local_file": tmp1_path},
                    {"local_file": tmp2_path},
                ],
                path="/home/user/",
            )

            assert result["files"] == 2

            call_kwargs = mock_data.call_args.kwargs
            assert "files" in call_kwargs
            params = call_kwargs.get("params", {})
            assert params.get("path") == "/home/user/"
        finally:
            Path(tmp1_path).unlink()
            Path(tmp2_path).unlink()

    def test_upload_files_empty_files_raises_error(self):
        client = RuntimeClient(data_endpoint="https://test.example.com")

        with pytest.raises(ValueError, match="Files list cannot be empty"):
            client.upload_files(
                agent_name="test-agent",
                session_id="session-123",
                files=[],
            )

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_upload_files_with_metadata(self, mock_data):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name

        try:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.status_code = 200
            mock_result.data = {"status": "uploaded"}
            mock_data.return_value = mock_result

            client = RuntimeClient(data_endpoint="https://test.example.com")
            client.upload_files(
                agent_name="test-agent",
                session_id="session-123",
                files=[{"path": "/home/user/test.txt", "local_file": tmp_path}],
                file_user_id=1001,
                file_group_id=1001,
                file_mode="0755",
            )

            call_kwargs = mock_data.call_args.kwargs
            params = call_kwargs.get("params", {})
            assert params.get("user_id") == 1001
            assert params.get("group_id") == 1001
            assert params.get("file_mode") == "0755"
        finally:
            Path(tmp_path).unlink()

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_upload_files_with_bearer_token(self, mock_data):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name

        try:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.status_code = 200
            mock_result.data = {"status": "uploaded"}
            mock_data.return_value = mock_result

            client = RuntimeClient(data_endpoint="https://test.example.com")
            client.upload_files(
                agent_name="test-agent",
                session_id="session-123",
                files=[{"path": "/home/user/test.txt", "local_file": tmp_path}],
                bearer_token="test-token",
            )

            call_kwargs = mock_data.call_args.kwargs
            headers = call_kwargs.get("headers", {})
            assert headers.get("Authorization") == "Bearer test-token"
        finally:
            Path(tmp_path).unlink()

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_upload_files_failure_raises_error(self, mock_data):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name

        try:
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.status_code = 500
            mock_result.error = "Upload failed"
            mock_data.return_value = mock_result

            client = RuntimeClient(data_endpoint="https://test.example.com")

            with pytest.raises(RuntimeError, match="upload_files failed"):
                client.upload_files(
                    agent_name="test-agent",
                    session_id="session-123",
                    files=[{"path": "/home/user/test.txt", "local_file": tmp_path}],
                )
        finally:
            Path(tmp_path).unlink()

    def test_upload_files_oversized_file_raises_error(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"x" * (100 * 1024 * 1024 + 1))
            tmp_path = tmp.name

        try:
            client = RuntimeClient(data_endpoint="https://test.example.com")

            with pytest.raises(ValueError, match="File too large"):
                client.upload_files(
                    agent_name="test-agent",
                    session_id="session-123",
                    files=[{"path": "/home/user/test.txt", "local_file": tmp_path}],
                )
        finally:
            Path(tmp_path).unlink()

    def test_upload_files_oversized_content_raises_error(self):
        client = RuntimeClient(data_endpoint="https://test.example.com")

        with pytest.raises(ValueError, match="Content too large"):
            client.upload_files(
                agent_name="test-agent",
                session_id="session-123",
                files=[{"content": b"x" * (100 * 1024 * 1024 + 1)}],
            )


class TestRuntimeClientDownloadFiles:
    """Tests for RuntimeClient.download_files method."""

    def test_download_files_returns_stream_result(self):
        client = RuntimeClient(data_endpoint="https://test.example.com")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.headers = {"Content-Type": "application/octet-stream"}
        mock_response.iter_content.return_value = iter([b"test content"])

        with patch.object(client._data_client._session, "request", return_value=mock_response):
            result = client.download_files(
                agent_name="test-agent",
                session_id="session-123",
                path="/home/user/test.txt",
            )

        assert isinstance(result, StreamDownloadResult)
        assert result.success is True
        assert result.status_code == 200
        assert "octet-stream" in result.content_type

    def test_download_files_recursive_tar(self):
        client = RuntimeClient(data_endpoint="https://test.example.com")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.headers = {"Content-Type": "application/x-tar"}
        mock_response.iter_content.return_value = iter([b"tar content"])

        with patch.object(client._data_client._session, "request", return_value=mock_response):
            result = client.download_files(
                agent_name="test-agent",
                session_id="session-123",
                path="/home/user/data",
                recursive=True,
            )

        assert isinstance(result, StreamDownloadResult)
        assert "x-tar" in result.content_type

    def test_download_files_iter_bytes(self):
        client = RuntimeClient(data_endpoint="https://test.example.com")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.headers = {"Content-Type": "application/octet-stream"}
        mock_response.iter_content.return_value = iter([b"chunk1", b"chunk2"])

        with patch.object(client._data_client._session, "request", return_value=mock_response):
            result = client.download_files(
                agent_name="test-agent",
                session_id="session-123",
                path="/home/user/test.txt",
            )

            chunks = list(result.iter_bytes())
            assert chunks == [b"chunk1", b"chunk2"]

    def test_download_files_close(self):
        client = RuntimeClient(data_endpoint="https://test.example.com")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.headers = {"Content-Type": "application/octet-stream"}
        mock_response.iter_content.return_value = iter([])

        with patch.object(client._data_client._session, "request", return_value=mock_response):
            result = client.download_files(
                agent_name="test-agent",
                session_id="session-123",
                path="/home/user/test.txt",
            )

            result.close()
            mock_response.close.assert_called_once()

    def test_stream_download_result_no_response_raises(self):
        result = StreamDownloadResult(
            success=True,
            status_code=200,
            content_type="application/octet-stream",
        )

        with pytest.raises(RuntimeError, match="No response available"):
            list(result.iter_bytes())


class TestRuntimeClientStopSession:
    """Tests for RuntimeClient.stop_session method."""

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_stop_session_success(self, mock_data):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.status_code = 200
        mock_result.data = {"status": "stopped"}
        mock_data.return_value = mock_result

        client = RuntimeClient(data_endpoint="https://test.example.com")
        result = client.stop_session(
            agent_name="test-agent",
            session_id="session-123",
        )

        assert result["status"] == "stopped"

        call_args = mock_data.call_args
        assert call_args[0][0] == "PUT"
        assert call_args[0][1] == "/runtimes/test-agent/sessions/stop"

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_stop_session_with_bearer_token(self, mock_data):
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.status_code = 200
        mock_result.data = {"status": "stopped"}
        mock_data.return_value = mock_result

        client = RuntimeClient(data_endpoint="https://test.example.com")
        client.stop_session(
            agent_name="test-agent",
            session_id="session-123",
            bearer_token="test-token",
        )

        call_kwargs = mock_data.call_args.kwargs
        headers = call_kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer test-token"

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_stop_session_failure_raises_error(self, mock_data):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.status_code = 404
        mock_result.error = "Session not found"
        mock_data.return_value = mock_result

        client = RuntimeClient(data_endpoint="https://test.example.com")

        with pytest.raises(RuntimeError, match="stop_session failed"):
            client.stop_session(
                agent_name="test-agent",
                session_id="session-123",
            )


class TestStreamDownloadResult:
    """Tests for StreamDownloadResult dataclass."""

    def test_stream_download_result_init(self):
        result = StreamDownloadResult(
            success=True,
            status_code=200,
            content_type="application/octet-stream",
        )

        assert result.success is True
        assert result.status_code == 200
        assert result.content_type == "application/octet-stream"
        assert result.error is None

    def test_stream_download_result_with_error(self):
        result = StreamDownloadResult(
            success=False,
            status_code=500,
            content_type="application/json",
            error="Download failed",
        )

        assert result.success is False
        assert result.error == "Download failed"

    def test_stream_download_result_close_with_none_response(self):
        result = StreamDownloadResult(
            success=True,
            status_code=200,
            content_type="application/octet-stream",
        )

        result.close()
        assert result._raw_response is None
