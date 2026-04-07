"""Deploy command definition"""

from typing import Annotated, Optional

import typer

from agentarts.toolkit.operations.runtime import deploy as deploy_op


def deploy(
    agent: Annotated[
        Optional[str],
        typer.Option("--agent", "-a", help="Agent name (uses default if not specified)"),
    ] = None,
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            "-m",
            help="Deploy mode: 'local' for local Docker, 'swr' for Huawei Cloud SWR (default)",
        ),
    ] = "swr",
    tag: Annotated[
        str,
        typer.Option("--tag", "-t", help="Docker image tag"),
    ] = "latest",
    port: Annotated[
        Optional[int],
        typer.Option("--port", "-p", help="Service port (overrides config)"),
    ] = None,
    local_port: Annotated[
        Optional[int],
        typer.Option("--local-port", "-l", help="Local port mapping (for local mode)"),
    ] = None,
    swr_org: Annotated[
        Optional[str],
        typer.Option("--swr-org", help="SWR organization (overrides config)"),
    ] = None,
    swr_repo: Annotated[
        Optional[str],
        typer.Option("--swr-repo", help="SWR repository (overrides config)"),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Agent description (overrides config)"),
    ] = None,
):
    """
    Deploy agent to Huawei Cloud or run locally.

    Two deployment modes are supported:
    - swr (default): Build image, push to SWR, create AgentArts runtime
    - local: Build image and run in local Docker

    All parameters can be overridden via command-line options.
    If not specified, values from the configuration file (.agentarts_config.yaml) are used.

    SWR organization and repository:
    - If --swr-org and --swr-repo are not specified, values from config are used
    - If organization_auto_create is true in config, organization will be created if not exists
    - If repository_auto_create is true in config, repository will be created if not exists

    Agent creation:
    - If agent already exists with the same name, it will be updated
    - All runtime configurations from yaml are used (network, auth, observability, etc.)

    Prerequisites:
    - Run 'agentarts config' first to generate configuration and Dockerfile
    - Docker must be installed and running
    - For SWR mode: Set HUAWEICLOUD_SDK_AK and HUAWEICLOUD_SDK_SK environment variables

    Examples:
        agentarts deploy
        agentarts deploy --agent my-agent
        agentarts deploy --mode local --local-port 8080
        agentarts deploy --mode swr --tag v1.0.0
        agentarts deploy --swr-org my-org --swr-repo my-repo
        agentarts deploy --description "My custom agent"
    """
    deploy_mode = deploy_op.DeployMode.SWR
    if mode.lower() == "local":
        deploy_mode = deploy_op.DeployMode.LOCAL
    elif mode.lower() != "swr":
        console = deploy_op.console
        console.print(f"[red]Error: Invalid mode '{mode}'. Use 'local' or 'swr'.[/red]")
        raise typer.Exit(1)

    success = deploy_op.deploy_project(
        agent_name=agent,
        mode=deploy_mode,
        image_tag=tag,
        port=port,
        local_port=local_port,
        swr_org=swr_org,
        swr_repo=swr_repo,
        description=description,
    )

    if not success:
        raise typer.Exit(1)
