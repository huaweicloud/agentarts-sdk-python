"""Config command definitions"""

from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

from agentarts.toolkit.operations.runtime import config as config_op
from agentarts.toolkit.utils.common import (
    echo_success,
    echo_error,
    echo_info,
    echo_key_value,
)

console = Console()

config_app = typer.Typer(
    name="config",
    help="Configuration management",
    invoke_without_command=True,
)


@config_app.callback()
def main(
    ctx: typer.Context,
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Agent name")] = None,
    entrypoint: Annotated[Optional[str], typer.Option("--entrypoint", "-e", help="Agent entrypoint (e.g., app:main)")] = None,
    region: Annotated[Optional[str], typer.Option("--region", "-r", help="Huawei Cloud region (e.g., cn-southwest-2)")] = None,
    dependency_file: Annotated[Optional[str], typer.Option("--dependency-file", "-d", help="Path to dependency file (e.g., requirements.txt)")] = None,
    swr_organization: Annotated[Optional[str], typer.Option("--swr-org", help="SWR organization name")] = None,
    swr_repository: Annotated[Optional[str], typer.Option("--swr-repo", help="SWR repository name")] = None,
    set_default: Annotated[bool, typer.Option("--set-default/--no-set-default", help="Set as default agent")] = True,
):
    """
    Configure agent settings.

    If run without arguments, starts interactive configuration.
    If arguments are provided, creates/updates configuration directly.

    Required parameters (will prompt if not provided):
    - Agent name
    - Entrypoint

    Examples:
        agentarts config
        agentarts config --name my-agent --entrypoint app:main
        agentarts config -n my-agent -e app:main --dependency-file requirements.txt --swr-org my-org --swr-repo my-repo
    """
    if ctx.invoked_subcommand is not None:
        return

    console.print()
    console.print("[bold cyan]═══════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]       AgentArts Configuration[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════[/bold cyan]")
    console.print()

    existing_agents = config_op.list_agents()
    if existing_agents:
        console.print(f"[dim]Existing agents: [cyan]{', '.join(existing_agents)}[/cyan][/dim]")
        console.print()

    agent_name = name
    if agent_name is None:
        default_name = config_op.get_default_agent()
        prompt_hint = f" [cyan]({default_name})[/cyan]" if default_name else ""
        console.print(f"[bold]Agent name{prompt_hint}:[/bold]")
        agent_name = Prompt.ask("  Name", default=default_name or "")

    if not agent_name:
        echo_error("Agent name is required")
        raise typer.Exit(1)

    agent_entrypoint = entrypoint
    if agent_entrypoint is None:
        existing_config = config_op.get_agent(agent_name)
        default_entrypoint = existing_config.base.entrypoint if existing_config else None
        prompt_hint = f" [cyan]({default_entrypoint})[/cyan]" if default_entrypoint else ""
        console.print(f"\n[bold]Entrypoint{prompt_hint}:[/bold]")
        console.print("[dim]  Format: module:function (e.g., app:main, agent:create_agent)[/dim]")
        agent_entrypoint = Prompt.ask("  Entrypoint", default=default_entrypoint or "")

    if not agent_entrypoint:
        echo_error("Entrypoint is required")
        raise typer.Exit(1)

    agent_region = region
    if agent_region is None:
        existing_config = config_op.get_agent(agent_name)
        default_region = existing_config.base.region if existing_config else "cn-southwest-2"
        console.print(f"\n[bold]Region [cyan]({default_region})[/cyan]:[/bold]")
        console.print("[dim]  Available region: cn-southwest-2[/dim]")
        agent_region = Prompt.ask("  Region", default=default_region)

    agent_dependency_file = dependency_file
    if agent_dependency_file is None:
        existing_config = config_op.get_agent(agent_name)
        default_dep = existing_config.base.dependency_file if existing_config else None
        
        if default_dep is None:
            default_dep = config_op.detect_dependency_file()
        
        console.print(f"\n[bold]Dependency file [cyan]({default_dep})[/cyan]:[/bold]")
        console.print("[dim]  Auto-detected from requirements.txt or pyproject.toml. Press Enter to use default[/dim]")
        agent_dependency_file = Prompt.ask("  File", default=default_dep)

    org = swr_organization
    auto_create_org = False
    if org is None:
        existing_config = config_op.get_agent(agent_name)
        default_org = existing_config.swr_config.organization if existing_config else None
        auto_org = "agentarts-org"
        
        console.print(f"\n[bold]SWR Organization:[/bold]")
        if default_org:
            console.print(f"[dim]  Current: [cyan]{default_org}[/cyan]. Press Enter to keep current, or input new name[/dim]")
        else:
            console.print(f"[dim]  Press Enter for auto-create [cyan]{auto_org}[/cyan]. Or input existing organization name[/dim]")
        
        org_input = Prompt.ask("  Organization", default="")
        
        if org_input:
            org = org_input
            auto_create_org = False
        elif default_org:
            org = default_org
            auto_create_org = existing_config.swr_config.organization_auto_create if existing_config else False
        else:
            org = auto_org
            auto_create_org = True

    repo = swr_repository
    auto_create_repo = False
    if repo is None:
        existing_config = config_op.get_agent(agent_name)
        default_repo = existing_config.swr_config.repository if existing_config else None
        auto_repo = agent_name
        
        console.print(f"\n[bold]SWR Repository:[/bold]")
        if default_repo:
            console.print(f"[dim]  Current: [cyan]{default_repo}[/cyan]. Press Enter to keep current, or input new name[/dim]")
        else:
            console.print(f"[dim]  Press Enter for auto-create [cyan]{auto_repo}[/cyan]. Or input existing repository name[/dim]")
        
        repo_input = Prompt.ask("  Repository", default="")
        
        if repo_input:
            repo = repo_input
            auto_create_repo = False
        elif default_repo:
            repo = default_repo
            auto_create_repo = existing_config.swr_config.repository_auto_create if existing_config else False
        else:
            repo = auto_repo
            auto_create_repo = True

    summary = (
        f"[cyan]Agent Name:[/cyan] [white]{agent_name}[/white]\n"
        f"[cyan]Entrypoint:[/cyan] [white]{agent_entrypoint}[/white]\n"
        f"[cyan]Region:[/cyan] [white]{agent_region}[/white]\n"
        f"[cyan]Dependency File:[/cyan] [white]{agent_dependency_file or 'None'}[/white]\n"
        f"\n"
        f"[bold]SWR Settings:[/bold]\n"
        f"[cyan]Organization:[/cyan] [white]{org}[/white] [dim](auto-create: {str(auto_create_org).lower()})[/dim]\n"
        f"[cyan]Repository:[/cyan] [white]{repo}[/white] [dim](auto-create: {str(auto_create_repo).lower()})[/dim]"
    )
    echo_info("Configuration Summary", summary)

    success = config_op.add_agent(
        name=agent_name,
        entrypoint=agent_entrypoint,
        region=agent_region,
        dependency_file=agent_dependency_file if agent_dependency_file else None,
        swr_organization=org,
        swr_repository=repo,
        set_as_default=set_default,
        organization_auto_create=auto_create_org,
        repository_auto_create=auto_create_repo,
    )

    if not success:
        raise typer.Exit(1)

    echo_success(f"Agent '{agent_name}' configured successfully!")
    config_op.generate_dockerfile(agent_name)


