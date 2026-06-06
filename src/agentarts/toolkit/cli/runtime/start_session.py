"""Runtime start-session command"""

import json
from typing import Annotated

import typer
from rich.console import Console

from agentarts.toolkit.operations.runtime.start_session import start_runtime_session
from agentarts.toolkit.utils.common import echo_error, echo_info, echo_success

console = Console()


def start_session_cmd(
    agent: Annotated[str, typer.Option("--agent", "-a", help="Agent name [required]")] = None,
    region: Annotated[str | None, typer.Option("--region", "-r", help="Region name")] = None,
    bearer_token: Annotated[str | None, typer.Option("--bearer-token", "-bt", help="Bearer token for authentication")] = None,
    endpoint: Annotated[str | None, typer.Option("--endpoint", "-e", help="Endpoint name")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
    user_id: Annotated[str | None, typer.Option("--user-id", "-u", help="User ID for OAuth2 outbound credentials")] = None,
) -> None:
    """
    Start runtime session (cloud only).

    Returns a session ID that can be used for subsequent operations.

    Examples:
        agentarts runtime start-session --agent myagent
        agentarts runtime start-session -a myagent -r cn-southwest-2
        agentarts runtime start-session -a myagent -bt <bearer-token>
        agentarts runtime start-session -a myagent -e myendpoint
        agentarts runtime start-session -a myagent --skip-ssl-verification
    """
    try:
        echo_info(
            "Start Session",
            f"[cyan]Agent:[/cyan] [white]{agent}[/white]",
        )

        result = start_runtime_session(
            agent_name=agent,
            region=region,
            bearer_token=bearer_token,
            endpoint=endpoint,
            skip_ssl_verification=skip_ssl_verification,
            user_id=user_id,
        )

        echo_success("Session started successfully")
        console.print(f"  Agent: [bold]{agent}[/bold]")
        console.print(f"  Response: [dim]{json.dumps(result, ensure_ascii=False)}[/dim]")

    except ValueError as e:
        echo_error(f"Validation error: {e}")
        raise typer.Exit(1)
    except Exception as e:
        echo_error(f"Failed to start session: {e}")
        raise typer.Exit(1)
