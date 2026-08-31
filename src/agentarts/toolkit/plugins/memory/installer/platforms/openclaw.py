"""OpenClaw platform adapter (placeholder).

OpenClaw support is not yet implemented.  install/uninstall print a
placeholder message and exit normally.
"""

from __future__ import annotations

from agentarts.toolkit.utils.common import echo_warning

from .base import InstallResult, Platform


class OpenClawPlatform(Platform):
    name = "openclaw"
    display = "OpenClaw"
    fixed_user_level = False

    def detect(self) -> bool:
        # We don't know how to detect OpenClaw yet.
        return False

    def config_dir(self, scope: str) -> str:
        return ""

    def install(self, scope: str, creds: dict, yes: bool) -> InstallResult:
        echo_warning("openclaw not yet implemented")
        return InstallResult(config_dir="", scripts_dir="", files=[], config_files=[])

    def uninstall(self, entry: dict) -> None:
        echo_warning("openclaw not yet implemented")
