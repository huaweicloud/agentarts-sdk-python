"""Hermes Agent platform adapter.

Deploys the hermes memory provider (provider.py, plugin.yaml, __init__.py)
into the active Hermes home's ``plugins/agentarts/`` directory.

Hermes home resolution priority (see :func:`hermes_home`):
  1. ``HERMES_HOME`` env var — set by the Hermes installer on *all* platforms.
  2. On Windows native: ``%LOCALAPPDATA%\\hermes`` (the installer default).
     The Windows installer does *not* create ``~/.hermes``; it stores data
     under ``%LOCALAPPDATA%\\hermes`` and sets ``HERMES_HOME`` accordingly.
  3. ``~/.hermes`` — the default on Linux / macOS / WSL.

All credentials (API Key, space_id, region) are written to
``<hermes_home>/.env`` (deduped by key). Hermes does NOT depend on the local
adapter server (provider connects to the cloud SDK directly).
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from ..utils import (
    ENV_API_KEY,
    ENV_REGION,
    ENV_SPACE_ID,
    expand,
    hermes_files,
    remove_if_empty,
    set_yaml_key,
    status_err,
    status_ok,
    strip_env_keys,
    write_env_file,
)
from .base import InstallResult, Platform

# Default Hermes home (Linux / macOS / WSL).
HERMES_HOME_DEFAULT = "~/.hermes"


def hermes_home() -> str:
    """Resolve the Hermes home directory.

    Priority:
    1. ``HERMES_HOME`` env var (set by Hermes installer on all platforms).
    2. Windows native: ``%LOCALAPPDATA%\\hermes`` (Hermes Windows default).
    3. ``~/.hermes`` (Linux / macOS / WSL default).
    """
    env_home = os.environ.get("HERMES_HOME", "")
    if env_home:
        return env_home
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            return os.path.join(local_app_data, "hermes")
    return HERMES_HOME_DEFAULT


class HermesPlatform(Platform):
    name = "hermes"
    display = "Hermes Agent"
    fixed_user_level = True

    def detect(self) -> bool:
        return self._dir_exists(hermes_home())

    def config_dir(self, scope: str) -> str:
        # scope is ignored — hermes is always user-level.
        return expand(os.path.join(hermes_home(), "plugins", "agentarts"))

    def install(self, scope: str, creds: dict, yes: bool) -> InstallResult:
        plugin_dir = expand(os.path.join(hermes_home(), "plugins", "agentarts"))
        env_path = expand(os.path.join(hermes_home(), ".env"))

        # Phase 1: Deploy plugin files.
        src_files = hermes_files()
        deployed: list[str] = []
        for src in src_files:
            dst = os.path.join(plugin_dir, os.path.basename(src))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            deployed.append(dst)
            status_ok(f"Deploy {os.path.basename(src)}", dst)

        # Phase 2: Write .env (API key, space_id, region).
        env_entries = {var: creds.get(var, "") for var in (ENV_API_KEY, ENV_SPACE_ID, ENV_REGION)}
        env_entries = {k: v for k, v in env_entries.items() if v}
        if env_entries:
            write_env_file(env_path, env_entries)
            status_ok("Write .env", env_path)
        else:
            status_err("Write .env", "Credentials missing")

        # Phase 3: Activate hermes memory provider in config.yaml.
        config_yaml_path = expand(os.path.join(hermes_home(), "config.yaml"))
        set_yaml_key(config_yaml_path, "memory", "provider", "agentarts")
        status_ok("Activate memory provider", config_yaml_path)

        config_files = [env_path, config_yaml_path]
        return InstallResult(
            config_dir=plugin_dir,
            scripts_dir="",
            files=deployed,
            config_files=config_files,
        )

    def uninstall(self, entry: dict) -> None:
        plugin_dir = expand(os.path.join(hermes_home(), "plugins", "agentarts"))
        env_path = expand(os.path.join(hermes_home(), ".env"))

        # Phase 1: Remove plugin directory.
        p = Path(plugin_dir)
        if p.exists():
            shutil.rmtree(p)
            status_ok("Remove plugin dir", str(p))
            # Clean up empty parent directories up to hermes home.
            parent = p.parent
            hermes_home_expanded = expand(hermes_home())
            while parent != Path(hermes_home_expanded) and parent.exists():
                try:
                    parent.rmdir()
                    parent = parent.parent
                except OSError:
                    break

        # Phase 2: Strip env keys from .env.
        strip_env_keys(env_path, [ENV_API_KEY, ENV_SPACE_ID, ENV_REGION])
        status_ok("Strip .env", env_path)

        # Phase 3: Deactivate hermes memory provider in config.yaml.
        config_yaml_path = expand(os.path.join(hermes_home(), "config.yaml"))
        set_yaml_key(config_yaml_path, "memory", "provider", "")
        status_ok("Deactivate memory provider", config_yaml_path)

        # Clean up empty directories.
        remove_if_empty(expand(hermes_home()))
