"""Centralized constants and environment variables for Huawei AgentArts SDK.

This module consolidates all environment variable access and configuration constants
to avoid duplication across the codebase.
"""

import os

# =============================================================================
# Cloud Credentials (for IAM authentication)
# =============================================================================
HUAWEICLOUD_SDK_AK = os.getenv("HUAWEICLOUD_SDK_AK")
HUAWEICLOUD_SDK_SK = os.getenv("HUAWEICLOUD_SDK_SK")
HUAWEICLOUD_SDK_SECURITY_TOKEN = os.getenv("HUAWEICLOUD_SDK_SECURITY_TOKEN")

# =============================================================================
# OIDC Token Authentication
# =============================================================================
HUAWEICLOUD_SDK_IDP_ID = os.getenv("HUAWEICLOUD_SDK_IDP_ID")
HUAWEICLOUD_SDK_ID_TOKEN_FILE = os.getenv("HUAWEICLOUD_SDK_ID_TOKEN_FILE")
HUAWEICLOUD_SDK_PROJECT_ID = os.getenv("HUAWEICLOUD_SDK_PROJECT_ID")

# =============================================================================
# Service Endpoints
# =============================================================================
AGENTARTS_CONTROL_ENDPOINT = os.getenv("AGENTARTS_CONTROL_ENDPOINT")
AGENTARTS_RUNTIME_DATA_ENDPOINT = os.getenv("AGENTARTS_RUNTIME_DATA_ENDPOINT")
IAM_ENDPOINT = os.getenv("HUAWEICLOUD_SDK_IAM_ENDPOINT")
SWR_ENDPOINT = os.getenv("HUAWEICLOUD_SDK_SWR_ENDPOINT")
AGENTARTS_MEMORY_CONTROL_ENDPOINT = os.getenv("AGENTARTS_MEMORY_CONTROL_ENDPOINT")
AGENTARTS_MEMORY_DATA_ENDPOINT = os.getenv("AGENTARTS_MEMORY_DATA_ENDPOINT")


# =============================================================================
# Docker/Container Configuration
# =============================================================================
PYTHON_BASE_IMAGE = os.getenv("PYTHON_BASE_IMAGE")
DOCKER_PROXY = os.getenv("DOCKER_PROXY")

# =============================================================================
# Bearer Token (for agent invocation)
# =============================================================================
AGENTRUN_BEARER_TOKEN = os.getenv("AGENTRUN_BEARER_TOKEN")



# =============================================================================
# MCP Gateway
# =============================================================================
DEFAULT_AGENCY_NAME = "AgentArtsCoreGateway"


def get_region() -> str:
    """Get the configured Huawei Cloud region."""
    # 1. Check for standard Huawei Cloud environment variables
    # HUAWEICLOUD_SDK_REGION is the convention used in many Huawei tools
    region_env = os.getenv("HUAWEICLOUD_SDK_REGION") or os.getenv("HUAWEICLOUD_REGION")
    if region_env:
        return region_env

    # 2. Check for OpenStack compatibility
    # (Huawei Cloud is built on OpenStack, so this is often set in containerized environments)
    os_region = os.getenv("OS_REGION_NAME")
    if os_region:
        return os_region

    # 3. Default to a primary region
    return "cn-north-4"


def get_control_plane_endpoint(region: str = None) -> str:
    """Get the AgentRun control plane endpoint URL."""
    if AGENTARTS_CONTROL_ENDPOINT:
        return AGENTARTS_CONTROL_ENDPOINT
    region = region or get_region()
    return f"https://agentarts.{region}.myhuaweicloud.com"


def get_data_plane_endpoint() -> str:
    """Get the AgentRun data plane endpoint URL."""
    return AGENTARTS_RUNTIME_DATA_ENDPOINT


def get_swr_endpoint(region: str = None) -> str:
    """Get the SWR endpoint URL for the specified region."""
    if SWR_ENDPOINT:
        return SWR_ENDPOINT
    region = region or get_region()
    return f"https://swr-api.{region}.myhuaweicloud.com"


def get_iam_endpoint(region: str = None) -> str:
    """Get the IAM endpoint URL for the specified region."""
    if IAM_ENDPOINT:
        return IAM_ENDPOINT
    region = region or get_region()
    return f"https://iam.{region}.myhuaweicloud.com"


def get_memory_endpoint(endpoint_type: str = "control", region: str = None, space_id: str = None) -> str:
    """Get the Memory API endpoint URL.
    
    Args:
        endpoint_type: "control" for management plane, "data" for data plane
        region: Huawei Cloud region name
        space_id: Space ID for data plane endpoint construction
        
    Returns:
        Memory API endpoint URL
        
    Raises:
        ValueError: If endpoint_type is "data" but space_id is not provided
    """
    # 优先从环境变量读取端点地址
    if endpoint_type == "data":
        # 首先尝试从环境变量获取数据面端点
        if AGENTARTS_MEMORY_DATA_ENDPOINT:
            return AGENTARTS_MEMORY_DATA_ENDPOINT
        # 如果环境变量不存在，则构建数据面端点模板
        if not space_id:
            raise ValueError("space_id is required for data plane endpoint")
        region = region or get_region()
        return f"https://{space_id}.memory.{region}.agentarts.myhuaweicloud.com"
    else:
        # 首先尝试从环境变量获取控制面端点
        if AGENTARTS_CONTROL_ENDPOINT:
            return AGENTARTS_CONTROL_ENDPOINT
        # 如果环境变量不存在，则使用现有的获取方法
        region = region or get_region()
        return f"https://memory.{region}.myhuaweicloud.com"
