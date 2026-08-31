"""Tests for utils.py — assets, config, manifest, and helpers (merged)."""

import json
import os

import sys
import pytest
from agentarts.toolkit.plugins.memory.installer import utils
from agentarts.toolkit.plugins.memory.installer.utils import (
    DEFAULT_REGION,
    ENV_API_KEY,
    ENV_REGION,
    ENV_SPACE_ID,
    EscapeInterrupt,
    add,
    check_env,
    claude_hooks_template,
    code_agent_scripts,
    code_agent_source,
    codex_hooks_template,
    confirm,
    ensure_credentials,
    expand,
    find,
    get_shell_rc,
    hermes_files,
    hermes_source,
    interactive_fill,
    list_all,
    load,
    manifest_path,
    merge_hooks,
    merge_toml_features,
    opencode_files,
    plugins_root,
    prompt_input,
    read_json,
    remove,
    remove_hooks_key,
    remove_if_empty,
    repo_root,
    select_one,
    strip_env_keys,
    strip_hooks,
    strip_json5,
    strip_toml_feature,
    validate_api_key,
    validate_region,
    validate_space_id,
    write_env_file,
    write_json_atomic,
    write_shell_rc,
    _mask_api_key,
)


class TestPaths:
    def test_repo_root_is_parent_of_plugins(self):
        assert plugins_root().startswith(repo_root())

    def test_plugins_root_exists(self):
        assert os.path.isdir(plugins_root())

    def test_hermes_source_exists(self):
        assert os.path.isdir(hermes_source())

    def test_code_agent_source_exists(self):
        assert os.path.isdir(code_agent_source())


class TestHermesFiles:
    def test_returns_three_files(self):
        files = hermes_files()
        assert len(files) == 3

    def test_files_exist(self):
        for f in hermes_files():
            assert os.path.isfile(f), f"Missing: {f}"

    def test_no_cli_py(self):
        files = hermes_files()
        for f in files:
            assert "cli.py" not in f

    def test_contains_expected_names(self):
        files = hermes_files()
        names = [os.path.basename(f) for f in files]
        assert "provider.py" in names
        assert "plugin.yaml" in names
        assert "__init__.py" in names


class TestCodeAgentScripts:
    def test_returns_three(self):
        scripts = code_agent_scripts()
        assert len(scripts) == 3

    def test_scripts_exist(self):
        for s in code_agent_scripts():
            assert os.path.isfile(s), f"Missing: {s}"

    def test_contains_shared(self):
        scripts = code_agent_scripts()
        names = [os.path.basename(s) for s in scripts]
        assert "_shared.mjs" in names

    def test_contains_all_expected(self):
        expected = [
            "_shared.mjs",
            "prompt-submit.mjs",
            "pre-compact.mjs",
        ]
        scripts = code_agent_scripts()
        names = [os.path.basename(s) for s in scripts]
        for name in expected:
            assert name in names, f"Missing script: {name}"


class TestHooksTemplates:
    def test_claude_template_exists(self):
        assert os.path.isfile(claude_hooks_template())

    def test_codex_template_exists(self):
        assert os.path.isfile(codex_hooks_template())


class TestOpenCodeFiles:
    def test_returns_three_entries(self):
        files = opencode_files()
        assert len(files) == 3

    def test_all_source_files_exist(self):
        for rel, src in opencode_files().items():
            assert os.path.isfile(src), f"Missing: {src}"

    def test_keys_are_relative_paths(self):
        files = opencode_files()
        assert "plugins/agentarts-memory-capture.ts" in files
        assert "commands/recall.md" in files
        assert "commands/remember.md" in files


# ── Validators ───────────────────────────────────────────────────────


class TestValidateSpaceId:
    def test_empty(self):
        ok, msg = validate_space_id("")
        assert not ok
        assert "empty" in msg

    def test_too_short(self):
        ok, msg = validate_space_id("abc")
        assert not ok
        assert "8" in msg

    def test_valid(self):
        ok, val = validate_space_id("  my-space-12345  ")
        assert ok
        assert val == "my-space-12345"


class TestValidateApiKey:
    def test_empty(self):
        ok, msg = validate_api_key("")
        assert not ok

    def test_too_short(self):
        ok, msg = validate_api_key("shortkey12345")  # 13 chars
        assert not ok
        assert "16" in msg

    def test_valid(self):
        ok, val = validate_api_key("  abcdefghijklmnop123456  ")
        assert ok
        assert val == "abcdefghijklmnop123456"


class TestValidateRegion:
    def test_empty_defaults(self):
        ok, val = validate_region("")
        assert ok
        assert val == DEFAULT_REGION

    def test_valid(self):
        ok, val = validate_region("cn-north-4")
        assert ok
        assert val == "cn-north-4"

    def test_invalid_format(self):
        ok, msg = validate_region("invalid")
        assert not ok
        assert "format" in msg.lower()

    def test_two_parts_invalid(self):
        ok, msg = validate_region("cn-north")
        assert not ok


