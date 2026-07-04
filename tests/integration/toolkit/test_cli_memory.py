"""Memory CLI e2e tests.

Invokes the real `agentarts memory` CLI via subprocess (reliable stdout capture
for `--output json` parsing). The default region for the memory CLI is
cn-north-4, so `--region` is passed explicitly to match the account under test.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from tests.integration._helpers import unique_name

pytestmark = pytest.mark.integration


def _run(agentarts_cmd, cli_env, args, timeout=120):
    return subprocess.run(
        agentarts_cmd + args,
        capture_output=True,
        text=True,
        env=cli_env,
        timeout=timeout,
    )


def _extract_json(text: str) -> dict:
    """Pull the JSON object out of stdout (operation INFO logs precede it)."""
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                return json.loads(text[i:])
            except json.JSONDecodeError:
                continue
    msg = f"no JSON object found in output:\n{text!r}"
    raise AssertionError(msg)


def test_cli_memory_list_readonly(agentarts_cmd, cli_env, cloud_credentials):
    """Read-only `memory list` — no resources created (default tier)."""
    r = _run(
        agentarts_cmd, cli_env,
        ["memory", "list", "--limit", "1", "--region", cloud_credentials["region"]],
    )
    assert r.returncode == 0, r.stderr


def test_cli_memory_lifecycle(
    agentarts_cmd, cli_env, cloud_credentials, allow_create, run_id, resource_registry
):
    region = cloud_credentials["region"]
    name = unique_name("cli-space", run_id)

    # create (JSON output → extract space id)
    r = _run(
        agentarts_cmd, cli_env,
        ["memory", "create", name, "--strategies", "semantic",
         "--region", region, "--output", "json"],
    )
    assert r.returncode == 0, r.stderr
    space_id = _extract_json(r.stdout).get("id")
    assert space_id
    resource_registry.register(
        lambda: _run(agentarts_cmd, cli_env,
                     ["memory", "delete", space_id, "--force", "--region", region]),
        f"cli-space:{space_id}",
    )

    # list / get / update / delete through the CLI
    assert _run(agentarts_cmd, cli_env,
                ["memory", "list", "--limit", "1", "--region", region]).returncode == 0
    assert _run(agentarts_cmd, cli_env,
                ["memory", "get", space_id, "--region", region]).returncode == 0
    assert _run(agentarts_cmd, cli_env,
                ["memory", "update", space_id, "--description", "updated by cli",
                 "--region", region]).returncode == 0
    assert _run(agentarts_cmd, cli_env,
                ["memory", "delete", space_id, "--force", "--region", region]).returncode == 0
