"""Config command definitions"""

from typing import Annotated, Optional

import typer

from agentarts.toolkit.operations.runtime import config as config_op

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
    region: Annotated[Optional[str], typer.Option("--region", "-r", help="Huawei Cloud region (e.g., cn-north-4)")] = None,
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
    - SWR organization
    - SWR repository

    Examples:
        agentarts config
        agentarts config --name my-agent --entrypoint app:main
        agentarts config -n my-agent -e app:main --dependency-file requirements.txt --swr-org my-org --swr-repo my-repo
    """
    if ctx.invoked_subcommand is not None:
        return

    console = config_op.console

    console.print("\n[bold cyan]AgentArts Configuration[/bold cyan]\n")

    existing_agents = config_op.list_agents()
    if existing_agents:
        console.print(f"[dim]Existing agents: {', '.join(existing_agents)}[/dim]\n")

    agent_name = name
    if agent_name is None:
        default_name = config_op.get_default_agent()
        prompt_text = "Agent name"
        if default_name:
            prompt_text += f" [{default_name}]"
        agent_name = typer.prompt(prompt_text, default=default_name or "")

    if not agent_name:
        console.print("[red]Error: Agent name is required[/red]")
        raise typer.Exit(1)

    agent_entrypoint = entrypoint
    if agent_entrypoint is None:
        existing_config = config_op.get_agent(agent_name)
        default_entrypoint = existing_config.base.entrypoint if existing_config else None
        prompt_text = "Entrypoint"
        if default_entrypoint:
            prompt_text += f" [{default_entrypoint}]"
        agent_entrypoint = typer.prompt(prompt_text, default=default_entrypoint or "")

    if not agent_entrypoint:
        console.print("[red]Error: Entrypoint is required[/red]")
        raise typer.Exit(1)

    agent_region = region
    if agent_region is None:
        existing_config = config_op.get_agent(agent_name)
        default_region = existing_config.base.region if existing_config else "cn-north-4"
        agent_region = typer.prompt("Region", default=default_region)

    agent_dependency_file = dependency_file
    if agent_dependency_file is None:
        existing_config = config_op.get_agent(agent_name)
        default_dep = existing_config.base.dependency_file if existing_config else None
        prompt_text = "Dependency file"
        if default_dep:
            prompt_text += f" [{default_dep}]"
        agent_dependency_file = typer.prompt(prompt_text, default=default_dep or "")

    org = swr_organization
    if org is None:
        existing_config = config_op.get_agent(agent_name)
        default_org = existing_config.swr_config.organization if existing_config else None
        prompt_text = "SWR organization"
        if default_org:
            prompt_text += f" [{default_org}]"
        org = typer.prompt(prompt_text, default=default_org or "")

    if not org:
        console.print("[red]Error: SWR organization is required[/red]")
        raise typer.Exit(1)

    repo = swr_repository
    if repo is None:
        existing_config = config_op.get_agent(agent_name)
        default_repo = existing_config.swr_config.repository if existing_config else None
        prompt_text = "SWR repository"
        if default_repo:
            prompt_text += f" [{default_repo}]"
        repo = typer.prompt(prompt_text, default=default_repo or "")

    if not repo:
        console.print("[red]Error: SWR repository is required[/red]")
        raise typer.Exit(1)

    success = config_op.add_agent(
        name=agent_name,
        entrypoint=agent_entrypoint,
        region=agent_region,
        dependency_file=agent_dependency_file if agent_dependency_file else None,
        swr_organization=org,
        swr_repository=repo,
        set_as_default=set_default,
    )

    if not success:
        raise typer.Exit(1)

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
        agentarts config set base.region cn-north-4
        agentarts config set base.name my-agent --agent my-agent
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
