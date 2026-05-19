"""Runtime upload-files operation"""

import os
from typing import Any

from rich.console import Console

from agentarts.sdk.service.runtime_client import RuntimeClient
from agentarts.toolkit.operations.runtime.invoke import _get_data_endpoint, _resolve_agent_info
from agentarts.toolkit.utils.common import echo_error, echo_info

console = Console()

DEFAULT_PATH = "/home/user"


def upload_runtime_files(
    agent_name: str | None = None,
    session_id: str | None = None,
    files: list[dict[str, str]] | None = None,
    username: str | None = None,
    groupname: str | None = None,
    filemode: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Upload files to runtime."""
    if not files:
        raise ValueError("Files are required")

    agent_name, region, agent_id, auth_type = _resolve_agent_info(agent_name, region)

    if agent_name is None:
        echo_error("No agent specified and no default agent configured")
        raise ValueError("Agent name is required")

    data_endpoint = _get_data_endpoint(agent_name, region or "", agent_id)

    if not data_endpoint:
        raise ValueError(f"No data endpoint for agent {agent_name}")

    for file_spec in files:
        path = file_spec.get("path", "")
        if not path.startswith(DEFAULT_PATH):
            normalized_path = os.path.normpath(path)
            file_spec["path"] = os.path.join(DEFAULT_PATH, normalized_path.lstrip("/"))

    echo_info(
        "Upload Files",
        f"[cyan]Agent:[/cyan] [white]{agent_name}[/white]\n[cyan]Session:[/cyan] [dim]{session_id}[/dim]\n[cyan]Files:[/cyan] [yellow]{len(files)}[/yellow]",
    )

    client = RuntimeClient(data_endpoint=data_endpoint, region_id=region or "")
    return client.upload_files(
        agent_name=agent_name,
        session_id=session_id,
        files=files,
        username=username,
        groupname=groupname,
        filemode=filemode,
    )
