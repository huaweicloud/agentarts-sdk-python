"""Runtime download-files command"""

from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from agentarts.toolkit.operations.runtime.download_files import download_runtime_files
from agentarts.toolkit.utils.common import echo_error, echo_success

console = Console()


def download_files_cmd(
    agent: Annotated[str, typer.Option("--agent", "-a", help="Agent name [required]")] = None,
    session: Annotated[str, typer.Option("--session", "-s", help="Session ID")] = None,
    path: Annotated[str, typer.Option("--path", "-p", help="Remote file/directory path to download [required]")] = "",
    output: Annotated[str | None, typer.Option("--output", "-o", help="Local output path")] = None,
    recursive: Annotated[bool, typer.Option("--recursive", "-r", help="Download directory as tar archive")] = False,
    region: Annotated[str | None, typer.Option("--region", help="Region name")] = None,
) -> None:
    """Download files from runtime (cloud only)."""
    try:
        if not path:
            echo_error("Path is required (-p)")
            raise typer.Exit(1)

        download_mode = "directory (tar)" if recursive else "single file (octet-stream)"
        console.print(f"[dim]Download mode: {download_mode}[/dim]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Downloading {path}...", total=None)

            saved_path = download_runtime_files(
                agent_name=agent,
                session_id=session,
                path=path,
                output=output,
                recursive=recursive,
                region=region,
            )

        echo_success(f"Downloaded to {saved_path}")
        console.print(f"  [green]✓[/green] {saved_path}")

    except ValueError as e:
        echo_error(f"Validation error: {e}")
        raise typer.Exit(1)
    except Exception as e:
        echo_error(f"Failed to download: {e}")
        raise typer.Exit(1)
