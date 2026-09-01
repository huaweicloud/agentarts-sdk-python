"""High-level MCP v2 stdio server for AgentArts Memory."""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Annotated, Any, NoReturn, Protocol

from mcp.server import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from agentarts import __version__
from agentarts.sdk.memory import (
    AsyncMemoryClient,
    MemoryListFilter,
    MemorySearchFilter,
    TextMessage,
)

from ..agentarts_client import AgentArtsMemoryClient
from .config import ENV_ACTOR_ID, ConfigurationError, ServerSettings
from .models import (
    AddMessagesResponse,
    LegacySearchMatch,
    LegacySearchResponse,
    MemoryListItem,
    MemoryListResponse,
    MessageInput,
    SearchMatch,
    SearchResponse,
    SummaryMatch,
    SummaryResponse,
)

DEFAULT_TOP_K = 5
DEFAULT_LIST_LIMIT = 10
DEFAULT_MIN_SCORE = 0.7
DEFAULT_SUMMARY_LIMIT = 3
MAX_RESULTS = 100
SERVER_NAME = "agentarts-memory"

logger = logging.getLogger(__name__)

SearchQuery = Annotated[str, Field(min_length=1, description="Search query string")]
TopK = Annotated[
    int,
    Field(ge=1, le=MAX_RESULTS, description="Number of relevant memories to return"),
]
Threshold = Annotated[
    float,
    Field(ge=0.0, le=1.0, description="Minimum similarity score"),
]
Limit = Annotated[int, Field(ge=1, le=MAX_RESULTS, description="Maximum results to return")]
Offset = Annotated[int, Field(ge=0, description="Pagination offset")]

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
WRITE_ANNOTATIONS = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)


class MemoryClient(Protocol):
    """Async SDK operations required by the MCP server."""

    async def create_memory_session(
        self,
        space_id: str,
        actor_id: str,
        assistant_id: str,
        **kwargs: Any,
    ) -> Any: ...

    async def add_messages(
        self,
        space_id: str,
        session_id: str,
        messages: list[TextMessage],
        **kwargs: Any,
    ) -> Any: ...

    async def search_memories(
        self,
        space_id: str,
        filters: MemorySearchFilter | None = None,
    ) -> Any: ...

    async def list_memories(
        self,
        space_id: str,
        limit: int = DEFAULT_LIST_LIMIT,
        offset: int = 0,
        filters: MemoryListFilter | None = None,
    ) -> Any: ...

    async def close(self) -> None: ...


MemoryClientFactory = Callable[..., Any]


@dataclass
class ServerRuntime:
    """Resources shared by all tool calls for one server process."""

    settings: ServerSettings
    client: MemoryClient
    sessions: dict[str, str] = field(default_factory=dict)
    session_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def session_id(self) -> str:
        """Return the cached write session, creating it when necessary."""
        actor_id = self.settings.actor_id
        if actor_id is None:
            raise ToolError("add_messages requires a configured actor")

        cache_key = f"{self.settings.scope_id}:{actor_id}"
        async with self.session_lock:
            if session_id := self.sessions.get(cache_key):
                return session_id

            file_session_id = AgentArtsMemoryClient._get_cached_sid_from_file(cache_key)
            if file_session_id:
                self.sessions[cache_key] = file_session_id
                return file_session_id

            session = await self.client.create_memory_session(
                space_id=self.settings.space_id,
                actor_id=actor_id,
                assistant_id=self.settings.write_assistant_id,
            )
            session_id = getattr(session, "id", None) or getattr(session, "session_id", "")
            if not session_id:
                raise RuntimeError("create_memory_session returned an empty session id")

            self.sessions[cache_key] = str(session_id)
            AgentArtsMemoryClient._put_cached_sid_to_file(cache_key, str(session_id))
            return str(session_id)


def _extract_content(record: object) -> str:
    if record is None:
        return ""
    if isinstance(record, str):
        return record
    if isinstance(record, Mapping):
        for key in ("content", "text", "summary", "message"):
            if value := record.get(key):
                return str(value)
        if nested := record.get("record"):
            return _extract_content(nested)
    return str(record)


def _extract_strategy_type(record: object) -> str | None:
    if isinstance(record, Mapping):
        for key in ("strategy_type", "memory_type", "type", "strategy"):
            value = record.get(key)
            if isinstance(value, str) and value:
                return value
        nested = record.get("record")
        if isinstance(nested, Mapping):
            return _extract_strategy_type(nested)
    return None


