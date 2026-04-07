"""Invoke command definition"""

import json
from typing import Annotated, Optional

import typer

from agentarts.toolkit.operations.runtime.invoke import (
    InvokeMode,
    invoke_agent,
    status_agent,
)

console = typer.Typer(help="Invoke agent locally or on cloud")


@console.command(name="invoke")
def invoke(
    payload: Annotated[
        str,
        typer.Argument(help="JSON payload to send to the agent"),
    ],
    agent: Annotated[
        Optional[str],
        typer.Option("--agent", "-a", help="Agent name (uses default if not specified for cloud mode)"),
    ] = None,
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            "-m",
            help="Invoke mode: 'local' for Docker container, 'cloud' for AgentArts runtime (default)",
        ),
    ] = "cloud",
    region: Annotated[
        Optional[str],
        typer.Option("--region", "-r", help="Huawei Cloud region (for cloud mode)"),
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option("--port", "-p", help="Local port (for local mode, default: 8080)"),
    ] = None,
    endpoint: Annotated[
        Optional[str],
        typer.Option("--endpoint", "-e", help="Endpoint name"),
    ] = None,
    session_id: Annotated[
        Optional[str],
        typer.Option("--session", "-s", help="Session ID for stateful agents"),
    ] = None,
    bearer_token: Annotated[
        Optional[str],
        typer.Option("--token", "-t", help="Bearer token for authentication"),
    ] = None,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Request timeout in seconds"),
    ] = 900,
):
    """
    Invoke agent with JSON payload.

    Two invoke modes are supported:
    - cloud (default): Invoke AgentArts runtime on Huawei Cloud
    - local: Invoke local Docker container

    The payload must be a valid JSON string.

    Examples:
        agentarts invoke '{"input": "hello"}'
        agentarts invoke '{"input": "hello"}' --agent my-agent
        agentarts invoke '{"input": "hello"}' --mode local --port 8080
        agentarts invoke '{"query": "test"}' --session my-session-123
    """
    from rich.console import Console as RichConsole

    rich_console = RichConsole()

    invoke_mode = InvokeMode.CLOUD
    if mode.lower() == "local":
        invoke_mode = InvokeMode.LOCAL
    elif mode.lower() != "cloud":
        rich_console.print(f"[red]Error: Invalid mode '{mode}'. Use 'local' or 'cloud'.[/red]")
        raise typer.Exit(1)

    success = invoke_agent(
        payload=payload,
        agent_name=agent,
        mode=invoke_mode,
        region=region,
        port=port,
        endpoint=endpoint,
        session_id=session_id,
        bearer_token=bearer_token,
        timeout=timeout,
    )

    if not success:
        raise typer.Exit(1)


@console.command(name="status")
def status(
    agent: Annotated[
        Optional[str],
        typer.Option("--agent", "-a", help="Agent name (uses default if not specified for cloud mode)"),
    ] = None,
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            "-m",
            help="Status mode: 'local' for Docker container, 'cloud' for AgentArts runtime (default)",
        ),
    ] = "cloud",
    region: Annotated[
        Optional[str],
        typer.Option("--region", "-r", help="Huawei Cloud region (for cloud mode)"),
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option("--port", "-p", help="Local port (for local mode, default: 8080)"),
    ] = None,
    bearer_token: Annotated[
        Optional[str],
        typer.Option("--token", "-t", help="Bearer token for authentication"),
    ] = None,
):
    """
    Check agent health status.

    Two status modes are supported:
    - cloud (default): Check AgentArts runtime on Huawei Cloud
    - local: Check local Docker container

    Examples:
        agentarts invoke status
        agentarts invoke status --agent my-agent
        agentarts invoke status --mode local --port 8080
    """
    from rich.console import Console as RichConsole

    rich_console = RichConsole()

    status_mode = InvokeMode.CLOUD
    if mode.lower() == "local":
        status_mode = InvokeMode.LOCAL
    elif mode.lower() != "cloud":
        rich_console.print(f"[red]Error: Invalid mode '{mode}'. Use 'local' or 'cloud'.[/red]")
        raise typer.Exit(1)

    success = status_agent(
        agent_name=agent,
        mode=status_mode,
        region=region,
        port=port,
        bearer_token=bearer_token,
    )

    if not success:
        raise typer.Exit(1)