# ── check_env ───────────────────────────────────────────────────────


class TestCheckEnv:
    def test_all_missing(self, monkeypatch):
        monkeypatch.delenv(ENV_SPACE_ID, raising=False)
        monkeypatch.delenv(ENV_API_KEY, raising=False)
        monkeypatch.delenv(ENV_REGION, raising=False)
        ok, cfg = check_env()
        assert not ok
        assert ENV_REGION in cfg
        assert cfg[ENV_REGION] == DEFAULT_REGION

    def test_all_set_valid(self, monkeypatch):
        monkeypatch.setenv(ENV_SPACE_ID, "my-space-12345")
        monkeypatch.setenv(ENV_API_KEY, "abcdefghijklmnop123456")
        monkeypatch.setenv(ENV_REGION, "cn-north-4")
        ok, cfg = check_env()
        assert ok
        assert cfg[ENV_SPACE_ID] == "my-space-12345"
        assert cfg[ENV_REGION] == "cn-north-4"

    def test_invalid_values_fail(self, monkeypatch):
        monkeypatch.setenv(ENV_SPACE_ID, "short")
        monkeypatch.setenv(ENV_API_KEY, "short")
        ok, cfg = check_env()
        assert not ok


# ── interactive_fill ─────────────────────────────────────────────────


class TestInteractiveFill:
    def test_yes_mode_returns_defaults(self):
        filled = interactive_fill([ENV_SPACE_ID, ENV_API_KEY], yes=True)
        assert filled[ENV_SPACE_ID] == ""
        assert filled[ENV_API_KEY] == ""

    def test_yes_mode_region_default(self):
        filled = interactive_fill([ENV_REGION], yes=True)
        assert filled[ENV_REGION] == DEFAULT_REGION


# ── ensure_credentials (--yes mode) ─────────────────────────────────


class TestEnsureCredentials:
    def test_with_env_set(self, monkeypatch):
        monkeypatch.setenv(ENV_SPACE_ID, "my-space-12345")
        monkeypatch.setenv(ENV_API_KEY, "abcdefghijklmnop123456")
        monkeypatch.setenv(ENV_REGION, "cn-north-4")
        cfg = ensure_credentials(yes=True)
        assert cfg[ENV_SPACE_ID] == "my-space-12345"
        assert cfg[ENV_API_KEY] == "abcdefghijklmnop123456"

    def test_missing_in_yes_mode_no_crash(self, monkeypatch):
        monkeypatch.delenv(ENV_SPACE_ID, raising=False)
        monkeypatch.delenv(ENV_API_KEY, raising=False)
        # Should not crash even if missing in yes mode.
        cfg = ensure_credentials(yes=True)
        assert ENV_SPACE_ID in cfg


class TestEnsureCredentialsRegionPrompt:
    def test_region_prompted_when_unset_interactive(self, monkeypatch):
        """In interactive mode, region is prompted (with default) when unset."""
        monkeypatch.setenv(ENV_SPACE_ID, "my-space-12345")
        monkeypatch.setenv(ENV_API_KEY, "abcdefghijklmnop123456")
        monkeypatch.delenv(ENV_REGION, raising=False)

        calls = []

        def fake_prompt_input(prompt, default=""):
            calls.append({"prompt": prompt, "default": default})
            return default

        monkeypatch.setattr(utils, "prompt_input", fake_prompt_input)
        monkeypatch.setattr(utils, "confirm", lambda *a, **k: False)
        monkeypatch.setattr(utils, "write_shell_rc", lambda *a, **k: None)

        cfg = ensure_credentials(yes=False)

        assert cfg[ENV_REGION] == DEFAULT_REGION
        assert any(c["default"] == DEFAULT_REGION for c in calls)

    def test_region_not_prompted_when_set_in_env(self, monkeypatch):
        """When region is already set in env, it is not prompted."""
        monkeypatch.setenv(ENV_SPACE_ID, "my-space-12345")
        monkeypatch.setenv(ENV_API_KEY, "abcdefghijklmnop123456")
        monkeypatch.setenv(ENV_REGION, "cn-north-4")

        def fail_prompt(*a, **k):
            raise AssertionError("prompt_input should not be called")

        monkeypatch.setattr(utils, "prompt_input", fail_prompt)
        # User accepts existing configuration.
        monkeypatch.setattr(utils, "confirm", lambda *a, **k: True)

        cfg = ensure_credentials(yes=False)

        assert cfg[ENV_REGION] == "cn-north-4"

    def test_region_not_prompted_in_yes_mode(self, monkeypatch):
        """In --yes mode, region is never prompted (uses default)."""
        monkeypatch.setenv(ENV_SPACE_ID, "my-space-12345")
        monkeypatch.setenv(ENV_API_KEY, "abcdefghijklmnop123456")
        monkeypatch.delenv(ENV_REGION, raising=False)

        def fail_prompt(*a, **k):
            raise AssertionError("prompt_input should not be called in --yes mode")

        monkeypatch.setattr(utils, "prompt_input", fail_prompt)

        cfg = ensure_credentials(yes=True)

        assert cfg[ENV_REGION] == DEFAULT_REGION


