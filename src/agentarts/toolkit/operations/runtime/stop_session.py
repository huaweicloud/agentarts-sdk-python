"""Runtime stop-session operation"""

from typing import Any

from rich.console import Console

from agentarts.sdk.service.runtime_client import RuntimeClient
from agentarts.toolkit.operations.runtime.invoke import _get_data_endpoint, _resolve_agent_info
from agentarts.toolkit.utils.common import echo_error, echo_info

console = Console()


def stop_runtime_session(
    agent_name: str | None = None,
    session_id: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """
    Stop runtime session.

    Args:
        agent_name: Agent name
        session_id: Session ID
        region: Region name

    Returns:
        Stop result dict
    """
    agent_name, region, agent_id, auth_type = _resolve_agent_info(agent_name, region)

    if agent_name is None:
        echo_error("No agent specified and no default agent configured")
        raise ValueError("Agent name is required")

    if session_id is None:
        raise ValueError("Session ID is required")

    data_endpoint = _get_data_endpoint(agent_name, region or "", agent_id)

    if not data_endpoint:
        raise ValueError(f"No data endpoint for agent {agent_name}")

    echo_info(
        "Stop Session",
        f"[cyan]Agent:[/cyan] [white]{agent_name}[/white]\n[cyan]Session:[/cyan] [dim]{session_id}[/dim]",
    )

    client = RuntimeClient(data_endpoint=data_endpoint, region_id=region or "")
    return client.stop_session(
        agent_name=agent_name,
        session_id=session_id,
    )
