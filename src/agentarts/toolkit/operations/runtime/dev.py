"""Dev operation implementation"""

import os
import sys
from pathlib import Path

import yaml
from rich.console import Console

from agentarts.toolkit.utils.common import echo_error, echo_info

console = Console()


def run_dev_server(
    port: int,
    host: str,
    reload: bool,
    config_path: str | None,
    env_vars: dict[str, str] | None = None,
) -> bool:
    """
    Run development server.

    Args:
        port: Server port
        host: Server host
        reload: Enable auto-reload
        config_path: Configuration file path
        env_vars: Environment variables from command line

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

    inject_environment_variables(config, env_vars)

    env_display = format_env_display(env_vars, config)

    console.print()
    echo_info("Development Server", f"[cyan]Host:[/cyan] [white]{host}[/white]\n[cyan]Port:[/cyan] [white]{port}[/white]\n[cyan]Config:[/cyan] [yellow]{config_path or '.agentarts_config.yaml'}[/yellow]\n[cyan]Entrypoint:[/cyan] [yellow]{entrypoint}[/yellow]\n[cyan]Auto-reload:[/cyan] [green]{'enabled' if reload else 'disabled'}[/green]{env_display}")
    console.print()
    console.print(f"[cyan]Invocation Endpoint:[/cyan] [white]POST[/white] [link]http://{host}:{port}/invocations[/link]")
    console.print(f"[cyan]Health Check:[/cyan] [white]GET[/white] [link]http://{host}:{port}/ping[/link]")
    console.print()

    try:
        import importlib

        import uvicorn

        sys.path.insert(0, os.getcwd())

        use_factory = False
        if ":" in entrypoint:
            module_name, target_name = entrypoint.split(":", 1)
            try:
                module = importlib.import_module(module_name)
                target = getattr(module, target_name, None)
                if target is not None:
                    from starlette.applications import Starlette
                    if callable(target) and not isinstance(target, Starlette):
                        use_factory = True
            except Exception:
                pass

        uvicorn.run(
            entrypoint,
            host=host,
            port=port,
            reload=reload,
            log_level="info",
            factory=use_factory,
        )
        return True
    except ImportError as e:
        echo_error(f"Failed to start server - {e}")
        console.print("[dim]Make sure all dependencies are installed: [yellow]pip install -e .[/yellow]")
        return False


def inject_environment_variables(config: dict, cli_env_vars: dict[str, str] | None = None) -> None:
    """
    Inject environment variables from config and CLI.

    CLI environment variables take precedence over config file.

    Args:
        config: Configuration dictionary
        cli_env_vars: Environment variables from command line
    """
    config_env_vars = get_config_env_vars(config)

    for key, value in config_env_vars.items():
        if value is not None:
            os.environ[key] = str(value)

    if cli_env_vars:
        for key, value in cli_env_vars.items():
            os.environ[key] = value


def get_config_env_vars(config: dict) -> dict[str, str]:
    """
    Get environment variables from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary of environment variables
    """
    env_vars = {}

    default_agent = config.get("default_agent")
    if not default_agent:
        agents = config.get("agents", {})
        if agents:
            default_agent = next(iter(agents.keys()), None)

    if not default_agent:
        return env_vars

    agents = config.get("agents", {})
    agent_config = agents.get(default_agent, {})
    runtime_config = agent_config.get("runtime", {})
    env_vars_list = runtime_config.get("environment_variables", []) or []

    for env_var in env_vars_list:
        if isinstance(env_var, dict):
            key = env_var.get("key")
            value = env_var.get("value")
            if key:
                env_vars[key] = value

    return env_vars


def format_env_display(cli_env_vars: dict[str, str] | None, config: dict) -> str:
    """
    Format environment variables for display.

    Args:
        cli_env_vars: Environment variables from command line
        config: Configuration dictionary

    Returns:
        Formatted string for display
    """
    config_env_vars = get_config_env_vars(config)

    all_env_vars = {}
    all_env_vars.update(config_env_vars)

    if cli_env_vars:
        all_env_vars.update(cli_env_vars)

    if not all_env_vars:
        return ""

    lines = "\n[cyan]Environment Variables:[/cyan]"
    for key, value in all_env_vars.items():
        is_from_cli = cli_env_vars and key in cli_env_vars
        source = "[green](CLI)[/green]" if is_from_cli else "[dim](config)[/dim]"

        if value:
            display_value = value if len(str(value)) < 30 else str(value)[:27] + "..."
            masked_value = mask_sensitive_value(key, display_value)
            lines += f"\n  [yellow]{key}[/yellow]=[white]{masked_value}[/white] {source}"
        else:
            lines += f"\n  [yellow]{key}[/yellow]=[dim]<not set>[/dim] {source}"

    return lines


def mask_sensitive_value(key: str, value: str) -> str:
    """
    Mask sensitive values for display.

    Args:
        key: Environment variable key
        value: Environment variable value

    Returns:
        Masked value if sensitive, otherwise original value
    """
    sensitive_keywords = ["key", "secret", "token", "password", "credential"]
    key_lower = key.lower()

    if any(keyword in key_lower for keyword in sensitive_keywords):
        if len(value) > 8:
            return value[:4] + "****" + value[-4:]
        return "****"

    return value


def get_entrypoint(config: dict) -> str | None:
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
    return base_config.get("entrypoint")



def load_config(config_path: str | None) -> dict:
    """
    Load configuration file.

    Args:
        config_path: Configuration file path

    Returns:
        Configuration dictionary
    """
    path = Path(config_path) if config_path else Path(".agentarts_config.yaml")

    if path.exists():
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    return {}
