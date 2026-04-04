"""Dev operation implementation"""

import os
import sys
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console

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
        console.print("[red]Error: agent.py not found[/red]")
        console.print("Please run 'agentarts init' first")
        return False

    os.environ["AGENTARTS_ENV"] = "development"
    os.environ["AGENTARTS_CONFIG"] = config_path or "agentarts.yaml"

    console.print(f"\n[bold cyan]Starting development server on {host}:{port}[/bold cyan]")
    console.print(f"Config: [yellow]{config_path or 'agentarts.yaml'}[/yellow]")
    console.print(f"Auto-reload: {'[green]enabled[/green]' if reload else '[dim]disabled[/dim]'}")
    console.print(f"\nAPI Documentation: [link]http://{host}:{port}/docs[/link]")
    console.print(f"Health Check: [link]http://{host}:{port}/health[/link]\n")

    try:
        import uvicorn

        sys.path.insert(0, os.getcwd())

        uvicorn.run(
            "agentarts.wrapper.runtime.app:create_app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
            factory=True,
        )
        return True
    except ImportError as e:
        console.print(f"[red]Error: Failed to start server - {e}[/red]")
        console.print("Make sure all dependencies are installed: [yellow]pip install -e .[/yellow]")
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
