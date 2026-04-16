"""
AgentArts CLI Entry Point

This module provides the main CLI entry point for the AgentArts toolkit.
It only handles command registration. Command definitions are in cli/
and implementation logic is in operations/.
"""

import logging
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler

from agentarts.toolkit.cli.mcp_gateway import mcp_gateway
from agentarts.toolkit.cli.memory.commands import memory_app
from agentarts.toolkit.cli.runtime import deploy, dev, init
from agentarts.toolkit.cli.runtime.config import config_app
from agentarts.toolkit.cli.runtime.destroy import destroy
from agentarts.toolkit.cli.runtime.invoke import invoke, status

console = Console()


def setup_logging(verbose: bool = False):
    """
    Configure logging for toolkit CLI.

    Args:
        verbose: If True, set log level to DEBUG; otherwise INFO.
    """
    log_format = "%(message)s"

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=log_format,
        handlers=[RichHandler(show_time=False, show_path=False, show_level=False, console=console)],
    )

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("huaweicloudsdkcore").setLevel(logging.WARNING)


app = typer.Typer(
    name="agentarts",
    help="AgentArts CLI - Huawei Cloud Agent Development Toolkit\n\nBuild, test, and deploy Agent applications quickly.",
    add_completion=False,
    rich_markup_mode="rich",
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", "-v", help="Show version and exit"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Enable verbose logging (DEBUG level)"),
    ] = False,
):
    """
    AgentArts CLI - Huawei Cloud Agent Development Toolkit

    Build, test, and deploy Agent applications quickly.

    Examples:
        agentarts init -n my_agent -t langgraph
        agentarts dev --port 8080
        agentarts deploy -r cn-southwest-2 -e production
    """
    setup_logging(verbose=verbose)

    if version:
        from agentarts import __version__
        console.print(f"agentarts version: [bold green]{__version__}[/bold green]")
        raise typer.Exit

    if ctx.invoked_subcommand is None:
        from agentarts import __version__
        console.print()
        console.print(f"[bold cyan]AgentArts CLI[/bold cyan] [dim]v{__version__}[/dim]")
        console.print("[dim]Huawei Cloud Agent Development Toolkit[/dim]")
        console.print()
        console.print("[yellow]Usage:[/yellow] agentarts [OPTIONS] COMMAND [ARGS]...")
        console.print()
        console.print("[yellow]Try:[/yellow]")
        console.print("  [cyan]agentarts --help[/cyan]     Show available commands")
        console.print("  [cyan]agentarts init --help[/cyan]  Show init command help")
        console.print()
        raise typer.Exit


app.command(name="init")(init)
app.command(name="dev")(dev)
app.command(name="deploy", help="Deploy agent to Huawei Cloud or run locally. (alias: launch)")(deploy)
app.command(name="launch", help="Alias for 'deploy' command.")(deploy)
app.command(name="status", help="Check agent health status.")(status)
app.command(name="destroy", help="Destroy agent from Huawei Cloud.")(destroy)
app.command(name="invoke", help="Invoke agent with JSON payload.")(invoke)
app.add_typer(config_app, name="config", help="Configuration management. (alias: configure)")
app.add_typer(config_app, name="configure", hidden=True)
app.add_typer(mcp_gateway, name="mcp-gateway")
app.add_typer(memory_app, name="memory")


def cli():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    cli()
