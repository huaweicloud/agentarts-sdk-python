"""Destroy agent operation."""


from rich.console import Console

from agentarts.sdk.utils.constant import get_region
from agentarts.toolkit.operations.runtime.config import get_agent, get_config_file_path
from agentarts.toolkit.utils.common import echo_error, echo_info, echo_success

console = Console()


def destroy_agent(
    agent_name: str | None = None,
    region: str | None = None,
    skip_ssl_verification: bool = False,
) -> bool:
    """
    Destroy agent from Huawei Cloud.

    Args:
        agent_name: Agent name to destroy
        region: Huawei Cloud region
        skip_ssl_verification: Skip SSL certificate verification (default: False)

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

        actual_region = region or get_region()

        console.print()
        echo_info("Destroy Agent", f"[cyan]Agent:[/cyan] [white]{agent_name}[/white]\n[cyan]Region:[/cyan] [yellow]{actual_region}[/yellow]")

        from agentarts.sdk.service import RuntimeClient
        from agentarts.sdk.utils.constant import get_control_plane_endpoint

        verify_ssl = not skip_ssl_verification
        control_endpoint = get_control_plane_endpoint(actual_region)
        client = RuntimeClient(control_endpoint=control_endpoint, verify_ssl=verify_ssl)

        result = client.delete_agent_by_name(agent_name=agent_name)

        if result:
            console.print()
            echo_success(f"Agent '{agent_name}' destroyed successfully")
            return True
        echo_error(f"Failed to destroy agent '{agent_name}'")
        return False

    except Exception as e:
        echo_error(str(e))
        return False
