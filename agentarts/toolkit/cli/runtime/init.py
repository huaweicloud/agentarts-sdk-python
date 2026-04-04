"""Init command definition"""

from typing import Annotated

import click
import typer

from agentarts.toolkit.operations.runtime import init as init_op


def init(
    name: Annotated[str, typer.Option("--name", "-n", help="Project name")] = ...,
    template: Annotated[
        str,
        typer.Option(
            "--template", "-t",
            help="Project template",
            click_type=click.Choice(["basic", "langgraph", "langchain", "autogen", "crewai"]),
        ),
    ] = "basic",
    path: Annotated[str, typer.Option("--path", "-p", help="Project path")] = ".",
):
    """
    Initialize a new project.

    Examples:
        agentarts init -n my_agent -t langgraph
    """
    success = init_op.init_project(template=template, name=name, path=path)
    if not success:
        raise typer.Exit(1)
