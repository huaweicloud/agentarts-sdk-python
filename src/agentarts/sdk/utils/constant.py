"""
AgentArts Constants and Environment Variables

Centralized configuration for Huawei Cloud credentials, endpoints,
and runtime settings. All values are loaded from environment variables.

Environment variables can be set via:
    - System environment variables
    - .env file (loaded by python-dotenv)
    - IDE configuration

Example:
    export HUAWEICLOUD_SDK_AK="your-access-key"
    export HUAWEICLOUD_SDK_SK="your-secret-key"
    export HUAWEICLOUD_SDK_REGION="cn-southwest-2"
"""

import os

ENV_HUAWEICLOUD_SDK_AK = "HUAWEICLOUD_SDK_AK"
ENV_HUAWEICLOUD_SDK_SK = "HUAWEICLOUD_SDK_SK"
ENV_HUAWEICLOUD_SDK_SECURITY_TOKEN = "HUAWEICLOUD_SDK_SECURITY_TOKEN"
ENV_HUAWEICLOUD_SDK_REGION = "HUAWEICLOUD_SDK_REGION"
ENV_HUAWEICLOUD_REGION = "HUAWEICLOUD_REGION"
ENV_OS_REGION_NAME = "OS_REGION_NAME"

ENV_HUAWEICLOUD_SDK_IDP_ID = "HUAWEICLOUD_SDK_IDP_ID"
ENV_HUAWEICLOUD_SDK_ID_TOKEN_FILE = "HUAWEICLOUD_SDK_ID_TOKEN_FILE"
ENV_HUAWEICLOUD_SDK_PROJECT_ID = "HUAWEICLOUD_SDK_PROJECT_ID"

ENV_AGENTARTS_CONTROL_ENDPOINT = "AGENTARTS_CONTROL_ENDPOINT"
ENV_AGENTARTS_RUNTIME_DATA_ENDPOINT = "AGENTARTS_RUNTIME_DATA_ENDPOINT"
ENV_AGENTARTS_MEMORY_DATA_ENDPOINT = "AGENTARTS_MEMORY_DATA_ENDPOINT"
ENV_AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT = "AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT"

ENV_HUAWEICLOUD_SDK_IAM_ENDPOINT = "HUAWEICLOUD_SDK_IAM_ENDPOINT"
ENV_HUAWEICLOUD_SDK_SWR_ENDPOINT = "HUAWEICLOUD_SDK_SWR_ENDPOINT"
ENV_HUAWEICLOUD_SDK_AGENTIDENTITY_ENDPOINT = "HUAWEICLOUD_SDK_AGENTIDENTITY_ENDPOINT"

ENV_PYTHON_BASE_IMAGE = "PYTHON_BASE_IMAGE"


def _ensure_https(endpoint: str) -> str:
    """
    Ensure endpoint has https:// prefix.

    Args:
        endpoint: The endpoint URL to check.

    Returns:
        The endpoint URL with https:// prefix.
    """
    if not endpoint:
        return endpoint
    if not endpoint.startswith(("http://", "https://")):
        return f"https://{endpoint}"
    return endpoint


def get_region() -> str:
    """
    Get the current Huawei Cloud region.

    Checks the following environment variables in order:
    1. HUAWEICLOUD_SDK_REGION
    2. HUAWEICLOUD_REGION
    3. OS_REGION_NAME (OpenStack compatibility)

    Returns:
        The region string (e.g., "cn-southwest-2"), or default region if not set.
    """
    region_env = os.getenv(ENV_HUAWEICLOUD_SDK_REGION) or os.getenv(ENV_HUAWEICLOUD_REGION)
    if region_env:
        return region_env
    os_region = os.getenv(ENV_OS_REGION_NAME)
    if os_region:
        return os_region
    return "cn-southwest-2"


def get_control_plane_endpoint(region: str | None = None) -> str:
    """
    Get the AgentArts control plane endpoint URL.

    If AGENTARTS_CONTROL_ENDPOINT is set, returns that value directly.
    Otherwise, constructs the endpoint from the region.

    Args:
        region: Huawei Cloud region (e.g., "cn-southwest-2").
                 If not provided, auto-detected from environment.

    Returns:
        The control plane endpoint URL.

    Example:
        >>> get_control_plane_endpoint("cn-southwest-2")
        "https://agentarts.cn-southwest-2.myhuaweicloud.com"
    """
    endpoint = os.getenv(ENV_AGENTARTS_CONTROL_ENDPOINT)
    if endpoint:
        return _ensure_https(endpoint)
    region = region or get_region()
    return f"https://agentarts.{region}.myhuaweicloud.com"


def get_runtime_data_plane_endpoint() -> str:
    """
    Get the AgentArts data plane endpoint URL.

    Returns:
        The data plane endpoint URL, or empty string if not configured.
    """
    endpoint = os.getenv(ENV_AGENTARTS_RUNTIME_DATA_ENDPOINT) or ""
    return _ensure_https(endpoint)


def get_code_interpreter_data_plane_endpoint(endpoint: str | None = None) -> str:
    """
    Get the AgentArts code interpreter data plane endpoint URL.

    Args:
        endpoint: Custom data plane endpoint URL. If not provided,
                  uses AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT from environment.

    Returns:
        The data plane endpoint URL, or empty string if not configured.
    """
    code_endpoint = os.getenv(ENV_AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT)
    if code_endpoint:
        return _ensure_https(code_endpoint)
    if endpoint:
        return _ensure_https(endpoint)
    runtime_endpoint = os.getenv(ENV_AGENTARTS_RUNTIME_DATA_ENDPOINT) or ""
    return _ensure_https(runtime_endpoint)