# ── Shell rc helpers ─────────────────────────────────────────────────


class TestShellRc:
    def test_get_shell_rc_zsh(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.setenv("HOME", "/home/test")
        assert get_shell_rc() == "/home/test/.zshrc"

    def test_get_shell_rc_bash(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/bash")
        monkeypatch.setenv("HOME", "/home/test")
        assert get_shell_rc() == "/home/test/.bashrc"

    def test_write_shell_rc_dedup(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("SHELL", "/bin/zsh")
        rc = str(tmp_path / ".zshrc")
        # Write once.
        write_shell_rc({ENV_API_KEY: "secret1"})
        # Write again — should update, not duplicate.
        write_shell_rc({ENV_API_KEY: "secret2"})
        content = open(rc).read()
        assert "secret2" in content
        assert "secret1" not in content
        # Only one export line for the key.
        assert content.count(f"export {ENV_API_KEY}=") == 1


def _set_tmp_home(monkeypatch, tmp_path):
    """Redirect manifest to tmp HOME."""
    monkeypatch.setenv("HOME", str(tmp_path))


class TestLoad:
    def test_nonexistent_returns_skeleton(self, monkeypatch, tmp_path):
        _set_tmp_home(monkeypatch, tmp_path)
        data = load()
        assert data["version"] == 1
        assert data["installs"] == []

    def test_manifest_path(self, monkeypatch, tmp_path):
        _set_tmp_home(monkeypatch, tmp_path)
        assert str(tmp_path) in manifest_path()
        assert manifest_path().endswith("installed.json")


class TestAddRemove:
    def test_add_then_load(self, monkeypatch, tmp_path):
        _set_tmp_home(monkeypatch, tmp_path)
        entry = {
            "platform": "hermes",
            "scope": "global",
            "config_dir": "/home/x/.hermes/plugins/agentarts",
            "scripts_dir": "",
            "files": ["/path/to/provider.py"],
            "config_files": ["/path/to/agentarts.json"],
        }
        add(entry)
        data = load()
        assert len(data["installs"]) == 1
        assert data["installs"][0]["platform"] == "hermes"
        assert "installed_at" in data["installs"][0]

    def test_add_idempotent(self, monkeypatch, tmp_path):
        _set_tmp_home(monkeypatch, tmp_path)
        entry = {
            "platform": "claude",
            "scope": "global",
            "config_dir": "/home/x/.claude",
            "scripts_dir": "/home/x/.claude/agentarts-memory/scripts",
            "files": [],
            "config_files": [],
        }
        add(entry)
        add(entry)  # re-add should not duplicate
        data = load()
        assert len(data["installs"]) == 1

    def test_add_multiple_platforms(self, monkeypatch, tmp_path):
        _set_tmp_home(monkeypatch, tmp_path)
        add(
            {
                "platform": "hermes",
                "scope": "global",
                "config_dir": "/a",
                "scripts_dir": "",
                "files": [],
                "config_files": [],
            }
        )
        add(
            {
                "platform": "claude",
                "scope": "global",
                "config_dir": "/b",
                "scripts_dir": "/b/scripts",
                "files": [],
                "config_files": [],
            }
        )
        data = load()
        assert len(data["installs"]) == 2

    def test_remove_returns_entry(self, monkeypatch, tmp_path):
        _set_tmp_home(monkeypatch, tmp_path)
        entry = {
            "platform": "codex",
            "scope": "project",
            "config_dir": "/c/.codex",
            "scripts_dir": "/c/.codex/agentarts-memory/scripts",
            "files": [],
            "config_files": [],
        }
        add(entry)
        removed = remove("codex", "project", "/c/.codex")
        assert removed is not None
        assert removed["platform"] == "codex"
        data = load()
        assert len(data["installs"]) == 0

    def test_remove_nonexistent_returns_none(self, monkeypatch, tmp_path):
        _set_tmp_home(monkeypatch, tmp_path)
        removed = remove("nonexistent", "global", "/nope")
        assert removed is None

    def test_remove_cleans_up_empty_manifest_file(self, monkeypatch, tmp_path):
        _set_tmp_home(monkeypatch, tmp_path)
        add(
            {
                "platform": "hermes",
                "scope": "global",
                "config_dir": "/a",
                "scripts_dir": "",
                "files": [],
                "config_files": [],
            }
        )
        remove("hermes", "global", "/a")
        assert not os.path.exists(manifest_path())


class TestFind:
    def test_find_by_platform(self, monkeypatch, tmp_path):
        _set_tmp_home(monkeypatch, tmp_path)
        add(
            {
                "platform": "claude",
                "scope": "global",
                "config_dir": "/x/.claude",
                "scripts_dir": "/x/.claude/agentarts-memory/scripts",
                "files": [],
                "config_files": [],
            }
        )
        result = find("claude")
        assert result is not None
        assert result["platform"] == "claude"

    def test_find_by_platform_scope_configdir(self, monkeypatch, tmp_path):
        _set_tmp_home(monkeypatch, tmp_path)
        add(
            {
                "platform": "claude",
                "scope": "global",
                "config_dir": "/x/.claude",
                "scripts_dir": "/x/.claude/agentarts-memory/scripts",
                "files": [],
                "config_files": [],
            }
        )
        # Match all.
        assert find("claude", "global", "/x/.claude") is not None
        # Mismatch scope.
        assert find("claude", "project", "/x/.claude") is None
        # Mismatch config_dir.
        assert find("claude", "global", "/wrong") is None

    def test_find_nonexistent(self, monkeypatch, tmp_path):
        _set_tmp_home(monkeypatch, tmp_path)
        assert find("bogus") is None


class TestListAll:
    def test_empty(self, monkeypatch, tmp_path):
        _set_tmp_home(monkeypatch, tmp_path)
        assert list_all() == []

    def test_multiple(self, monkeypatch, tmp_path):
        _set_tmp_home(monkeypatch, tmp_path)
        for i, plat in enumerate(["hermes", "claude", "codex"]):
            add(
                {
                    "platform": plat,
                    "scope": "global",
                    "config_dir": f"/dir{i}",
                    "scripts_dir": "",
                    "files": [],
                    "config_files": [],
                }
            )
        all_installs = list_all()
        assert len(all_installs) == 3


# ── expand ───────────────────────────────────────────────────────────


class TestExpand:
    def test_tilde(self, monkeypatch):
        monkeypatch.setenv("HOME", "/home/test")
        assert expand("~/.claude") == "/home/test/.claude"

    def test_env_var(self, monkeypatch):
        monkeypatch.setenv("FOO", "/bar")
        assert expand("$FOO/baz") == "/bar/baz"

    def test_no_expansion_needed(self):
        assert expand("/usr/local/bin") == "/usr/local/bin"


# ── strip_json5 ──────────────────────────────────────────────────────


class TestStripJson5:
    def test_line_comment(self):
        text = '{ "a": 1 // comment\n}'
        assert json.loads(strip_json5(text)) == {"a": 1}

    def test_block_comment(self):
        text = '{ "a": /* block */ 1 }'
        assert json.loads(strip_json5(text)) == {"a": 1}

    def test_trailing_comma_object(self):
        text = '{"a": 1, "b": 2,}'
        assert json.loads(strip_json5(text)) == {"a": 1, "b": 2}

    def test_trailing_comma_array(self):
        text = "[1, 2, 3,]"
        assert json.loads(strip_json5(text)) == [1, 2, 3]

    def test_url_in_string_preserved(self):
        text = '{"url": "http://example.com"}'
        assert json.loads(strip_json5(text)) == {"url": "http://example.com"}

    def test_escaped_quote_in_string(self):
        text = '{"a": "he said \\"hi\\""}'
        assert json.loads(strip_json5(text))["a"] == 'he said "hi"'


# ── read_json / write_json_atomic ────────────────────────────────────


class TestJsonIO:
    def test_read_nonexistent_returns_empty(self, tmp_path):
        assert read_json(str(tmp_path / "nope.json")) == {}

    def test_read_with_comments(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text('{\n  // comment\n  "a": 1,\n}', encoding="utf-8")
        assert read_json(str(p)) == {"a": 1}

    def test_write_then_read_roundtrip(self, tmp_path):
        p = str(tmp_path / "out.json")
        data = {"hooks": {"Event": [{"hooks": [{"command": "echo"}]}]}}
        write_json_atomic(p, data)
        assert read_json(p) == data

    def test_atomic_write_preserves_other_keys(self, tmp_path):
        p = str(tmp_path / "settings.json")
        original = {"permissions": {"allow": ["*"]}, "hooks": {}}
        write_json_atomic(p, original)
        updated = dict(original)
        updated["hooks"] = {"NewEvent": []}
        write_json_atomic(p, updated)
        result = read_json(p)
        assert "permissions" in result
        assert result["hooks"]["NewEvent"] == []


# ── merge_hooks / strip_hooks ────────────────────────────────────────


SAMPLE_HOOKS_TEMPLATE = {
    "hooks": {
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": 'node "/home/u/.claude/agentarts-memory/scripts/session-start.mjs"',
                    }
                ]
            }
        ],
        "PreToolUse": [
            {
                "matcher": "Edit|Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'node "/home/u/.claude/agentarts-memory/scripts/pre-tool-use.mjs"',
                    }
                ],
            }
        ],
    }
}

