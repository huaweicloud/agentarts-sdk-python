"""Init command definition"""

from typing import Annotated, Optional

import click
import typer

from agentarts.toolkit.operations.runtime import init as init_op


def init(
    name: Annotated[str, typer.Option("--name", "-n", help="Project name")] = ...,
    template: Annotated[
        str,
        typer.Option(
            "--template",
            "-t",
            help="Project template (basic, langgraph, langchain, google-adk)",
            click_type=click.Choice(["basic", "langgraph", "langchain", "google-adk"]),
        ),
    ] = "langgraph",
    path: Annotated[str, typer.Option("--path", "-p", help="Project path")] = ".",
    region: Annotated[
        Optional[str],
        typer.Option("--region", "-r", help="Huawei Cloud region"),
    ] = None,
    swr_org: Annotated[
        Optional[str],
        typer.Option("--swr-org", help="SWR organization (default: {name}-org)"),
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
        agentarts init -n my_agent
        agentarts init -n my_agent -t langgraph
        agentarts init -n my_agent -t langchain -r cn-southwest-2
        agentarts init -n my_agent --swr-org my-org --swr-repo my-repo
    """
    success = init_op.init_project(
        template=template,
        name=name,
        path=path,
        region=region,
        swr_org=swr_org,
        swr_repo=swr_repo,
    )
    if not success:
        raise typer.Exit(1)
