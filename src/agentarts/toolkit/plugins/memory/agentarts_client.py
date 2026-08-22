"""Adapter wrapping agentarts.sdk.memory.MemoryClient.

Provides:
  - scope_id:actor_id -> session_id caching (auto create_memory_session on first use)
  - user_id -> actor_id mapping
  - normalized result dicts for the HTTP layer
"""

from __future__ import annotations

import logging
import os
import json
import tempfile
import time
import threading
from typing import Any

logger = logging.getLogger("agentarts_memory_agent.server")

# Debug mode from environment
DEBUG = os.getenv("AGENTARTS_MEMORY_LOG_LEVEL", "info").lower() == "debug"

ENV_API_KEY = "HUAWEICLOUD_SDK_MEMORY_API_KEY"
ENV_REGION = "HUAWEICLOUD_SDK_REGION"
ENV_SPACE_ID = "AGENTARTS_MEMORY_SPACE_ID"

DEFAULT_REGION = "cn-southwest-2"
DEFAULT_ASSISTANT_ID = "agentarts-memory-agent"
DEFAULT_TOP_K = 5
DEFAULT_LIST_LIMIT = 10
DEFAULT_MIN_SCORE = 0.3
SESSION_TTL_SECONDS = 24 * 60 * 60  # 24 hours
SESSION_CACHE_DIR = os.path.join(tempfile.gettempdir(), "agentarts_memory")
SESSION_CACHE_FILE = os.path.join(SESSION_CACHE_DIR, "sessions.json")


