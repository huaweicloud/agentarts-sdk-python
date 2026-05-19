"""Runtime exec-command operation"""

import shlex
from collections.abc import Iterator
from typing import Any

from rich.console import Console

from agentarts.sdk.service.runtime_client import RuntimeClient
from agentarts.toolkit.operations.runtime.invoke import _get_data_endpoint, _resolve_agent_info
from agentarts.toolkit.utils.common import echo_error, echo_info

console = Console()


def exec_runtime_command(
    command: str,
    agent_name: str | None = None,
    session_id: str | None = None,
    chunked: bool = False,
    region: str | None = None,
) -> dict[str, Any] | Iterator[str]:
    """Execute command in runtime."""
    if not command:
        raise ValueError("Command is required")

    command_array = shlex.split(command)
    if not command_array:
        raise ValueError("Command cannot be empty")

    agent_name, region, agent_id, auth_type = _resolve_agent_info(agent_name, region)

    if agent_name is None:
        echo_error("No agent specified and no default agent configured")
        raise ValueError("Agent name is required")

    data_endpoint = _get_data_endpoint(agent_name, region or "", agent_id)

    if not data_endpoint:
        raise ValueError(f"No data endpoint for agent {agent_name}")

    mode_str = "chunked (ndjson)" if chunked else "json"
    echo_info(
        "Exec Command",
        f"[cyan]Agent:[/cyan] [white]{agent_name}[/white]\n[cyan]Session:[/cyan] [dim]{session_id}[/dim]\n[cyan]Mode:[/cyan] [yellow]{mode_str}[/yellow]\n[cyan]Command:[/cyan] [dim]{command_array}[/dim]",
    )

    client = RuntimeClient(data_endpoint=data_endpoint, region_id=region or "")
    return client.exec_command(
        agent_name=agent_name,
        session_id=session_id,
        command=command_array,
        chunked=chunked,
    )
