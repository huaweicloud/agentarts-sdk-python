"""Runtime stop-session command"""

import json
from typing import Annotated

import typer
from rich.console import Console

from agentarts.toolkit.operations.runtime.stop_session import stop_runtime_session
from agentarts.toolkit.utils.common import echo_error, echo_info, echo_success

console = Console()


def stop_session_cmd(
    agent: Annotated[str, typer.Option("--agent", "-a", help="Agent name [required]")] = None,
    session: Annotated[str, typer.Option("--session", "-s", help="Session ID [required]")] = None,
    bearer_token: Annotated[str | None, typer.Option("--bearer-token", "-bt", help="Bearer token for authentication")] = None,
    region: Annotated[str | None, typer.Option("--region", "-r", help="Region name")] = None,
    endpoint: Annotated[str | None, typer.Option("--endpoint", "-e", help="Endpoint name")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
    user_id: Annotated[str | None, typer.Option("--user-id", "-u", help="User ID for OAuth2 outbound credentials")] = None,
) -> None:
    """
    Stop runtime session (cloud only).

    Examples:
        agentarts runtime stop-session --agent myagent --session <session-id>
        agentarts runtime stop-session -a myagent -s <session-id> -bt <bearer-token>
        agentarts runtime stop-session -a myagent -s <session-id> -e myendpoint
        agentarts runtime stop-session -a myagent -s <session-id> --skip-ssl-verification
    """
    try:
        echo_info(
            "Stop Session",
            f"[cyan]Agent:[/cyan] [white]{agent}[/white]\n[cyan]Session:[/cyan] [dim]{session}[/dim]",
        )

        result = stop_runtime_session(
            agent_name=agent,
            session_id=session,
            bearer_token=bearer_token,
            region=region,
            endpoint=endpoint,
            skip_ssl_verification=skip_ssl_verification,
            user_id=user_id,
        )

        echo_success("Session stopped successfully")
        console.print(f"  Agent: [bold]{agent}[/bold]")
        console.print(f"  Session ID: [dim]{session}[/dim]")
        console.print(f"  Response: [dim]{json.dumps(result, ensure_ascii=False)}[/dim]")

    except ValueError as e:
        echo_error(f"Validation error: {e}")
        raise typer.Exit(1)
    except Exception as e:
        echo_error(f"Failed to stop session: {e}")
        raise typer.Exit(1)
