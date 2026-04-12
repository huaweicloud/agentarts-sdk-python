"""Invoke operation implementation"""

import json
import uuid
from enum import Enum
from typing import Any, Dict, Iterator, Optional, Union

from rich.console import Console
from rich.panel import Panel

from agentarts.sdk.utils.constant import get_region
from agentarts.toolkit.operations.runtime.config import (
    get_agent,
    get_config_file_path,
)
from agentarts.toolkit.utils.common import echo_error, echo_success, echo_info, echo_key_value
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
        echo_error("Payload must be valid JSON")
        return False

    try:
        if mode == InvokeMode.LOCAL:
            local_port = port or 8080
            client = LocalRuntimeClient(port=local_port)

            console.print()
            echo_info("Invoke Request", f"[cyan]Mode:[/cyan] [yellow]Local[/yellow]\n[cyan]Endpoint:[/cyan] [white]localhost:{local_port}[/white]")

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
                    echo_error("No agent specified and no default agent configured")
                    console.print("[dim]Specify --agent or set a default agent in config[/dim]")
                    return False

            actual_region = region or get_region()
            actual_session_id = session_id or str(uuid.uuid4())

            console.print()
            echo_info("Invoke Request", f"[cyan]Mode:[/cyan] [yellow]Cloud[/yellow]\n[cyan]Agent:[/cyan] [white]{agent_name}[/white]\n[cyan]Session:[/cyan] [dim]{actual_session_id}[/dim]")

            from agentarts.sdk.utils.constant import get_runtime_data_plane_endpoint

            data_endpoint = get_runtime_data_plane_endpoint(actual_region)
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
                echo_error(str(result.get("error")))
                return False

            console.print()
            console.print("[bold green]Response:[/bold green]")
            console.print_json(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        else:
            console.print()
            console.print("[bold green]Streaming Response:[/bold green]")
            for event in result:
                console.print(f"[dim]{event}[/dim]")
            return True

    except RuntimeError as e:
        echo_error(str(e))
        return False
    except Exception as e:
        echo_error(str(e))
        return False


def status_agent(
    agent_name: Optional[str] = None,
    mode: InvokeMode = InvokeMode.CLOUD,
    region: Optional[str] = None,
    port: Optional[int] = None,
    bearer_token: Optional[str] = None,
) -> bool:
    """
    Check agent health status.

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

            console.print()
            echo_info("Status Check", f"[cyan]Mode:[/cyan] [yellow]Local[/yellow]\n[cyan]Endpoint:[/cyan] [white]localhost:{local_port}[/white]")

            result = client.ping_agent(
                bearer_token=bearer_token,
            )

            status = result.get("status", "Unknown")
            if status.lower() in ("healthy", "ok", "running"):
                echo_success(f"Status: {status}")
                return True
            else:
                echo_error(f"Status: {status}")
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
                    echo_error("No agent specified")
                    return False

            actual_region = region or "cn-north-4"

            console.print()
            echo_info("Status Check", f"[cyan]Mode:[/cyan] [yellow]Cloud[/yellow]\n[cyan]Agent:[/cyan] [white]{agent_name}[/white]")

            from agentarts.sdk.utils.constant import get_runtime_data_plane_endpoint

            data_endpoint = get_runtime_data_plane_endpoint(actual_region)
            client = RuntimeClient(data_endpoint=data_endpoint)

            result = client.ping_agent(
                agent_name=agent_name,
                bearer_token=bearer_token,
            )

            if isinstance(result, dict):
                status = result.get("status", "Unknown")
                if status.lower() in ("healthy", "ok", "running"):
                    echo_success(f"Status: {status}")
                    return True
                else:
                    console.print(f"[yellow]Status: {status}[/yellow]")
                    return True
            else:
                echo_success("Status: Healthy (streaming)")
                return True

    except RuntimeError as e:
        echo_error(str(e))
        return False
    except Exception as e:
        echo_error(str(e))
        return False
