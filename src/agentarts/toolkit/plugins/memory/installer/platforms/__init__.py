"""Platform adapters registry for AgentArts Memory installer."""

from __future__ import annotations

from .base import Platform
from .claude import ClaudePlatform
from .codex import CodexPlatform
from .hermes import HermesPlatform
from .openclaw import OpenClawPlatform
from .opencode import OpenCodePlatform

# Registry of all supported platforms.
PLATFORMS: dict[str, Platform] = {
    "hermes": HermesPlatform(),
    "claude": ClaudePlatform(),
    "codex": CodexPlatform(),
    "opencode": OpenCodePlatform(),
    "openclaw": OpenClawPlatform(),
}

# Placeholder for platforms implemented in later phases.
# All platforms registered.


def get_platform(name: str) -> Platform | None:
    """Get a platform adapter by name, or None if unknown."""
    return PLATFORMS.get(name)


def detect_all(global_scope: bool) -> list[tuple[str, Platform]]:
    """Detect all platforms whose config directories exist.

    Returns a list of (name, platform) pairs.
    """
    detected: list[tuple[str, Platform]] = []
    for name, platform in PLATFORMS.items():
        if platform.detect():
            detected.append((name, platform))
    return detected
