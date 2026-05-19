"""Runtime stop-session command"""

from typing import Annotated

import typer
from rich.console import Console

from agentarts.toolkit.operations.runtime.stop_session import stop_runtime_session
from agentarts.toolkit.utils.common import echo_error, echo_success

console = Console()


def stop_session_cmd(
    agent: Annotated[str, typer.Option("--agent", "-a", help="Agent name [required]")] = None,
    session: Annotated[str, typer.Option("--session", "-s", help="Session ID [required]")] = None,
    region: Annotated[str | None, typer.Option("--region", "-r", help="Region name")] = None,
) -> None:
    """
    Stop runtime session (cloud only).

    Examples:
        agentarts runtime stop-session --agent myagent --session <session-id>
    """
    try:
        stop_runtime_session(
            agent_name=agent,
            session_id=session,
            region=region,
        )

        echo_success("Session stopped successfully")
        console.print(f"  Agent: [bold]{agent}[/bold]")
        console.print(f"  Session ID: [dim]{session}[/dim]")

    except ValueError as e:
        echo_error(f"Validation error: {e}")
        raise typer.Exit(1)
    except Exception as e:
        echo_error(f"Failed to stop session: {e}")
        raise typer.Exit(1)
