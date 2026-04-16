"""Destroy command definition"""

from typing import Annotated

import typer

from agentarts.toolkit.operations.runtime.destroy import destroy_agent


def destroy(
    agent: Annotated[
        str | None,
        typer.Option("--agent", "-a", help="Agent name to destroy (uses default if not specified)"),
    ] = None,
    region: Annotated[
        str | None,
        typer.Option("--region", "-r", help="Huawei Cloud region"),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt"),
    ] = False,
):
    """
    Destroy agent from Huawei Cloud.

    This command will permanently delete the agent and all its resources.

    Examples:
        agentarts destroy
        agentarts destroy --agent my-agent
        agentarts destroy --agent my-agent --region cn-southwest-2
        agentarts destroy --yes  # Skip confirmation
    """
    from rich.console import Console as RichConsole
    from rich.prompt import Confirm

    rich_console = RichConsole()

    if not yes:
        agent_display = agent or "default agent"
        rich_console.print(f"\n[yellow]Warning: This will permanently delete agent '{agent_display}'[/yellow]")
        if not Confirm.ask("Are you sure you want to continue?"):
            rich_console.print("[yellow]Operation cancelled[/yellow]")
            raise typer.Exit(0)

    success = destroy_agent(
        agent_name=agent,
        region=region,
    )

    if not success:
        raise typer.Exit(1)
