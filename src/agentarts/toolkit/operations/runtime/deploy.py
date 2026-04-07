"""Deploy operation implementation"""

from enum import Enum
from typing import Any, Dict, Optional

from rich.console import Console

from agentarts.toolkit.operations.runtime.config import (
    get_agent,
    get_config_file_path,
)
from agentarts.toolkit.utils.runtime.container import (
    check_docker_available,
    check_dockerfile_exists,
    build_docker_image,
    tag_image,
    push_image,
    login_to_registry,
    run_container,
)
from agentarts.sdk.service.swr_client import SWRClient
from agentarts.sdk.service.runtime_client import RuntimeClient

console = Console()


class DeployMode(str, Enum):
    """Deploy mode."""

    LOCAL = "local"
    SWR = "swr"


def create_agentarts_runtime(
    agent_name: str,
    swr_image: str,
    region: str,
    agent_config: Optional[Any] = None,
    port: Optional[int] = None,
    description: Optional[str] = None,
) -> Optional[str]:
    """
    Create or update AgentArts runtime using RuntimeClient.

    Args:
        agent_name: Agent name
        swr_image: SWR image URL
        region: Huawei Cloud region
        agent_config: Agent configuration from yaml
        port: Service port (overrides config)
        description: Agent description (overrides config)

    Returns:
        Agent ID if successful, None otherwise
    """
    console.print(f"\n[bold]Creating AgentArts runtime:[/bold] [cyan]{agent_name}[/cyan]")

    try:
        from agentarts.sdk.utils.constant import get_control_plane_endpoint

        endpoint = get_control_plane_endpoint(region)

        client = RuntimeClient(control_endpoint=endpoint)

        artifact_source_config = {
            "url": swr_image,
            "commands": [],
        }

        invoke_config = {}
        network_config = None
        identity_config = None
        observability_config = None
        env_vars = None
        tags_config = None
        execution_agency_name = None
        agent_gateway_id = None

        if agent_config is not None:
            runtime_cfg = agent_config.runtime

            if runtime_cfg.invoke_config:
                invoke_config = {
                    "protocol": runtime_cfg.invoke_config.protocol,
                    "port": port or runtime_cfg.invoke_config.port,
                }

            if runtime_cfg.network_config:
                network_config = runtime_cfg.network_config.to_dict()

            if runtime_cfg.identity_configuration:
                identity_config = runtime_cfg.identity_configuration.to_dict()

            if runtime_cfg.observability:
                observability_config = runtime_cfg.observability.to_dict()

            if runtime_cfg.environment_variables:
                env_vars = {kv.key: kv.value for kv in runtime_cfg.environment_variables if kv.value}

            if runtime_cfg.tags:
                tags_config = {kv.key: kv.value for kv in runtime_cfg.tags if kv.value}

            execution_agency_name = runtime_cfg.execution_agency_name
            agent_gateway_id = runtime_cfg.agent_gateway_id

        if not invoke_config:
            invoke_config = {
                "protocol": "HTTP",
                "port": port or 8080,
            }

        agent_description = description or f"Agent deployed from {swr_image}"

        agent = client.create_or_update_agent(
            agent_name=agent_name,
            description=agent_description,
            artifact_source_config=artifact_source_config,
            invoke_config=invoke_config,
            network_config=network_config,
            identity_config=identity_config,
            observability_config=observability_config,
            env_vars=env_vars,
            tags_config=tags_config,
            execution_agency_name=execution_agency_name,
            agent_gateway_id=agent_gateway_id,
        )

        agent_id = agent.get("agent_id")
        if agent_id:
            console.print(f"[green]Done:[/green] Runtime created/updated successfully")
            console.print(f"[dim]Agent ID: {agent_id}[/dim]")
            return agent_id
        else:
            console.print("[yellow]Warning: Agent created but no agent_id returned[/yellow]")
            return agent.get("name")

    except Exception as e:
        console.print(f"[red]Error creating runtime: {e}[/red]")
        return None


