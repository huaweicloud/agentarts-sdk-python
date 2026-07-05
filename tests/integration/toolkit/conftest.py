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
