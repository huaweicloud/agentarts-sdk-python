"""Tests for the agentarts memory install/uninstall CLI callbacks.

The installer ships Typer callbacks (``install_cmd``/``uninstall_cmd``)
registered onto ``agentarts memory``.  These tests exercise the business
logic (``_do_install``/``_do_uninstall``).
"""

import os
from unittest.mock import patch

from agentarts.toolkit.plugins.memory.installer import cli
from agentarts.toolkit.plugins.memory.installer.utils import (
    ENV_API_KEY,
    ENV_REGION,
    ENV_SPACE_ID,
    expand,
    find,
)

VALID_TARGETS = cli.VALID_TARGETS
_do_install = cli._do_install
_do_uninstall = cli._do_uninstall


def _set_home_and_creds(monkeypatch, tmp_path):
    """Redirect HOME to tmp and set valid credentials."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv(ENV_SPACE_ID, "test-space-12345")
    monkeypatch.setenv(ENV_API_KEY, "test-api-key-abcdef-123456")
    monkeypatch.setenv(ENV_REGION, "cn-north-4")


# ── targets ──────────────────────────────────────────────────────────


class TestTargets:
    def test_valid_targets(self):
        assert VALID_TARGETS == ("hermes", "claude", "codex", "opencode", "openclaw")


# ── openclaw placeholder ────────────────────────────────────────────


class TestOpenClawPlaceholder:
    def test_install_openclaw(self, capsys):
        assert _do_install("openclaw", False, False) == 0
        assert "not yet implemented" in capsys.readouterr().out

    def test_uninstall_openclaw(self, capsys):
        assert _do_uninstall("openclaw", False, False) == 0
        assert "not yet implemented" in capsys.readouterr().out


# ── invalid target ──────────────────────────────────────────────────


class TestInvalidTarget:
    def test_install_invalid(self, capsys):
        assert _do_install("bogus", False, False) == 2

    def test_uninstall_invalid(self, capsys):
        assert _do_uninstall("bogus", False, False) == 2


# ── no detection / no installs ─────────────────────────────────────


class TestNoTargets:
    def test_install_no_target_no_detection(self, monkeypatch, tmp_path, capsys):
        _set_home_and_creds(monkeypatch, tmp_path)
        # No ~/.claude, ~/.codex, ~/.hermes, ~/.config/opencode
        assert _do_install(None, False, True) == 1
        assert "No supported platforms detected" in capsys.readouterr().out

    def test_uninstall_no_target_no_installs(self, monkeypatch, tmp_path, capsys):
        _set_home_and_creds(monkeypatch, tmp_path)
        assert _do_uninstall(None, False, True) == 1
        assert "No installations found" in capsys.readouterr().out

    def test_uninstall_target_not_found(self, monkeypatch, tmp_path, capsys):
        _set_home_and_creds(monkeypatch, tmp_path)
        assert _do_uninstall("hermes", False, True) == 1
        assert "No hermes installation found" in capsys.readouterr().out


# ── end-to-end: install + uninstall hermes ───────────────────────────


class TestEndToEndHermes:
    def test_install_hermes_yes(self, monkeypatch, tmp_path):
        _set_home_and_creds(monkeypatch, tmp_path)
        assert _do_install("hermes", False, True) == 0

        plugin_dir = expand("~/.hermes/hermes-agent/plugins/memory/agentarts")
        assert os.path.isdir(plugin_dir)
        assert os.path.isfile(os.path.join(plugin_dir, "provider.py"))

        found = find("hermes")
        assert found is not None
        assert found["scope"] == "global"  # hermes is fixed_user_level

    def test_install_hermes_global_yes(self, monkeypatch, tmp_path):
        _set_home_and_creds(monkeypatch, tmp_path)
        assert _do_install("hermes", True, True) == 0

        # hermes is fixed_user_level, so scope should be "global" regardless.
        found = find("hermes")
        assert found is not None
        assert found["scope"] == "global"

    def test_uninstall_hermes_after_install(self, monkeypatch, tmp_path):
        _set_home_and_creds(monkeypatch, tmp_path)

        # Install first.
        _do_install("hermes", True, True)

        # Uninstall.
        assert _do_uninstall("hermes", True, True) == 0

        # Verify cleaned.
        plugin_dir = expand("~/.hermes/hermes-agent/plugins/memory/agentarts")
        assert not os.path.exists(plugin_dir)
        assert find("hermes") is None


# ── end-to-end: install + uninstall claude ──────────────────────────


class TestEndToEndClaude:
    def test_install_claude_global_yes(self, monkeypatch, tmp_path):
        _set_home_and_creds(monkeypatch, tmp_path)
        assert _do_install("claude", True, True) == 0

        scripts_dir = os.path.join(expand("~/.claude"), "agentarts-memory", "scripts")
        assert os.path.isdir(scripts_dir)

        settings_path = os.path.join(expand("~/.claude"), "settings.json")
        assert os.path.isfile(settings_path)

        found = find("claude")
        assert found is not None
        assert found["scope"] == "global"

    def test_uninstall_claude_after_install(self, monkeypatch, tmp_path):
        _set_home_and_creds(monkeypatch, tmp_path)

        _do_install("claude", True, True)
        assert _do_uninstall("claude", True, True) == 0

        scripts_dir = os.path.join(expand("~/.claude"), "agentarts-memory", "scripts")
        assert not os.path.exists(scripts_dir)
        assert find("claude") is None

    def test_server_dependency_hint_printed(self, monkeypatch, tmp_path, capsys):
        _set_home_and_creds(monkeypatch, tmp_path)
        _do_install("claude", True, True)
        out = capsys.readouterr().out
        # Server hint removed; MCP config is written by installer instead.
        assert "Restart" in out


# ── escape interrupt ───────────────────────────────────────────────


class TestEscapeInterrupt:
    def test_install_catches_escape(self, capsys):
        """install_cmd should catch EscapeInterrupt and not error out."""
        with patch.object(cli, "_do_install", side_effect=cli.EscapeInterrupt()):
            cli.install_cmd("hermes", False, True)
        assert "Cancelled" in capsys.readouterr().out