SCRIPTS_DIR = "/home/u/.claude/agentarts-memory/scripts"


class TestMergeStripHooks:
    def test_merge_into_empty(self):
        result = merge_hooks({}, SAMPLE_HOOKS_TEMPLATE, SCRIPTS_DIR)
        assert "hooks" in result
        assert "SessionStart" in result["hooks"]
        assert "PreToolUse" in result["hooks"]

    def test_merge_preserves_other_keys(self):
        existing = {"permissions": {"allow": ["*"]}}
        result = merge_hooks(existing, SAMPLE_HOOKS_TEMPLATE, SCRIPTS_DIR)
        assert "permissions" in result
        assert "hooks" in result

    def test_merge_idempotent(self):
        # Merge twice — should not duplicate.
        once = merge_hooks({}, SAMPLE_HOOKS_TEMPLATE, SCRIPTS_DIR)
        twice = merge_hooks(once, SAMPLE_HOOKS_TEMPLATE, SCRIPTS_DIR)
        assert once == twice

    def test_strip_returns_to_empty(self):
        merged = merge_hooks({}, SAMPLE_HOOKS_TEMPLATE, SCRIPTS_DIR)
        stripped = strip_hooks(merged["hooks"], SCRIPTS_DIR)
        assert stripped == {}

    def test_strip_preserves_user_hooks(self):
        existing = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {"type": "command", "command": "echo user-hook"},
                            {
                                "type": "command",
                                "command": f'node "{SCRIPTS_DIR}/session-start.mjs"',
                            },
                        ]
                    }
                ],
                "Stop": [{"hooks": [{"type": "command", "command": "echo keep"}]}],
            }
        }
        merged = merge_hooks(existing, SAMPLE_HOOKS_TEMPLATE, SCRIPTS_DIR)
        # After merge: SessionStart has 2 groups (user group stripped + our group).
        ss_groups = merged["hooks"]["SessionStart"]
        assert len(ss_groups) == 2
        # Group 0 = user hook (our hook stripped from it).
        assert len(ss_groups[0]["hooks"]) == 1
        assert "echo user-hook" in ss_groups[0]["hooks"][0]["command"]
        # Group 1 = our incoming hook.
        assert SCRIPTS_DIR in ss_groups[1]["hooks"][0]["command"]
        # Strip should remove our group but keep user's.
        stripped = remove_hooks_key(merged, SCRIPTS_DIR)
        ss_after = stripped["hooks"]["SessionStart"][0]["hooks"]
        assert len(ss_after) == 1
        assert "echo user-hook" in ss_after[0]["command"]
        assert "Stop" in stripped["hooks"]

    def test_strip_removes_empty_event(self):
        merged = merge_hooks({}, SAMPLE_HOOKS_TEMPLATE, SCRIPTS_DIR)
        result = remove_hooks_key(merged, SCRIPTS_DIR)
        assert "hooks" not in result

    def test_strip_removes_empty_hook_group(self):
        existing = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "Edit",
                        "hooks": [
                            {
                                "type": "command",
                                "command": f'node "{SCRIPTS_DIR}/session-start.mjs"',
                            }
                        ],
                    }
                ]
            }
        }
        result = remove_hooks_key(existing, SCRIPTS_DIR)
        assert "hooks" not in result


