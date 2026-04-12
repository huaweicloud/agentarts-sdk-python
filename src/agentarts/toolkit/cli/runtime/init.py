"""Init command definition"""

from enum import Enum
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

from agentarts.toolkit.operations.runtime import init as init_op

console = Console()


class TemplateType(str, Enum):
    """Available project templates"""
    basic = "basic"
    langgraph = "langgraph"
    langchain = "langchain"
    google_adk = "google-adk"


TEMPLATE_DESCRIPTIONS = {
    TemplateType.basic: "Basic agent template with minimal setup",
    TemplateType.langgraph: "LangGraph-based agent with state management",
    TemplateType.langchain: "LangChain-based agent with tool integration",
    TemplateType.google_adk: "Google ADK agent template",
}


def prompt_for_template() -> TemplateType:
    """Prompt user to select a template interactively"""
    console.print("\n[bold cyan]Available Templates:[/bold cyan]\n")
    
    for i, template in enumerate(TemplateType, 1):
        desc = TEMPLATE_DESCRIPTIONS.get(template, "")
        console.print(f"  [yellow]{i}[/yellow]. [green]{template.value:<12}[/green] - {desc}")
    
    console.print()
    
    choices = [str(i) for i in range(1, len(TemplateType) + 1)]
    choice_map = {str(i): t for i, t in enumerate(TemplateType, 1)}
    
    selection = Prompt.ask(
        "[bold]Select a template[/bold]",
        choices=choices,
        default="2",
        show_choices=False,
    )
    
    return choice_map[selection]


def prompt_for_name() -> str:
    """Prompt user to enter project name"""
    return Prompt.ask("\n[bold]Enter project name[/bold]", default="my_agent")


def prompt_for_region() -> str:
    """Prompt user to enter region"""
    console.print("\n[bold]Region:[/bold]")
    console.print("[dim]  Default: cn-southwest-2[/dim]")
    return Prompt.ask("  Region", default="cn-southwest-2")


def init(
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Project name"),
    ] = None,
    template: Annotated[
        Optional[TemplateType],
        typer.Option(
            "--template",
            "-t",
            help="Project template (basic, langgraph, langchain, google-adk)",
        ),
    ] = None,
    path: Annotated[str, typer.Option("--path", "-p", help="Project path")] = ".",
    region: Annotated[
        Optional[str],
        typer.Option("--region", "-r", help="Huawei Cloud region"),
    ] = None,
    swr_org: Annotated[
        Optional[str],
        typer.Option("--swr-org", help="SWR organization (default: agentarts-org)"),
    ] = None,
    swr_repo: Annotated[
        Optional[str],
        typer.Option("--swr-repo", help="SWR repository (default: {name})"),
    ] = None,
):
    """
    Initialize a new AgentArts project.

    Creates a complete project structure with:
    - agent.py: Agent implementation based on selected template
    - requirements.txt: Dependencies including SDK and framework packages
    - .agentarts_config.yaml: Configuration file for deployment
    - Dockerfile: Docker build file for containerization

    After initialization, you can directly deploy using 'agentarts deploy'.

    Examples:
        agentarts init
        agentarts init -n my_agent
        agentarts init -n my_agent -t langgraph
        agentarts init -n my_agent -t langchain -r cn-southwest-2
        agentarts init -n my_agent --swr-org my-org --swr-repo my-repo
    """
    if name is None:
        name = prompt_for_name()
    
    if template is None:
        template = prompt_for_template()
    
    if region is None:
        region = prompt_for_region()
    
    console.print(f"\n[bold]Creating project:[/bold] [cyan]{name}[/cyan]")
    console.print(f"[bold]Template:[/bold] [green]{template.value}[/green]")
    console.print(f"[bold]Region:[/bold] [yellow]{region}[/yellow]")
    console.print(f"[bold]Path:[/bold] {path}\n")
    
    success = init_op.init_project(
        template=template.value,
        name=name,
        path=path,
        region=region,
        swr_org=swr_org,
        swr_repo=swr_repo,
    )
    if not success:
        raise typer.Exit(1)
