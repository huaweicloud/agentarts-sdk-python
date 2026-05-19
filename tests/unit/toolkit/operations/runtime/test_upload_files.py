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
            upload_runtime_files(files=[])

    def test_upload_files_no_agent_raises_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValueError, match="Agent name is required"):
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
                        username="testuser",
                        groupname="testgroup",
                        filemode="644",
                    )

                    call_args = mock_instance.upload_files.call_args
                    assert call_args.kwargs["username"] == "testuser"
                    assert call_args.kwargs["groupname"] == "testgroup"
                    assert call_args.kwargs["filemode"] == "644"
        finally:
            Path(tmp_path_file).unlink()

    def test_upload_files_with_session_id(self, tmp_path, monkeypatch):
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
                    assert call_args.kwargs["session_id"] == "session-123"
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
                    )
        finally:
            Path(tmp_path_file).unlink()
