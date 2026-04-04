"""
AgentArts CLI Entry Point

This module provides the main CLI entry point for the AgentArts toolkit.
It only handles command registration. Command definitions are in cli/
and implementation logic is in operations/.
"""


from typing import Optional
from agentarts.toolkit.cli.mcp_gateway import mcp_gateway
from typing import Annotated

import typer
from rich.console import Console

from agentarts.toolkit.cli.runtime import (
    init,
    dev,
    build,
    deploy,
    config_set,
    config_get,
    config_list,
)

console = Console()

app = typer.Typer(
    name="agentarts",
    help="AgentArts CLI - Huawei Cloud Agent Development Toolkit\n\nBuild, test, and deploy Agent applications quickly.",
    add_completion=False,
    rich_markup_mode="rich",
)

config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")


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
app.command(name="build")(build)
app.command(name="deploy")(deploy)


@app.command()
def logs(
    follow: Annotated[bool, typer.Option("--follow", "-f", help="Follow logs in real-time")] = False,
    tail: Annotated[int, typer.Option("--tail", "-n", help="Number of lines to show")] = 100,
    level: Annotated[str, typer.Option("--level", help="Log level")] = "info",
):
    """
    View logs.

    Examples:
        agentarts logs -f --tail 50
    """
    console.print(f"Viewing logs (level: [yellow]{level}[/yellow], tail: [cyan]{tail}[/cyan])")


config_app.command(name="set")(config_set)
config_app.command(name="get")(config_get)
config_app.command(name="list")(config_list)

# Register MCP Gateway commands
app.add_typer(mcp_gateway, name="mcp-gateway")

def cli():
    """CLI entry point."""
    app()

if __name__ == '__main__':
    cli()
