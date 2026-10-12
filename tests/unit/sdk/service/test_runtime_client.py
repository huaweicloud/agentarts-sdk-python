"""Unit tests for RuntimeClient new methods"""

import tarfile
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentarts.sdk.service.runtime_client import (
    RuntimeClient,
    StreamDownloadResult,
    is_tar_payload,
    upload_content_type,
)


class TestTarDetection:
    """Direct tests for the module-level tar / content-type helpers."""

    @staticmethod
    def _make_tar(path: Path, fmt: int = tarfile.USTAR_FORMAT) -> None:
        with tarfile.open(path, "w", format=fmt) as t:
            data = b"hello tar"
            info = tarfile.TarInfo("inside.txt")
            info.size = len(data)
            t.addfile(info, BytesIO(data))

    def test_suffix_detected(self, tmp_path):
        p = tmp_path / "payload.tar"
        p.write_bytes(b"\x00" * 10)
        assert is_tar_payload(local_file=str(p)) is True
        assert upload_content_type(local_file=str(p)) == "application/x-tar"

    def test_gnu_magic_without_suffix(self, tmp_path):
        p = tmp_path / "payload.gnu"
        self._make_tar(p, fmt=tarfile.GNU_FORMAT)
        assert is_tar_payload(local_file=str(p)) is True
        assert upload_content_type(local_file=str(p)) == "application/x-tar"

    def test_pax_magic_without_suffix(self, tmp_path):
        p = tmp_path / "payload.pax"
        self._make_tar(p, fmt=tarfile.PAX_FORMAT)
        assert is_tar_payload(local_file=str(p)) is True

    def test_non_tar_is_octet_stream(self, tmp_path):
        p = tmp_path / "notes.txt"
        p.write_bytes(b"plain text")
        assert is_tar_payload(local_file=str(p)) is False
        assert upload_content_type(local_file=str(p)) == "application/octet-stream"

    def test_compressed_tarball_not_misdetected(self, tmp_path):
        import gzip

        p = tmp_path / "payload.tar.gz"
        with gzip.open(p, "wb") as fh:
            fh.write(b"not a raw tar")
        assert is_tar_payload(local_file=str(p)) is False
        assert upload_content_type(local_file=str(p)) == "application/octet-stream"

    def test_in_memory_tar_content(self, tmp_path):
        p = tmp_path / "real.tar"
        self._make_tar(p)
        content = p.read_bytes()
        assert is_tar_payload(content=content) is True
        assert upload_content_type(content=content) == "application/x-tar"

    def test_short_content_is_not_tar(self):
        # b"hello" (5 bytes) is what the v11 signing tests upload; must stay
        # octet-stream so those wire-level signing assertions still hold.
        assert is_tar_payload(content=b"hello", filename="f.txt") is False
        assert upload_content_type(content=b"hello", filename="f.txt") == "application/octet-stream"


