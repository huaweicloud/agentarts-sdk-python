"""Config operation implementation"""

from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console
from rich.table import Table

console = Console()

CONFIG_FILE = Path.home() / ".agentarts" / "config.yaml"


def ensure_config_dir() -> None:
    """Ensure config directory exists."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """
    Load configuration.

    Returns:
        Configuration dictionary
    """
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(config: dict) -> None:
    """
    Save configuration.

    Args:
        config: Configuration dictionary
    """
    ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False)


def set_config(key: str, value: str) -> bool:
    """
    Set configuration value.

    Args:
        key: Configuration key
        value: Configuration value

    Returns:
        True if successful
    """
    config = load_config()

    keys = key.split(".")
    current = config
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    current[keys[-1]] = value
    save_config(config)

    console.print(f"[green]Done:[/green] Set [cyan]{key}[/cyan] = [yellow]{value}[/yellow]")
    return True


def get_config(key: Optional[str]) -> bool:
    """
    Get configuration value.

    Args:
        key: Configuration key (optional)

    Returns:
        True if successful, False if key not found
    """
    config = load_config()

    if key is None:
        list_config()
        return True

    keys = key.split(".")
    current = config
    try:
        for k in keys:
            current = current[k]
        console.print(f"[cyan]{key}[/cyan] = [yellow]{current}[/yellow]")
        return True
    except (KeyError, TypeError):
        console.print(f"[red]Config key '{key}' not found[/red]")
        return False


def list_config() -> None:
    """List all configuration values."""
    config = load_config()

    if not config:
        console.print("[dim]No configuration found[/dim]")
        return

    table = Table(title="Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="yellow")

    def flatten(d: dict, prefix: str = ""):
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                flatten(v, key)
            else:
                table.add_row(key, str(v))

    flatten(config)
    console.print(table)
