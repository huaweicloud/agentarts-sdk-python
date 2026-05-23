"""Runtime download-files operation"""

import os
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from rich.console import Console

from agentarts.sdk.service.runtime_client import RuntimeClient
from agentarts.toolkit.operations.runtime.invoke import _get_data_endpoint, _resolve_agent_info
from agentarts.toolkit.utils.common import echo_error, echo_info

console = Console()

DEFAULT_PATH = "/home/user"


def download_runtime_files(
    agent_name: str | None = None,
    session_id: str | None = None,
    path: str | None = None,
    output: str | None = None,
    recursive: bool = False,
    bearer_token: str | None = None,
    region: str | None = None,
    endpoint: str | None = None,
    skip_ssl_verification: bool = False,
    user_id: str | None = None,
    timeout: int = 900,
) -> dict[str, Any]:
    """
    Download files from runtime.

    Args:
        agent_name: Agent name
        session_id: Session ID (required)
        path: Remote file/directory path (required)
        output: Local output path
        recursive: Download directory as tar archive
        bearer_token: Optional bearer token
        region: Region name
        endpoint: Optional endpoint name
        skip_ssl_verification: Skip SSL certificate verification
        user_id: Optional user ID for OAuth2 outbound credentials
        timeout: Request timeout in seconds

    Returns:
        Download result dict with saved_path, size, content_type
    """
    if not path:
        raise ValueError("Path is required (--path)")

    if not session_id:
        raise ValueError("Session ID is required (--session)")

    agent_name, region, agent_id, auth_type = _resolve_agent_info(agent_name, region)

    if agent_name is None:
        echo_error("No agent specified and no default agent configured")
        raise ValueError("Agent name is required")

    verify_ssl = not skip_ssl_verification
    data_endpoint = _get_data_endpoint(agent_name, region or "", agent_id, verify_ssl)

    if not data_endpoint:
        raise ValueError(f"No data endpoint for agent {agent_name}")

    if not path.startswith(DEFAULT_PATH):
        normalized_path = os.path.normpath(path)
        path = os.path.join(DEFAULT_PATH, normalized_path.lstrip("/"))

    echo_info(
        "Download Files",
        f"[cyan]Agent:[/cyan] [white]{agent_name}[/white]\n[cyan]Session:[/cyan] [dim]{session_id}[/dim]\n[cyan]Path:[/cyan] [yellow]{path}[/yellow]",
    )

    client = RuntimeClient(data_endpoint=data_endpoint, region_id=region or "", verify_ssl=verify_ssl)
    result = client.download_files(
        agent_name=agent_name,
        session_id=session_id,
        path=path,
        recursive=recursive,
        bearer_token=bearer_token,
        endpoint=endpoint,
        user_id=user_id,
        timeout=timeout,
    )

    if not result.success:
        raise RuntimeError(f"Download failed: {result.error}")

    filename = path.rsplit("/", maxsplit=1)[-1] if path else "downloaded"
    output = output or filename

    saved_path: str = ""
    total_size: int = 0
    content_type: str = result.content_type

    try:
        if recursive and "application/x-tar" in content_type:
            Path(output).mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                for chunk in result.iter_bytes():
                    tmp_file.write(chunk)
                    total_size += len(chunk)

            try:
                with tarfile.open(tmp_path, mode="r") as tar:
                    tar.extractall(output)
                    saved_path = output
            finally:
                Path(tmp_path).unlink()
        else:
            if Path(output).is_dir() or output.endswith(("/", "\\")):
                Path(output).mkdir(parents=True, exist_ok=True)
                output = os.path.join(output, filename)

            with open(output, "wb") as f:
                for chunk in result.iter_bytes():
                    f.write(chunk)
                    total_size += len(chunk)
            saved_path = output
    finally:
        result.close()

    return {
        "saved_path": saved_path,
        "size": total_size,
        "content_type": content_type,
        "path": path,
    }
