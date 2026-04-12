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


class RegionType(str, Enum):
    """Available Huawei Cloud regions"""
    cn_north_4 = "cn-north-4"
    cn_north_1 = "cn-north-1"
    cn_east_3 = "cn-east-3"
    cn_east_2 = "cn-east-2"
    cn_south_1 = "cn-south-1"
    cn_southwest_2 = "cn-southwest-2"
    ap_southeast_1 = "ap-southeast-1"
    ap_southeast_3 = "ap-southeast-3"


TEMPLATE_DESCRIPTIONS = {
    TemplateType.basic: "Basic agent template with minimal setup",
    TemplateType.langgraph: "LangGraph-based agent with state management",
    TemplateType.langchain: "LangChain-based agent with tool integration",
    TemplateType.google_adk: "Google ADK agent template",
}


REGION_NAMES = {
    RegionType.cn_north_4: "CN North 4 (Beijing)",
    RegionType.cn_north_1: "CN North 1 (Beijing)",
    RegionType.cn_east_3: "CN East 3 (Shanghai)",
    RegionType.cn_east_2: "CN East 2 (Shanghai)",
    RegionType.cn_south_1: "CN South 1 (Guangzhou)",
    RegionType.cn_southwest_2: "CN Southwest 2 (Guiyang)",
    RegionType.ap_southeast_1: "AP Southeast 1 (Hong Kong)",
    RegionType.ap_southeast_3: "AP Southeast 3 (Singapore)",
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
    """Prompt user to select a region interactively"""
    console.print("\n[bold cyan]Available Regions:[/bold cyan]\n")
    
    default_idx = 6  # cn-southwest-2
    for i, region in enumerate(RegionType, 1):
        name = REGION_NAMES.get(region, region.value)
        marker = " (default)" if i == default_idx else ""
        console.print(f"  [yellow]{i}[/yellow]. [green]{region.value:<18}[/green] - {name}{marker}")
    
    console.print()
    
    choices = [str(i) for i in range(1, len(RegionType) + 1)]
    choice_map = {str(i): t.value for i, t in enumerate(RegionType, 1)}
    
    selection = Prompt.ask(
        "[bold]Select a region[/bold]",
        choices=choices,
        default=str(default_idx),
        show_choices=False,
    )
    
    return choice_map[selection]


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
