"""Runtime exec-command operation"""

import shlex
from collections.abc import Iterator
from typing import Any

from agentarts.sdk.service.http_client import SignMode
from agentarts.sdk.service.runtime_client import RuntimeClient
from agentarts.toolkit.operations.runtime.invoke import _get_data_endpoint, _resolve_agent_info
from agentarts.toolkit.utils.common import echo_error

DEFAULT_TIMEOUT = 60
MAX_TIMEOUT = 300


def exec_runtime_command(
    command: str,
    agent_name: str | None = None,
    session_id: str | None = None,
    chunked: bool = False,
    bearer_token: str | None = None,
    region: str | None = None,
    endpoint: str | None = None,
    skip_ssl_verification: bool = False,
    user_id: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any] | Iterator[str]:
    """
    Execute command in runtime.

    Args:
        command: Command string to execute
        agent_name: Agent name
        session_id: Session ID
        chunked: Use chunked streaming mode
        bearer_token: Optional bearer token for authentication
        region: Region name
        endpoint: Optional endpoint name
        skip_ssl_verification: Skip SSL certificate verification
        user_id: Optional user ID for OAuth2 outbound credentials
        timeout: Request timeout in seconds (default: 60, max: 300)

    Returns:
        dict for normal mode, Iterator[str] for chunked mode
    """
    if not command:
        raise ValueError("Command is required")

    command_array = shlex.split(command)
    if not command_array:
        raise ValueError("Command cannot be empty")

    if timeout <= 0:
        raise ValueError(f"Timeout must be a positive number: {timeout}")
    if timeout > MAX_TIMEOUT:
        raise ValueError(f"Timeout exceeds maximum allowed value ({MAX_TIMEOUT}): {timeout}")

    agent_name, region, agent_id, auth_type = _resolve_agent_info(agent_name, region)

    if agent_name is None:
        echo_error("No agent specified and no default agent configured")
        raise ValueError("Agent name is required")

    verify_ssl = not skip_ssl_verification
    data_endpoint = _get_data_endpoint(agent_name, region or "", agent_id, verify_ssl)

    if not data_endpoint:
        raise ValueError(f"No data endpoint for agent {agent_name}")

    sign_mode = SignMode.SDK_HMAC_SHA256
    if auth_type and auth_type.upper() == "IAM":
        sign_mode = SignMode.V11_HMAC_SHA256

    client = RuntimeClient(
        data_endpoint=data_endpoint,
        region_id=region or "",
        verify_ssl=verify_ssl,
        sign_mode=sign_mode,
    )
    if bearer_token:
        client.set_auth_token(bearer_token)

    return client.exec_command(
        agent_name=agent_name,
        session_id=session_id,
        command=command_array,
        chunked=chunked,
        bearer_token=bearer_token,
        endpoint=endpoint,
        user_id=user_id,
        timeout=timeout,
    )