# ── TOML merge / strip ───────────────────────────────────────────────


class TestTomlMerge:
    def test_add_to_empty(self):
        result = merge_toml_features("", "hooks", "true")
        assert "[features]" in result
        assert "hooks = true" in result

    def test_add_to_existing_no_features(self):
        text = '[other]\nkey = "val"\n'
        result = merge_toml_features(text, "hooks", "true")
        assert "[features]" in result
        assert "hooks = true" in result
        assert "[other]" in result
        assert 'key = "val"' in result

    def test_add_to_existing_features(self):
        text = "[features]\nother_key = false\n"
        result = merge_toml_features(text, "hooks", "true")
        assert "other_key = false" in result
        assert "hooks = true" in result

    def test_update_existing_key(self):
        text = "[features]\nhooks = false\n"
        result = merge_toml_features(text, "hooks", "true")
        assert "hooks = true" in result
        assert "hooks = false" not in result

    def test_removes_deprecated_keys(self):
        text = "[features]\ncodex_hooks = true\nother_key = false\n"
        result = merge_toml_features(text, "hooks", "true", deprecated_keys=["codex_hooks"])
        assert "codex_hooks" not in result
        assert "hooks = true" in result
        assert "other_key = false" in result

    def test_removes_deprecated_and_updates_existing(self):
        text = "[features]\ncodex_hooks = true\nhooks = false\n"
        result = merge_toml_features(text, "hooks", "true", deprecated_keys=["codex_hooks"])
        assert "codex_hooks" not in result
        assert "hooks = true" in result
        assert "hooks = false" not in result

    def test_strip_removes_key(self):
        text = "[features]\nhooks = true\nother_key = false\n"
        result = strip_toml_feature(text, "hooks")
        assert "hooks" not in result
        assert "other_key = false" in result

    def test_strip_removes_empty_section(self):
        text = "[features]\nhooks = true\n"
        result = strip_toml_feature(text, "hooks")
        assert "[features]" not in result

    def test_roundtrip(self):
        text = "[other]\nfoo = 1\n"
        merged = merge_toml_features(text, "hooks", "true")
        stripped = strip_toml_feature(merged, "hooks")
        assert "hooks" not in stripped
        assert "foo = 1" in stripped

    def test_preserves_other_sections_after(self):
        text = "[features]\nhooks = true\n\n[other]\nbar = 2\n"
        result = strip_toml_feature(text, "hooks")
        assert "[other]" in result
        assert "bar = 2" in result
        assert "[features]" not in result


