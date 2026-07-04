"""Gateway CLI e2e tests.

Invokes the real `agentarts gateway` CLI via subprocess. Read-only `gateway
list` runs in the default tier; the gateway create lifecycle (ALLOW_CREATE)
exercises the auto-IAM-agency path (now fixed upstream via
`create_agency_with_policy`).
"""

from __future__ import annotations

import subprocess

import pytest

pytestmark = pytest.mark.integration


def _run(agentarts_cmd, cli_env, args, timeout=120):
    return subprocess.run(
        agentarts_cmd + args, capture_output=True, text=True, env=cli_env, timeout=timeout
    )


def test_cli_gateway_list_readonly(agentarts_cmd, cli_env, cloud_credentials):
    """Read-only `gateway list` — no resources created (default tier)."""
    r = _run(agentarts_cmd, cli_env, ["gateway", "list", "--limit", "1"])
    assert r.returncode == 0, r.stderr


def test_cli_gateway_create(
    agentarts_cmd, cli_env, cloud_credentials, allow_create, run_id, resource_registry
):
    """`gateway create` exercises the auto-agency path end-to-end through the CLI."""
    from tests.integration._helpers import unique_name

    name = unique_name("cli-gw", run_id)
    r = _run(
        agentarts_cmd, cli_env,
        ["gateway", "create", "--name", name, "--description", "aa-it"],
    )
    assert r.returncode == 0, r.stderr
