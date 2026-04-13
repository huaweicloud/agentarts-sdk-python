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
    config = load_config(config_path)

    entrypoint = get_entrypoint(config)
    if not entrypoint:
        echo_error("No entrypoint found in configuration")
        console.print("[dim]Please set 'entrypoint' in .agentarts_config.yaml[/dim]")
        return False

    module_name = entrypoint.split(":")[0] if ":" in entrypoint else entrypoint
    module_file = Path(f"{module_name}.py")
    if not module_file.exists():
        echo_error(f"Module file '{module_name}.py' not found")
        console.print(f"[dim]Please ensure '{module_name}.py' exists in current directory[/dim]")
        return False

    os.environ["AGENTARTS_ENV"] = "development"
    os.environ["AGENTARTS_CONFIG"] = config_path or ".agentarts_config.yaml"

    console.print()
    echo_info("Development Server", f"[cyan]Host:[/cyan] [white]{host}[/white]\n[cyan]Port:[/cyan] [white]{port}[/white]\n[cyan]Config:[/cyan] [yellow]{config_path or '.agentarts_config.yaml'}[/yellow]\n[cyan]Entrypoint:[/cyan] [yellow]{entrypoint}[/yellow]\n[cyan]Auto-reload:[/cyan] [green]{'enabled' if reload else 'disabled'}[/green]")
    console.print()
    console.print(f"[cyan]Invocation Endpoint:[/cyan] [white]POST[/white] [link]http://{host}:{port}/invocations[/link]")
    console.print(f"[cyan]Health Check:[/cyan] [white]GET[/white] [link]http://{host}:{port}/ping[/link]")
    console.print()

    try:
        import uvicorn

        sys.path.insert(0, os.getcwd())

        uvicorn.run(
            entrypoint,
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


def get_entrypoint(config: dict) -> Optional[str]:
    """
    Get entrypoint from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Entrypoint string (e.g., "agent:create_app") or None
    """
    default_agent = config.get("default_agent")
    if not default_agent:
        agents = config.get("agents", {})
        if agents:
            default_agent = next(iter(agents.keys()), None)

    if not default_agent:
        return None

    agents = config.get("agents", {})
    agent_config = agents.get(default_agent, {})
    base_config = agent_config.get("base", {})
    entrypoint = base_config.get("entrypoint")

    return entrypoint


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
        path = Path(".agentarts_config.yaml")

    if path.exists():
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    return {}
