"""Codex platform adapter.

Deploys 3 .mjs hook scripts to ``<config_dir>/agentarts-memory/scripts/``
and registers 2 hooks in ``<config_dir>/hooks.json`` using absolute paths
(the ``${CODEX_PLUGIN_ROOT}`` placeholder is replaced).

Also updates ``<config_dir>/config.toml`` to enable ``hooks = true``
under ``[features]`` (text-level merge, no toml library dependency).

Config dir:
  - project: ``.codex/``
  - global:  ``~/.codex/``
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
    code_agent_scripts,
    codex_hooks_template,
    expand,
    merge_hooks,
    merge_toml_mcp_server,
    merge_toml_features,
    read_json,
    remove_hooks_key,
    remove_if_empty,
    status_ok,
    status_updated,
    strip_json5,
    strip_toml_mcp_server,
    strip_toml_feature,
    write_json_atomic,
)
from .base import InstallResult, Platform

CODEX_PLACEHOLDER = "${CODEX_PLUGIN_ROOT}"
TOML_KEY = "hooks"


class CodexPlatform(Platform):
    name = "codex"
    display = "Codex"
    fixed_user_level = False

    def detect(self) -> bool:
        return self._dir_exists("~/.codex")

    def config_dir(self, scope: str) -> str:
        if scope == "global":
            return expand("~/.codex")
        return os.path.join(os.getcwd(), ".codex")

    def _scripts_dir(self, scope: str) -> str:
        return os.path.join(self.config_dir(scope), "agentarts-memory", "scripts")

    def _hooks_path(self, scope: str) -> str:
        return os.path.join(self.config_dir(scope), "hooks.json")

    def _config_toml_path(self, scope: str) -> str:
        return os.path.join(self.config_dir(scope), "config.toml")

    def _load_hooks_template(self, scripts_dir: str) -> dict:
        """Read hooks.codex.json template and replace placeholder with absolute path."""
        template_path = codex_hooks_template()
        raw = Path(template_path).read_text(encoding="utf-8")
        # Normalize to forward slashes so backslashes don't break JSON
        # parsing on Windows (e.g. C:\Users\... -> C:/Users/...).
        plugin_root = os.path.dirname(scripts_dir).replace("\\", "/")
        raw = raw.replace(CODEX_PLACEHOLDER, plugin_root)
        return cast(dict, json.loads(strip_json5(raw)))

    def install(self, scope: str, creds: dict, yes: bool) -> InstallResult:
        config_dir = self.config_dir(scope)
        scripts_dir = self._scripts_dir(scope)
        hooks_path = self._hooks_path(scope)
        toml_path = self._config_toml_path(scope)

        # Phase 1: Deploy hook scripts.
        src_scripts = code_agent_scripts()
        deployed: list[str] = []
        for src in src_scripts:
            dst = os.path.join(scripts_dir, os.path.basename(src))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            deployed.append(dst)
            status_ok(f"Deploy {os.path.basename(src)}", dst)

        # Phase 2: Merge hooks into hooks.json.
        hooks_template = self._load_hooks_template(scripts_dir)
        existing_hooks = read_json(hooks_path)
        merged = merge_hooks(existing_hooks, hooks_template, scripts_dir)
        write_json_atomic(hooks_path, merged)
        status_updated("hooks.json", hooks_path)

        # Phase 3: Update config.toml — enable hooks.
        toml_text = ""
        if os.path.isfile(toml_path):
            toml_text = Path(toml_path).read_text(encoding="utf-8")
        updated_toml = merge_toml_features(
            toml_text, TOML_KEY, "true", deprecated_keys=["codex_hooks"]
        )
        Path(toml_path).parent.mkdir(parents=True, exist_ok=True)
        Path(toml_path).write_text(updated_toml, encoding="utf-8")
        status_updated("config.toml", toml_path)

        # Phase 4: Merge MCP server config into config.toml.
        toml_text = Path(toml_path).read_text(encoding="utf-8")
        updated_toml = merge_toml_mcp_server(
            toml_text,
            MCP_SERVER_NAME,
            MCP_SERVER_COMMAND,
            MCP_SERVER_ARGS,
            build_mcp_env(creds, "codex"),
        )
        Path(toml_path).write_text(updated_toml, encoding="utf-8")
        status_updated("config.toml (MCP)", toml_path)

        return InstallResult(
            config_dir=config_dir,
            scripts_dir=scripts_dir,
            files=deployed,
            config_files=[hooks_path, toml_path],
        )

    def uninstall(self, entry: dict) -> None:
        scripts_dir = entry.get("scripts_dir", "")
        config_dir = entry.get("config_dir", "")
        hooks_path = os.path.join(config_dir, "hooks.json") if config_dir else ""
        toml_path = os.path.join(config_dir, "config.toml") if config_dir else ""

        # Phase 1: Strip our hooks from hooks.json.
        if hooks_path and os.path.isfile(hooks_path):
            hooks_data = read_json(hooks_path)
            cleaned = remove_hooks_key(hooks_data, scripts_dir)
            if cleaned and list(cleaned.keys()):
                write_json_atomic(hooks_path, cleaned)
                status_ok("Stripped hooks from hooks.json", hooks_path)
            else:
                os.unlink(hooks_path)
                status_ok("Removed hooks.json", hooks_path)

        # Phase 2: Strip hooks from config.toml.
        if toml_path and os.path.isfile(toml_path):
            toml_text = Path(toml_path).read_text(encoding="utf-8")
            # Strip MCP server config first, then hooks feature.
            toml_text = strip_toml_mcp_server(toml_text, MCP_SERVER_NAME)
            updated = strip_toml_feature(toml_text, TOML_KEY)
            if updated.strip():
                Path(toml_path).write_text(updated, encoding="utf-8")
                status_ok("Stripped hooks and MCP from config.toml", toml_path)
            else:
                os.unlink(toml_path)
                status_ok("Removed config.toml", toml_path)

        # Phase 3: Remove scripts directory.
        if scripts_dir and os.path.isdir(scripts_dir):
            shutil.rmtree(scripts_dir)
            status_ok("Remove scripts dir", scripts_dir)
            parent = os.path.dirname(scripts_dir)
            if os.path.isdir(parent):
                try:
                    os.rmdir(parent)
                except OSError:
                    pass
            if config_dir:
                remove_if_empty(config_dir)
