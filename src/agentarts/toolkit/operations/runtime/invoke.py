"""Invoke operation implementation"""

import json
import uuid
from enum import Enum
from typing import Any, Dict, Iterator, Optional, Union

from rich.console import Console

from agentarts.toolkit.operations.runtime.config import (
    get_agent,
    get_config_file_path,
)
from agentarts.sdk.service.runtime_client import LocalRuntimeClient, RuntimeClient

console = Console()


class InvokeMode(str, Enum):
    """Invoke mode."""

    LOCAL = "local"
    CLOUD = "cloud"


def invoke_agent(
    payload: str,
    agent_name: Optional[str] = None,
    mode: InvokeMode = InvokeMode.CLOUD,
    region: Optional[str] = None,
    port: Optional[int] = None,
    endpoint: Optional[str] = None,
    session_id: Optional[str] = None,
    bearer_token: Optional[str] = None,
    timeout: int = 900,
) -> bool:
    """
    Invoke agent locally or on cloud.

    Args:
        payload: JSON payload string
        agent_name: Agent name (for cloud mode, uses default if None)
        mode: Invoke mode (local or cloud)
        region: Huawei Cloud region (for cloud mode)
        port: Local port (for local mode)
        endpoint: Optional endpoint name
        session_id: Session ID for stateful agents
        bearer_token: Optional bearer token
        timeout: Request timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    try:
        json.loads(payload)
    except json.JSONDecodeError:
        console.print("[red]Error: Payload must be valid JSON[/red]")
        return False

    try:
        if mode == InvokeMode.LOCAL:
            local_port = port or 8080
            client = LocalRuntimeClient(port=local_port)

            console.print(f"\n[bold]Invoking local agent:[/bold] [cyan]localhost:{local_port}[/cyan]")

            result = client.invoke_agent(
                payload=payload,
                session_id=session_id,
                bearer_token=bearer_token,
                endpoint=endpoint,
                timeout=timeout,
            )
        else:
            if agent_name is None:
                config_path = get_config_file_path()
                if config_path.exists():
                    agent_config = get_agent(None)
                    if agent_config is not None:
                        agent_name = agent_config.base.name
                        region = region or agent_config.base.region

                if agent_name is None:
                    console.print("[red]Error: No agent specified and no default agent configured[/red]")
                    console.print("[dim]Specify --agent or set a default agent in config[/dim]")
                    return False

            actual_region = region or "cn-north-4"
            actual_session_id = session_id or str(uuid.uuid4())

            console.print(f"\n[bold]Invoking cloud agent:[/bold] [cyan]{agent_name}[/cyan]")
            console.print(f"[dim]Session ID: {actual_session_id}[/dim]")

            from agentarts.sdk.utils.constant import get_data_plane_endpoint

            data_endpoint = get_data_plane_endpoint(actual_region)
            client = RuntimeClient(data_endpoint=data_endpoint)

            result = client.invoke_agent(
                agent_name=agent_name,
                session_id=actual_session_id,
                payload=payload,
                bearer_token=bearer_token,
                endpoint=endpoint,
                timeout=timeout,
            )

        if isinstance(result, dict):
            if "error" in result:
                console.print(f"[red]Error: {result.get('error')}[/red]")
                return False

            console.print("\n[bold green]Response:[/bold green]")
            console.print_json(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        else:
            console.print("\n[bold green]Streaming Response:[/bold green]")
            for event in result:
                console.print(f"[dim]{event}[/dim]")
            return True

    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


def ping_agent(
    agent_name: Optional[str] = None,
    mode: InvokeMode = InvokeMode.CLOUD,
    region: Optional[str] = None,
    port: Optional[int] = None,
    bearer_token: Optional[str] = None,
) -> bool:
    """
    Ping agent to check health.

    Args:
        agent_name: Agent name (for cloud mode)
        mode: Invoke mode (local or cloud)
        region: Huawei Cloud region (for cloud mode)
        port: Local port (for local mode)
        bearer_token: Optional bearer token

    Returns:
        True if healthy, False otherwise
    """
    try:
        if mode == InvokeMode.LOCAL:
            local_port = port or 8080
            client = LocalRuntimeClient(port=local_port)

            console.print(f"\n[bold]Pinging local agent:[/bold] [cyan]localhost:{local_port}[/cyan]")

            result = client.ping_agent(
                bearer_token=bearer_token,
            )

            status = result.get("status", "Unknown")
            if status.lower() in ("healthy", "ok", "running"):
                console.print(f"[green]Status: {status}[/green]")
                return True
            else:
                console.print(f"[red]Status: {status}[/red]")
                return False
        else:
            if agent_name is None:
                config_path = get_config_file_path()
                if config_path.exists():
                    agent_config = get_agent(None)
                    if agent_config is not None:
                        agent_name = agent_config.base.name
                        region = region or agent_config.base.region

                if agent_name is None:
                    console.print("[red]Error: No agent specified[/red]")
                    return False

            actual_region = region or "cn-north-4"

            console.print(f"\n[bold]Pinging cloud agent:[/bold] [cyan]{agent_name}[/cyan]")

            from agentarts.sdk.utils.constant import get_data_plane_endpoint

            data_endpoint = get_data_plane_endpoint(actual_region)
            client = RuntimeClient(data_endpoint=data_endpoint)

            result = client.ping_agent(
                agent_name=agent_name,
                bearer_token=bearer_token,
            )

            if isinstance(result, dict):
                status = result.get("status", "Unknown")
                if status.lower() in ("healthy", "ok", "running"):
                    console.print(f"[green]Status: {status}[/green]")
                    return True
                else:
                    console.print(f"[yellow]Status: {status}[/yellow]")
                    return True
            else:
                console.print("[green]Status: Healthy (streaming)[/green]")
                return True

    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False