def _normalize_search_match(item: object) -> SearchMatch:
    """Convert one SDK search result into the portable result shape."""
    if isinstance(item, Mapping):
        record = item.get("record")
        raw_score = item.get("score")
    else:
        record = getattr(item, "record", item)
        raw_score = getattr(item, "score", None)

    score = (
        float(raw_score)
        if isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool)
        else None
    )
    return SearchMatch(
        content=_extract_content(record),
        score=score,
        strategy_type=_extract_strategy_type(record),
    )


def _normalize_list_item(item: object) -> MemoryListItem:
    """Convert one SDK list result into the existing public result shape."""
    if isinstance(item, Mapping):
        get = item.get
    else:

        def get(name: str, default: object = None) -> object:
            return getattr(item, name, default)

    strategy_type = get("strategy_type") or get("memory_type") or get("type") or ""
    created_at = get("created_at", "")
    return MemoryListItem(
        id=str(get("id", "") or ""),
        content=str(get("content", "") or ""),
        type=str(strategy_type),
        created_at=str(created_at or ""),
    )


def _runtime(ctx: Context[ServerRuntime, Any]) -> ServerRuntime:
    return ctx.request_context.lifespan_context


def _normalized_query(query: str) -> str:
    value = query.strip()
    if not value:
        raise ToolError("query must contain at least one non-whitespace character")
    return value


def _raise_upstream_error(operation: str, error: Exception) -> NoReturn:
    logger.exception("AgentArts Memory %s failed", operation)
    raise ToolError(f"AgentArts Memory {operation} failed; check the server logs") from error


async def _search(
    runtime: ServerRuntime,
    *,
    query: str,
    top_k: int,
    min_score: float | None = None,
) -> list[SearchMatch]:
    try:
        response = await runtime.client.search_memories(
            space_id=runtime.settings.space_id,
            filters=MemorySearchFilter(
                query=query,
                actor_id=runtime.settings.actor_id,
                assistant_id=runtime.settings.assistant_id,
                top_k=top_k,
                min_score=min_score,
            ),
        )
    except Exception as error:
        _raise_upstream_error("search", error)

    raw_results = getattr(response, "results", [])
    if not isinstance(raw_results, list):
        return []
    return [_normalize_search_match(item) for item in raw_results]


async def _list(runtime: ServerRuntime, *, limit: int, offset: int) -> list[MemoryListItem]:
    try:
        response = await runtime.client.list_memories(
            space_id=runtime.settings.space_id,
            limit=limit,
            offset=offset,
            filters=MemoryListFilter(
                actor_id=runtime.settings.actor_id,
                assistant_id=runtime.settings.assistant_id,
            ),
        )
    except Exception as error:
        _raise_upstream_error("list", error)

    raw_items = getattr(response, "items", [])
    if not isinstance(raw_items, list):
        return []
    return [_normalize_list_item(item) for item in raw_items]