@config_app.command("list")
def list():
    """
    List all configured agents.

    Examples:
        agentarts config list
    """
    config_op.print_config_list()


@config_app.command("set-default")
def set_default(
    name: Annotated[str, typer.Argument(help="Agent name to set as default")],
):
    """
    Set the default agent name.

    Examples:
        agentarts config set-default my-agent
    """
    success = config_op.set_default_agent(name)
    if not success:
        raise typer.Exit(1)


@config_app.command("get")
def get(
    key: Annotated[Optional[str], typer.Argument(help="Configuration key (dot notation, e.g., base.region)")] = None,
    agent: Annotated[Optional[str], typer.Option("--agent", "-a", help="Agent name")] = None,
):
    """
    Get configuration value or agent details.

    If no key is provided, prints the full agent configuration.

    Examples:
        agentarts config get
        agentarts config get base.region
        agentarts config get base.region --agent my-agent
    """
    if key is None:
        success = config_op.print_agent_detail(agent)
    else:
        success = config_op.get_config_value(key, agent)
    if not success:
        raise typer.Exit(1)


@config_app.command("set")
def set(
    key: Annotated[str, typer.Argument(help="Configuration key (dot notation, e.g., base.region)")],
    value: Annotated[str, typer.Argument(help="Configuration value")],
    agent: Annotated[Optional[str], typer.Option("--agent", "-a", help="Agent name")] = None,
):
    """
    Set configuration value.

    Examples:
        agentarts config set base.region cn-southwest-2
        agentarts config set base.name new-name --agent old-name
    """
    success = config_op.set_config_value(key, value, agent)
    if not success:
        raise typer.Exit(1)


@config_app.command("remove")
def remove(
    name: Annotated[str, typer.Argument(help="Agent name to remove")],
):
    """
    Remove an agent configuration.

    Examples:
        agentarts config remove my-agent
    """
    success = config_op.remove_agent(name)
    if not success:
        raise typer.Exit(1)
