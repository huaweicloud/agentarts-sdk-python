"""Config operation implementation"""

from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table

from agentarts.toolkit.utils.runtime.config import (
    AgentArtsConfig,
    AgentArtsConfigList,
    BaseConfig,
    SWRConfig,
)

console = Console()

CONFIG_FILE_NAME = ".agentarts_config.yaml"


def get_config_file_path() -> Path:
    """Get the configuration file path in current directory."""
    return Path.cwd() / CONFIG_FILE_NAME


def load_config() -> AgentArtsConfigList:
    """
    Load configuration from .agentarts_config.yaml.

    Returns:
        AgentArtsConfigList instance (empty if file doesn't exist)
    """
    config_path = get_config_file_path()
    if config_path.exists():
        try:
            return AgentArtsConfigList.from_yaml(str(config_path))
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load config file: {e}[/yellow]")
            return AgentArtsConfigList()
    return AgentArtsConfigList()


def save_config(config: AgentArtsConfigList) -> bool:
    """
    Save configuration to .agentarts_config.yaml.

    Args:
        config: AgentArtsConfigList instance to save

    Returns:
        True if successful, False otherwise
    """
    config_path = get_config_file_path()
    try:
        config.to_yaml(str(config_path))
        return True
    except Exception as e:
        console.print(f"[red]Error: Failed to save config file: {e}[/red]")
        return False


def ensure_config_exists() -> AgentArtsConfigList:
    """
    Ensure configuration file exists and return config.

    Returns:
        AgentArtsConfigList instance
    """
    config = load_config()
    if not get_config_file_path().exists():
        save_config(config)
    return config


def list_agents() -> List[str]:
    """
    List all configured agents.

    Returns:
        List of agent names
    """
    config = load_config()
    return config.list_agents()


def get_default_agent() -> Optional[str]:
    """
    Get the default agent name.

    Returns:
        Default agent name or None
    """
    config = load_config()
    return config.default_agent


def set_default_agent(name: str) -> bool:
    """
    Set the default agent name.

    Args:
        name: Agent name to set as default

    Returns:
        True if successful, False if agent not found
    """
    config = load_config()

    if name not in config.agents:
        console.print(f"[red]Error: Agent '{name}' not found in configuration[/red]")
        console.print(f"[dim]Available agents: {', '.join(config.list_agents()) or 'none'}[/dim]")
        return False

    config.default_agent = name
    if save_config(config):
        console.print(f"[green]Done:[/green] Default agent set to [cyan]{name}[/cyan]")
        return True
    return False


def get_agent(name: Optional[str] = None) -> Optional[AgentArtsConfig]:
    """
    Get agent configuration by name.

    Args:
        name: Agent name (uses default if None)

    Returns:
        AgentArtsConfig if found, None otherwise
    """
    config = load_config()
    return config.get_agent(name)


def add_agent(
    name: str,
    entrypoint: str,
    region: Optional[str] = None,
    swr_organization: Optional[str] = None,
    swr_repository: Optional[str] = None,
    dependency_file: Optional[str] = None,
    set_as_default: bool = True,
    organization_auto_create: bool = False,
    repository_auto_create: bool = False,
) -> bool:
    """
    Add or update an agent configuration.

    Args:
        name: Agent name
        entrypoint: Agent entrypoint
        region: Huawei Cloud region
        swr_organization: SWR organization
        swr_repository: SWR repository
        dependency_file: Path to dependency file (e.g., requirements.txt)
        set_as_default: Whether to set as default agent
        organization_auto_create: Whether to auto-create SWR organization
        repository_auto_create: Whether to auto-create SWR repository

    Returns:
        True if successful
    """
    config = load_config()

    agent_config = AgentArtsConfig(
        base=BaseConfig(
            name=name,
            entrypoint=entrypoint,
            region=region,
            dependency_file=dependency_file,
        ),
        swr_config=SWRConfig(
            organization=swr_organization,
            repository=swr_repository,
            organization_auto_create=organization_auto_create,
            repository_auto_create=repository_auto_create,
        ),
    )

    config.add_agent(name, agent_config)

    if set_as_default or config.default_agent is None:
        config.default_agent = name

    if save_config(config):
        console.print(f"[green]Done:[/green] Agent [cyan]{name}[/cyan] configured successfully")
        console.print(f"[dim]Config file: {get_config_file_path()}[/dim]")
        return True
    return False


def remove_agent(name: str) -> bool:
    """
    Remove an agent configuration.

    Args:
        name: Agent name

    Returns:
        True if successful, False if agent not found
    """
    config = load_config()

    if name not in config.agents:
        console.print(f"[red]Error: Agent '{name}' not found in configuration[/red]")
        return False

    config.remove_agent(name)
    if save_config(config):
        console.print(f"[green]Done:[/green] Agent [cyan]{name}[/cyan] removed")
        return True
    return False


