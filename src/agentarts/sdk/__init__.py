"""
Huawei Cloud AgentArts SDK

Build, deploy and manage AI agents with cloud capabilities.

Quick Start:
    # Runtime
    from agentarts.sdk import AgentArtsRuntimeApp, RequestContext
    app = AgentArtsRuntimeApp()

    # Tools
    from agentarts.sdk import CodeInterpreter, code_session

    # Memory
    from agentarts.sdk import MemoryClient

    # MCP Gateway
    from agentarts.sdk import MCPGatewayClient

    # Identity
    from agentarts.sdk import require_access_token, require_api_key, IdentityClient
"""

import warnings

import urllib3

warnings.filterwarnings("ignore", message="Unverified HTTPS request")
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

from agentarts.sdk.utils.logging import setup_logging

setup_logging()

from agentarts import __author__, __version__
from agentarts.sdk.identity import (
    IdentityClient,
    require_access_token,
    require_api_key,
    require_sts_token,
)
from agentarts.sdk.mcpgateway import MCPGatewayClient
from agentarts.sdk.memory import MemoryClient
from agentarts.sdk.runtime.app import AgentArtsRuntimeApp
from agentarts.sdk.runtime.context import AgentArtsRuntimeContext, RequestContext
from agentarts.sdk.runtime.model import PingStatus
from agentarts.sdk.tools import CodeInterpreter, code_session

__all__ = [
    "AgentArtsRuntimeApp",
    "AgentArtsRuntimeContext",
    "CodeInterpreter",
    "IdentityClient",
    "MCPGatewayClient",
    "MemoryClient",
    "PingStatus",
    "RequestContext",
    "__author__",
    "__version__",
    "code_session",
    "require_access_token",
    "require_api_key",
    "require_sts_token",
]
