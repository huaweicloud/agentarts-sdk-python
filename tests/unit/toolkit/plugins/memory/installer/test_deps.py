"""Tests for installer runtime dependency checks."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from types import SimpleNamespace

from agentarts.toolkit.plugins.memory.installer import deps


class TestNeedsMcp:
    def test_mcp_server_platforms_need_mcp(self):
        for target in ("claude", "codex", "opencode"):
            assert deps.needs_mcp(target) is True

    def test_other_platforms_do_not_need_mcp(self):
        assert deps.needs_mcp("hermes") is False
        assert deps.needs_mcp("openclaw") is False


class TestIsMcpAvailable:
    def test_missing_module(self, monkeypatch):
        monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)

        assert deps.is_mcp_available() is False

    def test_v2_is_supported(self, monkeypatch):
        monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: object())
        monkeypatch.setattr(deps, "version", lambda name: "2.3.0")

        assert deps.is_mcp_available() is True

    def test_v1_is_too_old(self, monkeypatch):
        monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: object())
        monkeypatch.setattr(deps, "version", lambda name: "1.12.0")

        assert deps.is_mcp_available() is False

    def test_missing_distribution_metadata_is_tolerated(self, monkeypatch):
        monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: object())

        def raise_missing(name):
            raise PackageNotFoundError(name)

        monkeypatch.setattr(deps, "version", raise_missing)

        assert deps.is_mcp_available() is True


class TestInstallCommand:
    def test_prefers_pip(self, monkeypatch):
        monkeypatch.setattr(
            deps.importlib.util,
            "find_spec",
            lambda name: object() if name == "pip" else None,
        )
        monkeypatch.setattr(deps.shutil, "which", lambda name: None)

        command = deps.install_command()

        assert command is not None
        assert command[0] == deps.sys.executable
        assert command[1:4] == ["-m", "pip", "install"]
        assert command[-1] == deps.MCP_REQUIRED_SPEC

    def test_falls_back_to_uv(self, monkeypatch):
        monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
        monkeypatch.setattr(
            deps.shutil,
            "which",
            lambda name: "/usr/bin/uv" if name == "uv" else None,
        )

        command = deps.install_command()

        assert command is not None
        assert command[0] == "/usr/bin/uv"
        assert command[1:3] == ["pip", "install"]
        assert "--python" in command
        assert deps.sys.executable in command
        assert command[-1] == deps.MCP_REQUIRED_SPEC

    def test_returns_none_without_installer(self, monkeypatch):
        monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
        monkeypatch.setattr(deps.shutil, "which", lambda name: None)

        assert deps.install_command() is None


class TestEnsureMcpInstalled:
    def test_noop_when_available(self, monkeypatch):
        monkeypatch.setattr(deps, "is_mcp_available", lambda: True)
        calls = []
        monkeypatch.setattr(
            deps.subprocess,
            "run",
            lambda *args, **kwargs: calls.append((args, kwargs)),
        )

        assert deps.ensure_mcp_installed() is True
        assert calls == []

    def test_runs_installer_when_missing(self, monkeypatch):
        state = {"available": False}

        def fake_run(command, check=False):
            state["available"] = True
            return SimpleNamespace(returncode=0)

        monkeypatch.setattr(deps, "is_mcp_available", lambda: state["available"])
        monkeypatch.setattr(deps, "install_command", lambda: ["installer", "mcp"])
        monkeypatch.setattr(deps.subprocess, "run", fake_run)

        assert deps.ensure_mcp_installed() is True
        assert state["available"] is True

    def test_returns_false_on_installer_failure(self, monkeypatch):
        monkeypatch.setattr(deps, "is_mcp_available", lambda: False)
        monkeypatch.setattr(deps, "install_command", lambda: ["installer", "mcp"])
        monkeypatch.setattr(
            deps.subprocess,
            "run",
            lambda command, check=False: SimpleNamespace(returncode=1),
        )

        assert deps.ensure_mcp_installed() is False

    def test_returns_false_when_installer_cannot_run(self, monkeypatch):
        monkeypatch.setattr(deps, "is_mcp_available", lambda: False)
        monkeypatch.setattr(deps, "install_command", lambda: ["installer", "mcp"])

        def raise_oserror(command, check=False):
            raise OSError("cannot execute")

        monkeypatch.setattr(deps.subprocess, "run", raise_oserror)

        assert deps.ensure_mcp_installed() is False

    def test_returns_false_when_no_installer(self, monkeypatch):
        monkeypatch.setattr(deps, "is_mcp_available", lambda: False)
        monkeypatch.setattr(deps, "install_command", lambda: None)

        assert deps.ensure_mcp_installed() is False
