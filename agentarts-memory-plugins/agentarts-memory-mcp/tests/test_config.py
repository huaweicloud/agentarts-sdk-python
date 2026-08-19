"""Tests for environment-backed server settings."""

import pytest

from agentarts_memory_mcp.config import (
    ENV_ACTOR_ID,
    ENV_API_KEY,
    ENV_ASSISTANT_ID,
    ENV_REGION,
    ENV_SPACE_ID,
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
        }
    )

    assert settings == ServerSettings(
        api_key="api-key",
        space_id="space-id",
        region="cn-north-4",
        actor_id="actor-id",
        assistant_id="assistant-id",
    )


def test_from_env_uses_sdk_region_default_when_region_is_absent() -> None:
    settings = ServerSettings.from_env(
        {
            ENV_API_KEY: "api-key",
            ENV_SPACE_ID: "space-id",
        }
    )

    assert settings.region is None
    assert settings.actor_id is None
    assert settings.assistant_id is None


@pytest.mark.parametrize(
    ("environ", "missing_name"),
    [
        ({ENV_SPACE_ID: "space-id"}, ENV_API_KEY),
        ({ENV_API_KEY: "api-key"}, ENV_SPACE_ID),
        ({ENV_API_KEY: " ", ENV_SPACE_ID: "space-id"}, ENV_API_KEY),
    ],
)
def test_from_env_reports_missing_variable_names_without_values(
    environ: dict[str, str],
    missing_name: str,
) -> None:
    with pytest.raises(ConfigurationError) as raised:
        ServerSettings.from_env(environ)

    assert missing_name in str(raised.value)
    assert "api-key" not in str(raised.value)
