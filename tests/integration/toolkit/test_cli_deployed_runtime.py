"""CLI runtime e2e against a Docker-deployed agent (billable tier).

A single session-scoped `deployed_runtime_agent` fixture runs
`agentarts init → config → deploy` (Docker build + SWR push + cloud runtime
create) once; the tests below reuse that live agent, and `destroy` runs as the
fixture's session-end teardown. This pairs the B-class (invoke / runtime
session) tests with the C-class Docker deploy instead of requiring a
separately pre-provisioned agent.

Gated behind Docker + cloud_credentials + ALLOW_CREATE + RUN_BILLABLE, so it
skips by default. SWR org/repo/image persist (documented residue).

All CLI invokes run with cwd = the deployed project dir, so the CLI resolves
the data-plane endpoint from `.agentarts_config.yaml` + a control-plane lookup
(no `--endpoint` needed).
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_deploy_succeeds(deployed_runtime_agent):
    """The fixture's deploy created a cloud runtime; the config now carries an
    agent_id."""
    agent = deployed_runtime_agent
    cfg = (Path(agent["project_dir"]) / ".agentarts_config.yaml").read_text()
    assert "agent_id" in cfg  # deploy writes the created agent's id back to config
    assert agent["name"]


def test_invoke_deployed_agent(deployed_runtime_agent):
    agent = deployed_runtime_agent
    r = agent["run"](
        ["invoke", "--agent", agent["name"], "--mode", "cloud",
         '{"message": "hello from deployed e2e"}'],
        cwd=agent["project_dir"],
        timeout=900,
    )
    assert r.returncode == 0, r.stderr or r.stdout


def test_runtime_session_on_deployed_agent(deployed_runtime_agent):
    agent = deployed_runtime_agent
    run = agent["run"]
    cwd = agent["project_dir"]
    common = ["--agent", agent["name"]]

    # start-session → parse session_id from the "Response: {…}" JSON the CLI prints
    start = run(["runtime", "start-session", *common], cwd=cwd, timeout=120)
    assert start.returncode == 0, start.stderr or start.stdout
    m = re.search(r"Response:\s*(\{.*\})\s*$", start.stdout, re.DOTALL)
    assert m, f"could not find session Response in output:\n{start.stdout}"
    session_id = json.loads(m.group(1)).get("session_id")
    assert session_id

    sess = common + ["--session", session_id]

    # exec-command
    assert run(["runtime", "exec-command", *sess, "echo aa-it"], cwd=cwd, timeout=120).returncode == 0

    # upload-files (small temp file) → download-files round-trip
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("hello-aa-it")
        local = f.name
    try:
        assert run(["runtime", "upload-files", *sess, "--files", local,
                    "--path", "/home/user/aa-it.txt"], cwd=cwd, timeout=120).returncode == 0
        assert run(["runtime", "download-files", *sess, "--path", "/home/user/aa-it.txt",
                    "--output", str(Path(local).with_suffix(".dl"))],
                   cwd=cwd, timeout=120).returncode == 0
    finally:
        Path(local).unlink(missing_ok=True)

    # stop-session
    assert run(["runtime", "stop-session", *sess], cwd=cwd, timeout=120).returncode == 0
