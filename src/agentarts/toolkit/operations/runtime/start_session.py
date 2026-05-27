"""Runtime start-session operation"""

from typing import Any

from agentarts.sdk.service.http_client import SignMode
from agentarts.sdk.service.runtime_client import RuntimeClient
from agentarts.toolkit.operations.runtime.invoke import _get_data_endpoint, _resolve_agent_info
from agentarts.toolkit.utils.common import echo_error


def start_runtime_session(
    agent_name: str | None = None,
    region: str | None = None,
    bearer_token: str | None = None,
    endpoint: str | None = None,
    skip_ssl_verification: bool = False,
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Start runtime session.

    Args:
        agent_name: Agent name
        region: Region name
        bearer_token: Optional bearer token for authentication
        endpoint: Optional endpoint name
        skip_ssl_verification: Skip SSL certificate verification
        user_id: Optional user ID for OAuth2 outbound credentials

    Returns:
        Start result dict with session_id
    """
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

    return client.start_session(
        agent_name=agent_name,
        bearer_token=bearer_token,
        endpoint=endpoint,
        user_id=user_id,
    )