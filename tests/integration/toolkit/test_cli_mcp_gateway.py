"""MCP Gateway CLI e2e tests.

Read-only `mcp-gateway list-mcp-gateways` runs in the default tier (no resources
created). The gateway+target lifecycle is xfailed: the SDK's `create_mcp_gateway`
auto-creates an IAM agency with a `trust_policy` the IAM API rejects (PAP5.0011).
On accounts where the shared agency already exists the path works (409-ignored),
masking the bug — see the sibling SDK test `test_mcp_gateway_lifecycle.py`.
"""

from __future__ import annotations

import subprocess

import pytest

pytestmark = pytest.mark.integration


def _run(agentarts_cmd, cli_env, args, timeout=120):
    return subprocess.run(
        agentarts_cmd + args, capture_output=True, text=True, env=cli_env, timeout=timeout
    )


def test_cli_mcp_gateway_list_readonly(agentarts_cmd, cli_env, cloud_credentials):
    """Read-only list — no resources created (default tier)."""
    r = _run(
        agentarts_cmd, cli_env,
        ["mcp-gateway", "list-mcp-gateways", "--limit", "1"],
    )
    assert r.returncode == 0, r.stderr


@pytest.mark.xfail(
    run=False,
    strict=False,
    reason=(
        "SDK bug (on accounts where the shared agency does not yet exist): "
        "create_mcp_gateway auto-creates IAM agency 'AgentArtsCoreGateway' with a "
        "trust_policy the IAM API rejects (PAP5.0011). See "
        "test_mcp_gateway_lifecycle.py for full detail. Remove once the "
        "trust_policy in src/agentarts/sdk/mcpgateway/mcp_gateway_client.py is fixed."
    ),
)
def test_cli_mcp_gateway_lifecycle(
    agentarts_cmd, cli_env, cloud_credentials, allow_create, run_id, resource_registry
):
    from tests.integration._helpers import unique_name

    name = unique_name("cli-gw", run_id)
    r = _run(agentarts_cmd, cli_env,
             ["mcp-gateway", "create-mcp-gateway", "--name", name, "--description", "aa-it"])
    assert r.returncode == 0, r.stderr
