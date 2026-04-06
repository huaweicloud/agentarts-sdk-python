"""Memory operation result models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SpaceResult:
    """Result of a space operation."""

    success: bool
    space_id: Optional[str] = None
    space: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class SpaceListResult:
    """Result of list_spaces operation."""

    success: bool
    spaces: List[Dict[str, Any]] = field(default_factory=list)
    total: int = field(default_factory=lambda: 0)
    error: Optional[str] = None


@dataclass
class MemoryResult:
    """Result of a memory operation."""

    success: bool
    memory_id: Optional[str] = None
    memory: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class MemoryListResult:
    """Result of list_memories operation."""

    success: bool
    memories: List[Dict[str, Any]] = field(default_factory=list)
    total: int = field(default_factory=lambda: 0)
    error: Optional[str] = None
