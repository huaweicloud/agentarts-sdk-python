"""Common CLI utilities."""

import typer
from rich.console import Console

console = Console()

def _handle_error(message: str) -> None:
    """Handle error and exit.

    Args:
        message: Error message
    """
    console.print(f"[red]Error: {message}[/red]")
    raise typer.Exit(1)

def _print_success(message: str) -> None:
    """Print success message.

    Args:
        message: Success message
    """
    console.print(f"[green]✓ {message}[/green]")
