"""
AgentArts Identity Module

Provides authentication, authorization, and multi-tenant support.

Usage:
    from agentarts.sdk.identity import require_access_token, require_api_key, IdentityClient
"""

from agentarts.sdk.identity.auth import (
    require_access_token,
    require_api_key,
    require_sts_token,
)
from agentarts.sdk.service.identity.identity_client import IdentityClient

__all__ = [
    "require_access_token",
    "require_api_key",
    "require_sts_token",
    "IdentityClient",
]
