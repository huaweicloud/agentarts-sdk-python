"""Fixtures for the toolkit (CLI) integration tests.

Two invocation styles:
  * ``cli_runner`` — in-process `typer.testing.CliRunner` against the real Typer
    ``app``. Fast; used for local commands (init/config) where we assert on
    filesystem side-effects rather than stdout (rich output capture is unreliable
    under CliRunner).
  * ``agentarts_cmd`` + ``cli_env`` — subprocess prefix + env to invoke the real
    `agentarts` console entry (`python -c "from agentarts.toolkit.main import
    app; app()" ...`). Reliable stdout capture (no TTY → rich emits plain text);
    used for cloud commands where output must be parsed (e.g. `memory create
    --output json`) and for the blocking `dev` server.

Completion handling: the CLI's `_auto_install_completion` touches `~/.agentarts`
on first run, and setting `_AGENTARTS_COMPLETE` (the obvious skip) instead
triggers click's completion protocol ("Invalid completion instruction"). So we
  * patch `_auto_install_completion` to a no-op for in-process CliRunner invokes;
  * point HOME at a temp dir with the marker pre-created for subprocess invokes.
"""

from __future__ import annotations

import os
import sys

import pytest
from typer.testing import CliRunner

_COMPLETE_NOOP = "agentarts.toolkit.main._auto_install_completion"


@pytest.fixture
def cli_runner(monkeypatch):
    """In-process CliRunner against the real Typer app (completion patched out)."""
    monkeypatch.setattr(_COMPLETE_NOOP, lambda: None)
    return CliRunner()


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """A fresh temp CWD so .agentarts_config.yaml / scaffold files never leak."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(scope="session")
def agentarts_cmd():
    """Subprocess prefix invoking the real agentarts CLI (true e2e)."""
    return [sys.executable, "-c", "from agentarts.toolkit.main import app; app()"]


@pytest.fixture(scope="session")
def docker_available():
    """Skip tests that need `agentarts deploy` when no Docker daemon is present."""
    import subprocess

    try:
        r = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=20)
    except (FileNotFoundError, subprocess.SubprocessError):
        pytest.skip("Docker not installed / not on PATH — required for `agentarts deploy`")
    if r.returncode != 0:
        pytest.skip("Docker daemon not available — required for `agentarts deploy`")
    return True


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    """Env for subprocess CLI invokes: HOME redirected to a temp dir with the
    completion marker pre-created, so `_auto_install_completion` is a no-op and
    no tip text pollutes stdout (important for `--output json` parsing)."""
    home = tmp_path / "fakehome"
    (home / ".agentarts").mkdir(parents=True, exist_ok=True)
    (home / ".agentarts" / ".completion_shown").touch()
    env = dict(os.environ)
    env["HOME"] = str(home)
    return env


# --------------------------------------------------------------------------- #
# Shared deployed runtime agent (Docker + billable).
# Session-scoped: ONE `agentarts deploy` (Docker build + SWR push + cloud
# runtime create) is shared by all CLI tests that need a live agent (invoke,
# runtime session ops). Destroy is registered with `resource_registry` so the
# agent is torn down at session end even if a test crashes. SWR org/repo/image
# remain (no cleanup in the operations layer — documented residue).
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def deployed_runtime_agent(
    agentarts_cmd,
    docker_available,
    cloud_credentials,
    allow_create,
    allow_billable,
    run_id,
    resource_registry,
    tmp_path_factory,
):
    import subprocess

    from tests.integration._helpers import unique_name

    region = cloud_credentials["region"]
    name = unique_name("agent", run_id)
    work = tmp_path_factory.mktemp("deploy")
    proj_dir = work / name

    # HOME with the completion marker so the CLI doesn't try to install
    # completion (and pollute stdout) inside the subprocess.
    home = tmp_path_factory.mktemp("home")
    (home / ".agentarts").mkdir(parents=True, exist_ok=True)
    (home / ".agentarts" / ".completion_shown").touch()
    env = dict(os.environ)
    env["HOME"] = str(home)

    def _run(args, timeout=900, cwd=None):
        return subprocess.run(
            agentarts_cmd + args,
            capture_output=True,
            text=True,
            env=env,
            cwd=cwd,
            timeout=timeout,
        )

    # 1. init (basic template) → 2. config (entrypoint/region/SWR, all flags → no prompt)
    assert _run(["init", "-n", name, "-t", "basic", "-r", region], cwd=str(work)).returncode == 0
    assert _run(
        ["config", "-n", name, "-e", "agent:app", "-r", region, "-d", "requirements.txt",
         "--swr-org", unique_name("swrorg", run_id), "--swr-repo", unique_name("swrrepo", run_id)],
        cwd=str(proj_dir),
    ).returncode == 0

    # 3. deploy (Docker build + SWR push + create cloud runtime)
    deploy = _run(["deploy", "--agent", name, "--mode", "cloud"], cwd=str(proj_dir), timeout=900)
    assert deploy.returncode == 0, deploy.stderr or deploy.stdout

    # safety net: destroy at session end
    resource_registry.register(
        lambda: _run(["destroy", "--agent", name, "--region", region, "--yes"],
                     cwd=str(proj_dir), timeout=120),
        f"deployed-agent:{name}",
    )

    return {"name": name, "project_dir": str(proj_dir), "region": region, "run": _run}
