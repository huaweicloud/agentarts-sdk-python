"""AgentArts CLI main module."""

import typer

from ..utils.logging_config import setup_toolkit_logging
from .identity.commands import identity_app
from .memory.commands import memory_app
from .runtime.commands import (
    configure_app,
    destroy,
    invoke,
    launch,
    list_cloud_agents,
    status,
)
from .mcp_gateway.commands import mcp_gateway_app
from .runtime.dev_command import dev

app = typer.Typer(
    name="agentrun",
    help="Huawei AgentArts CLI",
    add_completion=False,
    rich_markup_mode="rich",
)

# Setup centralized logging for CLI
setup_toolkit_logging(mode="cli")

# runtimes
app.command("invoke")(invoke)
app.command("launch")(launch)
app.command("list-agent")(list_cloud_agents)
app.command("destroy")(destroy)
app.command("status")(status)
app.command("dev")(dev)
app.add_typer(configure_app)

# Services
app.add_typer(identity_app, name="identity")
app.add_typer(mcp_gateway_app, name="mcp-gateway")
app.add_typer(memory_app, name="memory")


def main():
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
