"""
AgentArts CLI Entry Point

This module provides the main CLI entry point for the AgentArts toolkit.
It only handles command registration. Command definitions are in cli/
and implementation logic is in operations/.
"""

from typing import Annotated

import typer
from rich.console import Console

from agentarts.toolkit.cli.runtime import init, dev, deploy
from agentarts.toolkit.cli.runtime.config import config_app
from agentarts.toolkit.cli.runtime.invoke import console as invoke_app
from agentarts.toolkit.cli.mcp_gateway import mcp_gateway
from agentarts.toolkit.cli.memory.commands import memory_app

console = Console()

app = typer.Typer(
    name="agentarts",
    help="AgentArts CLI - Huawei Cloud Agent Development Toolkit\n\nBuild, test, and deploy Agent applications quickly.",
    add_completion=False,
    rich_markup_mode="rich",
)


@app.callback(invoke_without_command=True)
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-v", help="Show version and exit"),
    ] = False,
):
    """
    AgentArts CLI - Huawei Cloud Agent Development Toolkit

    Build, test, and deploy Agent applications quickly.

    Examples:
        agentarts init -n my_agent -t langgraph
        agentarts dev --port 8080
        agentarts deploy -r cn-north-4 -e production
    """
    if version:
        from agentarts import __version__
        console.print(f"agentarts version: [bold green]{__version__}[/bold green]")
        raise typer.Exit()


app.command(name="init")(init)
app.command(name="dev")(dev)
app.command(name="deploy", help="Deploy agent to Huawei Cloud or run locally. (alias: launch)")(deploy)
app.command(name="launch", help="Alias for 'deploy' command.")(deploy)
app.add_typer(config_app, name="config", help="Configuration management. (alias: configure)")
app.add_typer(config_app, name="configure", hidden=True)
app.add_typer(invoke_app, name="invoke")
app.add_typer(mcp_gateway, name="mcp-gateway")
app.add_typer(memory_app, name="memory")


def cli():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    cli()