# ── .env file ────────────────────────────────────────────────────────


class TestEnvFile:
    def test_write_new(self, tmp_path):
        p = str(tmp_path / ".env")
        write_env_file(p, {"API_KEY": "secret123"})
        content = open(p).read()
        assert "API_KEY=secret123" in content

    def test_dedup_update(self, tmp_path):
        p = str(tmp_path / ".env")
        write_env_file(p, {"API_KEY": "old", "SPACE": "s1"})
        write_env_file(p, {"API_KEY": "new"})
        content = open(p).read()
        assert "API_KEY=new" in content
        assert "API_KEY=old" not in content
        assert "SPACE=s1" in content

    def test_preserves_comments(self, tmp_path):
        p = str(tmp_path / ".env")
        open(p, "w").write("# comment line\nAPI_KEY=old\n")
        write_env_file(p, {"API_KEY": "new"})
        content = open(p).read()
        assert "# comment line" in content
        assert "API_KEY=new" in content

    def test_strip_keys(self, tmp_path):
        p = str(tmp_path / ".env")
        write_env_file(p, {"API_KEY": "val", "REGION": "cn-test-1"})
        strip_env_keys(p, ["API_KEY"])
        content = open(p).read()
        assert "API_KEY" not in content
        assert "REGION=cn-test-1" in content

    def test_strip_all_keys_removes_file(self, tmp_path):
        p = str(tmp_path / ".env")
        write_env_file(p, {"API_KEY": "val"})
        strip_env_keys(p, ["API_KEY"])
        assert not os.path.exists(p)


# ── remove_if_empty ──────────────────────────────────────────────────


class TestRemoveIfEmpty:
    def test_empty_file_removed(self, tmp_path):
        p = tmp_path / "empty.txt"
        p.write_text("")
        remove_if_empty(str(p))
        assert not p.exists()

    def test_nonempty_file_kept(self, tmp_path):
        p = tmp_path / "data.txt"
        p.write_text("data")
        remove_if_empty(str(p))
        assert p.exists()

    def test_empty_dir_removed(self, tmp_path):
        d = tmp_path / "emptydir"
        d.mkdir()
        remove_if_empty(str(d))
        assert not d.exists()

    def test_nonempty_dir_kept(self, tmp_path):
        d = tmp_path / "nonempty"
        d.mkdir()
        (d / "file.txt").write_text("data")
        remove_if_empty(str(d))
        assert d.exists()


# ── Interactive prompts (with --yes) ─────────────────────────────────


class TestInteractive:
    def test_confirm_yes_flag(self):
        utils.set_yes(True)
        assert confirm("test?", default=True) is True
        assert confirm("test?", default=False) is False
        utils.set_yes(False)

    def test_prompt_input_yes_flag(self):
        utils.set_yes(True)
        assert prompt_input("enter", default="fallback") == "fallback"
        utils.set_yes(False)

    def test_select_one_yes_flag(self):
        utils.set_yes(True)
        assert select_one("pick", ["a", "b"], default_idx=1) == 1
        utils.set_yes(False)


