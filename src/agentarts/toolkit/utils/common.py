"""
Common utility functions for CLI
"""

from rich.console import Console
from rich.panel import Panel

console = Console()


def echo_error(message: str):
    """Echo error message in red with cross mark

    Args:
        message: Error message to display
    """
    console.print(f"[red]×[/red] [bold red]ERROR:[/bold red] {message}")


def echo_success(message: str):
    """Echo success message in green with check mark

    Args:
        message: Success message to display
    """
    console.print(f"[green]√[/green] [bold green]SUCCESS:[/bold green] {message}")


def echo_warning(message: str):
    """Echo warning message in yellow with warning symbol

    Args:
        message: Warning message to display
    """
    console.print(f"[yellow]⚠[/yellow] [bold yellow]WARNING:[/bold yellow] {message}")


def echo_info(title: str, message: str):
    """Echo info message in a panel box

    Args:
        title: Title for the panel
        message: Info message to display
    """
    panel = Panel(
        message,
        title=f"[bold blue]{title}[/bold blue]",
        border_style="blue",
        padding=(0, 1),
    )
    console.print(panel)


def echo_step(step_num: int, message: str):
    """Echo a step in a process

    Args:
        step_num: Step number
        message: Step description
    """
    console.print(f"[bold cyan]Step {step_num}:[/bold cyan] {message}")


def echo_key_value(key: str, value: str, key_color: str = "cyan", value_color: str = "white"):
    """Echo a key-value pair in formatted style

    Args:
        key: Key name
        value: Value
        key_color: Color for key
        value_color: Color for value
    """
    console.print(f"  [{key_color}]{key}:[/{key_color}] [{value_color}]{value}[/{value_color}]")