def deploy_project(
    agent_name: Optional[str] = None,
    mode: DeployMode = DeployMode.SWR,
    image_tag: str = "latest",
    port: Optional[int] = None,
    local_port: Optional[int] = None,
    swr_org: Optional[str] = None,
    swr_repo: Optional[str] = None,
    description: Optional[str] = None,
) -> bool:
    """
    Deploy project.

    Args:
        agent_name: Agent name (uses default if None)
        mode: Deploy mode (local or swr)
        image_tag: Docker image tag
        port: Service port (for SWR mode)
        local_port: Local port (for local mode)
        swr_org: SWR organization (overrides config)
        swr_repo: SWR repository (overrides config)
        description: Agent description (overrides config)

    Returns:
        True if successful, False otherwise
    """
    config_path = get_config_file_path()
    if not config_path.exists():
        console.print("[red]Error: Configuration file not found[/red]")
        console.print("[dim]Run 'agentarts config' to create configuration first[/dim]")
        return False

    agent_config = get_agent(agent_name)
    if agent_config is None:
        console.print(f"[red]Error: Agent '{agent_name or 'default'}' not found in configuration[/red]")
        return False

    actual_agent_name = agent_config.base.name or agent_name or "agent"

    console.print(f"\n[bold cyan]Deploying Agent: {actual_agent_name}[/bold cyan]")
    console.print(f"Mode: [yellow]{mode.value}[/yellow]")

    if not check_docker_available():
        console.print("[red]Error: Docker is not available or not running[/red]")
        console.print("[dim]Please start Docker and try again[/dim]")
        return False

    if not check_dockerfile_exists():
        console.print("[red]Error: Dockerfile not found in current directory[/red]")
        console.print("[dim]Run 'agentarts config' to generate Dockerfile first[/dim]")
        return False

    region = agent_config.base.region or "cn-north-4"
    service_port = port or (agent_config.runtime.invoke_config.port if agent_config.runtime.invoke_config else 8080)

    local_image_name = f"{actual_agent_name}"
    local_full_image = f"{local_image_name}:{image_tag}"

    if not build_docker_image(local_image_name, image_tag):
        return False

    if mode == DeployMode.LOCAL:
        local_service_port = local_port or service_port
        return run_container(
            image_name=local_image_name,
            image_tag=image_tag,
            port=local_service_port,
            container_name=actual_agent_name,
        )

    final_swr_org = swr_org or agent_config.swr_config.organization
    final_swr_repo = swr_repo or agent_config.swr_config.repository

    if not final_swr_org or not final_swr_repo:
        console.print("[red]Error: SWR organization and repository must be configured[/red]")
        console.print("[dim]Specify via --swr-org and --swr-repo options, or configure in yaml[/dim]")
        return False

    console.print(f"\n[bold]Deploying to SWR:[/bold] [cyan]{final_swr_org}/{final_swr_repo}[/cyan]")

    try:
        swr_client = SWRClient(region=region)

        console.print(f"\n[bold]Setting up SWR resources...[/bold]")

        if agent_config.swr_config.organization_auto_create:
            org_result = swr_client.create_or_get_organization(final_swr_org)
            if org_result is None:
                console.print(f"[red]Error: Failed to create/get organization '{final_swr_org}'[/red]")
                return False
            console.print(f"[green]Done:[/green] Organization [cyan]{final_swr_org}[/cyan] ready")
        else:
            org_result = swr_client.get_organization(final_swr_org)
            if org_result is None:
                console.print(f"[red]Error: Organization '{final_swr_org}' not found[/red]")
                console.print("[dim]Set organization_auto_create: true in config to auto-create[/dim]")
                return False
            console.print(f"[green]Done:[/green] Using existing organization [cyan]{final_swr_org}[/cyan]")

        if agent_config.swr_config.repository_auto_create:
            repo_result = swr_client.create_or_get_repository(final_swr_org, final_swr_repo)
            if repo_result is None:
                console.print(f"[red]Error: Failed to create/get repository '{final_swr_org}/{final_swr_repo}'[/red]")
                return False
            console.print(f"[green]Done:[/green] Repository [cyan]{final_swr_org}/{final_swr_repo}[/cyan] ready")
        else:
            repo_result = swr_client.get_repository(final_swr_org, final_swr_repo)
            if repo_result is None:
                console.print(f"[red]Error: Repository '{final_swr_org}/{final_swr_repo}' not found[/red]")
                console.print("[dim]Set repository_auto_create: true in config to auto-create[/dim]")
                return False
            console.print(f"[green]Done:[/green] Using existing repository [cyan]{final_swr_org}/{final_swr_repo}[/cyan]")

        console.print(f"\n[bold]Getting SWR credentials...[/bold]")
        login_server, username, password = swr_client.create_swr_secret()
        if not username or not password:
            console.print("[red]Error: Failed to get SWR credentials[/red]")
            return False

        if not login_to_registry(login_server, username, password):
            console.print("[red]Error: Failed to login to SWR[/red]")
            return False

        swr_image = swr_client.get_full_image_name(final_swr_org, final_swr_repo, image_tag)

        if not tag_image(local_full_image, swr_image):
            console.print("[red]Error: Failed to tag image[/red]")
            return False

        if not push_image(swr_image):
            console.print("[red]Error: Failed to push image to SWR[/red]")
            return False

        console.print(f"[green]Done:[/green] Image deployed to [cyan]{swr_image}[/cyan]")

    except ImportError:
        console.print("[red]Error: Huawei Cloud SDK not installed[/red]")
        console.print("[dim]Install huaweicloudsdkswr for SWR deployment functionality.[/dim]")
        return False
    except Exception as e:
        console.print(f"[red]Error: SWR deployment failed: {e}[/red]")
        return False

    runtime_id = create_agentarts_runtime(
        agent_name=actual_agent_name,
        swr_image=swr_image,
        region=region,
        agent_config=agent_config,
        port=port,
        description=description,
    )

    if runtime_id is None:
        return False

    console.print(f"\n[bold green]Deployment successful![/bold green]")
    console.print(f"\n[bold]Runtime Details:[/bold]")
    console.print(f"  Agent Name: [cyan]{actual_agent_name}[/cyan]")
    console.print(f"  Runtime ID: [cyan]{runtime_id}[/cyan]")
    console.print(f"  Image: [cyan]{swr_image}[/cyan]")
    console.print(f"  Region: [yellow]{region}[/yellow]")
    console.print(f"\nDashboard: [link]https://console.huaweicloud.com/agentarts[/link]")

    return True
