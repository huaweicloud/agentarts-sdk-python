"""Runtime control-plane lifecycle tests (ALLOW_CREATE tier).

Creates an agent + an endpoint on the AgentArts control plane, exercises
find/get/update, then deletes the endpoint and the agent. Data-plane invoke /
session lifecycle is in ``test_runtime_session_lifecycle.py`` (RUN_BILLABLE).

Note: the backend may require ``artifact_source_config`` (a built image) for a
fully-functional agent; this suite only verifies the SDK wrapper's CRUD path
with a minimal payload — set additional fields via the SDK if your backend
rejects a bare create.
"""

from __future__ import annotations

import pytest

from tests.integration._helpers import unique_name

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason=(
            "Backend rejects create_agent without artifact_source_config (a built "
            "image) and identity_configuration — 'artifactSource cannot be null' / "
            "'identityConfiguration.notnull'. Supply a deployable artifact to "
            "exercise this CRUD path; remove this skip when one is available."
        )
    ),
]


# --------------------------------------------------------------------------- #
# Shared resources
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def created_agent(runtime_client, allow_create, run_id, resource_registry):
    name = unique_name("agent", run_id)
    agent = runtime_client.create_agent(name=name, description="aa-it agent")
    agent_id = agent["id"]
    resource_registry.register(
        lambda: runtime_client.delete_agent_by_name(name), f"agent:{name}"
    )
    return {"id": agent_id, "name": name}


@pytest.fixture(scope="module")
def created_endpoint(runtime_client, created_agent, run_id, resource_registry):
    ep_name = unique_name("ep", run_id)
    runtime_client.create_agent_endpoint(
        agent_id=created_agent["id"], endpoint_name=ep_name
    )
    resource_registry.register(
        lambda: runtime_client.delete_agent_endpoint(created_agent["id"], ep_name),
        f"endpoint:{ep_name}",
    )
    return ep_name


# --------------------------------------------------------------------------- #
# Agent
# --------------------------------------------------------------------------- #
def test_find_agent_by_name(runtime_client, created_agent):
    found = runtime_client.find_agent_by_name(created_agent["name"])
    assert found is not None
    assert found["id"] == created_agent["id"]


def test_find_agent_by_id(runtime_client, created_agent):
    found = runtime_client.find_agent_by_id(created_agent["id"])
    assert found is not None
    assert found["id"] == created_agent["id"]


def test_get_agents(runtime_client, created_agent):
    agents = runtime_client.get_agents(limit=1)
    assert isinstance(agents, list)


def test_update_agent(runtime_client, created_agent):
    updated = runtime_client.update_agent(
        created_agent["id"], description="updated by aa-it"
    )
    assert updated["id"] == created_agent["id"]


# --------------------------------------------------------------------------- #
# Endpoint
# --------------------------------------------------------------------------- #
def test_find_agent_endpoint(runtime_client, created_agent, created_endpoint):
    ep = runtime_client.find_agent_endpoint(created_agent["id"], created_endpoint)
    assert isinstance(ep, dict)


def test_update_agent_endpoint(runtime_client, created_agent, created_endpoint):
    ep = runtime_client.update_agent_endpoint(
        agent_id=created_agent["id"],
        endpoint_name=created_endpoint,
        config={"note": "updated by aa-it"},
    )
    assert isinstance(ep, dict)
