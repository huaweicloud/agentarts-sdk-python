"""Dev operation implementation"""

import os
import sys
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console

from agentarts.toolkit.utils.common import echo_error, echo_info, echo_step

console = Console()


def run_dev_server(
    port: int,
    host: str,
    reload: bool,
    config_path: Optional[str],
) -> bool:
    """
    Run development server.

    Args:
        port: Server port
        host: Server host
        reload: Enable auto-reload
        config_path: Configuration file path

    Returns:
        True if successful, False otherwise
    """
    load_config(config_path)

    agent_file = Path("agent.py")
    if not agent_file.exists():
        echo_error("agent.py not found")
        console.print("[dim]Please run 'agentarts init' first[/dim]")
        return False

    os.environ["AGENTARTS_ENV"] = "development"
    os.environ["AGENTARTS_CONFIG"] = config_path or "agentarts.yaml"

    console.print()
    echo_info("Development Server", f"[cyan]Host:[/cyan] [white]{host}[/white]\n[cyan]Port:[/cyan] [white]{port}[/white]\n[cyan]Config:[/cyan] [yellow]{config_path or 'agentarts.yaml'}[/yellow]\n[cyan]Auto-reload:[/cyan] [green]{'enabled' if reload else 'disabled'}[/green]")
    console.print()
    console.print(f"[cyan]API Documentation:[/cyan] [link]http://{host}:{port}/docs[/link]")
    console.print(f"[cyan]Health Check:[/cyan] [link]http://{host}:{port}/health[/link]")
    console.print()

    try:
        import uvicorn

        sys.path.insert(0, os.getcwd())

        uvicorn.run(
            "agentarts.sdk.runtime.app:create_app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
            factory=True,
        )
        return True
    except ImportError as e:
        echo_error(f"Failed to start server - {e}")
        console.print("[dim]Make sure all dependencies are installed: [yellow]pip install -e .[/yellow]")
        return False


def load_config(config_path: Optional[str]) -> dict:
    """
    Load configuration file.

    Args:
        config_path: Configuration file path

    Returns:
        Configuration dictionary
    """
    if config_path:
        path = Path(config_path)
    else:
        path = Path("agentarts.yaml")

    if path.exists():
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    return {}