def import_memory_sdk() -> Any:
    """Lazily import the AgentArts Memory SDK.

    Returns a namespace exposing MemoryClient, TextMessage and MemorySearchFilter.
    This indirection lets tests monkeypatch the import without requiring the SDK.
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


class AgentArtsMemoryClient:
    """Thin wrapper over MemoryClient with scope->session caching."""

    def __init__(
        self,
        *,
        space_id: str | None = None,
        region_name: str | None = None,
        api_key: str | None = None,
        assistant_id: str = DEFAULT_ASSISTANT_ID,
        sdk: Any = None,
    ) -> None:
        self._space_id = space_id or os.getenv(ENV_SPACE_ID, "")
        self._region = region_name or os.getenv(ENV_REGION, DEFAULT_REGION)
        self._api_key = api_key or os.getenv(ENV_API_KEY)
        self._assistant_id = assistant_id
        self._sdk = sdk or import_memory_sdk()
        self._client: Any = None
        self._lock = threading.Lock()
        # scope_id:actor_id -> session_id cache (in-memory)
        self._sessions: dict[str, str] = {}

    # ── file-based session cache (shared with hook scripts) ──

    @staticmethod
    def _read_file_cache() -> dict[str, Any]:
        try:
            if os.path.exists(SESSION_CACHE_FILE):
                with open(SESSION_CACHE_FILE, encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    @staticmethod
    def _write_file_cache(data: dict[str, Any]) -> None:
        try:
            os.makedirs(SESSION_CACHE_DIR, exist_ok=True)
            with open(SESSION_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def _get_cached_sid_from_file(cache_key: str) -> str | None:
        entry = AgentArtsMemoryClient._read_file_cache().get(cache_key)
        if not entry:
            return None
        if isinstance(entry, str):
            return None  # old format, force re-create
        sid = entry.get("sid")
        ts = entry.get("ts", 0)
        if sid and (time.time() - ts) < SESSION_TTL_SECONDS:
            return sid
        return None

    @staticmethod
    def _put_cached_sid_to_file(cache_key: str, sid: str) -> None:
        data = AgentArtsMemoryClient._read_file_cache()
        data[cache_key] = {"sid": sid, "ts": int(time.time())}
        AgentArtsMemoryClient._write_file_cache(data)

    @staticmethod
    def _invalidate_cached_sid(cache_key: str) -> None:
        data = AgentArtsMemoryClient._read_file_cache()
        if cache_key in data:
            del data[cache_key]
            AgentArtsMemoryClient._write_file_cache(data)

    # ── availability ──
    def is_configured(self) -> bool:
        """Return True if the minimal env vars are present (no network)."""
        return bool(self._space_id and self._api_key)

    @property
    def space_id(self) -> str:
        return self._space_id

    def _ensure_client(self) -> Any:
        if self._client is None:
            self._client = self._sdk.MemoryClient(
                region_name=self._region,
                api_key=self._api_key,
            )
        return self._client

    def _get_or_create_session(self, scope_id: str, actor_id: str) -> str:
        """Return cached session_id for scope+actor, creating one on first use."""
        with self._lock:
            cache_key = f"{scope_id}:{actor_id}"
            sid = self._sessions.get(cache_key)
            if sid:
                if DEBUG:
                    logger.debug(
                        "[SDK] session cache hit | scope_id=%s, actor_id=%s, session_id=%s",
                        scope_id,
                        actor_id,
                        sid,
                    )
                return sid
            # Check file-based cache (shared with hook scripts).
            file_sid = self._get_cached_sid_from_file(cache_key)
            if file_sid:
                self._sessions[cache_key] = file_sid
                return file_sid
            client = self._ensure_client()
            if DEBUG:
                logger.debug(
                    "[SDK] creating session | scope_id=%s, actor_id=%s, space_id=%s",
                    scope_id,
                    actor_id,
                    self._space_id[:8] + "...",
                )
            session = client.create_memory_session(
                space_id=self._space_id,
                actor_id=actor_id,
                assistant_id=self._assistant_id,
            )
            sid = getattr(session, "id", None) or getattr(session, "session_id", "")
            if not sid:
                raise RuntimeError("create_memory_session returned empty session id")
            self._sessions[cache_key] = sid
            self._put_cached_sid_to_file(cache_key, sid)
            if DEBUG:
                logger.debug(
                    "[SDK] session created | scope_id=%s, actor_id=%s, session_id=%s",
                    scope_id,
                    actor_id,
                    sid,
                )
            return sid

    def invalidate_session(self, scope_id: str, actor_id: str) -> None:
        """Invalidate cached session for scope+actor (in-memory + file)."""
        with self._lock:
            cache_key = f"{scope_id}:{actor_id}"
            self._sessions.pop(cache_key, None)
            self._invalidate_cached_sid(cache_key)

    # ── operations ──
    def add_messages(
        self,
        messages: list[dict[str, str]],
        *,
        user_id: str,
        scope_id: str,
    ) -> dict[str, Any]:
        """Record messages under the scope's session.

        ``messages`` is a list of ``{"role": str, "content": str}``.
        """
        sid = self._get_or_create_session(scope_id, user_id)
        client = self._ensure_client()
        sdk_msgs = [
            self._sdk.TextMessage(
                role=m["role"],
                content=m["content"],
                actor_id=user_id,
                assistant_id=self._assistant_id,
            )
            for m in messages
        ]
        if DEBUG:
            logger.debug(
                "[SDK] add_messages | user_id=%s, scope_id=%s, session_id=%s, count=%d",
                user_id,
                scope_id,
                sid,
                len(sdk_msgs),
            )
        resp = client.add_messages(
            space_id=self._space_id,
            session_id=sid,
            messages=sdk_msgs,
        )
        return {"session_id": sid, "count": len(sdk_msgs)}

    def search_memories(
        self,
        *,
        query: str,
        user_id: str,
        scope_id: str,
        num: int = DEFAULT_TOP_K,
        threshold: float = DEFAULT_MIN_SCORE,
    ) -> list[dict[str, Any]]:
        """Semantic search; returns normalized list of {content, score, type}."""
        client = self._ensure_client()
        if DEBUG:
            logger.debug(
                "[SDK] search_memories | user_id=%s, scope_id=%s, query='%s...', num=%d",
                user_id,
                scope_id,
                query[:50] if query else "",
                num,
            )
        filters = self._sdk.MemorySearchFilter(
            query=query,
            top_k=num,
            min_score=threshold,
            actor_id=user_id,
        )
        resp = client.search_memories(space_id=self._space_id, filters=filters)
        results = self._normalize_search_results(resp)
        if DEBUG:
            logger.debug("[SDK] search_memories | results=%d", len(results))
        return results

    def list_memories(
        self,
        *,
        user_id: str | None = None,
        scope_id: str | None = None,
        limit: int = DEFAULT_LIST_LIMIT,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List memory records; returns normalized list of {content, type, created_at}."""
        client = self._ensure_client()
        if DEBUG:
            logger.debug(
                "[SDK] list_memories | user_id=%s, scope_id=%s, limit=%d",
                user_id or "default",
                scope_id or "default",
                limit,
            )
        resp = client.list_memories(
            space_id=self._space_id,
            limit=limit,
            offset=offset,
        )
        return self._normalize_list_results(resp)

    def health(self) -> dict[str, Any]:
        """Return config readiness (no network call)."""
        return {
            "status": "healthy" if self.is_configured() else "misconfigured",
            "space_id": bool(self._space_id),
            "api_key": bool(self._api_key),
        }

    # ── normalization helpers ──
    @staticmethod
    def _extract_content(record: Any) -> str:
        """Best-effort extract content string from a search result record."""
        if record is None:
            return ""
        if isinstance(record, str):
            return record
        if isinstance(record, dict):
            for key in ("content", "text", "summary", "message"):
                val = record.get(key)
                if val:
                    return str(val)
            # nested record
            inner = record.get("record")
            if inner:
                return AgentArtsMemoryClient._extract_content(inner)
        return str(record)

    @staticmethod
    def _extract_type(record: Any) -> str:
        if isinstance(record, dict):
            for key in ("strategy_type", "memory_type", "type", "strategy"):
                val = record.get(key)
                if val:
                    return str(val)
            inner = record.get("record")
            if isinstance(inner, dict):
                return AgentArtsMemoryClient._extract_type(inner)
        return ""

    @classmethod
    def _normalize_search_results(cls, resp: Any) -> list[dict[str, Any]]:
        """Normalize MemorySearchResponse -> list of {content, score, type}."""
        raw_results = getattr(resp, "results", None)
        if not raw_results:
            return []
        out: list[dict[str, Any]] = []
        for item in raw_results:
            if isinstance(item, dict):
                record = item.get("record")
                score = item.get("score")
                content = cls._extract_content(record)
                mtype = cls._extract_type(record)
            else:
                record = getattr(item, "record", None)
                score = getattr(item, "score", None)
                content = cls._extract_content(record)
                mtype = cls._extract_type(record)
            out.append(
                {
                    "content": content,
                    "score": float(score) if score is not None else 0.0,
                    "type": mtype,
                }
            )
        return out

    @classmethod
    def _normalize_list_results(cls, resp: Any) -> list[dict[str, Any]]:
        """Normalize MemoryListResponse -> list of {content, type, created_at, id}."""
        items = getattr(resp, "items", None) or []
        out: list[dict[str, Any]] = []
        for mem in items:
            if isinstance(mem, dict):
                content = mem.get("content", "")
                mtype = mem.get("strategy_type") or mem.get("memory_type", "")
                mid = mem.get("id", "")
                created = mem.get("created_at", "")
            else:
                content = getattr(mem, "content", "")
                mtype = getattr(mem, "strategy_type", "") or getattr(mem, "memory_type", "")
                mid = getattr(mem, "id", "")
                created = getattr(mem, "created_at", "")
            out.append(
                {
                    "id": mid,
                    "content": content,
                    "type": mtype,
                    "created_at": created,
                }
            )
        return out
