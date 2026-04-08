"""Deploy command definition"""

from typing import Annotated, Optional

import click
import typer

from agentarts.toolkit.operations.runtime import deploy as deploy_op


def deploy(
    region: Annotated[str, typer.Option("--region", "-r", help="Deployment region")] = "cn-north-4",
    environment: Annotated[
        str,
        typer.Option(
            "--environment", "-e",
            help="Deployment environment",
            click_type=click.Choice(["development", "staging", "production"]),
        ),
    ] = "development",
    config: Annotated[
        Optional[str],
        typer.Option("--config", "-c", help="Deployment configuration file"),
    ] = None,
):
    """
    Deploy to Huawei Cloud.

    Examples:
        agentarts deploy -r cn-north-4 -e production
    """
    success = deploy_op.deploy_project(region=region, environment=environment, config_path=config)
    if not success:
        raise typer.Exit(1)
