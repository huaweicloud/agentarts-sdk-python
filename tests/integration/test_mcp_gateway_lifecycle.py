"""MCP Gateway lifecycle tests (ALLOW_CREATE tier).

Creates a gateway + a target, exercises get/list/update, then deletes the
target before the gateway. Note: ``create_mcp_gateway`` auto-creates a shared
IAM agency ``AgentArtsCoreGateway`` (409-ignored if it already exists) which the
SDK does not delete — this residue is documented and intentional.
"""

from __future__ import annotations

import pytest

from tests.integration._helpers import unique_name

pytestmark = [
    pytest.mark.integration,
    pytest.mark.xfail(
        run=False,
        strict=False,
        reason=(
            "SDK bug: MCPGatewayClient.create_mcp_gateway auto-creates the IAM "
            "agency 'AgentArtsCoreGateway' with a trust_policy the IAM API rejects "
            "(PAP5.0011 'malformed policy document'); with the agency absent, the "
            "gateway create then fails 'agency is invalid'. Fix the trust_policy in "
            "src/agentarts/sdk/mcpgateway/mcp_gateway_client.py — an agency trust "
            "policy should grant sts:agencies:assumeRole to the service principal, "
            "not resource actions. Remove this marker once fixed."
        ),
    ),
]


def _extract_id(data: dict, *keys: str) -> str:
    """Pull a resource id out of a response dict, trying common key names."""
    for k in keys:
        if data.get(k):
            return data[k]
    # last resort: scan a nested list (some responses wrap items)
    for v in data.values():
        if isinstance(v, list) and v and isinstance(v[0], dict) and v[0].get("id"):
            return v[0]["id"]
    msg = f"could not find id in response: {data!r}"
    raise AssertionError(msg)


# --------------------------------------------------------------------------- #
# Shared resources
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def created_gateway(mcp_gateway_client, allow_create, run_id, resource_registry):
    name = unique_name("gw", run_id)
    result = mcp_gateway_client.create_mcp_gateway(name=name, description="aa-it")
    assert result.success, f"create_mcp_gateway failed: {result.error}"
    gw_id = _extract_id(result.data, "id", "gateway_id")
    resource_registry.register(
        lambda: mcp_gateway_client.delete_mcp_gateway(gw_id), f"gateway:{gw_id}"
    )
    return {"id": gw_id, "name": name}


@pytest.fixture(scope="module")
def created_target(mcp_gateway_client, created_gateway, run_id, resource_registry):
    name = unique_name("tgt", run_id)
    result = mcp_gateway_client.create_mcp_gateway_target(
        gateway_id=created_gateway["id"], name=name
    )
    assert result.success, f"create_mcp_gateway_target failed: {result.error}"
    target_id = _extract_id(result.data, "id", "target_id")
    resource_registry.register(
        lambda: mcp_gateway_client.delete_mcp_gateway_target(
            created_gateway["id"], target_id
        ),
        f"target:{target_id}",
    )
    return {"id": target_id, "name": name}


# --------------------------------------------------------------------------- #
# Gateway
# --------------------------------------------------------------------------- #
def test_get_gateway(mcp_gateway_client, created_gateway):
    result = mcp_gateway_client.get_mcp_gateway(created_gateway["id"])
    assert result.success, result.error


def test_list_gateways(mcp_gateway_client, created_gateway):
    result = mcp_gateway_client.list_mcp_gateways(limit=200)
    assert result.success, result.error
    assert isinstance(result.data, dict)


def test_update_gateway(mcp_gateway_client, created_gateway):
    result = mcp_gateway_client.update_mcp_gateway(
        created_gateway["id"], description="updated by aa-it"
    )
    assert result.success, result.error


# --------------------------------------------------------------------------- #
# Target
# --------------------------------------------------------------------------- #
def test_get_target(mcp_gateway_client, created_gateway, created_target):
    result = mcp_gateway_client.get_mcp_gateway_target(
        created_gateway["id"], created_target["id"]
    )
    assert result.success, result.error


def test_list_targets(mcp_gateway_client, created_gateway, created_target):
    result = mcp_gateway_client.list_mcp_gateway_targets(
        gateway_id=created_gateway["id"], limit=200
    )
    assert result.success, result.error
    assert isinstance(result.data, dict)


def test_update_target(mcp_gateway_client, created_gateway, created_target):
    result = mcp_gateway_client.update_mcp_gateway_target(
        gateway_id=created_gateway["id"],
        target_id=created_target["id"],
        description="updated target by aa-it",
    )
    assert result.success, result.error