class TestEscapeInterrupt:
    """ESC during interactive prompts should exit the program."""

    def test_confirm_propagates_escape(self, monkeypatch):
        """confirm() must not swallow EscapeInterrupt."""
        utils.set_yes(False)
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        monkeypatch.setattr(
            utils, "_input_with_esc", lambda prompt: (_ for _ in ()).throw(EscapeInterrupt())
        )
        with pytest.raises(EscapeInterrupt):
            confirm("test?", default=True)

    def test_prompt_input_propagates_escape(self, monkeypatch):
        utils.set_yes(False)
        monkeypatch.setattr(
            utils, "_input_with_esc", lambda prompt: (_ for _ in ()).throw(EscapeInterrupt())
        )
        with pytest.raises(EscapeInterrupt):
            prompt_input("enter")

    def test_select_one_propagates_escape(self, monkeypatch):
        utils.set_yes(False)
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        monkeypatch.setattr(
            utils, "_input_with_esc", lambda prompt: (_ for _ in ()).throw(EscapeInterrupt())
        )
        with pytest.raises(EscapeInterrupt):
            select_one("pick", ["a", "b"])

    def test_input_with_esc_fallback_no_tty(self, monkeypatch):
        """When _HAS_TTY is False, _input_with_esc falls back to input()."""
        monkeypatch.setattr(utils, "_HAS_TTY", False)
        monkeypatch.setattr("builtins.input", lambda prompt: "hello")
        result = utils._input_with_esc("prompt: ")
        assert result == "hello"


# -- _command_contains_scripts_dir (cross-platform slash matching) --


class TestCommandContainsScriptsDir:
    """Verify mixed-slash matching for hook command lookup.

    On Windows, scripts_dir uses backslashes but commands are written
    with forward slashes (see _load_hooks_template).  The matching
    function must normalize both sides before comparing.
    """

    def test_forward_slash_match(self):
        entry = {"command": 'node "/home/u/.codex/agentarts-memory/scripts/prompt-submit.mjs"'}
        assert utils._command_contains_scripts_dir(entry, "/home/u/.codex/agentarts-memory/scripts")

    def test_backslash_scripts_dir_matches_forward_slash_cmd(self):
        """Windows scripts_dir (backslashes) matches forward-slash command."""
        entry = {
            "command": 'node "C:/Users/test/.codex/agentarts-memory/scripts/prompt-submit.mjs"'
        }
        win_scripts_dir = r"C:\Users\test\.codex\agentarts-memory\scripts"
        assert utils._command_contains_scripts_dir(entry, win_scripts_dir)

    def test_backslash_cmd_matches_forward_slash_scripts_dir(self):
        """Forward-slash scripts_dir matches backslash command (legacy file)."""
        entry = {
            "command": r'node "C:\Users\test\.codex\agentarts-memory\scripts\prompt-submit.mjs"'
        }
        scripts_dir = "C:/Users/test/.codex/agentarts-memory/scripts"
        assert utils._command_contains_scripts_dir(entry, scripts_dir)

    def test_no_match_unrelated_command(self):
        entry = {"command": "echo hello"}
        assert not utils._command_contains_scripts_dir(
            entry, "/home/u/.codex/agentarts-memory/scripts"
        )

    def test_no_match_different_scripts_dir(self):
        entry = {"command": 'node "/other/path/scripts/prompt-submit.mjs"'}
        assert not utils._command_contains_scripts_dir(
            entry, "/home/u/.codex/agentarts-memory/scripts"
        )


# -- Shell rc: Windows behavior --


class TestShellRcWindows:
    """On Windows, get_shell_rc returns empty and write_shell_rc uses setx."""

    def test_get_shell_rc_returns_empty_on_windows(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        assert get_shell_rc() == ""

    def test_write_shell_rc_uses_setx_on_windows(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "win32")
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)

        monkeypatch.setattr("subprocess.run", fake_run)
        write_shell_rc({ENV_API_KEY: "secret123", ENV_SPACE_ID: "space-12345"})
        assert len(calls) == 2
        assert calls[0] == ["setx", ENV_API_KEY, "secret123"]
        assert calls[1] == ["setx", ENV_SPACE_ID, "space-12345"]

    def test_get_shell_rc_unix_unchanged(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "darwin")
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.setenv("HOME", "/home/test")
        assert get_shell_rc() == "/home/test/.zshrc"


# -- _mask_api_key --


class TestMaskApiKey:
    def test_shows_first_6_and_last_4(self):
        assert _mask_api_key("abcdefghijklmnop123456") == "abcdef***3456"

    def test_short_value_all_masked(self):
        assert _mask_api_key("abc") == "***"

    def test_exact_6_chars(self):
        assert _mask_api_key("abcdef") == "******"

    def test_empty(self):
        assert _mask_api_key("") == ""


# -- ensure_credentials: existing config flow --


