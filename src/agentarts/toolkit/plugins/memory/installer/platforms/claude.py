"""Claude Code platform adapter.

Deploys 3 .mjs hook scripts to ``<config_dir>/agentarts-memory/scripts/``
and registers 2 hooks in ``<config_dir>/settings.json`` using absolute
paths (the ``${CLAUDE_PLUGIN_ROOT}`` placeholder is replaced).

Config dir:
  - project: ``.claude/``
  - global:  ``~/.claude/``
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import cast

from ..utils import (
    MCP_SERVER_ARGS,
    MCP_SERVER_COMMAND,
    MCP_SERVER_NAME,
    build_mcp_env,
    claude_hooks_template,
    code_agent_scripts,
    expand,
    merge_hooks,
    merge_mcp_servers,
    read_json,
    remove_hooks_key,
    remove_if_empty,
    status_ok,
    status_updated,
    strip_json5,
    strip_mcp_servers,
    write_json_atomic,
)
from .base import InstallResult, Platform

CLAUDE_PLACEHOLDER = "${CLAUDE_PLUGIN_ROOT}"


class ClaudePlatform(Platform):
    name = "claude"
    display = "Claude Code"
    fixed_user_level = False

    def detect(self) -> bool:
        return self._dir_exists("~/.claude")

    def config_dir(self, scope: str) -> str:
        if scope == "global":
            return expand("~/.claude")
        return os.path.join(os.getcwd(), ".claude")

    def _scripts_dir(self, scope: str) -> str:
        return os.path.join(self.config_dir(scope), "agentarts-memory", "scripts")

    def _settings_path(self, scope: str) -> str:
        return os.path.join(self.config_dir(scope), "settings.json")

    def _load_hooks_template(self, scripts_dir: str) -> dict:
        """Read hooks.json template and replace placeholder with absolute path."""
        template_path = claude_hooks_template()
        raw = Path(template_path).read_text(encoding="utf-8")
        # Replace ${CLAUDE_PLUGIN_ROOT} with the parent of scripts_dir
        # (plugin_root = config_dir/agentarts-memory).
        plugin_root = os.path.dirname(scripts_dir)
        raw = raw.replace(CLAUDE_PLACEHOLDER, plugin_root)
        return cast(dict, json.loads(strip_json5(raw)))

    def install(self, scope: str, creds: dict, yes: bool) -> InstallResult:
        config_dir = self.config_dir(scope)
        scripts_dir = self._scripts_dir(scope)
        settings_path = self._settings_path(scope)

        # Phase 1: Deploy hook scripts.
        src_scripts = code_agent_scripts()
        deployed: list[str] = []
        for src in src_scripts:
            dst = os.path.join(scripts_dir, os.path.basename(src))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            deployed.append(dst)
            status_ok(f"Deploy {os.path.basename(src)}", dst)

        # Phase 2: Load template with absolute paths.
        hooks_template = self._load_hooks_template(scripts_dir)

        # Phase 3: Merge into settings.json.
        settings = read_json(settings_path)
        merged = merge_hooks(settings, hooks_template, scripts_dir)
        # Phase 4: Merge MCP server config.
        merged = merge_mcp_servers(
            merged,
            MCP_SERVER_NAME,
            MCP_SERVER_COMMAND,
            MCP_SERVER_ARGS,
            build_mcp_env(creds, "claude-code"),
        )
        write_json_atomic(settings_path, merged)
        status_updated("settings.json", settings_path)

        return InstallResult(
            config_dir=config_dir,
            scripts_dir=scripts_dir,
            files=deployed,
            config_files=[settings_path],
        )

    def uninstall(self, entry: dict) -> None:
        scripts_dir = entry.get("scripts_dir", "")
        config_dir = entry.get("config_dir", "")
        settings_path = os.path.join(config_dir, "settings.json") if config_dir else ""

        # Phase 1: Strip our hooks from settings.json.
        if settings_path and os.path.isfile(settings_path):
            settings = read_json(settings_path)
            # Also strip MCP server config.
            settings = strip_mcp_servers(settings, MCP_SERVER_NAME)
            cleaned = remove_hooks_key(settings, scripts_dir)
            if cleaned and list(cleaned.keys()):
                # Preserve other settings.
                write_json_atomic(settings_path, cleaned)
                status_ok("Stripped hooks from settings.json", settings_path)
            else:
                # File is now empty or only had hooks.
                os.unlink(settings_path)
                status_ok("Removed settings.json", settings_path)

        # Phase 2: Remove scripts directory.
        if scripts_dir and os.path.isdir(scripts_dir):
            shutil.rmtree(scripts_dir)
            status_ok("Remove scripts dir", scripts_dir)
            # Clean up empty parent (agentarts-memory/).
            parent = os.path.dirname(scripts_dir)
            if os.path.isdir(parent):
                try:
                    os.rmdir(parent)
                except OSError:
                    pass
            # Clean up empty config dir (only if .claude/ is now empty).
            if config_dir:
                remove_if_empty(config_dir)
