"""Runtime control-plane CRUD tests.

Two ways to supply the target agent — either is enough, so environment issues
(Docker unavailable) don't block this module:

  * **standalone**: set ``AGENTARTS_TEST_RUNTIME_AGENT_NAME`` to a
    pre-provisioned agent — no Docker, no deploy, no billable.
  * **reuse**: with no env var, fall back to the shared
    ``deployed_runtime_agent`` fixture (Docker + ALLOW_CREATE + RUN_BILLABLE),
    which `agentarts deploy`s one.

The agent itself is NOT created/deleted here — `create_agent` needs an
`artifact_source_config` (a built image), which only `deploy` provides; that
path is covered transitively by the deploy fixture. These tests exercise
find/get/update + endpoint CRUD against an existing agent. The endpoint is
created and cleaned up via `resource_registry`; the agent is left intact
(owned by the env var, or by the deploy fixture's session-end teardown).

Requires ALLOW_CREATE (writes: update_agent + endpoint CRUD) in both modes.
"""

from __future__ import annotations

import os

import pytest

from tests.integration._helpers import ENV_RUN_BILLABLE, ENV_RUNTIME_AGENT_NAME, env_truthy, unique_name

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def runtime_agent(request, runtime_client, cloud_credentials, allow_create, resource_registry):
    name = os.getenv(ENV_RUNTIME_AGENT_NAME)
    if name:
        mode = "standalone"
    else:
        if not env_truthy(ENV_RUN_BILLABLE):
            pytest.skip(
                "Set AGENTARTS_TEST_RUNTIME_AGENT_NAME (standalone, no Docker) or "
                "AGENTARTS_TEST_RUN_BILLABLE=1 + Docker (reuse deploy) to run "
                "runtime-agent CRUD"
            )
        deployed = request.getfixturevalue("deployed_runtime_agent")
        name = deployed["name"]
        mode = "reuse"

    agent = runtime_client.find_agent_by_name(name)
    assert agent, (
        f"agent {name!r} not found in region {cloud_credentials['region']} "
        f"(mode={mode})"
    )
    return {"name": name, "id": agent["id"], "mode": mode}


@pytest.fixture(scope="module")
def created_endpoint(runtime_client, runtime_agent, run_id, resource_registry):
    ep_name = unique_name("ep", run_id)
    runtime_client.create_agent_endpoint(
        agent_id=runtime_agent["id"], endpoint_name=ep_name
    )
    resource_registry.register(
        lambda: runtime_client.delete_agent_endpoint(runtime_agent["id"], ep_name),
        f"endpoint:{ep_name}",
    )
    return ep_name


# --------------------------------------------------------------------------- #
# Agent read / update
# --------------------------------------------------------------------------- #
def test_find_agent_by_name(runtime_client, runtime_agent):
    found = runtime_client.find_agent_by_name(runtime_agent["name"])
    assert found is not None
    assert found["id"] == runtime_agent["id"]


def test_find_agent_by_id(runtime_client, runtime_agent):
    found = runtime_client.find_agent_by_id(runtime_agent["id"])
    assert found is not None
    assert found["id"] == runtime_agent["id"]


def test_get_agents(runtime_client, runtime_agent):
    agents = runtime_client.get_agents(limit=1)
    assert isinstance(agents, list)


def test_update_agent(runtime_client, runtime_agent):
    updated = runtime_client.update_agent(
        runtime_agent["id"], description="updated by aa-it"
    )
    assert updated["id"] == runtime_agent["id"]


# --------------------------------------------------------------------------- #
# Endpoint CRUD
# --------------------------------------------------------------------------- #
def test_find_agent_endpoint(runtime_client, runtime_agent, created_endpoint):
    ep = runtime_client.find_agent_endpoint(runtime_agent["id"], created_endpoint)
    assert isinstance(ep, dict)


def test_update_agent_endpoint(runtime_client, runtime_agent, created_endpoint):
    ep = runtime_client.update_agent_endpoint(
        agent_id=runtime_agent["id"],
        endpoint_name=created_endpoint,
        config={"note": "updated by aa-it"},
    )
    assert isinstance(ep, dict)