def print_config_list() -> None:
    """Print all configured agents in a table format."""
    config = load_config()

    if not config.agents:
        console.print("[dim]No agents configured[/dim]")
        console.print(f"\n[dim]Run 'agentarts config' to configure an agent[/dim]")
        return

    table = Table(title=f"Agent Configurations ({get_config_file_path()})")
    table.add_column("Default", style="dim", width=8)
    table.add_column("Agent Name", style="cyan")
    table.add_column("Region", style="yellow")
    table.add_column("Entrypoint", style="green")
    table.add_column("Dependency File", style="blue")
    table.add_column("SWR Org", style="magenta")
    table.add_column("SWR Repo", style="blue")

    for name, agent_config in config.agents.items():
        is_default = "*" if name == config.default_agent else ""
        region = agent_config.base.region or "-"
        entrypoint = agent_config.base.entrypoint or "-"
        dependency_file = agent_config.base.dependency_file or "-"
        swr_org = agent_config.swr_config.organization or "-"
        swr_repo = agent_config.swr_config.repository or "-"
        table.add_row(is_default, name, region, entrypoint, dependency_file, swr_org, swr_repo)

    console.print(table)

    if config.default_agent:
        console.print(f"\n[dim]Default agent: [cyan]{config.default_agent}[/cyan][/dim]")


def print_agent_detail(name: Optional[str] = None) -> bool:
    """
    Print detailed configuration for an agent.

    Args:
        name: Agent name (uses default if None)

    Returns:
        True if successful, False if agent not found
    """
    config = load_config()

    if name is None:
        name = config.default_agent

    if name is None:
        console.print("[red]Error: No agent specified and no default agent set[/red]")
        return False

    agent_config = config.get_agent(name)
    if agent_config is None:
        console.print(f"[red]Error: Agent '{name}' not found in configuration[/red]")
        return False

    import yaml

    console.print(f"\n[bold cyan]Agent: {name}[/bold cyan]")
    if name == config.default_agent:
        console.print("[dim](default)[/dim]")
    console.print()

    config_dict = agent_config.to_dict()
    yaml_str = yaml.dump(config_dict, default_flow_style=False, allow_unicode=True)
    console.print(yaml_str)

    return True


def set_config_value(key: str, value: str, agent_name: Optional[str] = None) -> bool:
    """
    Set a configuration value for an agent.

    Args:
        key: Configuration key (supports dot notation, e.g., "base.region")
        value: Configuration value
        agent_name: Agent name (uses default if None)

    Returns:
        True if successful
    """
    config = load_config()

    if agent_name is None:
        agent_name = config.default_agent

    if agent_name is None:
        console.print("[red]Error: No agent specified and no default agent set[/red]")
        return False

    agent_config = config.get_agent(agent_name)
    if agent_config is None:
        console.print(f"[red]Error: Agent '{agent_name}' not found[/red]")
        return False

    keys = key.split(".")
    config_dict = agent_config.to_dict()

    current = config_dict
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    current[keys[-1]] = value

    try:
        updated_config = AgentArtsConfig.from_dict(config_dict)
        config.agents[agent_name] = updated_config
        if save_config(config):
            console.print(f"[green]Done:[/green] Set [cyan]{key}[/cyan] = [yellow]{value}[/yellow] for agent [cyan]{agent_name}[/cyan]")
            return True
    except Exception as e:
        console.print(f"[red]Error: Failed to set configuration: {e}[/red]")
        return False

    return False


def get_config_value(key: str, agent_name: Optional[str] = None) -> bool:
    """
    Get a configuration value for an agent.

    Args:
        key: Configuration key (supports dot notation)
        agent_name: Agent name (uses default if None)

    Returns:
        True if successful, False if key not found
    """
    config = load_config()

    if agent_name is None:
        agent_name = config.default_agent

    if agent_name is None:
        console.print("[red]Error: No agent specified and no default agent set[/red]")
        return False

    agent_config = config.get_agent(agent_name)
    if agent_config is None:
        console.print(f"[red]Error: Agent '{agent_name}' not found[/red]")
        return False

    keys = key.split(".")
    config_dict = agent_config.to_dict()

    try:
        current = config_dict
        for k in keys:
            current = current[k]
        console.print(f"[cyan]{key}[/cyan] = [yellow]{current}[/yellow] (agent: {agent_name})")
        return True
    except (KeyError, TypeError):
        console.print(f"[red]Error: Key '{key}' not found in agent '{agent_name}'[/red]")
        return False


def generate_dockerfile(agent_name: Optional[str] = None, output_path: Optional[str] = None) -> bool:
    """
    Generate Dockerfile for an agent.

    Args:
        agent_name: Agent name (uses default if None)
        output_path: Output path for Dockerfile (default: ./Dockerfile)

    Returns:
        True if successful, False otherwise
    """
    from agentarts.toolkit.utils.runtime.container import generate_dockerfile as _generate_dockerfile

    config = load_config()

    if agent_name is None:
        agent_name = config.default_agent

    if agent_name is None:
        console.print("[red]Error: No agent specified and no default agent set[/red]")
        return False

    agent_config = config.get_agent(agent_name)
    if agent_config is None:
        console.print(f"[red]Error: Agent '{agent_name}' not found[/red]")
        return False

    base_image = agent_config.base.base_image
    dependency_file = agent_config.base.dependency_file
    entrypoint = agent_config.base.entrypoint
    port = agent_config.runtime.invoke_config.port if agent_config.runtime.invoke_config else 8080

    return _generate_dockerfile(
        base_image=base_image,
        dependency_file=dependency_file,
        entrypoint=entrypoint,
        port=port,
        output_path=output_path or "Dockerfile",
    )
