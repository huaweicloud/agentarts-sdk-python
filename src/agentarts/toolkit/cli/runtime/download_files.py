"""Runtime download-files command"""

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from agentarts.toolkit.operations.runtime.download_files import download_runtime_files
from agentarts.toolkit.utils.common import echo_error, echo_info, echo_success

console = Console()


def download_files_cmd(
    agent: Annotated[str, typer.Option("--agent", "-a", help="Agent name [required]")] = None,
    session: Annotated[str, typer.Option("--session", "-s", help="Session ID [required]")] = None,
    path: Annotated[str, typer.Option("--path", "-p", help="Remote file/directory path [required]")] = "",
    output: Annotated[str | None, typer.Option("--output", "-o", help="Local output path")] = None,
    recursive: Annotated[bool, typer.Option("--recursive", help="Download directory as tar archive")] = False,
    bearer_token: Annotated[str | None, typer.Option("--bearer-token", "-bt", help="Bearer token for authentication")] = None,
    region: Annotated[str | None, typer.Option("--region", help="Region name")] = None,
    endpoint: Annotated[str | None, typer.Option("--endpoint", "-e", help="Endpoint name")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
    user_id: Annotated[str | None, typer.Option("--user-id", "-u", help="User ID for OAuth2 outbound credentials")] = None,
    timeout: Annotated[int, typer.Option("--timeout", help="Request timeout in seconds (default: 900)")] = 900,
) -> None:
    """
    Download files from runtime (cloud only).

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
        # Download single file
        agentarts runtime download-files --agent myagent --session <session-id> --path /home/user/data.txt

        # Download with custom output path
        agentarts runtime download-files -a myagent -s <session-id> -p /home/user/data.txt -o ./local_data.txt

        # Download directory as tar
        agentarts runtime download-files -a myagent -s <session-id> -p /home/user/project --recursive

        # Use bearer token
        agentarts runtime download-files -a myagent -s <session-id> -p /data/file.txt -bt <token>
    """
    try:
        if not path:
            echo_error("Path is required (--path)")
            raise typer.Exit(1)

        if not session:
            echo_error("Session ID is required (--session)")
            raise typer.Exit(1)

        download_mode = "directory (tar archive)" if recursive else "single file"
        console.print(f"[dim]Download mode: {download_mode}[/dim]")

        echo_info(
            "Download Files",
            f"[cyan]Agent:[/cyan] [white]{agent}[/white]\n[cyan]Session:[/cyan] [dim]{session}[/dim]\n[cyan]Path:[/cyan] [yellow]{path}[/yellow]",
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"[cyan]Downloading[/cyan] {path}", total=None)

            result = download_runtime_files(
                agent_name=agent,
                session_id=session,
                path=path,
                output=output,
                recursive=recursive,
                bearer_token=bearer_token,
                region=region,
                endpoint=endpoint,
                skip_ssl_verification=skip_ssl_verification,
                user_id=user_id,
                timeout=timeout,
            )

            progress.update(task, completed=True, description="[green]Download complete[/green]")

        size_bytes = result.get("size", 0)
        size_kb = size_bytes / 1024
        size_mb = size_kb / 1024

        if size_mb >= 1:
            size_str = f"{size_mb:.2f} MB"
        elif size_kb >= 1:
            size_str = f"{size_kb:.2f} KB"
        else:
            size_str = f"{size_bytes} bytes"

        echo_success("Download completed successfully")
        console.print(f"  [cyan]Saved to:[/cyan] [bold]{result.get('saved_path')}[/bold]")
        console.print(f"  [cyan]Size:[/cyan] [dim]{size_str}[/dim]")
        console.print(f"  [cyan]Content-Type:[/cyan] [dim]{result.get('content_type', 'unknown')}[/dim]")
        console.print(f"  [cyan]Remote path:[/cyan] [dim]{result.get('path')}[/dim]")

    except ValueError as e:
        echo_error(f"Validation error: {e}")
        raise typer.Exit(1)
    except Exception as e:
        echo_error(f"Failed to download: {e}")
        raise typer.Exit(1)
