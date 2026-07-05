"""Local CLI e2e tests (default tier — no credentials, no Docker, no cloud).

Invokes the real `agentarts` Typer app via CliRunner (in-process) for
init/config (asserting on generated files) and via subprocess for the blocking
`dev` server. Safe to run in CI unconditionally.
"""

from __future__ import annotations

import json
import socket
import subprocess
import time
import urllib.request

import pytest
from typer.testing import CliRunner

from agentarts.toolkit.main import app

pytestmark = pytest.mark.integration

TEMPLATES = ["basic", "langgraph", "langchain", "google-adk"]


# --------------------------------------------------------------------------- #
# Smoke
# --------------------------------------------------------------------------- #
def test_cli_version(cli_runner):
    result = cli_runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "agentarts" in result.output.lower() or "0." in result.output


def test_cli_help(cli_runner):
    result = cli_runner.invoke(app, ["--help"])
    assert result.exit_code == 0


# --------------------------------------------------------------------------- #
# init
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("template", TEMPLATES)
def test_init_creates_project_files(cli_runner, tmp_project, template):
    result = cli_runner.invoke(
        app, ["init", "-n", "myagent", "-t", template, "-r", "cn-southwest-2"]
    )
    assert result.exit_code == 0, result.output
    project = tmp_project / "myagent"
    assert (project / "agent.py").exists()
    assert (project / "requirements.txt").exists()
    assert (project / ".agentarts_config.yaml").exists()
    assert (project / "Dockerfile").exists()


def test_init_path_option(cli_runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "sub"
    target.mkdir()
    result = cli_runner.invoke(
        app,
        ["init", "-n", "myagent", "-t", "basic", "-r", "cn-southwest-2", "-p", str(target)],
    )
    assert result.exit_code == 0, result.output
    assert (target / "myagent" / "agent.py").exists()


def test_init_invalid_name_fails(cli_runner, tmp_project):
    # uppercase name is normalised to lowercase; a name with invalid chars must fail
    result = cli_runner.invoke(
        app, ["init", "-n", "Bad_Name!", "-t", "basic", "-r", "cn-southwest-2"]
    )
    assert result.exit_code != 0


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #
def _add_agent(runner: CliRunner, name: str = "myagent"):
    # pass every flag the callback would otherwise prompt for (CliRunner has no
    # stdin → an unhandled Prompt.ask aborts with exit 1)
    return runner.invoke(
        app,
        [
            "config", "-n", name, "-e", "agent:app", "-r", "cn-southwest-2",
            "-d", "requirements.txt", "--swr-org", "o", "--swr-repo", "r",
        ],
    )


def test_config_add_writes_yaml_and_lists(cli_runner, tmp_project):
    result = _add_agent(cli_runner)
    assert result.exit_code == 0, result.output
    cfg = tmp_project / ".agentarts_config.yaml"
    assert cfg.exists()
    assert "myagent" in cfg.read_text()
    assert cli_runner.invoke(app, ["config", "list"]).exit_code == 0


def test_config_set_get_roundtrip(cli_runner, tmp_project):
    _add_agent(cli_runner)
    assert cli_runner.invoke(
        app, ["config", "set", "base.description", "hello", "-a", "myagent"]
    ).exit_code == 0
    # assert the value landed in the YAML (robust vs rich stdout capture)
    cfg = (tmp_project / ".agentarts_config.yaml").read_text()
    assert "hello" in cfg
    assert cli_runner.invoke(
        app, ["config", "get", "base.description", "-a", "myagent"]
    ).exit_code == 0


def test_config_env_lifecycle(cli_runner, tmp_project):
    _add_agent(cli_runner)
    assert cli_runner.invoke(
        app, ["config", "set-env", "MY_VAR", "val", "-a", "myagent"]
    ).exit_code == 0
    cfg = (tmp_project / ".agentarts_config.yaml").read_text()
    assert "MY_VAR" in cfg
    assert "val" in cfg
    assert cli_runner.invoke(app, ["config", "list-env", "-a", "myagent"]).exit_code == 0
    assert cli_runner.invoke(
        app, ["config", "remove-env", "MY_VAR", "-a", "myagent"]
    ).exit_code == 0
    assert "MY_VAR" not in (tmp_project / ".agentarts_config.yaml").read_text()


def test_config_set_default_and_remove(cli_runner, tmp_project):
    _add_agent(cli_runner, "a1")
    _add_agent(cli_runner, "a2")
    assert cli_runner.invoke(app, ["config", "set-default", "a2"]).exit_code == 0
    assert cli_runner.invoke(app, ["config", "remove", "a1"]).exit_code == 0
    remaining = (tmp_project / ".agentarts_config.yaml").read_text()
    assert "a2" in remaining
    assert "a1" not in remaining


# --------------------------------------------------------------------------- #
# dev (blocking uvicorn — subprocess)
# --------------------------------------------------------------------------- #
def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_dev_server_serves_ping_and_invocations(
    agentarts_cmd, cli_env, cli_runner, tmp_path, monkeypatch
):
    # 1. scaffold a basic project in tmp_path
    monkeypatch.chdir(tmp_path)
    init_result = cli_runner.invoke(
        app, ["init", "-n", "myagent", "-t", "basic", "-r", "cn-southwest-2"]
    )
    assert init_result.exit_code == 0, init_result.output
    project = tmp_path / "myagent"

    # 2. launch `agentarts dev` against it
    port = _free_port()
    proc = subprocess.Popen(
        agentarts_cmd + ["dev", "-p", str(port), "-h", "127.0.0.1"],
        cwd=str(project),
        env=cli_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        ping_ok = False
        for _ in range(40):  # ~20s startup window
            try:
                with urllib.request.urlopen(base + "/ping", timeout=1) as resp:
                    if resp.status == 200:
                        ping_ok = True
                        break
            except Exception:
                time.sleep(0.5)
        assert ping_ok, "dev server did not come up"

        # 3. POST /invocations
        req = urllib.request.Request(
            base + "/invocations",
            data=json.dumps({"message": "hi"}).encode(),
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            body = json.loads(resp.read())
        assert "response" in body
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
