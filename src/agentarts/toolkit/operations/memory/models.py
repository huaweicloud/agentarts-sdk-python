"""Memory operation result models."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpaceResult:
    """Result of a space operation."""

    success: bool
    space_id: str | None = None
    space: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class SpaceListResult:
    """Result of list_spaces operation."""

    success: bool
    spaces: list[dict[str, Any]] = field(default_factory=list)
    total: int = field(default_factory=lambda: 0)
    error: str | None = None


@dataclass
class MemoryResult:
    """Result of a memory operation."""

    success: bool
    memory_id: str | None = None
    memory: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class MemoryListResult:
    """Result of list_memories operation."""

    success: bool
    memories: list[dict[str, Any]] = field(default_factory=list)
    total: int = field(default_factory=lambda: 0)
    error: str | None = None
