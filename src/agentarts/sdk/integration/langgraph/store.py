"""
AgentArts Memory Store for LangGraph

Provides a BaseStore implementation that uses AgentArts Memory service
for cross-thread memory storage with semantic search capabilities.

Design (方案 D - 符合 LangGraph 标准):
- Namespace: 层级路径，如 ("memories",) 或 ("memories", "user-001")
- Filter: 精确过滤 actor_id/assistant_id/session_id
- Query: 语义搜索
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from agentarts.sdk.memory import AsyncMemoryClient, MemoryClient
from agentarts.sdk.memory.inner.config import MemorySearchFilter
from agentarts.sdk.utils.constant import get_region

logger = logging.getLogger(__name__)

try:
    from langgraph.store.base import (
        BaseStore,
        GetOp,
        Item,
        ListNamespacesOp,
        Op,
        PutOp,
        Result,
        SearchItem,
        SearchOp,
    )

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    BaseStore = object
    GetOp = object
    Item = object
    ListNamespacesOp = object
    Op = object
    PutOp = object
    Result = object
    SearchItem = object
    SearchOp = object


class AgentArtsMemoryStore(BaseStore):
    """
    AgentArts Memory Store for LangGraph cross-thread memory.

    This store enables sharing memory across different conversation threads
    using AgentArts Memory service with semantic search capabilities.

    Features:
        - Semantic search with query + score
        - Cross-thread memory sharing (space-level storage)
        - Automatic memory extraction from messages (backend processing)
        - Native async support using AsyncMemoryClient

    Namespace Usage (LangGraph Standard):
        - namespace is a hierarchical path for organization
        - Use filter for precise actor_id/assistant_id/session_id filtering

    Design Philosophy:
        - Put: add messages -> backend extracts memories automatically
        - Search: semantic search with query + filter
        - Get: retrieve specific memory by key (memory_id)
        - Delete: not supported (backend manages memory lifecycle)

    Example:
        >>> from agentarts.sdk.integration.langgraph import AgentArtsMemoryStore
        >>> from langchain_core.messages import HumanMessage
        >>>
        >>> store = AgentArtsMemoryStore(
        ...     space_id="your-space-id",
        ...     api_key="your-api-key"
        ... )
        >>>
        >>> # Put - add message (backend will extract memory)
        >>> store.put(
        ...     namespace=("memories", "user-001"),
        ...     key="msg-1",
        ...     value={
        ...         "content": "I prefer dark mode",
        ...         "actor_id": "user-001",
        ...         "session_id": "session-xyz"
        ...     }
        ... )
        >>>
        >>> # Search with query and filter
        >>> results = store.search(
        ...     ("memories",),
        ...     query="user preferences",
        ...     filter={"actor_id": "user-001"},
        ...     limit=5
        ... )
        >>> for item in results:
        ...     print(f"[{item.score:.2f}] {item.value['content']}")
        >>>
        >>> # Get specific memory
        >>> memory = store.get(("memories",), key="memory-id-from-search")

    Args:
        space_id: Space ID for the memory service (required)
        region: Huawei Cloud region name, default from environment
        api_key: API Key for data plane authentication (optional)
        verify_ssl: SSL verification setting (default: True)
    """

    supports_ttl: bool = False

    def __init__(
        self,
        space_id: str,
        region: str | None = None,
        api_key: str | None = None,
        verify_ssl: bool | str = True,
    ) -> None:
        if not LANGGRAPH_AVAILABLE:
            msg = (
                "LangGraph is required to use AgentArtsMemoryStore. "
                "Install it with: pip install langgraph"
            )
            raise ImportError(msg)

        self._space_id = space_id
        self._region = region or get_region()
        self._api_key = api_key
        self._verify_ssl = verify_ssl

        self._client = MemoryClient(
            region_name=self._region,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )
        self._async_client = AsyncMemoryClient(
            region_name=self._region,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )

    @property
    def space_id(self) -> str:
        """Get the Space ID."""
        return self._space_id

    @property
    def region(self) -> str:
        """Get the region."""
        return self._region

    def close(self) -> None:
        """Close the underlying MemoryClient connections."""
        self._client.close()

    def __enter__(self) -> AgentArtsMemoryStore:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def batch(self, ops: Iterable[Op]) -> list[Result]:
        """
        Execute multiple operations synchronously in a single batch.

        Args:
            ops: An iterable of operations to execute.

        Returns:
            A list of results corresponding to each operation.
        """
        results: list[Result] = []

        for op in ops:
            if isinstance(op, PutOp):
                self._handle_put(op)
                results.append(None)
            elif isinstance(op, SearchOp):
                result = self._handle_search(op)
                results.append(result)
            elif isinstance(op, GetOp):
                result = self._handle_get(op)
                results.append(result)
            elif isinstance(op, ListNamespacesOp):
                result = self._handle_list_namespaces(op)
                results.append(result)
            else:
                raise ValueError(f"Unknown operation type: {type(op)}")

        return results

    async def abatch(self, ops: Iterable[Op]) -> list[Result]:
        """
        Execute multiple operations asynchronously in a single batch.

        Args:
            ops: An iterable of operations to execute.

        Returns:
            A list of results corresponding to each operation.
        """
        results: list[Result] = []

        for op in ops:
            if isinstance(op, PutOp):
                await self._async_handle_put(op)
                results.append(None)
            elif isinstance(op, SearchOp):
                result = await self._async_handle_search(op)
                results.append(result)
            elif isinstance(op, GetOp):
                result = await self._async_handle_get(op)
                results.append(result)
            elif isinstance(op, ListNamespacesOp):
                result = await self._async_handle_list_namespaces(op)
                results.append(result)
            else:
                raise ValueError(f"Unknown operation type: {type(op)}")

        return results

    def _handle_put(self, op: PutOp) -> None:
        """
        Handle PutOp by adding messages to trigger backend memory extraction.

        Design:
            - value=None: delete operation (not supported, warning only)
            - value contains content and actor_id/session_id metadata
            - Calls add_messages -> backend extracts memories automatically
        """
        if op.value is None:
            logger.warning(
                "Delete operation (PutOp with value=None) is not supported "
                "in AgentArtsMemoryStore. Memories are managed by backend."
            )
            return

        session_id = op.value.get("session_id")
        if not session_id:
            msg = "value must contain 'session_id' for Put operation"
            raise ValueError(msg)

        content = op.value.get("content")
        if not content:
            msg = "value must contain 'content' for Put operation"
            raise ValueError(msg)

        actor_id = op.value.get("actor_id")
        assistant_id = op.value.get("assistant_id")

        message_data = {
            "role": "user",
            "parts": [{"type": "text", "text": content}],
        }
        if actor_id:
            message_data["actor_id"] = actor_id
        if assistant_id:
            message_data["assistant_id"] = assistant_id

        meta = {
            "store_key": op.key,
            "store_namespace": list(op.namespace),
        }
        message_data["meta"] = json.dumps(meta, ensure_ascii=False)

        try:
            self._client.add_messages(
                space_id=self._space_id,
                session_id=session_id,
                messages=[message_data],
            )
            logger.debug(f"Added message to session {session_id} for namespace {op.namespace}")

        except Exception as e:
            logger.exception(f"Failed to put item: {e}")

    async def _async_handle_put(self, op: PutOp) -> None:
        """Async version of _handle_put."""
        if op.value is None:
            logger.warning(
                "Delete operation (PutOp with value=None) is not supported "
                "in AgentArtsMemoryStore. Memories are managed by backend."
            )
            return

        session_id = op.value.get("session_id")
        if not session_id:
            msg = "value must contain 'session_id' for Put operation"
            raise ValueError(msg)

        content = op.value.get("content")
        if not content:
            msg = "value must contain 'content' for Put operation"
            raise ValueError(msg)

        actor_id = op.value.get("actor_id")
        assistant_id = op.value.get("assistant_id")

        message_data = {
            "role": "user",
            "parts": [{"type": "text", "text": content}],
        }
        if actor_id:
            message_data["actor_id"] = actor_id
        if assistant_id:
            message_data["assistant_id"] = assistant_id

        meta = {
            "store_key": op.key,
            "store_namespace": list(op.namespace),
        }
        message_data["meta"] = json.dumps(meta, ensure_ascii=False)

        try:
            await self._async_client.add_messages(
                space_id=self._space_id,
                session_id=session_id,
                messages=[message_data],
            )
            logger.debug(f"Added message to session {session_id} for namespace {op.namespace}")

        except Exception as e:
            logger.exception(f"Failed to put item: {e}")

    def _handle_get(self, op: GetOp) -> Item | None:
        """
        Handle GetOp by retrieving a specific memory by key (memory_id).

        Args:
            op: GetOp with namespace and key

        Returns:
            Item if memory found, None otherwise
        """
        try:
            memory_info = self._client.get_memory(
                space_id=self._space_id,
                memory_id=op.key,
            )

            return self._convert_memory_to_item(memory_info, op.namespace)

        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str or "404" in error_str:
                logger.debug(f"Memory {op.key} not found")
                return None
            logger.exception(f"Failed to get memory {op.key}: {e}")
            raise

    async def _async_handle_get(self, op: GetOp) -> Item | None:
        """Async version of _handle_get."""
        try:
            memory_info = await self._async_client.get_memory(
                space_id=self._space_id,
                memory_id=op.key,
            )

            return self._convert_memory_to_item(memory_info, op.namespace)

        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str or "404" in error_str:
                logger.debug(f"Memory {op.key} not found")
                return None
            logger.exception(f"Failed to get memory {op.key}: {e}")
            raise

    def _handle_search(self, op: SearchOp) -> list[SearchItem]:
        """
        Handle SearchOp by semantic search with query and filter.

        Design:
            - namespace_prefix: organizational path (optional filtering)
            - query: semantic search string
            - filter: actor_id/assistant_id/session_id filtering
            - limit: max results (top_k)

        Args:
            op: SearchOp with namespace_prefix, query, filter, limit

        Returns:
            List of SearchItem with similarity scores
        """
        if not op.query:
            return self._handle_search_without_query(op)

        search_filter = MemorySearchFilter(
            query=op.query,
            top_k=op.limit,
            min_score=0.0,
        )

        if op.filter:
            if "actor_id" in op.filter:
                search_filter.actor_id = op.filter["actor_id"]
            if "assistant_id" in op.filter:
                search_filter.assistant_id = op.filter["assistant_id"]
            if "session_id" in op.filter:
                search_filter.session_id = op.filter["session_id"]
            if "strategy_type" in op.filter:
                search_filter.strategy_type = op.filter["strategy_type"]
            if "memory_type" in op.filter:
                search_filter.memory_type = op.filter["memory_type"]

        try:
            response = self._client.search_memories(
                space_id=self._space_id,
                filters=search_filter,
            )

            return self._convert_search_results_to_items(
                response.results, op.namespace_prefix
            )

        except Exception as e:
            logger.exception(f"Failed to search memories: {e}")
            return []

    async def _async_handle_search(self, op: SearchOp) -> list[SearchItem]:
        """Async version of _handle_search."""
        if not op.query:
            return await self._async_handle_search_without_query(op)

        search_filter = MemorySearchFilter(
            query=op.query,
            top_k=op.limit,
            min_score=0.0,
        )

        if op.filter:
            if "actor_id" in op.filter:
                search_filter.actor_id = op.filter["actor_id"]
            if "assistant_id" in op.filter:
                search_filter.assistant_id = op.filter["assistant_id"]
            if "session_id" in op.filter:
                search_filter.session_id = op.filter["session_id"]
            if "strategy_type" in op.filter:
                search_filter.strategy_type = op.filter["strategy_type"]
            if "memory_type" in op.filter:
                search_filter.memory_type = op.filter["memory_type"]

        try:
            response = await self._async_client.search_memories(
                space_id=self._space_id,
                filters=search_filter,
            )

            return self._convert_search_results_to_items(
                response.results, op.namespace_prefix
            )

        except Exception as e:
            logger.exception(f"Failed to search memories: {e}")
            return []

    def _handle_search_without_query(self, op: SearchOp) -> list[SearchItem]:
        """Handle SearchOp without query using list_memories."""
        from agentarts.sdk.memory.inner.config import MemoryListFilter

        list_filter = MemoryListFilter()
        if op.filter:
            if "actor_id" in op.filter:
                list_filter.actor_id = op.filter["actor_id"]
            if "assistant_id" in op.filter:
                list_filter.assistant_id = op.filter["assistant_id"]
            if "session_id" in op.filter:
                list_filter.session_id = op.filter["session_id"]
            if "strategy_type" in op.filter:
                list_filter.strategy_type = op.filter["strategy_type"]

        try:
            response = self._client.list_memories(
                space_id=self._space_id,
                limit=op.limit,
                offset=op.offset,
                filters=list_filter,
            )

            return [
                SearchItem(
                    namespace=op.namespace_prefix,
                    key=mem.id,
                    value={
                        "content": mem.content,
                        "strategy_type": mem.strategy_type,
                        "actor_id": mem.actor_id,
                        "assistant_id": mem.assistant_id,
                        "session_id": mem.session_id,
                    },
                    created_at=self._parse_datetime(mem.created_at),
                    updated_at=self._parse_datetime(mem.updated_at),
                    score=None,
                )
                for mem in response.items
            ]

        except Exception as e:
            logger.exception(f"Failed to list memories: {e}")
            return []

    async def _async_handle_search_without_query(self, op: SearchOp) -> list[SearchItem]:
        """Async version of _handle_search_without_query."""
        from agentarts.sdk.memory.inner.config import MemoryListFilter

        list_filter = MemoryListFilter()
        if op.filter:
            if "actor_id" in op.filter:
                list_filter.actor_id = op.filter["actor_id"]
            if "assistant_id" in op.filter:
                list_filter.assistant_id = op.filter["assistant_id"]
            if "session_id" in op.filter:
                list_filter.session_id = op.filter["session_id"]
            if "strategy_type" in op.filter:
                list_filter.strategy_type = op.filter["strategy_type"]

        try:
            response = await self._async_client.list_memories(
                space_id=self._space_id,
                limit=op.limit,
                offset=op.offset,
                filters=list_filter,
            )

            return [
                SearchItem(
                    namespace=op.namespace_prefix,
                    key=mem.id,
                    value={
                        "content": mem.content,
                        "strategy_type": mem.strategy_type,
                        "actor_id": mem.actor_id,
                        "assistant_id": mem.assistant_id,
                        "session_id": mem.session_id,
                    },
                    created_at=self._parse_datetime(mem.created_at),
                    updated_at=self._parse_datetime(mem.updated_at),
                    score=None,
                )
                for mem in response.items
            ]

        except Exception as e:
            logger.exception(f"Failed to list memories: {e}")
            return []

    def _handle_list_namespaces(self, op: ListNamespacesOp) -> list[tuple[str, ...]]:
        """
        Handle ListNamespacesOp by extracting unique namespace combinations.

        Design:
            - Use list_memories to get all memories
            - Extract store_namespace from memory metadata
            - Apply prefix/suffix/max_depth filtering

        Args:
            op: ListNamespacesOp with match_conditions, max_depth, limit

        Returns:
            List of unique namespace tuples
        """
        max_limit = min(op.limit * 10, 1000)

        try:
            response = self._client.list_memories(
                space_id=self._space_id,
                limit=max_limit,
                offset=0,
            )

            namespaces_set: set[tuple[str, ...]] = set()

            for mem in response.items:
                namespace = self._extract_namespace_from_memory(mem)
                if namespace:
                    namespaces_set.add(namespace)

            namespaces = sorted(namespaces_set)

            if op.match_conditions:
                namespaces = [
                    ns for ns in namespaces
                    if all(self._matches_condition(ns, cond) for cond in op.match_conditions)
                ]

            if op.max_depth is not None:
                namespaces = sorted({ns[:op.max_depth] for ns in namespaces})

            return namespaces[op.offset:op.offset + op.limit]

        except Exception as e:
            logger.exception(f"Failed to list namespaces: {e}")
            return []

    async def _async_handle_list_namespaces(self, op: ListNamespacesOp) -> list[tuple[str, ...]]:
        """Async version of _handle_list_namespaces."""
        max_limit = min(op.limit * 10, 1000)

        try:
            response = await self._async_client.list_memories(
                space_id=self._space_id,
                limit=max_limit,
                offset=0,
            )

            namespaces_set: set[tuple[str, ...]] = set()

            for mem in response.items:
                namespace = self._extract_namespace_from_memory(mem)
                if namespace:
                    namespaces_set.add(namespace)

            namespaces = sorted(namespaces_set)

            if op.match_conditions:
                namespaces = [
                    ns for ns in namespaces
                    if all(self._matches_condition(ns, cond) for cond in op.match_conditions)
                ]

            if op.max_depth is not None:
                namespaces = sorted({ns[:op.max_depth] for ns in namespaces})

            return namespaces[op.offset:op.offset + op.limit]

        except Exception as e:
            logger.exception(f"Failed to list namespaces: {e}")
            return []

    def _convert_memory_to_item(self, memory_info: Any, namespace: tuple[str, ...]) -> Item:
        """Convert MemoryInfo to LangGraph Item."""
        return Item(
            namespace=namespace,
            key=memory_info.id,
            value={
                "content": memory_info.content,
                "strategy_type": memory_info.strategy_type,
                "actor_id": memory_info.actor_id,
                "assistant_id": memory_info.assistant_id,
                "session_id": memory_info.session_id,
            },
            created_at=self._parse_datetime(memory_info.created_at),
            updated_at=self._parse_datetime(memory_info.updated_at),
        )

    def _convert_search_results_to_items(
        self,
        results: list[dict[str, Any]],
        namespace: tuple[str, ...],
    ) -> list[SearchItem]:
        """Convert search results to LangGraph SearchItem list."""
        items = []

        for result in results:
            record = result.get("record")
            score = result.get("score")

            if not record:
                continue

            record_namespace = self._extract_namespace_from_memory(record) or namespace

            record_id = self._get_attr(record, "id")
            record_content = self._get_attr(record, "content", "")
            record_strategy_type = self._get_attr(record, "strategy_type")
            record_actor_id = self._get_attr(record, "actor_id")
            record_assistant_id = self._get_attr(record, "assistant_id")
            record_session_id = self._get_attr(record, "session_id")
            record_created_at = self._get_attr(record, "created_at")
            record_updated_at = self._get_attr(record, "updated_at")

            search_item = SearchItem(
                namespace=record_namespace,
                key=record_id,
                value={
                    "content": record_content,
                    "strategy_type": record_strategy_type,
                    "actor_id": record_actor_id,
                    "assistant_id": record_assistant_id,
                    "session_id": record_session_id,
                },
                created_at=self._parse_datetime(record_created_at),
                updated_at=self._parse_datetime(record_updated_at),
                score=float(score) if score is not None else None,
            )
            items.append(search_item)

        return items

    def _get_attr(self, obj: Any, attr: str, default: Any = None) -> Any:
        """Get attribute from object (dict or dataclass)."""
        if hasattr(obj, attr):
            return getattr(obj, attr, default)
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return default

    def _extract_namespace_from_memory(self, memory_info: Any) -> tuple[str, ...] | None:
        """Extract namespace from memory metadata."""
        try:
            meta = self._get_attr(memory_info, "meta")
            if meta and isinstance(meta, str):
                meta_dict = json.loads(meta)
                store_namespace = meta_dict.get("store_namespace")
                if store_namespace and isinstance(store_namespace, list):
                    return tuple(store_namespace)

            return None

        except (json.JSONDecodeError, TypeError, AttributeError):
            return None

    def _parse_datetime(self, dt: str | datetime | None) -> datetime:
        """Parse datetime string or return current time."""
        if dt is None:
            return datetime.now(timezone.utc)

        if isinstance(dt, datetime):
            return dt

        if isinstance(dt, str):
            try:
                if dt.endswith("Z"):
                    dt = dt[:-1] + "+00:00"
                return datetime.fromisoformat(dt)
            except ValueError:
                return datetime.now(timezone.utc)

        return datetime.now(timezone.utc)

    def _matches_condition(self, namespace: tuple[str, ...], condition: Any) -> bool:
        """Check if namespace matches a match condition."""
        match_type = getattr(condition, "match_type", None)
        path = getattr(condition, "path", None)

        if not match_type or not path:
            return True

        if match_type == "prefix":
            return namespace[:len(path)] == path if len(namespace) >= len(path) else False
        if match_type == "suffix":
            return namespace[-len(path):] == path if len(namespace) >= len(path) else False

        return True
