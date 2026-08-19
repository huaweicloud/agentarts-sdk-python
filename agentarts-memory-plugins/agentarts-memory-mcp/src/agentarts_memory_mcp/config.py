"""Environment-backed configuration for the memory server."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

ENV_API_KEY = "HUAWEICLOUD_SDK_MEMORY_API_KEY"
ENV_SPACE_ID = "AGENTARTS_MEMORY_SPACE_ID"
ENV_ACTOR_ID = "AGENTARTS_MEMORY_ACTOR_ID"
ENV_ASSISTANT_ID = "AGENTARTS_MEMORY_ASSISTANT_ID"
ENV_REGION = "HUAWEICLOUD_SDK_REGION"


class ConfigurationError(ValueError):
    """Raised when required memory-server configuration is absent or invalid."""


@dataclass(frozen=True)
class ServerSettings:
    """Validated configuration read once before the MCP server starts."""

    api_key: str
    space_id: str
    region: str | None = None
    actor_id: str | None = None
    assistant_id: str | None = None

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> ServerSettings:
        """Build settings from SDK-compatible environment variables."""
        values = os.environ if environ is None else environ
        api_key = values.get(ENV_API_KEY, "").strip()
        space_id = values.get(ENV_SPACE_ID, "").strip()

        missing = [
            name for name, value in ((ENV_API_KEY, api_key), (ENV_SPACE_ID, space_id)) if not value
        ]
        if missing:
            names = ", ".join(missing)
            message = f"Missing required environment variable(s): {names}"
            raise ConfigurationError(message)

        region = values.get(ENV_REGION, "").strip() or None
        actor_id = values.get(ENV_ACTOR_ID, "").strip() or None
        assistant_id = values.get(ENV_ASSISTANT_ID, "").strip() or None
        return cls(
            api_key=api_key,
            space_id=space_id,
            region=region,
            actor_id=actor_id,
            assistant_id=assistant_id,
        )
