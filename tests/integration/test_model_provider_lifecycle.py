"""Model provider lifecycle tests (ALLOW_CREATE tier).

Creates a model provider + a model + a model proxy, exercises get/list/update,
then tears down: the proxy is unbound via batch disassociation, the model and
the provider are deleted (registered with the session-scoped
``resource_registry``, LIFO at session end). Note: the model proxy reuses the
shared IAM agency ``AgentArtsCoreGateway`` which the SDK intentionally does
not delete — this residue is documented and intentional (same as the gateway
lifecycle suite).
"""

from __future__ import annotations

import pytest

from tests.integration._helpers import unique_name

pytestmark = pytest.mark.integration


def _extract_id(data: dict, *keys: str) -> str:
    """Pull a resource id out of a response dict, trying common shapes:
    top-level ``id``/``gateway_id``/... keys, or the first item of a list."""
    for k in keys:
        if data.get(k):
            return data[k]
    for v in data.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and v[0].get("id"):
            return v[0]["id"]
    msg = f"could not find id in response: {data!r}"
    raise AssertionError(msg)


# Minimal api_key credential configuration (no real secrets involved).
_CREDENTIAL_CONFIGURATION = {
    "provider_configuration": {
        "credential_provider_type": "api_key",
        "credential_provider": {
            "api_key_credential_provider": {
                "provider_name": "aa-it-key",
                "credential_location": "header",
            }
        },
    }
}


# --------------------------------------------------------------------------- #
# Shared resources
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def created_model_provider(cloud_credentials, allow_create, run_id, resource_registry):
    from agentarts.sdk import CustomModelProviderClient

    client = CustomModelProviderClient()
    name = unique_name("mp", run_id)
    result = client.create_model_provider(
        name=name,
        base_url="https://example.com/v1",
        credential_configuration=_CREDENTIAL_CONFIGURATION,
    )
    assert result.success, f"create_model_provider failed: {result.error}"
    provider_id = _extract_id(result.data, "id")
    resource_registry.register(
        lambda: client.delete_model_provider(provider_id), f"model_provider:{provider_id}"
    )
    return {"id": provider_id, "name": name}


@pytest.fixture(scope="module")
def created_model(created_model_provider, cloud_credentials, allow_create, run_id, resource_registry):
    from agentarts.sdk import CustomModelProviderClient

    client = CustomModelProviderClient()
    service_name = unique_name("model", run_id)
    result = client.create_model(
        model_provider_id=created_model_provider["id"],
        model="qwen2.5-72b",
        model_service_name=service_name,
        type_=["completions"],
        protocol="openai",
    )
    assert result.success, f"create_model failed: {result.error}"
    model_id = _extract_id(result.data, "id")
    resource_registry.register(
        lambda: client.delete_model(created_model_provider["id"], model_id),
        f"model:{model_id}",
    )
    return {"id": model_id, "model_service_name": service_name}


@pytest.fixture(scope="module")
def created_model_proxy(created_model_provider, cloud_credentials, allow_create, resource_registry):
    from agentarts.sdk import CustomModelProviderClient

    client = CustomModelProviderClient()
    result = client.create_model_proxy(
        custom_model_provider_id=created_model_provider["id"],
        agency_name="AgentArtsCoreGateway",
    )
    assert result.success, f"create_model_proxy failed: {result.error}"
    gateway_id = _extract_id(result.data, "gateway_id", "id")
    resource_registry.register(
        lambda: client.batch_disassociate_model_proxies(
            unbindings=[{
                "custom_model_provider_id": created_model_provider["id"],
                "gateway_id": gateway_id,
            }]
        ),
        f"model_proxy:{gateway_id}",
    )
    return {"id": gateway_id}


# --------------------------------------------------------------------------- #
# Model provider
# --------------------------------------------------------------------------- #
def test_get_model_provider(model_provider_client, created_model_provider):
    result = model_provider_client.get_model_provider(created_model_provider["id"])
    assert result.success, result.error


def test_list_model_providers(model_provider_client, created_model_provider):
    # limit capped at 100 by the backend
    result = model_provider_client.list_model_providers(limit=100)
    assert result.success, result.error
    assert isinstance(result.data, dict)


def test_update_model_provider(model_provider_client, created_model_provider):
    result = model_provider_client.update_model_provider(
        created_model_provider["id"], description="updated by aa-it"
    )
    assert result.success, result.error


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #
def test_get_model(model_provider_client, created_model_provider, created_model):
    result = model_provider_client.get_model(
        created_model_provider["id"], created_model["id"]
    )
    assert result.success, result.error


def test_list_models(model_provider_client, created_model_provider, created_model):
    result = model_provider_client.list_models(
        model_provider_id=created_model_provider["id"], limit=100
    )
    assert result.success, result.error
    assert isinstance(result.data, dict)


def test_update_model(model_provider_client, created_model_provider, created_model):
    result = model_provider_client.update_model(
        model_provider_id=created_model_provider["id"],
        model_id=created_model["id"],
        description="updated model by aa-it",
    )
    assert result.success, result.error


# --------------------------------------------------------------------------- #
# Model proxy
# --------------------------------------------------------------------------- #
def test_update_model_proxy(model_provider_client, created_model_proxy):
    result = model_provider_client.update_model_proxy(
        gateway_id=created_model_proxy["id"],
        tags=[{"key": "Environment", "value": "test"}],
    )
    assert result.success, result.error


# --------------------------------------------------------------------------- #
# Model management quotas
# --------------------------------------------------------------------------- #
def test_list_model_management_quotas(model_provider_client, created_model_provider):
    result = model_provider_client.list_model_management_quotas(
        custom_model_provider_id=created_model_provider["id"]
    )
    assert result.success, result.error
    assert isinstance(result.data, dict)
