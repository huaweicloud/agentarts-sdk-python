"""High-level MCP v2 stdio server for AgentArts Memory search."""

from __future__ import annotations

import logging
import sys
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Any, Protocol

from agentarts.sdk.memory import AsyncMemoryClient, MemorySearchFilter
from mcp.server import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from .config import ConfigurationError, ServerSettings
from .models import SearchMatch, SearchResponse

DEFAULT_TOP_K = 5
MAX_TOP_K = 100
SERVER_NAME = "agentarts-memory"

logger = logging.getLogger(__name__)

SearchQuery = Annotated[str, Field(min_length=1, description="Search query string")]
TopK = Annotated[
    int,
    Field(ge=1, le=MAX_TOP_K, description="Number of most relevant memories to return"),
]


class MemoryClient(Protocol):
    """Async client operations required by the memory server."""

    async def search_memories(
        self,
        space_id: str,
        filters: MemorySearchFilter | None = None,
    ) -> Any:
        """Search memories in one space."""

    async def close(self) -> None:
        """Release network resources."""


MemoryClientFactory = Callable[..., MemoryClient]


@dataclass(frozen=True)
class ServerRuntime:
    """Resources shared by all tool calls for one server process."""

    settings: ServerSettings
    client: MemoryClient


def _normalize_match(item: object) -> SearchMatch:
    """Convert one SDK search result into the stable MCP result shape."""
    if not isinstance(item, Mapping):
        return SearchMatch(content=str(item))

    record = item.get("record")
    if isinstance(record, Mapping):
        raw_content = record.get("content", "")
        raw_strategy_type = record.get("strategy_type")
    else:
        raw_content = "" if record is None else record
        raw_strategy_type = None

    raw_score = item.get("score")
    score = (
        float(raw_score)
        if isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool)
        else None
    )
    strategy_type = raw_strategy_type if isinstance(raw_strategy_type, str) else None

    return SearchMatch(
        content=str(raw_content),
        score=score,
        strategy_type=strategy_type,
    )


def create_server(
    settings: ServerSettings,
    *,
    client_factory: MemoryClientFactory = AsyncMemoryClient,
) -> MCPServer[ServerRuntime]:
    """Create a configured MCP server without starting a transport."""
    if settings.actor_id is None:
        logger.warning(
            "AGENTARTS_MEMORY_ACTOR_ID is not set; searches will include all actors "
            "in the configured Memory Space"
        )

    @asynccontextmanager
    async def lifespan(_server: MCPServer[ServerRuntime]) -> AsyncIterator[ServerRuntime]:
        client = client_factory(
            region_name=settings.region,
            api_key=settings.api_key,
        )
        try:
            yield ServerRuntime(settings=settings, client=client)
        finally:
            await client.close()

    server = MCPServer[ServerRuntime](
        name=SERVER_NAME,
        description="Read-only semantic search over one AgentArts Memory space.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @server.tool(
        name="ltm_search",
        description=("Search AgentArts long-term memory and return entries relevant to the query."),
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=True,
        ),
        structured_output=True,
    )
    async def ltm_search(
        query: SearchQuery,
        ctx: Context[ServerRuntime, Any],
        top_k: TopK = DEFAULT_TOP_K,
    ) -> SearchResponse:
        """Search long-term memories in the server's configured space."""
        normalized_query = query.strip()
        if not normalized_query:
            message = "query must contain at least one non-whitespace character"
            raise ToolError(message)

        runtime = ctx.request_context.lifespan_context
        try:
            response = await runtime.client.search_memories(
                space_id=runtime.settings.space_id,
                filters=MemorySearchFilter(
                    query=normalized_query,
                    actor_id=runtime.settings.actor_id,
                    assistant_id=runtime.settings.assistant_id,
                    top_k=top_k,
                ),
            )
        except Exception as error:
            logger.exception("AgentArts Memory search failed")
            message = "AgentArts Memory search failed; check the server logs"
            raise ToolError(message) from error

        raw_results = getattr(response, "results", [])
        if not isinstance(raw_results, list):
            raw_results = []

        return SearchResponse(
            query=normalized_query,
            results=[_normalize_match(item) for item in raw_results],
        )

    return server


def main() -> None:
    """Validate configuration and run the server over stdio."""
    try:
        settings = ServerSettings.from_env()
    except ConfigurationError as error:
        print(f"agentarts-memory-mcp: {error}", file=sys.stderr)
        raise SystemExit(2) from error

    create_server(settings).run(transport="stdio")