def get_memory_endpoint(
    endpoint_type: str = "control",
    region: str | None = None,
    space_id: str | None = None
) -> str:
    """
    Get the AgentArts memory service endpoint URL.

    Supports two endpoint types:
    - "control": Returns the control plane endpoint (same as get_control_plane_endpoint).
    - "data": Returns the memory data plane endpoint. Requires space_id
              unless AGENTARTS_MEMORY_DATA_ENDPOINT is set.

    Args:
        endpoint_type: Either "control" or "data".
        region: Huawei Cloud region. Auto-detected if not provided.
        space_id: Agent workspace ID. Required for "data" endpoint type.

    Returns:
        The memory service endpoint URL.

    Raises:
        ValueError: If endpoint_type is not "control" or "data",
                    or if space_id is missing for "data" type.

    Example:
        >>> get_memory_endpoint("control", "cn-southwest-2")
        "https://agentarts.cn-southwest-2.myhuaweicloud.com"

        >>> get_memory_endpoint("data", "cn-southwest-2", "my-workspace")
        "https://my-workspace.memory.cn-southwest-2.agentarts.myhuaweicloud.com"
    """
    if endpoint_type == "control":
        return get_control_plane_endpoint(region)
    if endpoint_type == "data":
        memory_endpoint = os.getenv(ENV_AGENTARTS_MEMORY_DATA_ENDPOINT)
        if memory_endpoint:
            return _ensure_https(memory_endpoint)
        if not space_id:
            msg = "space_id is required for data endpoint"
            raise ValueError(msg)
        region = region or get_region()
        return f"https://{space_id}.memory.{region}.agentarts.myhuaweicloud.com"
    msg = f"Invalid endpoint type: {endpoint_type}"
    raise ValueError(msg)


def get_iam_endpoint(region: str | None = None) -> str:
    """
    Get the Huawei Cloud IAM (Identity and Access Management) endpoint URL.

    If HUAWEICLOUD_SDK_IAM_ENDPOINT is set, returns that value directly.
    Otherwise, constructs the endpoint from the region.

    Args:
        region: Huawei Cloud region (e.g., "cn-southwest-2").
                 If not provided, auto-detected from environment.

    Returns:
        The IAM endpoint URL.

    Example:
        >>> get_iam_endpoint("cn-southwest-2")
        "https://iam.cn-southwest-2.myhuaweicloud.com"
    """
    endpoint = os.getenv(ENV_HUAWEICLOUD_SDK_IAM_ENDPOINT)
    if endpoint:
        return _ensure_https(endpoint)
    region = region or get_region()
    return f"https://iam.{region}.myhuaweicloud.com"


def get_swr_endpoint(region: str | None = None) -> str:
    """
    Get the Huawei Cloud SWR (Software Repository for Container) endpoint URL.

    If HUAWEICLOUD_SDK_SWR_ENDPOINT is set, returns that value directly.
    Otherwise, constructs the endpoint from the region.

    Args:
        region: Huawei Cloud region (e.g., "cn-southwest-2").
                 If not provided, auto-detected from environment.

    Returns:
        The SWR endpoint URL.

    Example:
        >>> get_swr_endpoint("cn-southwest-2")
        "https://swr-api.cn-southwest-2.myhuaweicloud.com"
    """
    endpoint = os.getenv(ENV_HUAWEICLOUD_SDK_SWR_ENDPOINT)
    if endpoint:
        return _ensure_https(endpoint)
    region = region or get_region()
    return f"https://swr-api.{region}.myhuaweicloud.com"


def get_identity_endpoint(region: str | None = None) -> str:
    """
    Get the Huawei Cloud Agent Identity endpoint URL.

    If HUAWEICLOUD_SDK_AGENTIDENTITY_ENDPOINT is set, returns that value directly.
    Otherwise, constructs the endpoint from the region.

    Args:
        region: Huawei Cloud region (e.g., "cn-southwest-2").
                 If not provided, auto-detected from environment.

    Returns:
        The Agent Identity endpoint URL.

    Example:
        >>> get_identity_endpoint("cn-southwest-2")
        "https://agent-identity.cn-southwest-2.myhuaweicloud.com"
    """
    endpoint = os.getenv(ENV_HUAWEICLOUD_SDK_AGENTIDENTITY_ENDPOINT)
    if endpoint:
        return _ensure_https(endpoint)
    region = region or get_region()
    return f"https://agent-identity.{region}.myhuaweicloud.com"


def get_ak() -> str:
    """Get Huawei Cloud Access Key ID from environment."""
    return os.getenv(ENV_HUAWEICLOUD_SDK_AK) or ""


def get_sk() -> str:
    """Get Huawei Cloud Secret Access Key from environment."""
    return os.getenv(ENV_HUAWEICLOUD_SDK_SK) or ""


def get_security_token() -> str:
    """Get Huawei Cloud Security Token from environment (for STS)."""
    return os.getenv(ENV_HUAWEICLOUD_SDK_SECURITY_TOKEN) or ""


def get_project_id() -> str:
    """Get Huawei Cloud Project ID from environment."""
    return os.getenv(ENV_HUAWEICLOUD_SDK_PROJECT_ID) or ""


def get_python_base_image() -> str:
    """Get Python base image from environment."""
    return os.getenv(ENV_PYTHON_BASE_IMAGE) or ""
