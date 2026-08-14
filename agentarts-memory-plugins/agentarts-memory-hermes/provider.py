"""AgentArts Memory Provider for Hermes Agent.

This module implements a Hermes MemoryProvider backed by Huawei Cloud
AgentArts Memory. It provides cross-session long-term memory persistence
and retrieval (ltm_search / ltm_search_summary tools).
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

# ── Environment variable names ──
ENV_API_KEY = "HUAWEICLOUD_SDK_MEMORY_API_KEY"
ENV_REGION = "HUAWEICLOUD_SDK_REGION"
ENV_SPACE_ID = "AGENTARTS_MEMORY_SPACE_ID"

# ── Default values ──
DEFAULT_REGION = "cn-southwest-2"
DEFAULT_TOP_K = 5
DEFAULT_LIST_LIMIT = 10
SYNC_JOIN_TIMEOUT = 5.0

# ── Provider identity ──
PROVIDER_NAME = "agentarts_memory"
PROVIDER_ASSISTANT_ID = "hermes-agent"

# ── system_prompt_block text ──
SYSTEM_PROMPT_BLOCK = (
    "## Long-term Memory (AgentArts Memory)\n"
    "This session provides cross-session long-term memory via Huawei Cloud AgentArts Memory.\n"
    "- Conversation content is automatically written to memory after each turn (non-blocking)\n"
    "- Relevant memories are injected before each LLM call"
    " (user profile / episodic / semantic + history summary)\n"
    "- Use the ltm_search tool to actively retrieve long-term memories\n"
    "- Use the ltm_search_summary tool to view memory summaries\n"
)

# ── Config: non-secret keys written to agentarts.json ──
_NON_SECRET_KEYS = frozenset({"space_id", "region"})

CONFIG_SCHEMA: list[dict[str, Any]] = [
    {
        "key": "api_key",
        "description": "Huawei Cloud AgentArts Memory API Key",
        "secret": True,
        "required": True,
        "env_var": ENV_API_KEY,
    },
    {
        "key": "space_id",
        "description": "Huawei Cloud AgentArts Memory Space ID",
        "required": True,
        "env_var": ENV_SPACE_ID,
    },
    {
        "key": "region",
        "description": "Huawei Cloud Region",
        "default": DEFAULT_REGION,
        "env_var": ENV_REGION,
    },
]


def save_config(values: dict[str, Any], hermes_home: str) -> None:
    """Write non-secret config values to agentarts.json.

    Secret fields (api_key) are handled by Hermes and written to .env.
    Only non-secret fields (space_id, region) are persisted to the JSON file.
    """
    non_secret = {k: v for k, v in values.items() if k in _NON_SECRET_KEYS}
    config_path = Path(hermes_home) / "agentarts.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(non_secret, indent=2, ensure_ascii=False), encoding="utf-8")


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "ltm_search",
        "description": (
            "Search AgentArts long-term memory and return memory entries relevant to the query"
            " (user profile / episodic / semantic + history summary)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Return top K results",
                    "default": DEFAULT_TOP_K,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "ltm_search_summary",
        "description": "Get a list of AgentArts memory summaries to review generated memory overview.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of entries to return",
                    "default": DEFAULT_LIST_LIMIT,
                },
            },
        },
    },
]


def import_memory_sdk() -> Any:
    """Lazily import the AgentArts Memory SDK at runtime.

    Returns a namespace exposing ``MemoryClient``, ``TextMessage`` and
    ``MemorySearchFilter``. This indirection lets tests monkeypatch the
    import without requiring the full SDK to be installed.
    """
    from agentarts.sdk.memory import MemoryClient
    from agentarts.sdk.memory.inner.config import MemorySearchFilter, TextMessage

    return type(
        "_Namespace",
        (),
        {
            "MemoryClient": MemoryClient,
            "TextMessage": TextMessage,
            "MemorySearchFilter": MemorySearchFilter,
        },
    )


logger = logging.getLogger(__name__)


class AgentArtsMemoryProvider:
    """Hermes Memory Provider backed by Huawei Cloud AgentArts Memory."""

    def __init__(self) -> None:
        self._client: Any = None
        self._space_id: str = ""
        self._session_id: str = ""
        self._actor_id: str = ""
        self._assistant_id: str = PROVIDER_ASSISTANT_ID
        self._hermes_home: str = ""
        self._sync_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._sdk: Any = None

    # ── Core lifecycle ──

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    def is_available(self) -> bool:
        """Check whether required env vars are set. Must NOT perform network requests."""
        return all(bool(os.getenv(var)) for var in (ENV_API_KEY, ENV_SPACE_ID))

    def initialize(self, session_id: str, **kwargs: Any) -> None:
        """Called once when the agent starts.

        kwargs always includes ``hermes_home (str)``: the active HERMES_HOME path.
        """
        self._hermes_home = kwargs.get("hermes_home", "")
        self._session_id = session_id
        self._actor_id = session_id
        self._space_id = os.getenv(ENV_SPACE_ID, "")
        region = os.getenv(ENV_REGION, DEFAULT_REGION)
        api_key = os.getenv(ENV_API_KEY, "")

        self._sdk = import_memory_sdk()
        self._client = self._sdk.MemoryClient(
            region_name=region,
            api_key=api_key,
        )

        # Create or reuse an AgentArts Memory session.
        try:
            session_data = self._client.create_memory_session(
                space_id=self._space_id,
                actor_id=self._actor_id,
                assistant_id=self._assistant_id,
            )
            self._session_id = session_data.id
        except Exception as e:
            logger.warning("Failed to create memory session, using Hermes session_id: %s", e)

        logger.info(
            "AgentArts Memory provider initialized: space=%s, session=%s",
            self._space_id,
            self._session_id,
        )

    # ── Configuration ──

    def get_config_schema(self) -> list[dict[str, Any]]:
        return CONFIG_SCHEMA

    def save_config(self, values: dict[str, Any], hermes_home: str) -> None:
        save_config(values, hermes_home)

    # ── Tools ──

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return TOOL_SCHEMAS

    def handle_tool_call(self, name: str, args: dict[str, Any]) -> str:
        if name == "ltm_search":
            return self._ltm_search(args)
        if name == "ltm_search_summary":
            return self._ltm_search_summary(args)
        return json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)

    def _ltm_search(self, args: dict[str, Any] | None) -> str:
        """Execute ltm_search: search AgentArts long-term memories."""
        if not self._client:
            return json.dumps({"error": "Memory provider not initialized"}, ensure_ascii=False)

        if not isinstance(args, dict):
            return json.dumps({"error": "Invalid arguments: expected a dict"}, ensure_ascii=False)

        query = args.get("query", "")
        if not query:
            return json.dumps({"error": "Missing required parameter: query"}, ensure_ascii=False)

        top_k = args.get("top_k", DEFAULT_TOP_K)
        sdk = self._sdk
        if sdk is None:
            return json.dumps({"error": "Memory SDK not initialized"}, ensure_ascii=False)

        try:
            with self._lock:
                results = self._client.search_memories(
                    space_id=self._space_id,
                    filters=sdk.MemorySearchFilter(query=query, top_k=top_k),
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

        result_list = getattr(results, "results", [])
        items: list[dict[str, Any]] = []
        for item in result_list:
            if isinstance(item, dict):
                record = item.get("record", {})
                if isinstance(record, dict):
                    content = record.get("content", "")
                    strategy_type = record.get("strategy_type")
                else:
                    content = str(record)
                    strategy_type = None
                items.append(
                    {
                        "content": content,
                        "score": item.get("score"),
                        "strategy_type": strategy_type,
                    }
                )
            else:
                items.append({"content": str(item), "score": None, "strategy_type": None})

        return json.dumps({"query": query, "results": items}, ensure_ascii=False, indent=2)

    def _ltm_search_summary(self, args: dict[str, Any] | None) -> str:
        """Execute ltm_search_summary: list AgentArts memory summaries."""
        if not self._client:
            return json.dumps({"error": "Memory provider not initialized"}, ensure_ascii=False)

        if not isinstance(args, dict):
            args = {}

        limit = args.get("limit", DEFAULT_LIST_LIMIT)

        try:
            with self._lock:
                memories = self._client.list_memories(
                    space_id=self._space_id,
                    limit=limit,
                )
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

        raw_items = getattr(memories, "items", [])
        items = []
        for m in raw_items:
            items.append(
                {
                    "id": getattr(m, "id", None),
                    "content": getattr(m, "content", None),
                    "strategy_type": getattr(m, "strategy_type", None),
                    "created_at": getattr(m, "created_at", None),
                }
            )

        return json.dumps(
            {"total": getattr(memories, "total", len(items)), "items": items},
            ensure_ascii=False,
            indent=2,
        )

    # ── Optional hooks ──

    def system_prompt_block(self) -> str:
        return SYSTEM_PROMPT_BLOCK

    def prefetch(self, query: str) -> str:
        """Inject relevant long-term memories before each LLM call."""
        if not self._client or not query:
            return ""
        try:
            sdk = self._sdk
            with self._lock:
                results = self._client.search_memories(
                    space_id=self._space_id,
                    filters=sdk.MemorySearchFilter(query=query, top_k=DEFAULT_TOP_K),
                )
            return self._format_search_results(results, query)
        except Exception as e:
            logger.warning("prefetch failed: %s", e)
            return ""

    def _format_search_results(self, results: Any, query: str) -> str:
        """Format search results into text for context injection."""
        result_list = getattr(results, "results", None)
        if not result_list:
            return ""
        lines = [f"## Retrieved Long-term Memory (query: {query})"]
        for i, item in enumerate(result_list, 1):
            if isinstance(item, dict):
                record = item.get("record", {})
                content = record.get("content", "") if isinstance(record, dict) else str(record)
                score = item.get("score", "")
                lines.append(f"{i}. [{score}] {content}")
            else:
                lines.append(f"{i}. {item}")
        return "\n".join(lines) + "\n"

    def sync_turn(self, user_content: str, assistant_content: str) -> None:
        """Persist each conversation turn to AgentArts Memory (non-blocking)."""
        if not self._client:
            return

        space_id = self._space_id
        session_id = self._session_id
        actor_id = self._actor_id
        assistant_id = self._assistant_id

        def _sync() -> None:
            try:
                sdk = self._sdk
                messages = [
                    sdk.TextMessage(
                        role="user",
                        content=user_content,
                        actor_id=actor_id,
                        assistant_id=assistant_id,
                    ),
                    sdk.TextMessage(
                        role="assistant",
                        content=assistant_content,
                        actor_id=actor_id,
                        assistant_id=assistant_id,
                    ),
                ]
                with self._lock:
                    self._client.add_messages(
                        space_id=space_id,
                        session_id=session_id,
                        messages=messages,
                    )
            except Exception as e:
                logger.warning("sync_turn failed: %s", e)

        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=SYNC_JOIN_TIMEOUT)

        self._sync_thread = threading.Thread(target=_sync, daemon=True)
        self._sync_thread.start()

    def on_pre_compress(self, messages: list[Any]) -> str:
        """Re-inject relevant memories before context compression."""
        query = self._extract_query_from_messages(messages)
        return self.prefetch(query)

    def _extract_query_from_messages(self, messages: list[Any]) -> str:
        """Extract a search query from the message list (last user message)."""
        for msg in reversed(messages):
            if isinstance(msg, dict):
                role = msg.get("role")
                content = msg.get("content")
            else:
                role = getattr(msg, "role", None)
                content = getattr(msg, "content", None)
            if role == "user" and content:
                return str(content)[:200]
        return ""

    def on_memory_write(self, action: str, target: str, content: str) -> None:
        """Mirror Hermes MEMORY.md writes to AgentArts Memory."""
        if not self._client or not content:
            return
        try:
            sdk = self._sdk
            message = sdk.TextMessage(
                role="system",
                content=f"[MEMORY_MIRROR][{action}][{target}] {content}",
                actor_id=self._actor_id,
                assistant_id=self._assistant_id,
            )
            with self._lock:
                self._client.add_messages(
                    space_id=self._space_id,
                    session_id=self._session_id,
                    messages=[message],
                )
        except Exception as e:
            logger.warning("on_memory_write failed: %s", e)

    def on_session_end(self, messages: list[Any]) -> None:
        """Default no-op; turns are already persisted via sync_turn."""

    def shutdown(self) -> None:
        """Clean up connections on process exit."""
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=SYNC_JOIN_TIMEOUT)
        if self._client:
            try:
                close = getattr(self._client, "close", None) or getattr(
                    self._client, "shutdown", None
                )
                if close:
                    close()
            except Exception as e:
                logger.warning("shutdown failed: %s", e)
        self._client = None


def register(ctx: Any) -> None:
    """Entry point called by the Hermes memory plugin discovery system."""
    ctx.register_memory_provider(AgentArtsMemoryProvider())
