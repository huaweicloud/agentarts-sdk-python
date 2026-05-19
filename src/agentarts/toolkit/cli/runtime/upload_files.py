"""Runtime upload-files command"""

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from agentarts.toolkit.operations.runtime.upload_files import upload_runtime_files
from agentarts.toolkit.utils.common import echo_error, echo_success

console = Console()

MAX_FILE_SIZE = 100 * 1024 * 1024


def upload_files_cmd(
    agent: Annotated[str, typer.Option("--agent", "-a", help="Agent name [required]")] = None,
    session: Annotated[str, typer.Option("--session", "-s", help="Session ID")] = None,
    files: Annotated[
        list[str] | None,
        typer.Option("--files", "-f", help="Local file to upload. Use '/remote/path@local_file' format to specify remote path. Can be specified multiple times for multiple files [required]"),
    ] = None,
    username: Annotated[str | None, typer.Option("--username", help="File owner username")] = None,
    groupname: Annotated[str | None, typer.Option("--groupname", help="File owner groupname")] = None,
    filemode: Annotated[str | None, typer.Option("--filemode", help="File permissions (e.g., 644, 755)")] = None,
    region: Annotated[str | None, typer.Option("--region", "-r", help="Region name")] = None,
) -> None:
    """Upload files to runtime (cloud only).

    Examples:
        # Single file
        agentarts runtime upload-files --agent myagent -f file1.txt

        # Multiple files (use -f multiple times)
        agentarts runtime upload-files --agent myagent -f file1.txt -f file2.txt -f file3.txt

        # Specify remote path with @ format
        agentarts runtime upload-files --agent myagent -f "/home/user/data.txt@local_file.txt"

        # Multiple files with custom remote paths
        agentarts runtime upload-files --agent myagent -f "/app/config.yaml@config.yaml" -f "/data/input.txt@input.txt"

        # With file permissions
        agentarts runtime upload-files --agent myagent -f script.sh --filemode 755
    """
    try:
        if not files:
            echo_error("Files are required (-f)")
            raise typer.Exit(1)

        file_list: list[dict[str, str]] = []
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

            file_list.append({"path": remote_path, "local_file": local_path})

        upload_mode = "streaming (octet-stream)" if len(file_list) == 1 else "multipart"
        console.print(f"[dim]Upload mode: {upload_mode}[/dim]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Uploading {len(file_list)} files...", total=None)

            upload_runtime_files(
                agent_name=agent,
                session_id=session,
                files=file_list,
                username=username,
                groupname=groupname,
                filemode=filemode,
                region=region,
            )

        echo_success(f"Uploaded {len(file_list)} files successfully")
        for file_spec in file_list:
            console.print(f"  [green]✓[/green] {file_spec['path']}")

    except ValueError as e:
        echo_error(f"Validation error: {e}")
        raise typer.Exit(1)
    except FileNotFoundError as e:
        echo_error(f"File error: {e}")
        raise typer.Exit(1)
    except Exception as e:
        echo_error(f"Failed to upload files: {e}")
        raise typer.Exit(1)
