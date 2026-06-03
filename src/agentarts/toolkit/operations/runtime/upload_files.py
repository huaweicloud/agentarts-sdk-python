"""Runtime upload-files operation"""

from typing import Any

from agentarts.sdk.service.http_client import SignMode
from agentarts.sdk.service.runtime_client import RuntimeClient
from agentarts.toolkit.operations.runtime.invoke import (
    _check_file_transfer_enabled,
    _get_data_endpoint,
    _resolve_agent_info,
)
from agentarts.toolkit.utils.common import echo_error

DEFAULT_FILE_USER_ID = 1000
DEFAULT_FILE_GROUP_ID = 1000
DEFAULT_FILE_MODE = "0644"


def upload_runtime_files(
    agent_name: str | None = None,
    session_id: str | None = None,
    files: list[dict[str, str]] | None = None,
    path: str = "/home/user/",
    file_user_id: int | None = None,
    file_group_id: int | None = None,
    file_mode: str | None = None,
    bearer_token: str | None = None,
    region: str | None = None,
    endpoint: str | None = None,
    skip_ssl_verification: bool = False,
    user_id: str | None = None,
    timeout: int = 900,
) -> dict[str, Any]:
    """Upload files to runtime.

    Args:
        agent_name: Agent name
        session_id: Session ID
        files: List of file specs with local_file
        path: Remote directory path (must end with '/')
        file_user_id: File owner user ID (None for backend default)
        file_group_id: File owner group ID (None for backend default)
        file_mode: File permissions in octal (None for backend default)
        bearer_token: Optional bearer token
        region: Region name
        endpoint: Optional endpoint name
        skip_ssl_verification: Skip SSL certificate verification
        user_id: Optional user ID for OAuth2 outbound credentials
        timeout: Request timeout in seconds

    Returns:
        Upload result dict
    """
    if not files:
        raise ValueError("Files are required")

    agent_name, region, agent_id, auth_type = _resolve_agent_info(agent_name, region)

    if agent_name is None:
        echo_error("No agent specified and no default agent configured")
        raise ValueError("Agent name is required")

    verify_ssl = not skip_ssl_verification

    _check_file_transfer_enabled(agent_name, region or "", agent_id, verify_ssl)

    if session_id is None:
        raise ValueError("Session ID is required")

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

    return client.upload_files(
        agent_name=agent_name,
        session_id=session_id,
        files=files,
        path=path,
        file_user_id=file_user_id,
        file_group_id=file_group_id,
        file_mode=file_mode,
        bearer_token=bearer_token,
        endpoint=endpoint,
        user_id=user_id,
        timeout=timeout,
    )
