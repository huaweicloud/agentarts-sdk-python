"""Read-only identity tests (default tier).

Exercise the ``IdentityClient`` list/get surface and ephemeral token issuance
without creating any persistent cloud resource. Requires AK/SK; the optional
``AGENTARTS_TEST_WORKLOAD_IDENTITY_NAME`` adds a get + workload-access-token
assertion against a pre-provisioned identity.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_list_workload_identities(identity_client):
    items = identity_client.list_workload_identities(limit=1)
    assert isinstance(items, list)


def test_list_api_key_credential_providers(identity_client):
    items = identity_client.list_api_key_credential_providers(limit=1)
    assert isinstance(items, list)


def test_list_oauth2_credential_providers(identity_client):
    items = identity_client.list_oauth2_credential_providers(limit=1)
    assert isinstance(items, list)


def test_list_sts_credential_providers(identity_client):
    items = identity_client.list_sts_credential_providers(limit=1)
    assert isinstance(items, list)


def test_get_and_token_for_preprovisioned_workload_identity(
    identity_client, pre_workload_identity
):
    """get_workload_identity + create_workload_access_token (ephemeral, no residue)."""
    wi = identity_client.get_workload_identity(pre_workload_identity)
    assert wi is not None
    assert getattr(wi, "name", None) == pre_workload_identity

    token = identity_client.create_workload_access_token(
        pre_workload_identity, user_id="aa-it-reader"
    )
    assert isinstance(token, str) and token
