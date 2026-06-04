"""Runtime upload-files command"""

import json
import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn

from agentarts.toolkit.operations.runtime.upload_files import upload_runtime_files
from agentarts.toolkit.utils.common import echo_error, echo_info, echo_success

console = Console()

MAX_FILE_SIZE = 100 * 1024 * 1024
DEFAULT_USER_ID = 1000
DEFAULT_GROUP_ID = 1000
DEFAULT_FILE_MODE = "0644"


def validate_file_mode(file_mode: str) -> bool:
    """Validate file mode is valid octal format."""
    try:
        mode_int = int(file_mode, 8)
        return 0 <= mode_int <= 0o7777
    except ValueError:
        return False


def upload_files_cmd(
    agent: Annotated[str, typer.Option("--agent", "-a", help="Agent name [required]")] = None,
    session: Annotated[str, typer.Option("--session", "-s", help="Session ID [required]")] = None,
    files: Annotated[
        list[str] | None,
        typer.Option("--files", "-f", help="Local file path to upload. Can be specified multiple times for multiple files [required]"),
    ] = None,
    path: Annotated[str, typer.Option("--path", "-p", help="Remote directory path to upload files to. Must end with '/' (e.g., /home/user/). Default: /home/user/")] = "/home/user/",
    file_user_id: Annotated[int | None, typer.Option("--file-user-id", help="File owner user ID (default: 1000)")] = None,
    file_group_id: Annotated[int | None, typer.Option("--file-group-id", help="File owner group ID (default: 1000)")] = None,
    file_mode: Annotated[str | None, typer.Option("--file-mode", "-m", help="File permissions in octal (default: 0644)")] = None,
    bearer_token: Annotated[str | None, typer.Option("--bearer-token", "-bt", help="Bearer token for authentication")] = None,
    region: Annotated[str | None, typer.Option("--region", "-r", help="Region name")] = None,
    endpoint: Annotated[str | None, typer.Option("--endpoint", "-e", help="Endpoint name")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
    user_id: Annotated[str | None, typer.Option("--user-id", "-u", help="User ID for OAuth2 outbound credentials (used in OAuth authentication flow)")] = None,
    timeout: Annotated[int, typer.Option("--timeout", help="Request timeout in seconds (default: 900)")] = 900,
) -> None:
    """Upload files to runtime (cloud only).

    Configuration Requirement:
        This command requires file transfer to be enabled on the deployed agent.
        You can enable it in two ways:
        1. Set file_transfer_config.enabled=true in .agentarts_config.yaml and redeploy with 'agentarts deploy'
        2. Update the configuration directly on Huawei Cloud AgentArts console

    Example configuration in .agentarts_config.yaml:
        runtime:
          invoke_config:
            file_transfer_config:
              enabled: true

    Examples:
        # Single file (uploaded to default /home/user/)
        agentarts runtime upload-files --agent myagent --session <session-id> -f file1.txt

        # Multiple files (use -f multiple times)
        agentarts runtime upload-files --agent myagent --session <session-id> -f file1.txt -f file2.txt

        # Specify remote directory path (must end with '/')
        agentarts runtime upload-files --agent myagent --session <session-id> -f file1.txt -f file2.txt -p /app/data/

        # With custom permissions
        agentarts runtime upload-files --agent myagent --session <session-id> -f script.sh --file-mode 0755

        # With custom file owner
        agentarts runtime upload-files --agent myagent --session <session-id> -f data.txt --file-user-id 1001 --file-group-id 1001

        # With OAuth user ID
        agentarts runtime upload-files --agent myagent --session <session-id> -f data.txt --user-id oauth-user-123
    """
    try:
        if not files:
            echo_error("Files are required (-f)")
            raise typer.Exit(1)

        if not session:
            echo_error("Session ID is required (--session)")
            raise typer.Exit(1)

        if not path.endswith("/"):
            echo_error(f"Remote path must be a directory and end with '/': {path}")
            raise typer.Exit(1)

        if file_mode is not None and not validate_file_mode(file_mode):
            echo_error(f"Invalid file mode: {file_mode}. Must be valid octal (e.g., 0644, 0755)")
            raise typer.Exit(1)

        file_list: list[dict[str, str]] = []
        total_size = 0
        for item in files:
            local_path = item.strip()

            if not os.path.exists(local_path):
                echo_error(f"Local file not found: {local_path}")
                raise typer.Exit(1)

            file_size = Path(local_path).stat().st_size
            if file_size > MAX_FILE_SIZE:
                echo_error(f"File too large: {local_path} ({file_size / 1024 / 1024:.1f}MB, max 100MB)")
                raise typer.Exit(1)

            total_size += file_size
            file_list.append({"local_file": local_path})

        upload_mode = "streaming (octet-stream)" if len(file_list) == 1 else "multipart"
        console.print(f"[dim]Upload mode: {upload_mode}[/dim]")

        if total_size >= 1024 * 1024:
            size_str = f"{total_size / 1024 / 1024:.1f} MB"
        elif total_size >= 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        else:
            size_str = f"{total_size} bytes"
        console.print(f"[dim]Total size: {size_str}[/dim]")

        display_file_user_id = file_user_id if file_user_id is not None else DEFAULT_USER_ID
        display_file_group_id = file_group_id if file_group_id is not None else DEFAULT_GROUP_ID
        display_file_mode = file_mode if file_mode is not None else DEFAULT_FILE_MODE

        user_id_note = "" if file_user_id is not None else " (default)"
        group_id_note = "" if file_group_id is not None else " (default)"
        mode_note = "" if file_mode is not None else " (default)"

        echo_info(
            "Upload Files",
            f"[cyan]Agent:[/cyan] [white]{agent}[/white]\n[cyan]Session:[/cyan] [dim]{session}[/dim]\n[cyan]Files:[/cyan] [yellow]{len(file_list)}[/yellow]\n[cyan]File User ID:[/cyan] [dim]{display_file_user_id}{user_id_note}[/dim]\n[cyan]File Group ID:[/cyan] [dim]{display_file_group_id}{group_id_note}[/dim]\n[cyan]File Mode:[/cyan] [dim]{display_file_mode}{mode_note}[/dim]",
        )

        from agentarts.toolkit.operations.runtime.invoke import (
            _check_file_transfer_enabled,
            _resolve_agent_info,
        )
        resolved_name, resolved_region, agent_id, _ = _resolve_agent_info(agent, region)
        if resolved_name:
            _check_file_transfer_enabled(resolved_name, resolved_region or "", agent_id, not skip_ssl_verification)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Uploading {len(file_list)} files...",
                total=None,
            )

            result = upload_runtime_files(
                agent_name=agent,
                session_id=session,
                files=file_list,
                path=path,
                file_user_id=file_user_id,
                file_group_id=file_group_id,
                file_mode=file_mode,
                bearer_token=bearer_token,
                region=region,
                endpoint=endpoint,
                skip_ssl_verification=skip_ssl_verification,
                user_id=user_id,
                timeout=timeout,
            )

            progress.update(task, completed=True, description="[green]Upload complete")

        echo_success(f"Uploaded {len(file_list)} files successfully")
        console.print(f"[cyan]File User ID:[/cyan] [dim]{display_file_user_id}{user_id_note}[/dim]")
        console.print(f"[cyan]File Group ID:[/cyan] [dim]{display_file_group_id}{group_id_note}[/dim]")
        console.print(f"[cyan]File Mode:[/cyan] [dim]{display_file_mode}{mode_note}[/dim]")

        for file_spec in file_list:
            filename = Path(file_spec["local_file"]).name
            console.print(f"  [green]✓[/green] {path}{filename}")

        console.print()
        console.print("[cyan]API Response:[/cyan]")
        console.print(f"[dim]{json.dumps(result, ensure_ascii=False, indent=2)}[/dim]")

    except ValueError as e:
        echo_error(f"Validation error: {e}")
        if "file transfer is not enabled" in str(e).lower():
            from agentarts.toolkit.utils.common import echo_warning
            echo_warning(
                "The file_transfer_config.enabled parameter cannot be modified for existing agents. "
                "You need to create a new agent with file transfer enabled."
            )
        raise typer.Exit(1)
    except FileNotFoundError as e:
        echo_error(f"File error: {e}")
        raise typer.Exit(1)
    except Exception as e:
        echo_error(f"Failed to upload files: {e}")
        raise typer.Exit(1)
