"""Tests for MCP config utility functions in utils.py."""

from __future__ import annotations

from agentarts.toolkit.plugins.memory.installer.utils import (
    ENV_API_KEY,
    ENV_REGION,
    ENV_SPACE_ID,
    MCP_SERVER_ARGS,
    MCP_SERVER_COMMAND,
    MCP_SERVER_NAME,
    build_mcp_env,
    merge_mcp_servers,
    merge_opencode_mcp,
    merge_toml_mcp_server,
    strip_mcp_servers,
    strip_opencode_mcp,
    strip_toml_mcp_server,
)


# ── merge_mcp_servers / strip_mcp_servers ─────────────────────────


class TestMergeStripMcpServers:
    def test_merge_adds_mcp_servers_key(self):
        settings = {"theme": "dark"}
        result = merge_mcp_servers(settings, "my_server", "python3", ["-m", "foo"], {"KEY": "val"})
        assert "mcpServers" in result
        assert result["mcpServers"]["my_server"]["command"] == "python3"
        assert result["mcpServers"]["my_server"]["args"] == ["-m", "foo"]
        assert result["mcpServers"]["my_server"]["env"]["KEY"] == "val"
        assert result["theme"] == "dark"

    def test_merge_is_idempotent(self):
        settings = {}
        result1 = merge_mcp_servers(settings, "srv", "python3", [], {})
        result2 = merge_mcp_servers(result1, "srv", "python3", [], {})
        assert list(result2["mcpServers"].keys()) == ["srv"]

    def test_merge_preserves_other_servers(self):
        settings = {"mcpServers": {"other": {"command": "node"}}}
        result = merge_mcp_servers(settings, "srv", "python3", [], {})
        assert "other" in result["mcpServers"]
        assert "srv" in result["mcpServers"]

    def test_strip_removes_server(self):
        settings = {"mcpServers": {"srv": {"command": "python3"}}, "theme": "dark"}
        result = strip_mcp_servers(settings, "srv")
        assert "mcpServers" not in result
        assert result["theme"] == "dark"

    def test_strip_preserves_other_servers(self):
        settings = {"mcpServers": {"srv": {}, "other": {"command": "node"}}}
        result = strip_mcp_servers(settings, "srv")
        assert "other" in result["mcpServers"]
        assert "srv" not in result["mcpServers"]

    def test_strip_when_no_mcp_servers(self):
        settings = {"theme": "dark"}
        result = strip_mcp_servers(settings, "srv")
        assert "mcpServers" not in result


# ── merge_toml_mcp_server / strip_toml_mcp_server ────────────────


class TestMergeStripTomlMcpServer:
    def test_merge_adds_section(self):
        text = "[features]\nhooks = true\n"
        result = merge_toml_mcp_server(text, "srv", "python3", ["-m", "foo"], {"KEY": "val"})
        assert "[mcp_servers.srv]" in result
        assert 'command = "python3"' in result
        assert 'args = ["-m", "foo"]' in result
        assert 'KEY = "val"' in result
        assert "[features]" in result
        assert "hooks = true" in result

    def test_merge_is_idempotent(self):
        text = ""
        result1 = merge_toml_mcp_server(text, "srv", "python3", [], {})
        result2 = merge_toml_mcp_server(result1, "srv", "python3", [], {})
        assert result2.count("[mcp_servers.srv]") == 1

    def test_merge_no_env(self):
        text = ""
        result = merge_toml_mcp_server(text, "srv", "python3", [], {})
        assert "[mcp_servers.srv]" in result
        assert 'command = "python3"' in result

    def test_strip_removes_section(self):
        text = "[features]\nhooks = true\n\n[mcp_servers.srv]\ncommand = \"python3\"\nargs = []\n"
        result = strip_toml_mcp_server(text, "srv")
        assert "[mcp_servers.srv]" not in result
        assert "hooks = true" in result

    def test_strip_removes_env_subsection(self):
        text = (
            "[features]\nhooks = true\n"
            "\n[mcp_servers.srv]\ncommand = \"python3\"\nargs = []\n"
            "\n[mcp_servers.srv.env]\nKEY = \"val\"\n"
        )
        result = strip_toml_mcp_server(text, "srv")
        assert "[mcp_servers.srv]" not in result
        assert "hooks = true" in result

    def test_strip_preserves_other_sections(self):
        text = (
            "[mcp_servers.other]\ncommand = \"node\"\n"
            "\n[mcp_servers.srv]\ncommand = \"python3\"\n"
        )
        result = strip_toml_mcp_server(text, "srv")
        assert "[mcp_servers.other]" in result
        assert "[mcp_servers.srv]" not in result

    def test_strip_when_not_present(self):
        text = "[features]\nhooks = true\n"
        result = strip_toml_mcp_server(text, "srv")
        assert "hooks = true" in result