def create_server(
    settings: ServerSettings,
    *,
    client_factory: MemoryClientFactory = AsyncMemoryClient,
) -> MCPServer[ServerRuntime]:
    """Create a configured MCP server without starting a transport."""
    if settings.actor_id is None:
        logger.warning(
            "%s is not set; searches will include all actors in the configured Memory Space",
            ENV_ACTOR_ID,
        )

    @asynccontextmanager
    async def lifespan(_server: MCPServer[ServerRuntime]) -> AsyncIterator[ServerRuntime]:
        client: MemoryClient = client_factory(
            region_name=settings.region,
            api_key=settings.api_key,
        )
        try:
            yield ServerRuntime(settings=settings, client=client)
        finally:
            await client.close()

    server = MCPServer[ServerRuntime](
        name=SERVER_NAME,
        description="AgentArts cloud memory tools.",
        version=__version__,
        lifespan=lifespan,
    )

    @server.tool(
        name="ltm_search",
        description="Search AgentArts long-term memory for entries relevant to the query.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def ltm_search(
        query: SearchQuery,
        ctx: Context[ServerRuntime, Any],
        top_k: TopK = DEFAULT_TOP_K,
    ) -> SearchResponse:
        normalized_query = _normalized_query(query)
        results = await _search(
            _runtime(ctx),
            query=normalized_query,
            top_k=top_k,
        )
        return SearchResponse(query=normalized_query, results=results)

    @server.tool(
        name="search_memories",
        description="Search cloud memories by semantic similarity.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def search_memories(
        query: SearchQuery,
        ctx: Context[ServerRuntime, Any],
        num: TopK = DEFAULT_TOP_K,
        threshold: Threshold = DEFAULT_MIN_SCORE,
    ) -> LegacySearchResponse:
        normalized_query = _normalized_query(query)
        matches = await _search(
            _runtime(ctx),
            query=normalized_query,
            top_k=num,
            min_score=threshold,
        )
        results = [
            LegacySearchMatch(
                content=match.content,
                score=match.score,
                type=match.strategy_type or "",
            )
            for match in matches
        ]
        return LegacySearchResponse(
            query=normalized_query,
            results=results,
            total=len(results),
        )

    @server.tool(
        name="add_messages",
        description="Record conversation messages in AgentArts Memory.",
        annotations=WRITE_ANNOTATIONS,
        structured_output=True,
    )
    async def add_messages(
        messages: list[MessageInput],
        ctx: Context[ServerRuntime, Any],
    ) -> AddMessagesResponse:
        runtime = _runtime(ctx)
        try:
            session_id = await runtime.session_id()
            sdk_messages = [
                TextMessage(
                    role=message.role,
                    content=message.content,
                    actor_id=runtime.settings.actor_id,
                    assistant_id=runtime.settings.write_assistant_id,
                )
                for message in messages
            ]
            await runtime.client.add_messages(
                space_id=runtime.settings.space_id,
                session_id=session_id,
                messages=sdk_messages,
            )
        except ToolError:
            raise
        except Exception as error:
            _raise_upstream_error("message ingestion", error)
        return AddMessagesResponse(session_id=session_id, count=len(sdk_messages))

    @server.tool(
        name="list_memories",
        description="List memory records from the configured AgentArts Memory Space.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def list_memories(
        ctx: Context[ServerRuntime, Any],
        limit: Limit = DEFAULT_LIST_LIMIT,
        offset: Offset = 0,
    ) -> MemoryListResponse:
        results = await _list(_runtime(ctx), limit=limit, offset=offset)
        return MemoryListResponse(results=results, total=len(results))

    @server.tool(
        name="search_summary",
        description="Search summary-type memories, falling back to recent memories.",
        annotations=READ_ONLY_ANNOTATIONS,
        structured_output=True,
    )
    async def search_summary(
        query: SearchQuery,
        ctx: Context[ServerRuntime, Any],
        num: TopK = DEFAULT_SUMMARY_LIMIT,
    ) -> SummaryResponse:
        normalized_query = _normalized_query(query)
        runtime = _runtime(ctx)
        matches = await _search(
            runtime,
            query=normalized_query,
            top_k=min(max(num * 3, DEFAULT_TOP_K), MAX_RESULTS),
            min_score=DEFAULT_MIN_SCORE,
        )
        summary_types = {"summary", "episodic", "user_preference"}
        summaries = [
            SummaryMatch(
                content=match.content,
                score=match.score,
                type=match.strategy_type or "",
            )
            for match in matches
            if match.strategy_type in summary_types
        ]
        if not summaries:
            listed = await _list(
                runtime,
                limit=min(max(num * 5, DEFAULT_LIST_LIMIT), 20),
                offset=0,
            )
            summaries = [
                SummaryMatch(
                    id=item.id,
                    content=item.content,
                    type=item.type,
                    created_at=item.created_at,
                )
                for item in listed
                if item.type in summary_types
            ]
            if not summaries:
                summaries = [
                    SummaryMatch(
                        id=item.id,
                        content=item.content,
                        type=item.type,
                        created_at=item.created_at,
                    )
                    for item in listed
                ]
        summaries = summaries[:num]
        return SummaryResponse(
            query=normalized_query,
            results=summaries,
            total=len(summaries),
        )

    return server


def main() -> None:
    """Validate configuration and run the server over stdio."""
    logging.basicConfig(level=logging.INFO)
    try:
        settings = ServerSettings.from_env()
    except ConfigurationError as error:
        print(f"agentarts-memory-mcp: {error}", file=sys.stderr)
        raise SystemExit(2) from error

    create_server(settings).run(transport="stdio")


if __name__ == "__main__":
    main()
