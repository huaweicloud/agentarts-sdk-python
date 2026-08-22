"""Hermes Agent platform adapter.

Deploys the hermes memory provider (provider.py, plugin.yaml, __init__.py)
to ``~/.hermes/hermes-agent/plugins/memory/agentarts/`` and
``~/.hermes/plugins/agentarts/``.

Credentials:
  - API Key → ``~/.hermes/.env`` (deduped by key)
  - space_id, region → ``~/.hermes/agentarts.json``

Hermes does NOT depend on the local adapter server (provider connects
to the cloud SDK directly).
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from ..utils import (
    DEFAULT_REGION,
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

HERMES_HOME = "~/.hermes"
PLUGIN_DIR = "~/.hermes/hermes-agent/plugins/memory/agentarts"
PLUGIN_DIR_NEW = "~/.hermes/plugins/agentarts"
PLUGIN_DIRS = [PLUGIN_DIR, PLUGIN_DIR_NEW]
ENV_FILE = "~/.hermes/.env"
CONFIG_FILE = "~/.hermes/agentarts.json"
CONFIG_YAML = "~/.hermes/config.yaml"


class HermesPlatform(Platform):
    name = "hermes"
    display = "Hermes Agent"
    fixed_user_level = True

    def detect(self) -> bool:
        return self._dir_exists(HERMES_HOME)

    def config_dir(self, scope: str) -> str:
        # scope is ignored — hermes is always user-level.
        return expand(PLUGIN_DIR)

    def install(self, scope: str, creds: dict, yes: bool) -> InstallResult:
        plugin_dir = expand(PLUGIN_DIR)
        env_path = expand(ENV_FILE)
        config_path = expand(CONFIG_FILE)

        # Phase 1: Deploy plugin files.
        src_files = hermes_files()
        deployed: list[str] = []
        for pdir in PLUGIN_DIRS:
            target_dir = expand(pdir)
            for src in src_files:
                dst = os.path.join(target_dir, os.path.basename(src))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                deployed.append(dst)
                status_ok(f"Deploy {os.path.basename(src)}", dst)

        # Phase 2: Write .env (API key).
        api_key = creds.get(ENV_API_KEY, "")
        if api_key:
            write_env_file(env_path, {ENV_API_KEY: api_key})
            status_ok("Write .env", env_path)
        else:
            status_err("Write .env", "API key missing in credentials")

        # Phase 3: Write agentarts.json (space_id, region).
        config_data = {
            "space_id": creds.get(ENV_SPACE_ID, ""),
            "region": creds.get(ENV_REGION, DEFAULT_REGION),
        }
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        Path(config_path).write_text(
            json.dumps(config_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        status_ok("Write agentarts.json", config_path)

        # Phase 4: Activate hermes memory provider in config.yaml.
        config_yaml_path = expand(CONFIG_YAML)
        set_yaml_key(config_yaml_path, "memory", "provider", "agentarts")
        status_ok("Activate memory provider", config_yaml_path)

        config_files = [env_path, config_path, config_yaml_path]
        return InstallResult(
            config_dir=plugin_dir,
            scripts_dir="",
            files=deployed,
            config_files=config_files,
        )

    def uninstall(self, entry: dict) -> None:
        plugin_dir = expand(PLUGIN_DIR)
        env_path = expand(ENV_FILE)
        config_path = expand(CONFIG_FILE)

        # Phase 1: Remove plugin directory.
        for pdir in PLUGIN_DIRS:
            p = Path(expand(pdir))
            if p.exists():
                shutil.rmtree(p)
                status_ok("Remove plugin dir", str(p))
                # Clean up empty parent directories up to ~/.hermes.
                parent = p.parent
                hermes_home = expand(HERMES_HOME)
                while parent != Path(hermes_home) and parent.exists():
                    try:
                        parent.rmdir()
                        parent = parent.parent
                    except OSError:
                        break

        # Phase 2: Strip API key from .env.
        strip_env_keys(env_path, [ENV_API_KEY])
        status_ok("Strip .env", env_path)

        # Phase 3: Remove agentarts.json.
        c = Path(config_path)
        if c.exists():
            c.unlink()
            status_ok("Remove agentarts.json", config_path)

        # Phase 4: Deactivate hermes memory provider in config.yaml.
        config_yaml_path = expand(CONFIG_YAML)
        set_yaml_key(config_yaml_path, "memory", "provider", "")
        status_ok("Deactivate memory provider", config_yaml_path)

        # Clean up empty directories.
        remove_if_empty(expand(HERMES_HOME))
