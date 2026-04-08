"""Build command definition"""

from typing import Annotated

import click
import typer

from agentarts.toolkit.operations.runtime import build as build_op


def build(
    output: Annotated[str, typer.Option("--output", "-o", help="Output directory")] = "./dist",
    platform: Annotated[
        str,
        typer.Option(
            "--platform",
            help="Target platform",
            click_type=click.Choice(["docker", "kubernetes", "serverless"]),
        ),
    ] = "docker",
):
    """
    Build project.

    Examples:
        agentarts build --platform docker
    """
    success = build_op.build_project(output=output, platform=platform)
    if not success:
        raise typer.Exit(1)
