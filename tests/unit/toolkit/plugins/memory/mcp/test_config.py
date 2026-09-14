"""Tests for environment-backed Memory MCP settings."""

from __future__ import annotations

import pytest

from agentarts.toolkit.plugins.memory.agentarts_client import DEFAULT_ASSISTANT_ID
from agentarts.toolkit.plugins.memory.mcp.config import (
    ENV_ACTOR_ID,
    ENV_API_KEY,
    ENV_ASSISTANT_ID,
    ENV_PLATFORM,
    ENV_PROJECT_NAME,
    ENV_REGION,
    ENV_SPACE_ID,
    ENV_USER_ID,
    ConfigurationError,
    ServerSettings,
)


def test_from_env_reads_required_and_optional_values() -> None:
    settings = ServerSettings.from_env(
        {
            ENV_API_KEY: " api-key ",
            ENV_SPACE_ID: " space-id ",
            ENV_ACTOR_ID: " actor-id ",
            ENV_ASSISTANT_ID: " assistant-id ",
            ENV_REGION: " cn-north-4 ",
            ENV_PROJECT_NAME: " project-a ",
        }
    )

    assert settings == ServerSettings(
        api_key="api-key",
        space_id="space-id",
        region="cn-north-4",
        actor_id="actor-id",
        assistant_id="assistant-id",
        scope_id="project-a",
        write_assistant_id="assistant-id",
    )


def test_from_env_uses_legacy_defaults() -> None:
    settings = ServerSettings.from_env({ENV_API_KEY: "key", ENV_SPACE_ID: "space"})

    assert settings.actor_id == "__default__"
    assert settings.scope_id == "default"
    assert settings.write_assistant_id == DEFAULT_ASSISTANT_ID


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ({ENV_PLATFORM: "codex"}, "codex-user"),
        ({ENV_PLATFORM: "claude-code"}, "cc-user"),
        ({ENV_PLATFORM: "opencode"}, "opencode-user"),
        ({ENV_USER_ID: "legacy-user", ENV_PLATFORM: "codex"}, "legacy-user"),
        (
            {
                ENV_ACTOR_ID: "explicit-actor",
                ENV_USER_ID: "legacy-user",
                ENV_PLATFORM: "codex",
            },
            "explicit-actor",
        ),
    ],
)
def test_actor_resolution_precedence(environment: dict[str, str], expected: str) -> None:
    settings = ServerSettings.from_env({ENV_API_KEY: "key", ENV_SPACE_ID: "space", **environment})

    assert settings.actor_id == expected


@pytest.mark.parametrize(
    ("environment", "missing_name"),
    [
        ({ENV_SPACE_ID: "space"}, ENV_API_KEY),
        ({ENV_API_KEY: "key"}, ENV_SPACE_ID),
        ({ENV_API_KEY: " ", ENV_SPACE_ID: "space"}, ENV_API_KEY),
    ],
)
def test_from_env_reports_missing_names_without_values(
    environment: dict[str, str], missing_name: str
) -> None:
    with pytest.raises(ConfigurationError) as raised:
        ServerSettings.from_env(environment)

    assert missing_name in str(raised.value)
    assert "key" not in str(raised.value)
