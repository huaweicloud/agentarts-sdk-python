"""Runtime start-session operation"""

from typing import Any

from rich.console import Console

from agentarts.sdk.service.runtime_client import RuntimeClient
from agentarts.toolkit.operations.runtime.invoke import _get_data_endpoint, _resolve_agent_info
from agentarts.toolkit.utils.common import echo_error, echo_info

console = Console()


def start_runtime_session(
    agent_name: str | None = None,
    region: str | None = None,
    bearer_token: str | None = None,
) -> dict[str, Any]:
    """
    Start runtime session.

    Args:
        agent_name: Agent name
        region: Region name
        bearer_token: Optional bearer token for authentication

    Returns:
        Start result dict with session_id
    """
    agent_name, region, agent_id, auth_type = _resolve_agent_info(agent_name, region)

    if agent_name is None:
        echo_error("No agent specified and no default agent configured")
        raise ValueError("Agent name is required")

    data_endpoint = _get_data_endpoint(agent_name, region or "", agent_id)

    if not data_endpoint:
        raise ValueError(f"No data endpoint for agent {agent_name}")

    echo_info(
        "Start Session",
        f"[cyan]Agent:[/cyan] [white]{agent_name}[/white]",
    )

    client = RuntimeClient(data_endpoint=data_endpoint, region_id=region or "")
    return client.start_session(
        agent_name=agent_name,
        bearer_token=bearer_token,
    )