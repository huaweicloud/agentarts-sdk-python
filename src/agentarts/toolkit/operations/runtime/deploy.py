"""Deploy operation implementation"""

from enum import Enum
from typing import Any, Dict, Optional

from rich.console import Console
from rich.panel import Panel

from agentarts.sdk.utils.constant import get_region
from agentarts.toolkit.operations.runtime.config import (
    get_agent,
    get_config_file_path,
    load_config,
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
from agentarts.toolkit.utils.common import (
    echo_error,
    echo_success,
    echo_info,
    echo_step,
    echo_key_value,
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
    console.print(f"[bold cyan]Creating AgentArts runtime: [cyan]{agent_name}[/cyan]")

    try:
        from agentarts.sdk.utils.constant import get_control_plane_endpoint

        endpoint = get_control_plane_endpoint(region)

        client = RuntimeClient(control_endpoint=endpoint, verify_ssl=False)

        artifact_source_config = None
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

            if runtime_cfg.artifact_source:
                artifact_source_config = runtime_cfg.artifact_source.to_dict()

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
                env_vars = [{"key": kv.key, "value": kv.value} for kv in runtime_cfg.environment_variables if kv.value]

            if runtime_cfg.tags:
                tags_config = [{"key": kv.key, "value": kv.value} for kv in runtime_cfg.tags if kv.value]

            execution_agency_name = runtime_cfg.execution_agency_name
            agent_gateway_id = runtime_cfg.agent_gateway_id

        if not artifact_source_config:
            artifact_source_config = {
                "url": swr_image,
                "commands": [],
            }

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

        agent_id = agent.get("id")
        latest_version = agent.get("latest_version")

        echo_success(f"Runtime created/updated successfully with [dim]Agent ID: {agent_id}({latest_version})[/dim]")
        return agent_id

    except Exception as e:
        echo_error(f"Failed to create runtime: {e}")
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
        echo_error("Configuration file not found")
        console.print("[dim]Run 'agentarts config' to create configuration first[/dim]")
        return False

    agent_config = get_agent(agent_name)
    if agent_config is None:
        echo_error(f"Agent '{agent_name or 'default'}' not found in configuration")
        return False

    actual_agent_name = agent_config.base.name or agent_name or "agent"
    region = agent_config.base.region or get_region()
    service_port = port or (agent_config.runtime.invoke_config.port if agent_config.runtime.invoke_config else 8080)

    echo_info("Deploy Configuration", f"[cyan]Agent:[/cyan] [white]{actual_agent_name}[/white]\n[cyan]Mode:[/cyan] [yellow]{mode.value}[/yellow]\n[cyan]Region:[/cyan] [yellow]{region}[/yellow]")

    if not check_docker_available():
        echo_error("Docker is not available or not running")
        console.print("[dim]Please start Docker and try again[/dim]")
        return False

    if not check_dockerfile_exists():
        echo_error("Dockerfile not found in current directory")
        console.print("[dim]Run 'agentarts config' to generate Dockerfile first[/dim]")
        return False

    local_image_name = f"{actual_agent_name}"
    local_full_image = f"{local_image_name}:{image_tag}"

    console.print(Panel(
        f"[bold]Step 1/6[/bold] Building Docker image\n[dim]Image: {local_full_image}[/dim]",
        title="[bold cyan]Deploy Progress[/bold cyan]",
        border_style="cyan",
    ))
    if not build_docker_image(local_image_name, image_tag):
        return False

    if mode == DeployMode.LOCAL:
        local_service_port = local_port or service_port
        console.print(Panel(
            f"[bold]Step 2/2[/bold] Starting local container\n[dim]Port: {local_service_port}[/dim]",
            title="[bold cyan]Deploy Progress[/bold cyan]",
            border_style="cyan",
        ))
        return run_container(
            image_name=local_image_name,
            image_tag=image_tag,
            port=local_service_port,
            container_name=actual_agent_name,
        )

    final_swr_org = swr_org or agent_config.swr_config.organization
    final_swr_repo = swr_repo or agent_config.swr_config.repository

    if not final_swr_org or not final_swr_repo:
        echo_error("SWR organization and repository must be configured")
        console.print("[dim]Specify via --swr-org and --swr-repo options, or configure in yaml[/dim]")
        return False

    console.print(Panel(
        f"[bold]Step 2/6[/bold] Setting up SWR resources\n[dim]Organization: {final_swr_org}\n[dim]Repository: {final_swr_repo}[/dim]",
        title="[bold cyan]Deploy Progress[/bold cyan]",
        border_style="cyan",
    ))

    try:
        swr_client = SWRClient(region=region)

        if agent_config.swr_config.organization_auto_create:
            org_result = swr_client.create_or_get_organization(final_swr_org)
            if org_result is None:
                echo_error(f"Failed to create/get organization '{final_swr_org}'")
                return False
            echo_success(f"Organization [cyan]{final_swr_org}[/cyan] ready")
        else:
            org_result = swr_client.get_organization(final_swr_org)
            if org_result is None:
                echo_error(f"Organization '{final_swr_org}' not found")
                console.print("[dim]Set organization_auto_create: true in config to auto-create[/dim]")
                return False
            echo_success(f"Using existing organization [cyan]{final_swr_org}[/cyan]")

        if agent_config.swr_config.repository_auto_create:
            repo_result = swr_client.create_or_get_repository(final_swr_org, final_swr_repo)
            if repo_result is None:
                echo_error(f"Failed to create/get repository '{final_swr_org}/{final_swr_repo}'")
                return False
            echo_success(f"Repository [cyan]{final_swr_org}/{final_swr_repo}[/cyan] ready")
        else:
            repo_result = swr_client.get_repository(final_swr_org, final_swr_repo)
            if repo_result is None:
                echo_error(f"Repository '{final_swr_org}/{final_swr_repo}' not found")
                console.print("[dim]Set repository_auto_create: true in config to auto-create[/dim]")
                return False
            echo_success(f"Using existing repository [cyan]{final_swr_org}/{final_swr_repo}[/cyan]")

        console.print(Panel(
            f"[bold]Step 3/6[/bold] Getting SWR credentials\n[dim]Registry: swr.{region}.myhuaweicloud.com[/dim]",
            title="[bold cyan]Deploy Progress[/bold cyan]",
            border_style="cyan",
        ))
        login_server, username, password = swr_client.create_swr_secret()
        if not username or not password:
            echo_error("Failed to get SWR credentials")
            return False

        if not login_to_registry(login_server, username, password):
            echo_error("Failed to login to SWR")
            return False

        swr_image = swr_client.get_full_image_name(final_swr_org, final_swr_repo, image_tag)

        console.print(Panel(
            f"[bold]Step 4/6[/bold] Tagging and pushing image\n[dim]Source: {local_full_image}\n[dim]Target: {swr_image}[/dim]",
            title="[bold cyan]Deploy Progress[/bold cyan]",
            border_style="cyan",
        ))
        if not tag_image(local_full_image, swr_image):
            echo_error("Failed to tag image")
            return False

        if not push_image(swr_image):
            echo_error("Failed to push image to SWR")
            return False

        echo_success(f"Image deployed to [cyan]{swr_image}[/cyan]")

    except ImportError:
        echo_error("Huawei Cloud SDK not installed")
        console.print("[dim]Install huaweicloudsdkswr for SWR deployment functionality.[/dim]")
        return False
    except Exception as e:
        echo_error(f"SWR deployment failed: {e}")
        return False

    console.print(Panel(
        f"[bold]Step 5/6[/bold] Creating AgentArts runtime\n[dim]Agent: {actual_agent_name}\n[dim]Image: {swr_image}[/dim]",
        title="[bold cyan]Deploy Progress[/bold cyan]",
        border_style="cyan",
    ))
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

    full_config = load_config()
    if full_config:
        agent_key = agent_name or full_config.default_agent or "default"
        if agent_key in (full_config.agents or {}):
            full_config.agents[agent_key].runtime.agent_id = runtime_id
            full_config.to_yaml(str(config_path))

    console.print(Panel(
        f"[bold]Step 6/6[/bold] Deployment complete!",
        title="[bold green]Deploy Progress[/bold green]",
        border_style="green",
    ))
    summary = (
        f"[cyan]Agent Name:[/cyan] [white]{actual_agent_name}[/white]\n"
        f"[cyan]Runtime ID:[/cyan] [white]{runtime_id}[/white]\n"
        f"[cyan]Image:[/cyan] [white]{swr_image}[/white]\n"
        f"[cyan]Region:[/cyan] [yellow]{region}[/yellow]\n"
    )
    echo_success(summary)

    return True