# ── merge_opencode_mcp / strip_opencode_mcp ──────────────────────


class TestMergeStripOpenCodeMcp:
    def test_merge_adds_mcp_key(self):
        config = {"theme": "dark"}
        result = merge_opencode_mcp(config, "srv", ["python3", "-m", "foo"], {"KEY": "val"})
        assert "mcp" in result
        assert result["mcp"]["srv"]["type"] == "local"
        assert result["mcp"]["srv"]["command"] == ["python3", "-m", "foo"]
        assert result["mcp"]["srv"]["environment"]["KEY"] == "val"
        assert result["theme"] == "dark"

    def test_merge_is_idempotent(self):
        config = {}
        result1 = merge_opencode_mcp(config, "srv", ["python3"], {})
        result2 = merge_opencode_mcp(result1, "srv", ["python3"], {})
        assert list(result2["mcp"].keys()) == ["srv"]

    def test_strip_removes_server(self):
        config = {"mcp": {"srv": {"type": "local"}}, "theme": "dark"}
        result = strip_opencode_mcp(config, "srv")
        assert "mcp" not in result
        assert result["theme"] == "dark"

    def test_strip_preserves_other_servers(self):
        config = {"mcp": {"srv": {}, "other": {"type": "local"}}}
        result = strip_opencode_mcp(config, "srv")
        assert "other" in result["mcp"]
        assert "srv" not in result["mcp"]


# ── build_mcp_env ────────────────────────────────────────────────


class TestBuildMcpEnv:
    def test_builds_env_from_creds(self):
        creds = {
            ENV_API_KEY: "my-key",
            ENV_SPACE_ID: "my-space",
            ENV_REGION: "cn-north-4",
        }
        env = build_mcp_env(creds, "opencode")
        assert env[ENV_API_KEY] == "my-key"
        assert env[ENV_SPACE_ID] == "my-space"
        assert env[ENV_REGION] == "cn-north-4"
        assert env["AGENTARTS_MEMORY_PLATFORM"] == "opencode"

    def test_skips_missing_creds(self):
        creds = {ENV_API_KEY: "my-key"}
        env = build_mcp_env(creds)
        assert ENV_API_KEY in env
        assert ENV_SPACE_ID not in env
        assert ENV_REGION not in env

    def test_empty_creds(self):
        env = build_mcp_env({})
        assert env == {}

    def test_platform_name_optional(self):
        creds = {ENV_API_KEY: "my-key"}
        env = build_mcp_env(creds)
        assert "AGENTARTS_MEMORY_PLATFORM" not in env


# ── Constants ───────────────────────────────────────────────────


class TestConstants:
    def test_server_name(self):
        assert MCP_SERVER_NAME == "agentarts_memory"

    def test_server_command(self):
        assert MCP_SERVER_COMMAND == "python3"

    def test_server_args(self):
        assert "-m" in MCP_SERVER_ARGS
        assert "agentarts.toolkit.plugins.memory.mcp.server" in MCP_SERVER_ARGS