class TestEnsureCredentialsExistingConfig:
    """When all env vars exist, show them and ask whether to use or override."""

    def test_use_existing_skips_shell_rc(self, monkeypatch):
        """Accepting existing config does not prompt for shell rc."""
        monkeypatch.setenv(ENV_SPACE_ID, "my-space-12345")
        monkeypatch.setenv(ENV_API_KEY, "abcdefghijklmnop123456")
        monkeypatch.setenv(ENV_REGION, "cn-north-4")

        confirm_calls = []

        def track_confirm(prompt, default=True):
            confirm_calls.append(prompt)
            return True

        monkeypatch.setattr(utils, "confirm", track_confirm)
        monkeypatch.setattr(utils, "write_shell_rc", lambda *a, **k: None)

        cfg = ensure_credentials(yes=False)

        assert cfg[ENV_SPACE_ID] == "my-space-12345"
        assert cfg[ENV_API_KEY] == "abcdefghijklmnop123456"
        assert cfg[ENV_REGION] == "cn-north-4"
        assert any("Use existing" in c for c in confirm_calls)
        assert not any("Save configuration" in c for c in confirm_calls)

    def test_override_triggers_shell_rc(self, monkeypatch):
        """Overriding a value triggers the shell rc prompt."""
        monkeypatch.setenv(ENV_SPACE_ID, "my-space-12345")
        monkeypatch.setenv(ENV_API_KEY, "abcdefghijklmnop123456")
        monkeypatch.setenv(ENV_REGION, "cn-north-4")

        confirm_results = iter([False, True])
        monkeypatch.setattr(utils, "confirm", lambda *a, **k: next(confirm_results))

        def fake_prompt_input(prompt, default=""):
            if "API Key" in prompt:
                return "new-api-key-12345678"
            return default

        monkeypatch.setattr(utils, "prompt_input", fake_prompt_input)
        monkeypatch.setattr(utils, "write_shell_rc", lambda *a, **k: None)

        cfg = ensure_credentials(yes=False)

        assert cfg[ENV_API_KEY] == "new-api-key-12345678"
        assert cfg[ENV_SPACE_ID] == "my-space-12345"
        assert cfg[ENV_REGION] == "cn-north-4"

    def test_override_same_values_skips_shell_rc(self, monkeypatch):
        """Overriding but entering same values does not trigger shell rc."""
        monkeypatch.setenv(ENV_SPACE_ID, "my-space-12345")
        monkeypatch.setenv(ENV_API_KEY, "abcdefghijklmnop123456")
        monkeypatch.setenv(ENV_REGION, "cn-north-4")

        confirm_calls = []

        def track_confirm(prompt, default=True):
            confirm_calls.append(prompt)
            return False

        monkeypatch.setattr(utils, "confirm", track_confirm)
        monkeypatch.setattr(utils, "prompt_input", lambda prompt, default="": default)
        monkeypatch.setattr(utils, "write_shell_rc", lambda *a, **k: None)

        cfg = ensure_credentials(yes=False)

        assert cfg[ENV_SPACE_ID] == "my-space-12345"
        assert cfg[ENV_API_KEY] == "abcdefghijklmnop123456"
        assert cfg[ENV_REGION] == "cn-north-4"
        # "Use existing?" was asked, "Save configuration?" was NOT.
        assert any("Use existing" in c for c in confirm_calls)
        assert not any("Save configuration" in c for c in confirm_calls)

    def test_api_key_masked_in_display(self, monkeypatch):
        """API key is shown as first 6 + *** + last 4, not the full key."""
        monkeypatch.setenv(ENV_SPACE_ID, "my-space-12345")
        monkeypatch.setenv(ENV_API_KEY, "abcdefghijklmnop123456")
        monkeypatch.setenv(ENV_REGION, "cn-north-4")

        printed = []
        original_print = utils.console.print

        def track_print(*args, **kwargs):
            if args:
                printed.append(str(args[0]))
            original_print(*args, **kwargs)

        monkeypatch.setattr(utils.console, "print", track_print)
        monkeypatch.setattr(utils, "confirm", lambda *a, **k: True)
        monkeypatch.setattr(utils, "write_shell_rc", lambda *a, **k: None)

        ensure_credentials(yes=False)

        api_lines = [p for p in printed if "API Key" in p]
        assert any("abcdef***3456" in p for p in api_lines)
        assert not any("abcdefghijklmnop123456" in p for p in api_lines)

    def test_space_id_and_region_shown_full(self, monkeypatch):
        """Space ID and Region are shown in full, not masked."""
        monkeypatch.setenv(ENV_SPACE_ID, "my-space-12345")
        monkeypatch.setenv(ENV_API_KEY, "abcdefghijklmnop123456")
        monkeypatch.setenv(ENV_REGION, "cn-north-4")

        printed = []
        original_print = utils.console.print

        def track_print(*args, **kwargs):
            if args:
                printed.append(str(args[0]))
            original_print(*args, **kwargs)

        monkeypatch.setattr(utils.console, "print", track_print)
        monkeypatch.setattr(utils, "confirm", lambda *a, **k: True)
        monkeypatch.setattr(utils, "write_shell_rc", lambda *a, **k: None)

        ensure_credentials(yes=False)

        assert any("my-space-12345" in p for p in printed)
        assert any("cn-north-4" in p for p in printed)
