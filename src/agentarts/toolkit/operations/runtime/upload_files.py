"""Runtime upload-files operation"""

import os
from typing import Any

from rich.console import Console

from agentarts.sdk.service.runtime_client import RuntimeClient
from agentarts.toolkit.operations.runtime.invoke import _get_data_endpoint, _resolve_agent_info
from agentarts.toolkit.utils.common import echo_error, echo_info

console = Console()

DEFAULT_PATH = "/home/user"
DEFAULT_USER_ID = 1000
DEFAULT_GROUP_ID = 1000
DEFAULT_FILE_MODE = "0644"


def upload_runtime_files(
    agent_name: str | None = None,
    session_id: str | None = None,
    files: list[dict[str, str]] | None = None,
    user_id: int = DEFAULT_USER_ID,
    group_id: int = DEFAULT_GROUP_ID,
    file_mode: str = DEFAULT_FILE_MODE,
    bearer_token: str | None = None,
    region: str | None = None,
    endpoint: str | None = None,
    skip_ssl_verification: bool = False,
    oauth_user_id: str | None = None,
    timeout: int = 900,
) -> dict[str, Any]:
    """Upload files to runtime.

    Args:
        agent_name: Agent name
        session_id: Session ID
        files: List of file specs with path and local_file
        user_id: File owner user ID (default: 1000)
        group_id: File owner group ID (default: 1000)
        file_mode: File permissions in octal (default: "0644")
        bearer_token: Optional bearer token
        region: Region name
        endpoint: Optional endpoint name
        skip_ssl_verification: Skip SSL certificate verification
        oauth_user_id: Optional user ID for OAuth2 outbound credentials
        timeout: Request timeout in seconds

    Returns:
        Upload result dict
    """
    if not files:
        raise ValueError("Files are required")

    agent_name, region, agent_id, auth_type = _resolve_agent_info(agent_name, region)

    if agent_name is None:
        echo_error("No agent specified and no default agent configured")
        raise ValueError("Agent name is required")

    if session_id is None:
        raise ValueError("Session ID is required")

    verify_ssl = not skip_ssl_verification
    data_endpoint = _get_data_endpoint(agent_name, region or "", agent_id, verify_ssl)

    if not data_endpoint:
        raise ValueError(f"No data endpoint for agent {agent_name}")

    for file_spec in files:
        path = file_spec.get("path", "")
        if not path.startswith(DEFAULT_PATH):
            normalized_path = os.path.normpath(path)
            file_spec["path"] = os.path.join(DEFAULT_PATH, normalized_path.lstrip("/"))

    echo_info(
        "Upload Files",
        f"[cyan]Agent:[/cyan] [white]{agent_name}[/white]\n[cyan]Session:[/cyan] [dim]{session_id}[/dim]\n[cyan]Files:[/cyan] [yellow]{len(files)}[/yellow]\n[cyan]User ID:[/cyan] [dim]{user_id}[/dim]\n[cyan]Group ID:[/cyan] [dim]{group_id}[/dim]\n[cyan]File Mode:[/cyan] [dim]{file_mode}[/dim]",
    )

    client = RuntimeClient(data_endpoint=data_endpoint, region_id=region or "", verify_ssl=verify_ssl)
    return client.upload_files(
        agent_name=agent_name,
        session_id=session_id,
        files=files,
        user_id=user_id,
        group_id=group_id,
        file_mode=file_mode,
        bearer_token=bearer_token,
        endpoint=endpoint,
        oauth_user_id=oauth_user_id,
        timeout=timeout,
    )
