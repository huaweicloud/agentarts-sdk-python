"""Optional-dependency-safe launcher for the Memory MCP server."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import NoReturn

MCP_EXTRA = "agentarts-sdk[memory-mcp]"


def _load_server_main() -> Callable[[], None]:
    from .server import main

    return main


def _missing_dependency(error: ModuleNotFoundError) -> NoReturn:
    print(
        f"agentarts-memory-mcp requires the optional MCP dependencies; "
        f"install them with: pip install '{MCP_EXTRA}'",
        file=sys.stderr,
    )
    raise SystemExit(2) from error


def main() -> None:
    """Start the MCP server or explain how to install its optional extra."""
    try:
        server_main = _load_server_main()
    except ModuleNotFoundError as error:
        if error.name != "mcp":
            raise
        _missing_dependency(error)
    server_main()


if __name__ == "__main__":
    main()
