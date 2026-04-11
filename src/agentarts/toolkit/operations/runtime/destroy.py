"""Destroy agent operation."""

from typing import Optional

from rich.console import Console

from agentarts.toolkit.operations.runtime.config import get_agent, get_config_file_path
from agentarts.toolkit.utils.common import echo_error, echo_success, echo_info

console = Console()


def destroy_agent(
    agent_name: Optional[str] = None,
    region: Optional[str] = None,
) -> bool:
    """
    Destroy agent from Huawei Cloud.

    Args:
        agent_name: Agent name to destroy
        region: Huawei Cloud region

    Returns:
        True if destroyed successfully, False otherwise
    """
    try:
        if agent_name is None:
            config_path = get_config_file_path()
            if config_path.exists():
                agent_config = get_agent(None)
                if agent_config is not None:
                    agent_name = agent_config.base.name
                    region = region or agent_config.base.region

            if agent_name is None:
                echo_error("No agent specified")
                return False

        actual_region = region or "cn-north-4"

        console.print()
        echo_info("Destroy Agent", f"[cyan]Agent:[/cyan] [white]{agent_name}[/white]\n[cyan]Region:[/cyan] [yellow]{actual_region}[/yellow]")

        from agentarts.sdk.service import RuntimeClient
        from agentarts.sdk.utils.constant import get_control_plane_endpoint

        control_endpoint = get_control_plane_endpoint(actual_region)
        client = RuntimeClient(control_endpoint=control_endpoint)

        result = client.delete_agent_by_name(agent_name=agent_name)

        if result:
            console.print()
            echo_success(f"Agent '{agent_name}' destroyed successfully")
            return True
        else:
            echo_error(f"Failed to destroy agent '{agent_name}'")
            return False

    except Exception as e:
        echo_error(str(e))
        return False
