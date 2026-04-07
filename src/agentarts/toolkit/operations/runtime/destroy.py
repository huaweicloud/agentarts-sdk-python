"""Destroy agent operation."""

from typing import Optional

from rich.console import Console

from agentarts.toolkit.operations.runtime.config import get_agent, get_config_file_path

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
                console.print("[red]Error: No agent specified[/red]")
                return False

        actual_region = region or "cn-north-4"

        console.print(f"\n[bold]Destroying agent:[/bold] [cyan]{agent_name}[/cyan]")
        console.print(f"[yellow]Region: {actual_region}[/yellow]")

        from agentarts.sdk.service import RuntimeClient
        from agentarts.sdk.utils.constant import get_control_plane_endpoint

        control_endpoint = get_control_plane_endpoint(actual_region)
        client = RuntimeClient(control_endpoint=control_endpoint)

        result = client.delete_agent_by_name(agent_name=agent_name)

        if result:
            console.print(f"[green]✓ Agent '{agent_name}' destroyed successfully[/green]")
            return True
        else:
            console.print(f"[red]✗ Failed to destroy agent '{agent_name}'[/red]")
            return False

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False
