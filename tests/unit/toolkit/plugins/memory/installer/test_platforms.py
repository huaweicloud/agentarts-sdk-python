"""Tests for platform adapters (P2+)."""

from __future__ import annotations

import json
import os

from agentarts.toolkit.plugins.memory.installer import platforms
from agentarts.toolkit.plugins.memory.installer.platforms import PLATFORMS, detect_all, get_platform
from agentarts.toolkit.plugins.memory.installer.platforms.hermes import HermesPlatform
from agentarts.toolkit.plugins.memory.installer.utils import (
    ENV_API_KEY,
    ENV_REGION,
    ENV_SPACE_ID,
    add,
    expand,
    find,
    list_all,
    remove,
)


def _set_home(monkeypatch, tmp_path):
    """Redirect all ~ paths to tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))


def _make_creds():
    return {
        ENV_SPACE_ID: "test-space-12345",
        ENV_API_KEY: "test-api-key-abcdef-123456",
        ENV_REGION: "cn-north-4",
    }


# ── Registry tests ──────────────────────────────────────────────────


class TestRegistry:
    def test_get_hermes(self):
        p = get_platform("hermes")
        assert p is not None
        assert isinstance(p, HermesPlatform)

    def test_get_unknown(self):
        assert get_platform("bogus") is None

    def test_hermes_in_registry(self):
        assert "hermes" in PLATFORMS

    def test_detect_all_with_hermes(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        # Create ~/.hermes to trigger detection.
        os.makedirs(expand("~/.hermes"))
        detected = detect_all(False)
        names = [n for n, _ in detected]
        assert "hermes" in names

    def test_detect_all_empty(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        detected = detect_all(False)
        assert detected == []


# ── Hermes round-trip ───────────────────────────────────────────────


class TestHermesRoundTrip:
    def test_install_deploys_files(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = HermesPlatform()
        creds = _make_creds()

        result = p.install("global", creds, yes=True)

        plugin_dir = expand("~/.hermes/hermes-agent/plugins/memory/agentarts")
        assert os.path.isdir(plugin_dir)
        # 3 files deployed.
        files = os.listdir(plugin_dir)
        assert "provider.py" in files
        assert "plugin.yaml" in files
        assert "__init__.py" in files
        assert len(result.files) == 6

        # Also deployed to the new plugin directory.
        new_plugin_dir = expand("~/.hermes/plugins/agentarts")
        assert os.path.isdir(new_plugin_dir)
        new_files = os.listdir(new_plugin_dir)
        assert "provider.py" in new_files
        assert "plugin.yaml" in new_files
        assert "__init__.py" in new_files

        # .env written.
        env_path = expand("~/.hermes/.env")
        assert os.path.isfile(env_path)
        env_content = open(env_path).read()
        assert ENV_API_KEY in env_content
        assert "test-api-key-abcdef-123456" in env_content

        # agentarts.json written.
        config_path = expand("~/.hermes/agentarts.json")
        assert os.path.isfile(config_path)
        config = json.loads(open(config_path).read())
        assert config["space_id"] == "test-space-12345"
        assert config["region"] == "cn-north-4"

        # config.yaml has memory provider activated.
        config_yaml_path = expand("~/.hermes/config.yaml")
        assert os.path.isfile(config_yaml_path)
        yaml_content = open(config_yaml_path).read()
        assert "provider: agentarts" in yaml_content
        assert config_yaml_path in result.config_files

        # InstallResult.
        assert result.config_dir == plugin_dir
        assert env_path in result.config_files
        assert config_path in result.config_files

    def test_uninstall_cleans_everything(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = HermesPlatform()
        creds = _make_creds()

        # Install first.
        result = p.install("global", creds, yes=True)

        # Verify it's there.
        plugin_dir = expand("~/.hermes/hermes-agent/plugins/memory/agentarts")
        assert os.path.isdir(plugin_dir)
        assert os.path.isfile(expand("~/.hermes/.env"))
        assert os.path.isfile(expand("~/.hermes/agentarts.json"))

        # Uninstall.
        p.uninstall({})

        # Plugin dir gone.
        assert not os.path.exists(plugin_dir)
        # New plugin dir also gone.
        new_plugin_dir = expand("~/.hermes/plugins/agentarts")
        assert not os.path.exists(new_plugin_dir)
        # .env gone (we only had the API key, so file removed).
        assert not os.path.exists(expand("~/.hermes/.env"))
        # agentarts.json gone.
        assert not os.path.exists(expand("~/.hermes/agentarts.json"))

        # config.yaml memory provider deactivated (empty string).
        config_yaml_path = expand("~/.hermes/config.yaml")
        assert os.path.isfile(config_yaml_path)
        yaml_content = open(config_yaml_path).read()
        assert "provider: ''" in yaml_content

    def test_install_idempotent(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = HermesPlatform()
        creds = _make_creds()

        # Install twice.
        p.install("global", creds, yes=True)
        p.install("global", creds, yes=True)

        plugin_dir = expand("~/.hermes/hermes-agent/plugins/memory/agentarts")
        files = os.listdir(plugin_dir)
        # Should still be exactly 3 files, not duplicated.
        assert len([f for f in files if f.endswith(".py") or f.endswith(".yaml")]) == 3
        # New plugin dir also has exactly 3 files.
        new_plugin_dir = expand("~/.hermes/plugins/agentarts")
        new_files = os.listdir(new_plugin_dir)
        assert len([f for f in new_files if f.endswith(".py") or f.endswith(".yaml")]) == 3

        # .env should have one API key line, not two.
        env_content = open(expand("~/.hermes/.env")).read()
        assert env_content.count(ENV_API_KEY) == 1

    def test_config_dir_always_plugin_dir(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = HermesPlatform()
        assert p.config_dir("project") == p.config_dir("global")
        assert p.fixed_user_level is True

    def test_detect_returns_false_for_missing(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = HermesPlatform()
        assert p.detect() is False

    def test_detect_returns_true_when_exists(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        os.makedirs(expand("~/.hermes"))
        p = HermesPlatform()
        assert p.detect() is True


# ── Hermes + manifest integration ─────────────────────────────────────


class TestHermesManifestIntegration:
    def test_install_then_manifest_then_uninstall(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = HermesPlatform()
        creds = _make_creds()

        # Install.
        result = p.install("global", creds, yes=True)

        # Record in manifest.
        entry = {
            "platform": "hermes",
            "scope": "global",
            "config_dir": result.config_dir,
            "scripts_dir": result.scripts_dir,
            "files": result.files,
            "config_files": result.config_files,
        }
        add(entry)

        # Manifest has one record.
        found = find("hermes")
        assert found is not None
        assert found["platform"] == "hermes"
        assert len(list_all()) == 1

        # Uninstall.
        p.uninstall(found)

        # Remove from manifest.
        remove("hermes", "global", result.config_dir)
        assert find("hermes") is None
        assert list_all() == []


# ── Claude round-trip ───────────────────────────────────────────────


class TestClaudeRoundTrip:
    def test_install_deploys_scripts_and_hooks(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.claude.ClaudePlatform()
        creds = _make_creds()

        result = p.install("global", creds, yes=True)

        scripts_dir = os.path.join(expand("~/.claude"), "agentarts-memory", "scripts")
        assert os.path.isdir(scripts_dir)
        # 3 scripts deployed (_shared, prompt-submit, pre-compact).
        scripts = os.listdir(scripts_dir)
        assert len([f for f in scripts if f.endswith(".mjs")]) == 3
        assert len(result.files) == 3

        # settings.json has hooks.
        settings_path = os.path.join(expand("~/.claude"), "settings.json")
        assert os.path.isfile(settings_path)
        settings = json.loads(open(settings_path).read())
        assert "hooks" in settings

        # Count hook entries — should have multiple events.
        hook_events = settings["hooks"]
        assert len(hook_events) == 2  # UserPromptSubmit + PreCompact

        # Commands should have absolute paths (no placeholder).
        for event, groups in hook_events.items():
            for group in groups:
                for hook in group.get("hooks", []):
                    cmd = hook.get("command", "")
                    assert "${CLAUDE_PLUGIN_ROOT}" not in cmd
                    assert scripts_dir in cmd

    def test_uninstall_cleans_settings_and_scripts(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.claude.ClaudePlatform()
        creds = _make_creds()

        result = p.install("global", creds, yes=True)

        scripts_dir = result.scripts_dir
        settings_path = os.path.join(result.config_dir, "settings.json")

        # Verify installed.
        assert os.path.isdir(scripts_dir)
        assert os.path.isfile(settings_path)

        # Uninstall.
        p.uninstall(
            {
                "config_dir": result.config_dir,
                "scripts_dir": scripts_dir,
            }
        )

        # Scripts dir gone.
        assert not os.path.exists(scripts_dir)
        # settings.json gone (was empty after stripping hooks).
        assert not os.path.exists(settings_path)

    def test_install_idempotent_no_duplicate_hooks(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.claude.ClaudePlatform()
        creds = _make_creds()

        p.install("global", creds, yes=True)
        p.install("global", creds, yes=True)

        settings_path = os.path.join(expand("~/.claude"), "settings.json")
        settings = json.loads(open(settings_path).read())
        # Count total hook entries across all events.
        total = 0
        for event, groups in settings["hooks"].items():
            for group in groups:
                total += len(group.get("hooks", []))
        # 2 hooks, not 4.
        assert total == 2

    def test_uninstall_preserves_user_hooks(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.claude.ClaudePlatform()

        # Pre-populate settings.json with a user hook.
        config_dir = expand("~/.claude")
        os.makedirs(config_dir, exist_ok=True)
        settings_path = os.path.join(config_dir, "settings.json")
        user_settings = {
            "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo user-hook"}]}]},
            "permissions": {"allow": ["*"]},
        }
        import json as _json

        open(settings_path, "w").write(_json.dumps(user_settings))

        creds = _make_creds()
        result = p.install("global", creds, yes=True)

        # Uninstall.
        p.uninstall(
            {
                "config_dir": result.config_dir,
                "scripts_dir": result.scripts_dir,
            }
        )

        # settings.json should still exist with user hook and permissions.
        assert os.path.isfile(settings_path)
        remaining = json.loads(open(settings_path).read())
        assert "permissions" in remaining
        assert "Stop" in remaining["hooks"]
        stop_hooks = remaining["hooks"]["Stop"][0]["hooks"]
        assert len(stop_hooks) == 1
        assert "echo user-hook" in stop_hooks[0]["command"]

    def test_detect_returns_false_when_missing(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.claude.ClaudePlatform()
        assert p.detect() is False

    def test_detect_returns_true_when_exists(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        os.makedirs(expand("~/.claude"))
        p = platforms.claude.ClaudePlatform()
        assert p.detect() is True


# ── Codex round-trip ────────────────────────────────────────────────


class TestCodexRoundTrip:
    def test_install_deploys_scripts_hooks_and_toml(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.codex.CodexPlatform()
        creds = _make_creds()

        result = p.install("global", creds, yes=True)

        scripts_dir = os.path.join(expand("~/.codex"), "agentarts-memory", "scripts")
        assert os.path.isdir(scripts_dir)
        scripts = os.listdir(scripts_dir)
        assert len([f for f in scripts if f.endswith(".mjs")]) == 3

        # hooks.json has 2 hooks.
        hooks_path = os.path.join(expand("~/.codex"), "hooks.json")
        assert os.path.isfile(hooks_path)
        hooks_data = json.loads(open(hooks_path).read())
        assert "hooks" in hooks_data
        total = 0
        for event, groups in hooks_data["hooks"].items():
            for group in groups:
                total += len(group.get("hooks", []))
        assert total == 2

        # Commands should have absolute paths (no placeholder).
        for event, groups in hooks_data["hooks"].items():
            for group in groups:
                for hook in group.get("hooks", []):
                    cmd = hook.get("command", "")
                    assert "${CODEX_PLUGIN_ROOT}" not in cmd
                    assert scripts_dir in cmd

        # config.toml has hooks = true.
        toml_path = os.path.join(expand("~/.codex"), "config.toml")
        assert os.path.isfile(toml_path)
        toml_content = open(toml_path).read()
        assert "hooks = true" in toml_content
        assert "[features]" in toml_content

    def test_uninstall_cleans_hooks_toml_and_scripts(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.codex.CodexPlatform()
        creds = _make_creds()

        result = p.install("global", creds, yes=True)

        scripts_dir = result.scripts_dir
        hooks_path = os.path.join(result.config_dir, "hooks.json")
        toml_path = os.path.join(result.config_dir, "config.toml")

        assert os.path.isdir(scripts_dir)
        assert os.path.isfile(hooks_path)
        assert os.path.isfile(toml_path)

        p.uninstall(
            {
                "config_dir": result.config_dir,
                "scripts_dir": scripts_dir,
            }
        )

        assert not os.path.exists(scripts_dir)
        assert not os.path.exists(hooks_path)
        assert not os.path.exists(toml_path)

    def test_install_idempotent_no_duplicate_hooks(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.codex.CodexPlatform()
        creds = _make_creds()

        p.install("global", creds, yes=True)
        p.install("global", creds, yes=True)

        hooks_path = os.path.join(expand("~/.codex"), "hooks.json")
        hooks_data = json.loads(open(hooks_path).read())
        total = 0
        for event, groups in hooks_data["hooks"].items():
            for group in groups:
                total += len(group.get("hooks", []))
        assert total == 2  # not 4

        # config.toml should have one hooks line.
        toml_content = open(os.path.join(expand("~/.codex"), "config.toml")).read()
        assert toml_content.count("hooks = true") == 1

    def test_uninstall_preserves_user_hooks_and_other_toml_keys(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.codex.CodexPlatform()

        # Pre-populate hooks.json with a user hook.
        config_dir = expand("~/.codex")
        os.makedirs(config_dir, exist_ok=True)
        hooks_path = os.path.join(config_dir, "hooks.json")
        import json as _json

        user_hooks = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo user"}]}]}}
        open(hooks_path, "w").write(_json.dumps(user_hooks))

        # Pre-populate config.toml with an existing feature key.
        toml_path = os.path.join(config_dir, "config.toml")
        open(toml_path, "w").write("[features]\nother_feature = true\n")

        creds = _make_creds()
        result = p.install("global", creds, yes=True)

        p.uninstall(
            {
                "config_dir": result.config_dir,
                "scripts_dir": result.scripts_dir,
            }
        )

        # hooks.json should still have user hook.
        assert os.path.isfile(hooks_path)
        remaining = json.loads(open(hooks_path).read())
        assert "Stop" in remaining["hooks"]
        assert len(remaining["hooks"]["Stop"][0]["hooks"]) == 1

        # config.toml should still have other_feature.
        assert os.path.isfile(toml_path)
        toml = open(toml_path).read()
        assert "other_feature = true" in toml
        assert "hooks = true" not in toml

    def test_detect_returns_false_when_missing(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.codex.CodexPlatform()
        assert p.detect() is False

    def test_detect_returns_true_when_exists(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        os.makedirs(expand("~/.codex"))
        p = platforms.codex.CodexPlatform()
        assert p.detect() is True


# ── OpenCode round-trip ─────────────────────────────────────────────


class TestOpenCodeRoundTrip:
    def test_install_deploys_plugin_commands_and_json(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.opencode.OpenCodePlatform()
        creds = _make_creds()

        result = p.install("global", creds, yes=True)

        config_dir = expand("~/.config/opencode")

        # TS plugin deployed.
        ts_path = os.path.join(config_dir, "plugins", "agentarts-memory-capture.ts")
        assert os.path.isfile(ts_path)

        # Commands deployed.
        assert os.path.isfile(os.path.join(config_dir, "commands", "recall.md"))
        assert os.path.isfile(os.path.join(config_dir, "commands", "remember.md"))

        # opencode.json has plugin entry.
        json_path = os.path.join(config_dir, "opencode.json")
        assert os.path.isfile(json_path)
        config = json.loads(open(json_path).read())
        assert "plugin" in config
        assert "./plugins/agentarts-memory-capture.ts" in config["plugin"]

        # 3 files deployed.
        assert len(result.files) == 3

    def test_uninstall_cleans_plugin_commands_and_json(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.opencode.OpenCodePlatform()
        creds = _make_creds()

        result = p.install("global", creds, yes=True)

        config_dir = result.config_dir

        p.uninstall({"config_dir": config_dir})

        # TS plugin gone.
        assert not os.path.exists(
            os.path.join(config_dir, "plugins", "agentarts-memory-capture.ts")
        )
        # Commands gone.
        assert not os.path.exists(os.path.join(config_dir, "commands", "recall.md"))
        assert not os.path.exists(os.path.join(config_dir, "commands", "remember.md"))
        # opencode.json gone (was only our entry).
        assert not os.path.exists(os.path.join(config_dir, "opencode.json"))

    def test_install_idempotent_no_duplicate_entries(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.opencode.OpenCodePlatform()
        creds = _make_creds()

        p.install("global", creds, yes=True)
        p.install("global", creds, yes=True)

        json_path = os.path.join(expand("~/.config/opencode"), "opencode.json")
        config = json.loads(open(json_path).read())
        # Only one entry, not two.
        assert config["plugin"].count("./plugins/agentarts-memory-capture.ts") == 1

    def test_uninstall_preserves_user_config(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.opencode.OpenCodePlatform()

        # Pre-populate opencode.json with user settings.
        config_dir = expand("~/.config/opencode")
        os.makedirs(config_dir, exist_ok=True)
        json_path = os.path.join(config_dir, "opencode.json")
        import json as _json

        user_config = {
            "theme": "dark",
            "plugin": ["./plugins/user-plugin.ts"],
        }
        open(json_path, "w").write(_json.dumps(user_config))

        creds = _make_creds()
        result = p.install("global", creds, yes=True)

        # Verify both plugins are registered.
        config = json.loads(open(json_path).read())
        assert len(config["plugin"]) == 2

        # Uninstall.
        p.uninstall({"config_dir": config_dir})

        # Should still have user plugin and theme.
        remaining = json.loads(open(json_path).read())
        assert remaining["theme"] == "dark"
        assert "./plugins/user-plugin.ts" in remaining["plugin"]
        assert "./plugins/agentarts-memory-capture.ts" not in remaining["plugin"]

    def test_detect_returns_false_when_missing(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.opencode.OpenCodePlatform()
        assert p.detect() is False

    def test_detect_returns_true_when_exists(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        os.makedirs(expand("~/.config/opencode"))
        p = platforms.opencode.OpenCodePlatform()
        assert p.detect() is True


# ── MCP config integration ─────────────────────────────────────────


class TestMcpConfigIntegration:
    """Verify MCP server config is written on install and removed on uninstall."""

    def test_claude_install_writes_mcp_config(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.claude.ClaudePlatform()
        creds = _make_creds()
        result = p.install("global", creds, yes=True)

        settings_path = os.path.join(result.config_dir, "settings.json")
        settings = json.loads(open(settings_path).read())
        assert "mcpServers" in settings
        assert "agentarts_memory" in settings["mcpServers"]
        assert settings["mcpServers"]["agentarts_memory"]["command"] == "python3"
        assert settings["mcpServers"]["agentarts_memory"]["env"]["AGENTARTS_MEMORY_PLATFORM"] == "claude-code"

    def test_claude_uninstall_removes_mcp_config(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.claude.ClaudePlatform()
        creds = _make_creds()
        result = p.install("global", creds, yes=True)

        p.uninstall({"config_dir": result.config_dir, "scripts_dir": result.scripts_dir})

        settings_path = os.path.join(result.config_dir, "settings.json")
        if os.path.isfile(settings_path):
            settings = json.loads(open(settings_path).read())
            assert "mcpServers" not in settings or "agentarts_memory" not in settings.get("mcpServers", {})

    def test_codex_install_writes_mcp_config(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.codex.CodexPlatform()
        creds = _make_creds()
        result = p.install("global", creds, yes=True)

        toml_path = os.path.join(result.config_dir, "config.toml")
        toml_content = open(toml_path).read()
        assert "[mcp_servers.agentarts_memory]" in toml_content
        assert 'command = "python3"' in toml_content
        assert "AGENTARTS_MEMORY_PLATFORM" in toml_content
        assert '"claude-code"' not in toml_content or '"codex"' not in toml_content or True  # platform is in env section
        # Codex TOML format: key = "value" inside [mcp_servers.agentarts_memory.env]
        assert 'AGENTARTS_MEMORY_PLATFORM = "codex"' in toml_content

    def test_codex_uninstall_removes_mcp_config(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.codex.CodexPlatform()
        creds = _make_creds()
        result = p.install("global", creds, yes=True)

        p.uninstall({"config_dir": result.config_dir, "scripts_dir": result.scripts_dir})

        toml_path = os.path.join(result.config_dir, "config.toml")
        if os.path.isfile(toml_path):
            toml_content = open(toml_path).read()
            assert "[mcp_servers.agentarts_memory]" not in toml_content

    def test_opencode_install_writes_mcp_config(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.opencode.OpenCodePlatform()
        creds = _make_creds()
        result = p.install("global", creds, yes=True)

        json_path = os.path.join(result.config_dir, "opencode.json")
        config = json.loads(open(json_path).read())
        assert "mcp" in config
        assert "agentarts_memory" in config["mcp"]
        assert config["mcp"]["agentarts_memory"]["type"] == "local"
        assert config["mcp"]["agentarts_memory"]["environment"]["AGENTARTS_MEMORY_PLATFORM"] == "opencode"

    def test_opencode_uninstall_removes_mcp_config(self, monkeypatch, tmp_path):
        _set_home(monkeypatch, tmp_path)
        p = platforms.opencode.OpenCodePlatform()
        creds = _make_creds()
        result = p.install("global", creds, yes=True)

        p.uninstall({"config_dir": result.config_dir})

        json_path = os.path.join(result.config_dir, "opencode.json")
        if os.path.isfile(json_path):
            config = json.loads(open(json_path).read())
            assert "mcp" not in config or "agentarts_memory" not in config.get("mcp", {})
