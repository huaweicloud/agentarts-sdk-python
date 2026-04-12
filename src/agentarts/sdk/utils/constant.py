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


# ============================================================
# Huawei Cloud Credentials
# ============================================================

HUAWEICLOUD_SDK_AK = os.getenv("HUAWEICLOUD_SDK_AK")
"""Huawei Cloud Access Key ID for API authentication."""

HUAWEICLOUD_SDK_SK = os.getenv("HUAWEICLOUD_SDK_SK")
"""Huawei Cloud Secret Access Key for API authentication."""

HUAWEICLOUD_SDK_SECURITY_TOKEN = os.getenv("HUAWEICLOUD_SDK_SECURITY_TOKEN")
"""Security token for temporary credentials (STS). Required when using
temporary AK/SK obtained from the Security Token Service."""

HUAWEICLOUD_SDK_REGION = os.getenv("HUAWEICLOUD_SDK_REGION")
"""Huawei Cloud region for API requests. Defaults to "cn-southwest-2"."""

# ============================================================
# Huawei Cloud Identity Provider (IDP) Settings
# ============================================================

HUAWEICLOUD_SDK_IDP_ID = os.getenv("HUAWEICLOUD_SDK_IDP_ID")
"""Identity Provider ID for federated authentication."""

HUAWEICLOUD_SDK_ID_TOKEN_FILE = os.getenv("HUAWEICLOUD_SDK_ID_TOKEN_FILE")
"""Path to the ID token file used for federated authentication."""

HUAWEICLOUD_SDK_PROJECT_ID = os.getenv("HUAWEICLOUD_SDK_PROJECT_ID")
"""Huawei Cloud project ID. Used to scope API requests to a specific project."""


# ============================================================
# AgentArts Service Endpoints
# ============================================================

AGENTARTS_CONTROL_ENDPOINT = os.getenv("AGENTARTS_CONTROL_ENDPOINT")
"""AgentArts control plane endpoint. Override this to use a custom control
plane URL. If not set, the endpoint is derived from the region.

Example: https://agentarts.cn-southwest-2.myhuaweicloud.com
"""

AGENTARTS_RUNTIME_DATA_ENDPOINT = os.getenv("AGENTARTS_RUNTIME_DATA_ENDPOINT")
"""AgentArts runtime data plane endpoint. Used for agent execution
and data exchange during runtime."""

AGENTARTS_MEMORY_DATA_ENDPOINT = os.getenv("AGENTARTS_MEMORY_DATA_ENDPOINT")
"""AgentArts memory data plane endpoint. Override this to use a custom
memory service URL. If not set, the endpoint is derived from the
region and space ID."""

AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT = os.getenv("AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT")

# ============================================================
# Huawei Cloud Service Endpoints
# ============================================================

HUAWEICLOUD_SDK_IAM_ENDPOINT = os.getenv("HUAWEICLOUD_SDK_IAM_ENDPOINT")
"""Huawei Cloud IAM (Identity and Access Management) endpoint.
Override this to use a custom IAM endpoint for authentication."""

HUAWEICLOUD_SDK_SWR_ENDPOINT = os.getenv("HUAWEICLOUD_SDK_SWR_ENDPOINT")
"""Huawei Cloud SWR (Software Repository for Container) endpoint.
Used for container image management during deployment."""

HUAWEICLOUD_SDK_AGENTIDENTITY_ENDPOINT = os.getenv("HUAWEICLOUD_SDK_AGENTIDENTITY_ENDPOINT")

# ============================================================
# Runtime Settings
# ============================================================

PYTHON_BASE_IMAGE = os.getenv("PYTHON_BASE_IMAGE")
"""Base Docker image for Python agent runtime. Override this to use
a custom base image for agent deployment.

Example: swr.cn-southwest-2.myhuaweicloud.com/my-python-base:3.12
"""


# ============================================================
# Helper Functions
# ============================================================

def get_region() -> str:
    """
    Get the current Huawei Cloud region.

    Checks the following environment variables in order:
    1. HUAWEICLOUD_SDK_REGION
    2. HUAWEICLOUD_REGION
    3. OS_REGION_NAME (OpenStack compatibility)

    Returns:
        The region string (e.g., "cn-southwest-2"), or empty string if not set.
    """
    if HUAWEICLOUD_SDK_REGION:
        return HUAWEICLOUD_SDK_REGION
    region_env = os.getenv("HUAWEICLOUD_REGION")
    if region_env:
        return region_env
    os_region = os.getenv("OS_REGION_NAME")
    if os_region:
        return os_region
    return "cn-southwest-2"


def get_control_plane_endpoint(region: str = None) -> str:
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
    if AGENTARTS_CONTROL_ENDPOINT:
        return AGENTARTS_CONTROL_ENDPOINT
    region = region or get_region()
    return f"https://agentarts.{region}.myhuaweicloud.com"


def get_runtime_data_plane_endpoint() -> str:
    """
    Get the AgentArts runtime data plane endpoint URL.

    Args:
        endpoint: Custom data plane endpoint URL. If not provided,
                  uses AGENTARTS_RUNTIME_DATA_ENDPOINT from environment.

    Returns:
        The data plane endpoint URL, or empty string if not configured.
    """
    return AGENTARTS_RUNTIME_DATA_ENDPOINT


def get_data_plane_endpoint() -> str:
    """
    Get the AgentArts data plane endpoint URL (alias for runtime).

    This is an alias for get_runtime_data_plane_endpoint() for backward
    compatibility.

    Returns:
        The data plane endpoint URL, or empty string if not configured.
    """
    return get_runtime_data_plane_endpoint()

def get_code_interpreter_data_plane_endpoint() -> str:
    """
    Get the AgentArts data plane endpoint URL.

    Args:
        endpoint: Custom data plane endpoint URL. If not provided,
                  uses AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT from environment.

    Returns:
        The data plane endpoint URL, or empty string if not configured.
    """
    if AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT:
        return AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT
    return AGENTARTS_RUNTIME_DATA_ENDPOINT

def get_memory_endpoint(
    endpoint_type: str = "control",
    region: str = None,
    space_id: str = None
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
    elif endpoint_type == "data":
        if AGENTARTS_MEMORY_DATA_ENDPOINT:
            return AGENTARTS_MEMORY_DATA_ENDPOINT
        if not space_id:
            raise ValueError("space_id is required for data endpoint")
        region = region or get_region()
        return f"https://{space_id}.memory.{region}.agentarts.myhuaweicloud.com"
    else:
        raise ValueError(f"Invalid endpoint type: {endpoint_type}")


def get_iam_endpoint(region: str = None) -> str:
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
    if HUAWEICLOUD_SDK_IAM_ENDPOINT:
        return HUAWEICLOUD_SDK_IAM_ENDPOINT
    region = region or get_region()
    return f"https://iam.{region}.myhuaweicloud.com"

def get_swr_endpoint(region: str = None) -> str:
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
    if HUAWEICLOUD_SDK_SWR_ENDPOINT:
        return HUAWEICLOUD_SDK_SWR_ENDPOINT
    region = region or get_region()
    return f"https://swr-api.{region}.myhuaweicloud.com"

def get_identity_endpoint(region: str = None) -> str:
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
        "https://agent-identity.cn-southwest-2.myhuaweicloud.com"
    """
    if HUAWEICLOUD_SDK_AGENTIDENTITY_ENDPOINT:
        return HUAWEICLOUD_SDK_AGENTIDENTITY_ENDPOINT
    region = region or get_region()
    return f"https://agent-identity.{region}.myhuaweicloud.com"
