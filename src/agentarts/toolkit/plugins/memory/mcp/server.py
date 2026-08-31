"""MCP server exposing AgentArts Memory tools via stdio transport.

This module wraps :class:`AgentArtsMemoryClient` and exposes four MCP tools that the AI
agent can call on-demand:

- ``search_memories`` — semantic search of cloud memories
- ``add_messages`` — record conversation messages to cloud memory
- ``list_memories`` — paginated list of memory records
- ``search_summary`` — list summary-type memories

Lifecycle is managed by the platform (Claude Code / Codex / OpenCode):
the platform launches ``python -m agentarts.toolkit.plugins.memory.mcp.server``
as a subprocess and communicates via stdin/stdout JSON-RPC.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server import MCPServer

from ..agentarts_client import (
    DEFAULT_LIST_LIMIT,
    DEFAULT_MIN_SCORE,
    DEFAULT_TOP_K,
    AgentArtsMemoryClient,
)

logger = logging.getLogger("agentarts_memory.mcp")

_PLATFORM_USER_ID = {
    "claude-code": "cc-user",
    "codex": "codex-user",
    "opencode": "opencode-user",
    "unknown": "__default__",
}


def _detect_platform() -> str:
    if os.getenv("AGENTARTS_MEMORY_PLATFORM"):
        return os.getenv("AGENTARTS_MEMORY_PLATFORM", "")
    if os.getenv("CLAUDE_PLUGIN_ROOT"):
        return "claude-code"
    if os.getenv("CODEX_PLUGIN_ROOT"):
        return "codex"
    if os.getenv("OPENCODE_PLUGIN_ROOT"):
        return "opencode"
    return "unknown"


def _resolve_user_id(user_id: str | None) -> str:
    if user_id:
        return user_id
    if env_uid := os.getenv("AGENTARTS_MEMORY_USER_ID"):
        return env_uid
    return _PLATFORM_USER_ID.get(_detect_platform(), "__default__")


def _resolve_scope_id(scope_id: str | None) -> str:
    if scope_id:
        return scope_id
    if env_scope := os.getenv("AGENTARTS_MEMORY_PROJECT_NAME"):
        return env_scope
    return "default"


# ── shared client instance ──
_client: AgentArtsMemoryClient | None = None


def get_client() -> AgentArtsMemoryClient:
    """Return the shared AgentArtsMemoryClient singleton."""
    global _client
    if _client is None:
        _client = AgentArtsMemoryClient()
    return _client


def reset_client(client: AgentArtsMemoryClient | None = None) -> None:
    """Replace the shared client (used by tests)."""
    global _client
    _client = client


# ── MCP server instance ──
mcp = MCPServer(
    name="agentarts-memory",
    version="1.0.0",
    instructions=(
        "AgentArts Memory provides cross-session cloud memory via Huawei Cloud. "
        "Use search_memories to find relevant past context, add_messages to record "
        "important information, and list_memories to browse stored memories."
    ),
)


# ── Tool implementations ──


@mcp.tool()
def search_memories(
    query: str,
    num: int = DEFAULT_TOP_K,
    threshold: float = DEFAULT_MIN_SCORE,
) -> dict[str, Any]:
    """Search cloud memories by semantic similarity.

    Args:
        query: Natural-language search query.
        num: Maximum results to return (1-100).
        threshold: Minimum similarity score (0.0-1.0).

    Returns:
        Dict with ``results`` (list of {content, score, type}) and ``total``.
    """
    try:
        results = get_client().search_memories(
            query=query,
            user_id=_resolve_user_id(None),
            scope_id=_resolve_scope_id(None),
            num=num,
            threshold=threshold,
        )
        return {"results": results, "total": len(results), "query": query}
    except Exception as exc:
        logger.warning("search_memories failed: %s", exc)
        return {"error": str(exc), "results": [], "total": 0}


@mcp.tool()
def add_messages(
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    """Record conversation messages to cloud memory.

    Args:
        messages: List of {role, content} dicts (role: user/assistant/system).

    Returns:
        Dict with ``session_id`` and ``count`` of recorded messages.
    """
    try:
        result = get_client().add_messages(
            messages,
            user_id=_resolve_user_id(None),
            scope_id=_resolve_scope_id(None),
        )
        return result
    except Exception as exc:
        logger.warning("add_messages failed: %s", exc)
        return {"error": str(exc), "session_id": "", "count": 0}


@mcp.tool()
def list_memories(
    limit: int = DEFAULT_LIST_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    """List memory records from cloud memory.

    Args:
        limit: Maximum records to return (1-100).
        offset: Pagination offset.

    Returns:
        Dict with ``results`` (list of {id, content, type, created_at}) and ``total``.
    """
    try:
        results = get_client().list_memories(
            user_id=_resolve_user_id(None),
            scope_id=_resolve_scope_id(None),
            limit=limit,
            offset=offset,
        )
        return {"results": results, "total": len(results)}
    except Exception as exc:
        logger.warning("list_memories failed: %s", exc)
        return {"error": str(exc), "results": [], "total": 0}


@mcp.tool()
def search_summary(
    query: str,
    num: int = 3,
) -> dict[str, Any]:
    """Search summary-type memories by semantic similarity.

    Performs a semantic search with the query, then filters results to
    summary-type memories (episodic, summary, user_preference). Falls back
    to listing all memories if no summary-type results are found.

    Args:
        query: Natural-language search query.
        num: Maximum results to return.

    Returns:
        Dict with ``results`` (list of {content, type}) and ``total``.
    """
    try:
        summary_types = {"summary", "episodic", "user_preference"}

        uid = _resolve_user_id(None)
        sid = _resolve_scope_id(None)

        # Semantic search with query, then filter to summary types.
        search_results = get_client().search_memories(
            query=query,
            user_id=uid,
            scope_id=sid,
            num=max(num * 3, DEFAULT_TOP_K),
            threshold=DEFAULT_MIN_SCORE,
        )
        summaries = [m for m in search_results if m.get("type") in summary_types]

        # Fallback: list memories and filter by type if semantic search found none.
        if not summaries:
            all_mem = get_client().list_memories(
                user_id=uid,
                scope_id=sid,
                limit=min(max(num * 5, DEFAULT_LIST_LIMIT), 20),
                offset=0,
            )
            summaries = [m for m in all_mem if m.get("type") in summary_types]
            if not summaries:
                summaries = all_mem

        summaries = summaries[:num]
        return {"results": summaries, "total": len(summaries), "query": query}
    except Exception as exc:
        logger.warning("search_summary failed: %s", exc)
        return {"error": str(exc), "results": [], "total": 0}


def main() -> None:
    """Entry point for ``python -m agentarts.toolkit.plugins.memory.mcp.server``."""
    logging.basicConfig(level=logging.INFO)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
