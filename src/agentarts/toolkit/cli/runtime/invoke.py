"""Invoke command definition"""

from typing import Annotated

import typer
from rich.console import Console

from agentarts.toolkit.operations.runtime.invoke import (
    InvokeMode,
    invoke_agent,
)

rich_console = Console()


def invoke(
    payload: Annotated[
        str,
        typer.Argument(help="JSON payload to send to the agent (e.g., '{\"message\": \"hello\"}')"),
    ],
    agent: Annotated[
        str | None,
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
        str | None,
        typer.Option("--region", "-r", help="Huawei Cloud region (for cloud mode)"),
    ] = None,
    port: Annotated[
        int | None,
        typer.Option("--port", "-p", help="Local port (for local mode, default: 8080)"),
    ] = None,
    endpoint: Annotated[
        str | None,
        typer.Option("--endpoint", "-e", help="Endpoint name"),
    ] = None,
    session_id: Annotated[
        str | None,
        typer.Option("--session", "-s", help="Session ID for stateful agents"),
    ] = None,
    bearer_token: Annotated[
        str | None,
        typer.Option("--bearer-token", "-bt", help="Bearer token for authentication"),
    ] = None,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Request timeout in seconds (default: 900)"),
    ] = 900,
    skip_ssl_verification: Annotated[
        bool,
        typer.Option("--skip-ssl-verification", help="Skip SSL certificate verification"),
    ] = False,
    user_id: Annotated[
        str | None,
        typer.Option("--user-id", "-u", help="User ID for OAuth2 outbound credentials"),
    ] = None,
    custom_path: Annotated[
        str | None,
        typer.Option("--custom-path", help="Custom path appended to /invocations (e.g., 'stream' -> /invocations/stream)"),
    ] = None,
):
    """
    Invoke agent with JSON payload.

    Two invoke modes are supported:
    - cloud (default): Invoke AgentArts runtime on Huawei Cloud
    - local: Invoke local Docker container

    The payload must be a valid JSON string.

    Examples:
        agentarts invoke '{"message": "hello"}'
        agentarts invoke '{"message": "hello"}' --agent myagent
        agentarts invoke '{"message": "hello"}' --mode local --port 8080
        agentarts invoke '{"message": "test"}' --session my-session-123
        agentarts invoke '{"message": "test"}' --user-id my-user-id
        agentarts invoke '{"message": "test"}' --custom-path stream
    """
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
        skip_ssl_verification=skip_ssl_verification,
        user_id=user_id,
        custom_path=custom_path,
    )

    if not success:
        raise typer.Exit(1)
