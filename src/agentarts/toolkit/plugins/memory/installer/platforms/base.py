"""Abstract base class for platform adapters."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class InstallResult:
    """Result of an installation operation."""

    config_dir: str
    scripts_dir: str = ""
    files: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)


class Platform(ABC):
    """Abstract platform adapter for install/uninstall operations."""

    name: str = ""
    display: str = ""
    fixed_user_level: bool = False

    @abstractmethod
    def detect(self) -> bool:
        """Detect whether this platform's config directory exists."""
        ...

    @abstractmethod
    def config_dir(self, scope: str) -> str:
        """Return the platform's configuration directory path."""
        ...

    @abstractmethod
    def install(self, scope: str, creds: dict, yes: bool) -> InstallResult:
        """Install the plugin for this platform."""
        ...

    @abstractmethod
    def uninstall(self, entry: dict) -> None:
        """Uninstall the plugin, removing only our additions."""
        ...

    @staticmethod
    def _dir_exists(path: str) -> bool:
        """Helper: check if a directory exists after path expansion."""
        return os.path.isdir(os.path.expanduser(os.path.expandvars(path)))
