"""Environment-backed configuration for the AgentArts Memory MCP server."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from ..agentarts_client import DEFAULT_ASSISTANT_ID

ENV_API_KEY = "HUAWEICLOUD_SDK_MEMORY_API_KEY"
ENV_SPACE_ID = "AGENTARTS_MEMORY_SPACE_ID"
ENV_ACTOR_ID = "AGENTARTS_MEMORY_ACTOR_ID"
ENV_ASSISTANT_ID = "AGENTARTS_MEMORY_ASSISTANT_ID"
ENV_REGION = "HUAWEICLOUD_SDK_REGION"
ENV_USER_ID = "AGENTARTS_MEMORY_USER_ID"
ENV_PROJECT_NAME = "AGENTARTS_MEMORY_PROJECT_NAME"
ENV_PLATFORM = "AGENTARTS_MEMORY_PLATFORM"

_PLATFORM_ACTOR_ID = {
    "claude-code": "cc-user",
    "codex": "codex-user",
    "opencode": "opencode-user",
}


class ConfigurationError(ValueError):
    """Raised when required server configuration is absent or invalid."""


def _value(values: Mapping[str, str], name: str) -> str | None:
    """Return a stripped environment value, treating blanks as absent."""
    return values.get(name, "").strip() or None


def _detect_platform(values: Mapping[str, str]) -> str | None:
    """Resolve the host platform from explicit or host-provided variables."""
    if platform := _value(values, ENV_PLATFORM):
        return platform
    if _value(values, "CLAUDE_PLUGIN_ROOT"):
        return "claude-code"
    if _value(values, "CODEX_PLUGIN_ROOT"):
        return "codex"
    if _value(values, "OPENCODE_PLUGIN_ROOT"):
        return "opencode"
    return None


def _resolve_actor_id(values: Mapping[str, str]) -> str | None:
    """Resolve a process-bound actor while retaining legacy host defaults."""
    if actor_id := _value(values, ENV_ACTOR_ID):
        return actor_id
    if user_id := _value(values, ENV_USER_ID):
        return user_id
    platform = _detect_platform(values)
    if platform is not None:
        return _PLATFORM_ACTOR_ID.get(platform)
    return "__default__"


@dataclass(frozen=True)
class ServerSettings:
    """Validated configuration read once before the MCP server starts."""

    api_key: str
    space_id: str
    region: str | None = None
    actor_id: str | None = None
    assistant_id: str | None = None
    scope_id: str = "default"
    write_assistant_id: str = DEFAULT_ASSISTANT_ID

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> ServerSettings:
        """Build settings from SDK-compatible environment variables."""
        values = os.environ if environ is None else environ
        api_key = _value(values, ENV_API_KEY)
        space_id = _value(values, ENV_SPACE_ID)

        missing = [
            name
            for name, value in ((ENV_API_KEY, api_key), (ENV_SPACE_ID, space_id))
            if value is None
        ]
        if missing:
            names = ", ".join(missing)
            raise ConfigurationError(f"Missing required environment variable(s): {names}")
        assert api_key is not None
        assert space_id is not None

        assistant_id = _value(values, ENV_ASSISTANT_ID)
        return cls(
            api_key=api_key,
            space_id=space_id,
            region=_value(values, ENV_REGION),
            actor_id=_resolve_actor_id(values),
            assistant_id=assistant_id,
            scope_id=_value(values, ENV_PROJECT_NAME) or "default",
            write_assistant_id=assistant_id or DEFAULT_ASSISTANT_ID,
        )