class TestRuntimeClientLifecycleConfig:
    """Lifecycle configuration is sent through every control-plane path."""

    def test_create_agent_includes_lifecycle_config(self):
        client = RuntimeClient(control_endpoint="https://control.example.com")
        lifecycle_config = {
            "idle_session_timeout_sec": 600,
            "max_alive_time_sec": 3600,
        }

        with patch.object(client, "_control") as mock_control, patch.object(
            client, "_check", return_value={"id": "agent-1"}
        ):
            client.create_agent(name="test-agent", lifecycle_config=lifecycle_config)

        assert mock_control.call_args.kwargs["json"]["lifecycle_config"] == lifecycle_config

    def test_update_agent_includes_lifecycle_config(self):
        client = RuntimeClient(control_endpoint="https://control.example.com")
        lifecycle_config = {"idle_session_timeout_sec": 900}

        with patch.object(client, "_control") as mock_control, patch.object(
            client, "_check", return_value={"id": "agent-1"}
        ):
            client.update_agent(agent_id="agent-1", lifecycle_config=lifecycle_config)

        assert mock_control.call_args.kwargs["json"]["lifecycle_config"] == lifecycle_config

    def test_lifecycle_config_none_is_omitted(self):
        client = RuntimeClient(control_endpoint="https://control.example.com")

        with patch.object(client, "_control") as mock_control, patch.object(
            client, "_check", return_value={"id": "agent-1"}
        ):
            client.create_agent(name="test-agent", lifecycle_config=None)

        assert "lifecycle_config" not in mock_control.call_args.kwargs["json"]

    def test_upsert_forwards_lifecycle_config_to_create_and_update(self):
        client = RuntimeClient(control_endpoint="https://control.example.com")
        lifecycle_config = {"max_alive_time_sec": 86400}

        with patch.object(client, "find_agent_by_name", return_value=None), patch.object(
            client, "create_agent", return_value={"id": "agent-1"}
        ) as mock_create:
            client.create_or_update_agent(
                agent_name="test-agent", lifecycle_config=lifecycle_config
            )
        assert mock_create.call_args.kwargs["lifecycle_config"] == lifecycle_config

        with patch.object(
            client, "find_agent_by_name", return_value={"id": "agent-1"}
        ), patch.object(
            client, "update_agent", return_value={"id": "agent-1"}
        ) as mock_update:
            client.create_or_update_agent(
                agent_name="test-agent", lifecycle_config=lifecycle_config
            )
        assert mock_update.call_args.kwargs["lifecycle_config"] == lifecycle_config


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

    @staticmethod
    def _make_tar(path: str) -> None:
        with tarfile.open(path, "w") as t:
            data = b"tar payload"
            info = tarfile.TarInfo("inside.txt")
            info.size = len(data)
            t.addfile(info, BytesIO(data))

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_upload_files_single_tar_uses_x_tar(self, mock_data):
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
            tmp_path = tmp.name
        self._make_tar(tmp_path)

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
                files=[{"local_file": tmp_path}],
                path="/tmp/",
            )

            call_kwargs = mock_data.call_args.kwargs
            headers = call_kwargs.get("headers", {})
            # tar must go on the dedicated application/x-tar channel; sending it
            # as application/octet-stream makes the gateway reset the connection
            # and the real server error is masked by an SSL EOF.
            assert headers.get("Content-Type") == "application/x-tar"
        finally:
            Path(tmp_path).unlink()

    @patch("agentarts.sdk.service.runtime_client.RuntimeClient._data")
    def test_upload_files_tar_by_magic_bytes_without_extension(self, mock_data):
        # A real tar whose filename lacks the .tar suffix must still be detected
        # via the ustar magic at offset 257.
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        self._make_tar(tmp_path)

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
                files=[{"local_file": tmp_path}],
                path="/tmp/",
            )

            call_kwargs = mock_data.call_args.kwargs
            headers = call_kwargs.get("headers", {})
            assert headers.get("Content-Type") == "application/x-tar"
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
                path="/tmp/",
            )

            assert result["files"] == 2

            call_kwargs = mock_data.call_args.kwargs
            assert "files" in call_kwargs
            params = call_kwargs.get("params", {})
            assert params.get("path") == "/tmp/"
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

    def test_download_files_signs_when_ak_sk_enabled(self):
        """Regression: _request_stream must sign (V11) when the data client has
        open_ak_sk set. Previously download_files called session.request
        directly, bypassing signing -> unsigned request -> HTTP 401 on IAM
        agents (while upload_files, which goes through _request, signed fine)."""
        from types import SimpleNamespace

        from agentarts.sdk.service.http_client import SignMode

        client = RuntimeClient(
            data_endpoint="https://test.example.com",
            sign_mode=SignMode.V11_HMAC_SHA256,
            region_id="cn-southwest-2",
        )
        client._data_client._credentials = SimpleNamespace(
            ak="ak", sk="sk", security_token=None
        )
        assert client._data_client._open_ak_sk is True

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.headers = {"Content-Type": "application/octet-stream"}
        mock_response.iter_content.return_value = iter([b"test content"])

        with patch.object(
            client._data_client, "_sign_request", return_value={"headers": {}}
        ) as mock_sign, patch.object(
            client._data_client._session, "request", return_value=mock_response
        ):
            client.download_files(
                agent_name="test-agent", session_id="session-123", path="/x"
            )

        mock_sign.assert_called_once()

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
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/runtimes/test-agent/sessions-stop"

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
