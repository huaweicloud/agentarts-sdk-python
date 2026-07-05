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
import os
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
    """Core session lifecycle: start-session → exec-command → stop-session."""
    agent = deployed_runtime_agent
    run = agent["run"]
    cwd = agent["project_dir"]
    common = ["--agent", agent["name"]]

    start = run(["runtime", "start-session", *common], cwd=cwd, timeout=120)
    assert start.returncode == 0, start.stderr or start.stdout
    m = re.search(r"Response:\s*(\{.*\})\s*$", start.stdout, re.DOTALL)
    assert m, f"could not find session Response in output:\n{start.stdout}"
    # strict=False: the result dict can contain raw control chars (e.g. newlines) in string values.
    # session_id may be top-level or nested under "data" ({"code":..., "data":{"session_id":...}}).
    parsed = json.loads(m.group(1), strict=False)
    session_id = parsed.get("session_id") or (parsed.get("data") or {}).get("session_id")
    assert session_id, f"no session_id in start-session response:\n{start.stdout}"

    sess = common + ["--session", session_id]
    assert run(["runtime", "exec-command", *sess, "echo aa-it"], cwd=cwd, timeout=120).returncode == 0
    assert run(["runtime", "stop-session", *sess], cwd=cwd, timeout=120).returncode == 0


def test_runtime_file_transfer_on_deployed_agent(deployed_runtime_agent):
    """Best-effort file round-trip (upload → download). The file-upload endpoint
    may require a bearer token that an IAM-only agent doesn't have (401); in that
    case this test skips rather than fails — the core session lifecycle is
    covered by test_runtime_session_on_deployed_agent."""
    agent = deployed_runtime_agent
    run = agent["run"]
    cwd = agent["project_dir"]
    common = ["--agent", agent["name"]]

    start = run(["runtime", "start-session", *common], cwd=cwd, timeout=120)
    assert start.returncode == 0, start.stderr or start.stdout
    m = re.search(r"Response:\s*(\{.*\})\s*$", start.stdout, re.DOTALL)
    parsed = json.loads(m.group(1), strict=False)
    session_id = parsed.get("session_id") or (parsed.get("data") or {}).get("session_id")
    sess = common + ["--session", session_id]

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("hello-aa-it")
        local = f.name
    remote_file = f"/home/user/{os.path.basename(local)}"
    try:
        up = run(["runtime", "upload-files", *sess, "--files", local, "--path", "/home/user/"],
                 cwd=cwd, timeout=120)
        if up.returncode != 0 and "401" in (up.stderr or "") + (up.stdout or ""):
            pytest.skip("upload-files returned 401 (IAM-only agent likely needs a bearer token)")
        assert up.returncode == 0, up.stderr or up.stdout
        assert run(["runtime", "download-files", *sess, "--path", remote_file,
                    "--output", str(Path(local).with_suffix(".dl"))],
                   cwd=cwd, timeout=120).returncode == 0
    finally:
        Path(local).unlink(missing_ok=True)
        run(["runtime", "stop-session", *sess], cwd=cwd, timeout=120)
