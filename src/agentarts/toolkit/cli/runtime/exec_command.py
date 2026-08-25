"""Runtime exec-command command"""

import json
import uuid
from collections.abc import Iterator
from typing import Annotated

import typer
from rich.console import Console

from agentarts.toolkit.operations.runtime.exec_command import exec_runtime_command
from agentarts.toolkit.utils.common import echo_error, echo_info, echo_success

console = Console()

DEFAULT_TIMEOUT = 60
MAX_TIMEOUT = 3600


def validate_timeout(timeout: int) -> int:
    """Validate timeout parameter."""
    if timeout <= 0:
        echo_error(f"Timeout must be a positive number: {timeout}")
        raise typer.Exit(1)
    if timeout > MAX_TIMEOUT:
        echo_error(f"Timeout exceeds maximum allowed value ({MAX_TIMEOUT}): {timeout}")
        raise typer.Exit(1)
    return timeout


def exec_command_cmd(
    command: Annotated[str, typer.Argument(help="Command to execute (e.g., 'ls -la' or 'ls')")],
    agent: Annotated[str, typer.Option("--agent", "-a", help="Agent name [required]")] = None,
    session: Annotated[str, typer.Option("--session", "-s", help="Session ID")] = None,
    chunked: Annotated[bool, typer.Option("--chunked", help="Enable chunked streaming response (application/x-ndjson)")] = False,
    bearer_token: Annotated[str | None, typer.Option("--bearer-token", "-bt", help="Bearer token for authentication")] = None,
    region: Annotated[str | None, typer.Option("--region", "-r", help="Region name")] = None,
    endpoint: Annotated[str | None, typer.Option("--endpoint", "-e", help="Endpoint name")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
    user_id: Annotated[str | None, typer.Option("--user-id", "-u", help="User ID for OAuth2 outbound credentials")] = None,
    timeout: Annotated[int, typer.Option("--timeout", help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT}, max: {MAX_TIMEOUT})")] = DEFAULT_TIMEOUT,
) -> None:
    """
    Execute command in runtime (cloud only).

    The backend runs the command as a Docker exec-form JSON array (no shell),
    so shell operators (>, |, ;, &&, $(), ...) are NOT interpreted by default.
    When such operators are present (outside quotes), this command auto-wraps
    the command as ["sh", "-c", "<command>"] so the shell interprets them.
    Quote metacharacters (e.g. 'echo "a > b"') to pass them through literally.
    To force a shell yourself, write 'sh -c \"...\"' explicitly.

    Examples:
        agentarts runtime exec-command "ls -la" --agent myagent --session <session-id>
        agentarts runtime exec-command "echo 1214 > file.txt" --agent myagent --session <session-id>
        agentarts runtime exec-command "ls -la" --agent myagent --session <session-id> --chunked
        agentarts runtime exec-command "ls" --agent myagent --session <session-id> -bt <bearer-token>
        agentarts runtime exec-command "ls" --agent myagent --session <session-id> -e myendpoint
        agentarts runtime exec-command "ls" --agent myagent --session <session-id> --skip-ssl-verification
    """
    try:
        validated_timeout = validate_timeout(timeout)

        # Mirror `invoke`: auto-generate a session id when the user did not pass
        # one, instead of crashing later in the V11 signer with an opaque
        # "'NoneType' object has no attribute 'strip'" error.
        session = session or str(uuid.uuid4())

        mode_str = "chunked (ndjson)" if chunked else "json"
        echo_info(
            "Exec Command",
            f"[cyan]Agent:[/cyan] [white]{agent}[/white]\n[cyan]Session:[/cyan] [dim]{session}[/dim]\n[cyan]Mode:[/cyan] [yellow]{mode_str}[/yellow]\n[cyan]Command:[/cyan] [dim]{command}[/dim]",
        )

        result = exec_runtime_command(
            command=command,
            agent_name=agent,
            session_id=session,
            chunked=chunked,
            bearer_token=bearer_token,
            region=region,
            endpoint=endpoint,
            skip_ssl_verification=skip_ssl_verification,
            user_id=user_id,
            timeout=validated_timeout,
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
