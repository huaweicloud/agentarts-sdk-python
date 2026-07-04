"""Runtime CLI e2e tests (billable tier).

Invokes `agentarts invoke` and `agentarts runtime *` against a pre-deployed
agent via subprocess. Gated behind `AGENTARTS_TEST_RUN_BILLABLE=1` and
`AGENTARTS_TEST_RUNTIME_AGENT_NAME`. The data-plane endpoint must be supplied
via `AGENTARTS_RUNTIME_DATA_ENDPOINT` (env) or `--endpoint`.

These mirror the SDK `test_runtime_session_lifecycle.py` but exercise the CLI
→ operation → RuntimeClient chain. Signature-checked; not实跑-verified without
billable credentials.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _run(agentarts_cmd, cli_env, args, timeout=120):
    return subprocess.run(
        agentarts_cmd + args, capture_output=True, text=True, env=cli_env, timeout=timeout
    )


def test_cli_invoke_cloud(
    agentarts_cmd, cli_env, allow_billable, runtime_agent_name
):
    payload = '{"message": "hello from cli"}'
    args = ["invoke", "--agent", runtime_agent_name, "--mode", "cloud", payload]
    if os.getenv("AGENTARTS_RUNTIME_DATA_ENDPOINT"):
        args += ["--endpoint", os.getenv("AGENTARTS_RUNTIME_DATA_ENDPOINT")]
    r = _run(agentarts_cmd, cli_env, args, timeout=900)
    assert r.returncode == 0, r.stderr


def test_cli_runtime_session_lifecycle(
    agentarts_cmd, cli_env, allow_billable, runtime_agent_name
):
    agent = runtime_agent_name
    session_id = f"aa-it-{uuid.uuid4().hex[:8]}"
    endpoint = os.getenv("AGENTARTS_RUNTIME_DATA_ENDPOINT")

    def _args(*extra):
        base = ["--agent", agent, "--session", session_id]
        if endpoint:
            base += ["--endpoint", endpoint]
        return base + list(extra)

    # start-session
    start_args = ["runtime", "start-session", "--agent", agent]
    if endpoint:
        start_args += ["--endpoint", endpoint]
    r = _run(agentarts_cmd, cli_env, start_args, timeout=120)
    assert r.returncode == 0, r.stderr

    # exec-command
    assert _run(agentarts_cmd, cli_env,
                ["runtime", "exec-command", *_args("echo aa-it")]).returncode == 0

    # upload-files (small temp file)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("hello-aa-it")
        local = f.name
    try:
        assert _run(agentarts_cmd, cli_env,
                    ["runtime", "upload-files", *_args("--files", local, "--path", "/home/user/aa-it.txt")]).returncode == 0
        # download-files
        assert _run(agentarts_cmd, cli_env,
                    ["runtime", "download-files", *_args("--path", "/home/user/aa-it.txt", "--output", str(Path(local).with_suffix(".dl")))]).returncode == 0
    finally:
        os.unlink(local)

    # stop-session
    assert _run(agentarts_cmd, cli_env,
                ["runtime", "stop-session", *_args()]).returncode == 0
