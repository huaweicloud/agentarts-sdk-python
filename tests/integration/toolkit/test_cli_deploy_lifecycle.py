"""Full CLI lifecycle e2e: init → config → deploy → invoke → destroy.

This is the real user journey through the `agentarts` CLI, end-to-end and
non-mock. It is the heaviest test in the suite — gated behind Docker
availability, cloud credentials, ALLOW_CREATE, and RUN_BILLABLE — so it skips
by default and only runs when all prereqs are present.

Residue note: `deploy --mode cloud` auto-creates an SWR organization and
repository (organization_auto_create/repository_auto_create are true in the
init-generated config) and pushes an image. The operations layer exposes no
SWR org/repo/image deletion, so those persist — like the MCP shared agency,
this is accepted, documented residue. The cloud runtime (agent) IS destroyed
by `destroy`, and the local scaffold is in a temp dir (auto-cleaned).
"""

from __future__ import annotations

import os
import subprocess

import pytest

from tests.integration._helpers import unique_name

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def docker_available():
    r = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        pytest.skip("Docker daemon not available — required for `agentarts deploy`")
    return True


def _run(agentarts_cmd, cli_env, args, timeout=900):
    return subprocess.run(
        agentarts_cmd + args, capture_output=True, text=True, env=cli_env, timeout=timeout
    )


def test_cli_full_lifecycle(
    agentarts_cmd,
    cli_env,
    cli_runner,
    tmp_path,
    monkeypatch,
    cloud_credentials,
    allow_create,
    allow_billable,
    docker_available,
    run_id,
    resource_registry,
):
    from agentarts.toolkit.main import app

    region = cloud_credentials["region"]
    name = unique_name("agent", run_id)  # lowercase, satisfies agent-name rules
    swr_org = unique_name("swrorg", run_id)
    swr_repo = unique_name("swrrepo", run_id)

    monkeypatch.chdir(tmp_path)

    # 1. init — scaffold a basic project
    init = cli_runner.invoke(
        app, ["init", "-n", name, "-t", "basic", "-r", region]
    )
    assert init.exit_code == 0, init.output
    project = tmp_path / name
    assert (project / "agent.py").exists()
    assert (project / ".agentarts_config.yaml").exists()

    # 2. config — set entrypoint / region / SWR org+repo (writes .agentarts_config.yaml)
    monkeypatch.chdir(project)
    cfg = cli_runner.invoke(
        app, ["config", "-n", name, "-e", "agent:app", "-r", region,
              "-d", "requirements.txt", "--swr-org", swr_org, "--swr-repo", swr_repo]
    )
    assert cfg.exit_code == 0, cfg.output

    # 3. deploy — build image, push to SWR, create cloud runtime
    deploy = _run(agentarts_cmd, cli_env, ["deploy", "--agent", name, "--mode", "cloud"], timeout=900)
    assert deploy.returncode == 0, deploy.stderr or deploy.stdout

    # 4. safety net: always destroy the agent at session end, even if invoke fails
    resource_registry.register(
        lambda: _run(agentarts_cmd, cli_env,
                     ["destroy", "--agent", name, "--region", region, "--yes"], timeout=120),
        f"cli-deploy-agent:{name}",
    )

    # 5. invoke — data-plane call to the deployed agent
    invoke = _run(
        agentarts_cmd, cli_env,
        ["invoke", "--agent", name, "--mode", "cloud", '{"message": "hello from e2e"}'],
        timeout=900,
    )
    assert invoke.returncode == 0, invoke.stderr or invoke.stdout

    # 6. destroy — delete the cloud agent
    destroy = _run(
        agentarts_cmd, cli_env,
        ["destroy", "--agent", name, "--region", region, "--yes"], timeout=120,
    )
    assert destroy.returncode == 0, destroy.stderr or destroy.stdout

    # 7. local cleanup is automatic (tmp_path); SWR org/repo/image remain (documented residue)
