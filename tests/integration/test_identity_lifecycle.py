"""Identity lifecycle tests (ALLOW_CREATE tier).

Creates a workload identity + an API-key credential provider, exercises
get/list/update and ephemeral token issuance (``create_workload_access_token``,
``get_resource_api_key``), then tears everything down via the raw
``AgentIdentityClient.delete_*`` methods (the high-level wrapper has no delete).

OAuth2 / STS credential-provider flows need external inputs (vendor creds,
agency URN) and are conditionally skipped otherwise.
"""

from __future__ import annotations

import os

import pytest

from tests.integration._helpers import unique_name

pytestmark = pytest.mark.integration

# --------------------------------------------------------------------------- #
# Workload identity + api-key credential provider are session-scoped fixtures
# in conftest (shared with the auth-decorator module); created once, cleaned up
# once at session end via the raw AgentIdentityClient.delete_* methods.
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# Workload identity
# --------------------------------------------------------------------------- #
def test_get_created_workload_identity(identity_client, created_workload_identity):
    wi = identity_client.get_workload_identity(created_workload_identity["name"])
    assert wi is not None
    assert getattr(wi, "name", None) == created_workload_identity["name"]


def test_update_workload_identity(identity_client, created_workload_identity):
    wi = identity_client.update_workload_identity(
        created_workload_identity["name"],
        allowed_resource_oauth2_return_urls=["https://example.com/callback"],
    )
    assert wi is not None


def test_list_workload_identities_contains_created(
    identity_client, created_workload_identity
):
    # limit=200 to keep it a single cheap call while covering the common case
    items = identity_client.list_workload_identities(limit=200)
    names = [getattr(it, "name", None) for it in items]
    assert created_workload_identity["name"] in names


# --------------------------------------------------------------------------- #
# API-key credential provider
# --------------------------------------------------------------------------- #
def test_get_api_key_credential_provider(identity_client, created_api_key_provider):
    cp = identity_client.get_api_key_credential_provider(created_api_key_provider)
    assert cp is not None
    assert getattr(cp, "name", None) == created_api_key_provider


def test_list_api_key_credential_providers_contains_created(
    identity_client, created_api_key_provider
):
    items = identity_client.list_api_key_credential_providers(limit=200)
    names = [getattr(it, "name", None) for it in items]
    assert created_api_key_provider in names


# --------------------------------------------------------------------------- #
# Ephemeral token issuance (no persistent resource)
# --------------------------------------------------------------------------- #
def test_create_workload_access_token(identity_client, created_workload_identity):
    token = identity_client.create_workload_access_token(
        created_workload_identity["name"], user_id="aa-it-token-user"
    )
    assert isinstance(token, str) and token


def test_get_resource_api_key(
    identity_client, created_workload_identity, created_api_key_provider
):
    access_token = identity_client.create_workload_access_token(
        created_workload_identity["name"], user_id="aa-it-token-user"
    )
    api_key = identity_client.get_resource_api_key(
        provider_name=created_api_key_provider,
        workload_access_token=access_token,
    )
    assert isinstance(api_key, str) and api_key


# --------------------------------------------------------------------------- #
# Conditionally-skipped OAuth2 / STS provider flows
# --------------------------------------------------------------------------- #
@pytest.fixture
def oauth2_provider_inputs():
    cid = os.getenv("AGENTARTS_TEST_OAUTH2_CLIENT_ID")
    csec = os.getenv("AGENTARTS_TEST_OAUTH2_CLIENT_SECRET")
    vendor = os.getenv("AGENTARTS_TEST_OAUTH2_VENDOR", "GITHUBOAUTH2")
    if not cid or not csec:
        pytest.skip(
            "Set AGENTARTS_TEST_OAUTH2_CLIENT_ID / _CLIENT_SECRET / _VENDOR "
            "to exercise OAuth2 credential-provider lifecycle"
        )
    return cid, csec, vendor


@pytest.mark.slow
def test_create_and_delete_oauth2_credential_provider(
    identity_client, allow_create, run_id, oauth2_provider_inputs, identity_cleanup, resource_registry
):
    from agentarts.sdk.identity.types import OAuth2Vendor

    cid, csec, vendor = oauth2_provider_inputs
    name = unique_name("cp-oa", run_id)
    identity_client.create_oauth2_credential_provider(
        name=name,
        vendor=OAuth2Vendor[vendor],
        client_id=cid,
        client_secret=csec,
    )
    resource_registry.register(
        lambda: identity_cleanup.credential_provider("oauth2", name),
        f"credential_provider:oauth2:{name}",
    )
    cp = identity_client.get_oauth2_credential_provider(name)
    assert getattr(cp, "name", None) == name


def test_create_and_delete_sts_credential_provider(
    identity_client, allow_create, run_id, sts_agency_urn, identity_cleanup, resource_registry
):
    name = unique_name("cp-sts", run_id)
    identity_client.create_sts_credential_provider(name=name, agency_urn=sts_agency_urn)
    resource_registry.register(
        lambda: identity_cleanup.credential_provider("sts", name),
        f"credential_provider:sts:{name}",
    )
    cp = identity_client.get_sts_credential_provider(name)
    assert getattr(cp, "name", None) == name
