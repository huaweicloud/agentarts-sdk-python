"""Runtime exec-command command"""

import json
from collections.abc import Iterator
from typing import Annotated

import typer
from rich.console import Console

from agentarts.toolkit.operations.runtime.exec_command import exec_runtime_command
from agentarts.toolkit.utils.common import echo_error, echo_success

console = Console()


def exec_command_cmd(
    command: Annotated[str, typer.Argument(help="Command to execute (e.g., 'ls -la' or 'ls')")],
    agent: Annotated[str, typer.Option("--agent", "-a", help="Agent name [required]")] = None,
    session: Annotated[str, typer.Option("--session", "-s", help="Session ID")] = None,
    chunked: Annotated[bool, typer.Option("--chunked", help="Enable chunked streaming response (application/x-ndjson)")] = False,
    region: Annotated[str | None, typer.Option("--region", "-r", help="Region name")] = None,
) -> None:
    """
    Execute command in runtime (cloud only).

    The command can be a simple string like 'ls' or 'ls -la'.
    It will be parsed as a command array when sent to backend.

    Examples:
        agentarts runtime exec-command "ls -la" --agent myagent --session <session-id>
        agentarts runtime exec-command "ls -la" --agent myagent --session <session-id> --chunked
        agentarts runtime exec-command "ls" --agent myagent --session <session-id>
    """
    try:
        result = exec_runtime_command(
            command=command,
            agent_name=agent,
            session_id=session,
            chunked=chunked,
            region=region,
        )

        if chunked and isinstance(result, Iterator):
            echo_success("Streaming output (ndjson):")
            for line in result:
                try:
                    data = json.loads(line)
                    console.print_json(json.dumps(data, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    console.print(line)
        else:
            echo_success("Command executed")
            console.print_json(json.dumps(result, indent=2, ensure_ascii=False))

    except ValueError as e:
        echo_error(f"Validation error: {e}")
        raise typer.Exit(1)
    except Exception as e:
        echo_error(f"Failed to execute command: {e}")
        raise typer.Exit(1)
