"""Gateway lifecycle tests (ALLOW_CREATE tier).

Creates a gateway + a target, exercises get/list/update, then deletes the
target before the gateway. Note: ``create_gateway`` auto-creates a shared IAM
agency ``AgentArtsCoreGateway`` (409-ignored if it already exists) which the
SDK intentionally does not delete — this residue is documented and intentional.

The earlier xfail (IAM `trust_policy` rejected, PAP5.0011) was resolved upstream
by `create_agency_with_policy` (auto policy attachment); the marker is removed.
"""

from __future__ import annotations

import pytest

from tests.integration._helpers import unique_name

pytestmark = pytest.mark.integration


def _extract_id(data: dict, *keys: str) -> str:
    """Pull a resource id out of a response dict, trying common shapes:
    top-level ``id``/``gateway_id``/``target_id``, nested ``data["gateway"]``/
    ``data["target"]``, or the first item of a list."""
    for k in keys:
        if data.get(k):
            return data[k]
    for nested in ("gateway", "target"):
        obj = data.get(nested)
        if isinstance(obj, dict):
            for k in keys:
                if obj.get(k):
                    return obj[k]
    for v in data.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and v[0].get("id"):
            return v[0]["id"]
    msg = f"could not find id in response: {data!r}"
    raise AssertionError(msg)


# --------------------------------------------------------------------------- #
# Shared resources
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def created_gateway(gateway_client, allow_create, run_id, resource_registry):
    name = unique_name("gw", run_id)
    result = gateway_client.create_gateway(name=name, description="aa-it")
    assert result.success, f"create_gateway failed: {result.error}"
    gw_id = _extract_id(result.data, "id", "gateway_id")
    resource_registry.register(
        lambda: gateway_client.delete_gateway(gw_id), f"gateway:{gw_id}"
    )
    return {"id": gw_id, "name": name}


@pytest.fixture(scope="module")
def created_target(gateway_client, created_gateway, run_id, resource_registry):
    name = unique_name("tgt", run_id)
    result = gateway_client.create_gateway_target(
        gateway_id=created_gateway["id"],
        name=name,
        target_configuration={
            "mcp_server": {"endpoint": "https://example.com/mcp", "server_type": "sse"}
        },
    )
    assert result.success, f"create_gateway_target failed: {result.error}"
    target_id = _extract_id(result.data, "id", "target_id")
    resource_registry.register(
        lambda: gateway_client.delete_gateway_target(
            created_gateway["id"], target_id
        ),
        f"target:{target_id}",
    )
    return {"id": target_id, "name": name}


# --------------------------------------------------------------------------- #
# Gateway
# --------------------------------------------------------------------------- #
def test_get_gateway(gateway_client, created_gateway):
    result = gateway_client.get_gateway(created_gateway["id"])
    assert result.success, result.error


def test_list_gateways(gateway_client, created_gateway):
    # limit capped at 100 by the backend
    result = gateway_client.list_gateways(limit=100)
    assert result.success, result.error
    assert isinstance(result.data, dict)


def test_update_gateway(gateway_client, created_gateway):
    result = gateway_client.update_gateway(
        created_gateway["id"], description="updated by aa-it"
    )
    assert result.success, result.error


# --------------------------------------------------------------------------- #
# Target
# --------------------------------------------------------------------------- #
def test_get_target(gateway_client, created_gateway, created_target):
    result = gateway_client.get_gateway_target(
        created_gateway["id"], created_target["id"]
    )
    assert result.success, result.error


def test_list_targets(gateway_client, created_gateway, created_target):
    result = gateway_client.list_gateway_targets(
        gateway_id=created_gateway["id"], limit=100
    )
    assert result.success, result.error
    assert isinstance(result.data, dict)


def test_update_target(gateway_client, created_gateway, created_target):
    result = gateway_client.update_gateway_target(
        gateway_id=created_gateway["id"],
        target_id=created_target["id"],
        description="updated target by aa-it",
    )
    assert result.success, result.error
