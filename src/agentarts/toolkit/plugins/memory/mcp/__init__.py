"""AgentArts Memory MCP server package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config import ServerSettings

if TYPE_CHECKING:
    from .server import create_server

__all__ = ["ServerSettings", "create_server"]


def __getattr__(name: str) -> Any:
    """Load MCP-backed exports only when the optional server is requested."""
    if name == "create_server":
        from .server import create_server

        return create_server
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
