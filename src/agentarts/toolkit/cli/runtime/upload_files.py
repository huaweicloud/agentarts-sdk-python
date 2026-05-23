"""Runtime upload-files command"""

import json
import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn

from agentarts.toolkit.operations.runtime.upload_files import upload_runtime_files
from agentarts.toolkit.utils.common import echo_error, echo_success

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
        typer.Option("--files", "-f", help="Local file to upload. Use '/remote/path@local_file' format to specify remote path. Can be specified multiple times for multiple files [required]"),
    ] = None,
    user_id: Annotated[int, typer.Option("--user-id", "-u", help="File owner user ID (default: 1000)")] = DEFAULT_USER_ID,
    group_id: Annotated[int, typer.Option("--group-id", "-g", help="File owner group ID (default: 1000)")] = DEFAULT_GROUP_ID,
    file_mode: Annotated[str, typer.Option("--file-mode", "-m", help="File permissions in octal (default: 0644)")] = DEFAULT_FILE_MODE,
    bearer_token: Annotated[str | None, typer.Option("--bearer-token", "-bt", help="Bearer token for authentication")] = None,
    region: Annotated[str | None, typer.Option("--region", "-r", help="Region name")] = None,
) -> None:
    """Upload files to runtime (cloud only).

    Examples:
        # Single file
        agentarts runtime upload-files --agent myagent --session <session-id> -f file1.txt

        # Multiple files (use -f multiple times)
        agentarts runtime upload-files --agent myagent --session <session-id> -f file1.txt -f file2.txt

        # Specify remote path with @ format
        agentarts runtime upload-files --agent myagent --session <session-id> -f "/home/user/data.txt@local_file.txt"

        # With custom permissions
        agentarts runtime upload-files --agent myagent --session <session-id> -f script.sh --file-mode 0755

        # With custom owner
        agentarts runtime upload-files --agent myagent --session <session-id> -f data.txt --user-id 1001 --group-id 1001
    """
    try:
        if not files:
            echo_error("Files are required (-f)")
            raise typer.Exit(1)

        if not session:
            echo_error("Session ID is required (--session)")
            raise typer.Exit(1)

        if not validate_file_mode(file_mode):
            echo_error(f"Invalid file mode: {file_mode}. Must be valid octal (e.g., 0644, 0755)")
            raise typer.Exit(1)

        file_list: list[dict[str, str]] = []
        total_size = 0
        for item in files:
            item = item.strip()
            if "@" in item:
                remote_path, local_path = item.split("@", 1)
            else:
                filename = Path(item).name
                remote_path = f"/home/user/{filename}"
                local_path = item

            if not os.path.exists(local_path):
                echo_error(f"Local file not found: {local_path}")
                raise typer.Exit(1)

            file_size = Path(local_path).stat().st_size
            if file_size > MAX_FILE_SIZE:
                echo_error(f"File too large: {local_path} ({file_size / 1024 / 1024:.1f}MB, max 100MB)")
                raise typer.Exit(1)

            total_size += file_size
            file_list.append({"path": remote_path, "local_file": local_path})

        upload_mode = "streaming (octet-stream)" if len(file_list) == 1 else "multipart"
        console.print(f"[dim]Upload mode: {upload_mode}[/dim]")
        console.print(f"[dim]Total size: {total_size / 1024:.1f} KB[/dim]")

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
                user_id=user_id,
                group_id=group_id,
                file_mode=file_mode,
                bearer_token=bearer_token,
                region=region,
            )

            progress.update(task, completed=True, description="[green]Upload complete")

        echo_success(f"Uploaded {len(file_list)} files successfully")
        console.print(f"[cyan]User ID:[/cyan] [dim]{user_id}[/dim]")
        console.print(f"[cyan]Group ID:[/cyan] [dim]{group_id}[/dim]")
        console.print(f"[cyan]File Mode:[/cyan] [dim]{file_mode}[/dim]")
        
        for file_spec in file_list:
            console.print(f"  [green]✓[/green] {file_spec['path']}")

        console.print()
        console.print("[cyan]API Response:[/cyan]")
        console.print(f"[dim]{json.dumps(result, ensure_ascii=False, indent=2)}[/dim]")

    except ValueError as e:
        echo_error(f"Validation error: {e}")
        raise typer.Exit(1)
    except FileNotFoundError as e:
        echo_error(f"File error: {e}")
        raise typer.Exit(1)
    except Exception as e:
        echo_error(f"Failed to upload files: {e}")
        raise typer.Exit(1)
