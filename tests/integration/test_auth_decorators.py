"""Auth decorator tests (ALLOW_CREATE tier).

Exercises the real ``require_api_key`` / ``require_sts_token`` decorators
end-to-end against the shared workload identity + credential providers. The
decorators' local-auth bootstrap persists ``.agent_identity.json``; the
``isolated_identity_config`` fixture chdir's into a temp dir so the repo is
never polluted, and a pre-seeded ``Config`` makes the bootstrap reuse the
session workload identity (no extra create).

The OAuth2 ``require_access_token`` flow is a 3-legged interactive round trip
and is intentionally skipped here (covered by unit tests for wiring; e2e 3LO
is a manual exercise).
"""

from __future__ import annotations

import pytest

from agentarts.sdk import require_api_key, require_sts_token
from agentarts.sdk.identity.config import Config

pytestmark = pytest.mark.integration


@pytest.fixture
def seeded_identity_config(
    created_workload_identity, isolated_identity_config
):
    """Pre-seed .agent_identity.json so the decorator reuses the session WI."""
    Config(
        workload_identity_name=created_workload_identity["name"],
        user_id="aa-it-auth",
    ).save()
    return isolated_identity_config


def test_require_api_key_injects_key(
    created_api_key_provider, seeded_identity_config
):
    captured: dict = {}

    @require_api_key(provider_name=created_api_key_provider, into="api_key")
    def handler(payload, api_key=None):  # noqa: ANN001
        captured["api_key"] = api_key
        return {"ok": True}

    result = handler({"x": 1})
    assert result == {"ok": True}
    assert isinstance(captured["api_key"], str) and captured["api_key"]


@pytest.fixture
def sts_provider_for_auth(
    identity_client, allow_create, run_id, sts_agency_urn, identity_cleanup, resource_registry
):
    from tests.integration._helpers import unique_name

    name = unique_name("cp-sts", run_id)
    identity_client.create_sts_credential_provider(name=name, agency_urn=sts_agency_urn)
    resource_registry.register(
        lambda: identity_cleanup.credential_provider("sts", name),
        f"credential_provider:sts:{name}",
    )
    return name


def test_require_sts_token_injects_credentials(
    sts_provider_for_auth, seeded_identity_config
):
    @require_sts_token(
        provider_name=sts_provider_for_auth,
        agency_session_name="aa-it-session",
    )
    def handler(sts_credentials=None):  # noqa: ANN001
        return sts_credentials

    creds = handler()
    assert creds is not None
    assert getattr(creds, "access_key_id", None)
    assert getattr(creds, "secret_access_key", None)


@pytest.mark.slow
def test_require_access_token_3lo_is_manual(seeded_identity_config):
    """OAuth2 3LO requires an interactive browser round trip — skip in CI."""
    pytest.skip(
        "require_access_token (OAuth2 3LO) is interactive; run manually with "
        "AGENTARTS_TEST_OAUTH2_* and an on_auth_url callback"
    )
