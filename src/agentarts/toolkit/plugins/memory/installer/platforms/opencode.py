"""OpenCode platform adapter.

Deploys the TypeScript plugin (``agentarts-memory-capture.ts``) to
``<config_dir>/plugins/`` and slash commands (``recall.md``,
``remember.md``) to ``<config_dir>/commands/``.

Registers the plugin in ``<config_dir>/opencode.json`` under the
``plugin`` array (deduplicated).

Config dir:
  - project: ``.opencode/``
  - global:  ``~/.config/opencode/``
"""

from __future__ import annotations

import os
import shutil

from ..utils import (
    MCP_SERVER_ARGS,
    MCP_SERVER_COMMAND,
    MCP_SERVER_NAME,
    build_mcp_env,
    expand,
    merge_opencode_mcp,
    opencode_files,
    read_json,
    remove_if_empty,
    status_ok,
    strip_opencode_mcp,
    status_updated,
    write_json_atomic,
)
from .base import InstallResult, Platform

# The relative path we register in opencode.json.
PLUGIN_ENTRY = "./plugins/agentarts-memory-capture.ts"


class OpenCodePlatform(Platform):
    name = "opencode"
    display = "OpenCode"
    fixed_user_level = False

    def detect(self) -> bool:
        return self._dir_exists("~/.config/opencode")

    def config_dir(self, scope: str) -> str:
        if scope == "global":
            return expand("~/.config/opencode")
        return os.path.join(os.getcwd(), ".opencode")

    def _opencode_json_path(self, scope: str) -> str:
        return os.path.join(self.config_dir(scope), "opencode.json")

    def install(self, scope: str, creds: dict, yes: bool) -> InstallResult:
        config_dir = self.config_dir(scope)
        json_path = self._opencode_json_path(scope)

        deployed: list[str] = []

        # Phase 1: Deploy TS plugin.
        oc_files = opencode_files()
        for rel_target, src_path in oc_files.items():
            # Split rel_target on "/" so os.path.join uses OS-native
            # separators instead of embedding forward slashes.
            dst = os.path.join(config_dir, *rel_target.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src_path, dst)
            deployed.append(dst)
            status_ok(f"Deploy {os.path.basename(dst)}", dst)

        # Phase 2: Register plugin in opencode.json.
        config = read_json(json_path)
        plugin_list = config.get("plugin", [])

        # Dedup: remove existing entry first, then add.
        plugin_list = [p for p in plugin_list if p != PLUGIN_ENTRY]
        plugin_list.append(PLUGIN_ENTRY)

        config["plugin"] = plugin_list
        # Phase 3: Merge MCP server config.
        config = merge_opencode_mcp(
            config,
            MCP_SERVER_NAME,
            [MCP_SERVER_COMMAND] + MCP_SERVER_ARGS,
            build_mcp_env(creds, "opencode"),
        )
        write_json_atomic(json_path, config)
        status_updated("opencode.json", json_path)

        return InstallResult(
            config_dir=config_dir,
            scripts_dir="",  # opencode has no scripts dir
            files=deployed,
            config_files=[json_path],
        )

    def uninstall(self, entry: dict) -> None:
        config_dir = entry.get("config_dir", "")
        json_path = os.path.join(config_dir, "opencode.json") if config_dir else ""

        # Phase 1: Remove our entry from opencode.json.
        if json_path and os.path.isfile(json_path):
            config = read_json(json_path)
            plugin_list = config.get("plugin", [])
            plugin_list = [p for p in plugin_list if p != PLUGIN_ENTRY]

            config = strip_opencode_mcp(config, MCP_SERVER_NAME)
            if plugin_list:
                config["plugin"] = plugin_list
                write_json_atomic(json_path, config)
                status_ok("Stripped plugin entry from opencode.json", json_path)
            else:
                config.pop("plugin", None)
                if config:
                    write_json_atomic(json_path, config)
                    status_ok("Removed plugin entry from opencode.json", json_path)
                else:
                    os.unlink(json_path)
                    status_ok("Removed opencode.json", json_path)

        # Phase 2: Delete deployed files.
        files_to_remove = [
            os.path.join(config_dir, "plugins", "agentarts-memory-capture.ts"),
            os.path.join(config_dir, "commands", "recall.md"),
            os.path.join(config_dir, "commands", "remember.md"),
        ]
        for f in files_to_remove:
            if os.path.isfile(f):
                os.unlink(f)
                status_ok(f"Remove {os.path.basename(f)}", f)

        # Phase 3: Clean up empty directories.
        if config_dir:
            for sub in ("commands", "plugins"):
                remove_if_empty(os.path.join(config_dir, sub))
            remove_if_empty(config_dir)
