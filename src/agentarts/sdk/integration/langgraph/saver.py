"""
AgentArts Memory Session Saver for LangGraph

Provides a checkpoint saver implementation that uses AgentArts Memory service
for persisting LangGraph conversation state.

Supports both synchronous and asynchronous operations:
- Synchronous methods (get_tuple, put, etc.) use MemoryClient
- Async methods (aget_tuple, aput, etc.) use AsyncMemoryClient for native async
"""

from __future__ import annotations

import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from typing_extensions import Self

from agentarts.sdk.integration.langgraph.config import CheckpointerConfig
from agentarts.sdk.integration.langgraph.converter import (
    langgraph_messages_to_memory,
    memory_to_langgraph_message,
)
from agentarts.sdk.memory import AsyncMemoryClient, MemoryClient, TextMessage
from agentarts.sdk.service import APIException
from agentarts.sdk.utils.constant import get_region

if TYPE_CHECKING:
    import builtins
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

# Namespace UUID for generating deterministic writes session IDs
WRITES_SESSION_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

try:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.base import (
        WRITES_IDX_MAP,
        BaseCheckpointSaver,
        Checkpoint,
        CheckpointMetadata,
        CheckpointTuple,
    )
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    BaseCheckpointSaver = object
    Checkpoint = dict[str, Any]
    CheckpointMetadata = dict[str, Any]
    CheckpointTuple = Any
    JsonPlusSerializer = object
    RunnableConfig = dict[str, Any]
    WRITES_IDX_MAP = {}


class AgentArtsMemorySessionSaver(BaseCheckpointSaver):
    """
    A LangGraph checkpoint saver that uses AgentArts Memory service.

    This class provides seamless integration between LangGraph's checkpointing
    system and AgentArts Memory service, enabling stateful conversations with
    automatic memory management.

    Features:
        - Seamless integration with LangGraph's checkpointing system
        - Automatic state persistence using AgentArts Memory service
        - Support for conversation resumption across sessions
        - Thread ID directly maps to session ID for simplicity
        - Built-in memory extraction and semantic search capabilities
        - Native async support using AsyncMemoryClient (no thread pool overhead)

    Architecture:
        - Checkpoints are stored as messages in the Memory service
        - Each checkpoint is tagged with metadata for retrieval
        - Thread ID is used directly as session ID
        - Sync methods use MemoryClient, async methods use AsyncMemoryClient
        - Delta tracking: put/aput only send new messages since last persisted count to avoid duplicates, tracked per session_id in memory (self._persisted_count). The count is (re)initialized from backend state on every get_tuple()/aget_tuple() call, so it stays in sync with backend state. Reuse a single AgentArtsMemorySessionSaver instance for the application lifetime to maintain the persisted count across multiple get/put calls; do not create multiple saver instances for the same session_id, as each instance maintains its own persisted count.

    Usage:
        >>> from agentarts.sdk.integration.langgraph import AgentArtsMemorySessionSaver
        >>>
        >>> # Create checkpoint saver
        >>> checkpointer = AgentArtsMemorySessionSaver(
        ...     space_id="your-space-id",
        ...     api_key="your-api-key",
        ...     max_messages=10
        ... )
        >>>
        >>> # Use with LangGraph (sync)
        >>> from langgraph.graph import StateGraph
        >>> graph = StateGraph(...)
        >>> compiled = graph.compile(checkpointer=checkpointer)
        >>>
        >>> # Run with thread_id for stateful conversation (sync)
        >>> result = compiled.invoke(
        ...     {"input": "hello"},
        ...     config={"configurable": {"thread_id": "conversation-123"}}
        ... )
        >>>
        >>> # Run with thread_id for stateful conversation (async - recommended)
        >>> result = await compiled.ainvoke(
        ...     {"input": "hello"},
        ...     config={"configurable": {"thread_id": "conversation-123"}}
        ... )

    Args:
        space_id: Space ID for the memory service (required)
        region: Huawei Cloud region name, default from environment
        api_key: API Key for data plane authentication (optional,
            falls back to HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable)
        max_messages: Maximum number of messages to retrieve per query, default 10
        serde: Serializer/deserializer for checkpoints (default: JsonPlusSerializer)
        verify_ssl: SSL verification setting (default: True). Can be:
            - True: Verify SSL certificates using system CA bundle
            - False: Skip SSL verification (not recommended for production)
            - str: Path to custom CA certificate file
    """

    def __init__(
            self,
            space_id: str,
            region: str | None = None,
            api_key: str | None = None,
            max_messages: int = 10,
            serde: JsonPlusSerializer | None = None,
            verify_ssl: bool | str = True,
    ) -> None:
        if not LANGGRAPH_AVAILABLE:
            msg = (
                "LangGraph is required to use AgentArtsMemorySessionSaver. "
                "Install it with: pip install langgraph langchain-core"
            )
            raise ImportError(
                msg
            )

        super().__init__(serde=serde or JsonPlusSerializer())
        self._space_id = space_id
        self._region = region or get_region()
        self._api_key = api_key
        self._max_messages = max_messages
        self._verify_ssl = verify_ssl

        # Trace how many messages have been persisted for each session (thread_id)
        # so put() only sends the delta (new messages since last put)
        # Initialized by get_tuple()/aget_tuple() from backend state, updated by put()/aput()
        self._persisted_count: dict[str, int] = {}

        self._client = MemoryClient(
            region_name=self._region,
            api_key=api_key,
            verify_ssl=verify_ssl
        )
        self._async_client = AsyncMemoryClient(
            region_name=self._region,
            api_key=api_key,
            verify_ssl=verify_ssl
        )

    @property
    def space_id(self) -> str:
        """Get the Space ID."""
        return self._space_id

    @property
    def region(self) -> str:
        """Get the region."""
        return self._region

    @property
    def max_messages(self) -> int:
        """Get the max messages limit."""
        return self._max_messages

    def _get_runtime_config(self, config: RunnableConfig) -> CheckpointerConfig:
        """Extract runtime configuration from RunnableConfig."""
        return CheckpointerConfig.from_runnable_config(config)

    @staticmethod
    def _writes_session_id(session_id: str) -> str:
        """Get the session ID used for storing pending writes.

        Uses UUID5 to generate a deterministic UUID from the session_id,
        ensuring the writes session ID is a valid UUID (required by backend).
        """
        return str(uuid.uuid5(WRITES_SESSION_NAMESPACE, session_id))

    def _extract_pending_writes(
        self,
        messages: list,  # list[MessageInfo] from writes session
        checkpoint_id: str,
    ) -> list[tuple[str, str, Any]]:
        """
        Extract and deduplicate pending writes from write messages.

        Matches InMemorySaver semantics:
        - Regular writes (write_idx >= 0): first occurrence wins (idempotent skip)
        - Special writes (write_idx < 0): last occurrence wins (always overwrite)
        """
        # Messages are ordered oldest to newest; dedupe by (task_id, write_idx)
        seen: dict[tuple[str, int], dict] = {}

        for msg in messages:
            if not (hasattr(msg, "meta") and msg.meta):
                continue
            try:
                meta = json.loads(msg.meta)
            except (json.JSONDecodeError, TypeError):
                continue

            if meta.get("type") != "pending_writes":
                continue
            if meta.get("checkpoint_id") != checkpoint_id:
                continue

            for w in meta.get("writes", []):
                key = (w["task_id"], w["write_idx"])
                if w["write_idx"] >= 0:
                    # Regular write: first occurrence wins (matches InMemorySaver skip)
                    if key not in seen:
                        seen[key] = w
                else:
                    # Special write (ERROR/INTERRUPT/RESUME/SCHEDULED): last wins
                    seen[key] = w

        # Reconstruct PendingWrite tuples: (task_id, channel, value)
        pending_writes: list[tuple[str, str, Any]] = []
        for w in seen.values():
            value_type = w["value_type"]
            value_bytes = base64.b64decode(w["value_data"])
            value = self.serde.loads_typed((value_type, value_bytes))
            pending_writes.append((w["task_id"], w["channel"], value))

        return pending_writes

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """
        Get a checkpoint tuple from the memory service.

        Retrieves messages from the memory service, converts them to LangGraph format,
        and builds a checkpoint tuple.

        Args:
            config: Runnable config containing thread_id and optionally checkpoint_id

        Returns:
            CheckpointTuple if messages found, None otherwise
        """
        runtime_config = self._get_runtime_config(config)
        session_id = runtime_config.session_id

        checkpoint_id_from_config = config.get("configurable", {}).get("checkpoint_id")

        try:
            messages = self._client.get_last_k_messages(
                session_id=session_id,
                k=self._max_messages,
                space_id=self._space_id
            )

        except Exception as e:
            logger.exception(f"Failed to get checkpoint tuple: {e}")
            return None
        if not messages:
            return None

        langgraph_messages = []
        for msg in messages:
            try:
                lg_msg = memory_to_langgraph_message(msg)
                langgraph_messages.append(lg_msg)
            except Exception as e:
                logger.debug(f"Failed to convert message: {e}")
                continue

        if not langgraph_messages:
            return None

        step = 0
        source = "loop"
        checkpoint_id = str(uuid.uuid4())
        checkpoint_ts = datetime.now(timezone.utc).isoformat()
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "meta") and last_msg.meta:
                try:
                    meta = json.loads(last_msg.meta)
                    step = meta.get("step", 0)
                    source = meta.get("source", "loop")
                    checkpoint_id = meta.get("checkpoint_id", checkpoint_id)
                    checkpoint_ts = meta.get("checkpoint_ts", checkpoint_ts)
                except (json.JSONDecodeError, TypeError):
                    logger.debug(f"Failed to parse meta: {last_msg.meta}")

        if checkpoint_id_from_config and checkpoint_id_from_config != checkpoint_id:
            logger.debug(
                f"Requested checkpoint_id {checkpoint_id_from_config} "
                f"does not match latest {checkpoint_id}"
            )
            return None

        checkpoint = Checkpoint(
            v=1,
            id=checkpoint_id,
            ts=checkpoint_ts,
            channel_values={"messages": langgraph_messages},
            channel_versions={"messages": 1},
            versions_seen={},
            step=-1,
            pending_sends=[],
            parents={},
        )

        metadata = CheckpointMetadata(
            source=source,
            step=step,
            writes={},
            parents={},
        )

        # Initialize persisted count from backend state.
        # This runs on every get_tuple() call (including session resume after process restart),
        # so the count stays in sync with backend state. put()/aput() will update the count after persisting new messages.
        self._persisted_count[session_id] = len(langgraph_messages)

        # Pending writes live in a dedicated session (see _writes_session_id)
        pending_writes: list[tuple[str, str, Any]] = []
        try:
            writes_messages = self._client.get_last_k_messages(
                session_id=self._writes_session_id(session_id),
                k=self._max_messages,
                space_id=self._space_id,
            )
            if writes_messages:
                pending_writes = self._extract_pending_writes(
                    writes_messages, checkpoint_id
                )
        except Exception as e:
            logger.debug(f"Failed to retrieve pending writes: {e}")

        return CheckpointTuple(
            config=runtime_config.to_runnable_config(),
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=None,
            pending_writes=pending_writes if pending_writes else None,
        )
    def get(self, config: RunnableConfig) -> Checkpoint | None:
        if value := self.get_tuple(config):
            return value.checkpoint
        return None

    def put(
            self,
            config: RunnableConfig,
            checkpoint: Checkpoint,
            metadata: CheckpointMetadata,
            new_versions: dict[str, str | int | float] | None = None,
    ) -> RunnableConfig:
        """
        Store a checkpoint to the memory service.

        Args:
            config: Runnable config containing thread_id
            checkpoint: Checkpoint data to store
            metadata: Checkpoint metadata
            new_versions: New versions (optional)

        Returns:
            Updated config with checkpoint_id
        """
        runtime_config = self._get_runtime_config(config)
        session_id = runtime_config.session_id

        channel_values = checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])
        if not messages:
            return config

        # Delta tracking: Only send new messages since last persisted count
        # Langgraph calls put() on every step with the full message history, so we need to avoid sending duplicates.
        last_count = self._persisted_count.get(session_id, 0)
        # Defensive: if count is somehow ahead of current messages
        # (e.g., if messages were deleted from backend), reset to 0 to avoid skipping new messages
        if last_count > len(messages):
            last_count = 0
        new_messages = messages[last_count:]
        if not new_messages:
            # if no new messages to persist, skip sending to backend
            return config

        step = metadata.get("step", 0)
        source = metadata.get("source", "loop")
        checkpoint_id = checkpoint.get("id", str(uuid.uuid4()))
        checkpoint_ts = checkpoint.get("ts", datetime.now(timezone.utc).isoformat())
        checkpoint_meta = json.dumps({
            "step": step,
            "source": source,
            "checkpoint_id": checkpoint_id,
            "checkpoint_ts": checkpoint_ts,
        }, ensure_ascii=False)
        cloud_messages = langgraph_messages_to_memory(
            new_messages,
            runtime_config.actor_id,
            runtime_config.assistant_id,
            meta=checkpoint_meta
        )

        try:
            self._client.add_messages(
                space_id=self._space_id,
                session_id=session_id,
                messages=cloud_messages
            )

            # Only update persisted count after successful put to backend.
            # If the call failed (exception), the count remains at the last successful persisted count, so next put() will retry sending the delta.
            self._persisted_count[session_id] = len(messages)

        except Exception as e:
            logger.exception(f"Failed to put checkpoint for session {session_id} with: {e}")

        return config

    def put_writes(
            self,
            config: RunnableConfig,
            writes: Sequence[tuple[str, Any]],
            task_id: str,
            task_path: str = "",
    ) -> None:
        """
        Store intermediate writes linked to a checkpoint.

        Writes are stored as messages in a dedicated writes session
        (UUID5-derived from {session_id}), separate from conversation messages.

        Each put_writes call produces one message containing all writes
        serialized via serde. Idempotency is handled on read side:
        regular writes (idx >= 0) keep first occurrence; special writes
        (ERROR/INTERRUPT/RESUME/SCHEDULED, idx < 0) keep last.

        If the writes session does not exist (HTTP 404), it is automatically
        created and the write is retried.

        Args:
            config: Runnable config containing thread_id and checkpoint_id
            writes: List of writes to store (channel, value) pairs
            task_id: Task identifier
            task_path: Task path (optional)
        """
        if not writes:
            return

        runtime_config = self._get_runtime_config(config)
        session_id = runtime_config.session_id
        writes_session_id = self._writes_session_id(session_id)
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id", "")

        writes_data = []
        for idx, (channel, value) in enumerate(writes):
            write_idx = WRITES_IDX_MAP.get(channel, idx)
            value_type, value_bytes = self.serde.dumps_typed(value)
            writes_data.append({
                "task_id": task_id,
                "task_path": task_path,
                "channel": channel,
                "write_idx": write_idx,
                "value_type": value_type,
                "value_data": base64.b64encode(value_bytes).decode("ascii"),
            })

        write_meta = json.dumps({
            "type": "pending_writes",
            "checkpoint_id": checkpoint_id,
            "writes": writes_data,
        }, ensure_ascii=False)

        cloud_message = TextMessage(
            role="system",
            content="pending_writes",
            meta=write_meta,
        )

        try:
            self._client.add_messages(
                space_id=self._space_id,
                session_id=writes_session_id,
                messages=[cloud_message],
            )
        except APIException as e:
            if e.status_code == 404:
                logger.info(
                    f"Writes session {writes_session_id} not found, creating it"
                )
                try:
                    self._client.create_memory_session(
                        space_id=self._space_id,
                        id=writes_session_id,
                    )
                except Exception:
                    pass
                try:
                    self._client.add_messages(
                        space_id=self._space_id,
                        session_id=writes_session_id,
                        messages=[cloud_message],
                    )
                except Exception as e2:
                    logger.exception(
                        f"Failed to put_writes for session {session_id} "
                        f"after retry: {e2}"
                    )
            else:
                logger.exception(
                    f"Failed to put_writes for session {session_id}: {e}"
                )
        except Exception as e:
            logger.exception(f"Failed to put_writes for session {session_id}: {e}")

    def list(
            self,
            config: RunnableConfig | None,
            *,
            filter: dict[str, Any] | None = None,
            before: RunnableConfig | None = None,
            limit: int | None = None,
    ) -> builtins.list[CheckpointTuple]:
        """
        List checkpoints for a given thread.

        Args:
            config: Runnable config containing thread_id
            filter: Optional filter criteria
            before: List checkpoints before this config
            limit: Maximum number of checkpoints to return

        Returns:
            List of CheckpointTuple objects
        """
        if config is None:
            return []

        runtime_config = self._get_runtime_config(config)
        session_id = runtime_config.session_id

        try:
            result = self._client.list_messages(
                space_id=self._space_id,
                session_id=session_id,
                limit=limit or self._max_messages,
                offset=0
            )
        except Exception as e:
            logger.exception(f"Failed to list checkpoints: {e}")
            return []
        messages = result.items if hasattr(result, "items") else []

        if not messages:
            return []

        langgraph_messages = []
        for msg in messages:
            try:
                lg_msg = memory_to_langgraph_message(msg)
                langgraph_messages.append(lg_msg)
            except Exception as e:
                logger.debug(f"Failed to convert message: {e}")
                continue

        if not langgraph_messages:
            return []

        step = 0
        source = "loop"
        checkpoint_id = str(uuid.uuid4())
        checkpoint_ts = datetime.now(timezone.utc).isoformat()
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "meta") and last_msg.meta:
                try:
                    meta = json.loads(last_msg.meta)
                    step = meta.get("step", 0)
                    source = meta.get("source", "loop")
                    checkpoint_id = meta.get("checkpoint_id", checkpoint_id)
                    checkpoint_ts = meta.get("checkpoint_ts", checkpoint_ts)
                except (json.JSONDecodeError, TypeError):
                    logger.debug(f"Failed to parse meta: {last_msg.meta}")

        checkpoint = Checkpoint(
            v=1,
            id=checkpoint_id,
            ts=checkpoint_ts,
            channel_values={"messages": langgraph_messages},
            channel_versions={"messages": 1},
            versions_seen={},
            step=-1,
            pending_sends=[],
            parents={},
        )

        metadata = CheckpointMetadata(
            source=source,
            step=step,
            writes={},
            parents={},
        )

        # Pending writes live in a dedicated session (see _writes_session_id)
        pending_writes: list[tuple[str, str, Any]] = []
        try:
            writes_messages = self._client.get_last_k_messages(
                session_id=self._writes_session_id(session_id),
                k=self._max_messages,
                space_id=self._space_id,
            )
            if writes_messages:
                pending_writes = self._extract_pending_writes(
                    writes_messages, checkpoint_id
                )
        except Exception as e:
            logger.debug(f"Failed to retrieve pending writes: {e}")

        return [
            CheckpointTuple(
                config=runtime_config.to_runnable_config(),
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=None,
                pending_writes=pending_writes if pending_writes else None,
            )
        ]

    def delete_thread(self, thread_id: str) -> None:
        """
        Delete all checkpoints and writes for a thread.

        Deletes both the main session (conversation messages) and the
        writes session (pending writes). Deletion is soft; the backend
        cleans up associated data asynchronously.

        Args:
            thread_id: Thread ID (= session ID) to delete
        """
        try:
            self._client.delete_session(
                space_id=self._space_id,
                session_id=thread_id,
            )
        except Exception as e:
            logger.exception(f"Failed to delete session for thread {thread_id}: {e}")

        # Also delete the writes session
        writes_sid = self._writes_session_id(thread_id)
        try:
            self._client.delete_session(
                space_id=self._space_id,
                session_id=writes_sid,
            )
        except Exception as e:
            # Writes session may not exist — log at debug level
            logger.debug(f"Failed to delete writes session for thread {thread_id}: {e}")

        # Clean up persisted count tracking
        self._persisted_count.pop(thread_id, None)

    def close(self) -> None:
        """
        Close the underlying MemoryClient connections.

        Releases all underlying connection resources.
        """
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    async def aclose(self) -> None:
        """Close both sync and async client connections."""
        self.close()
        await self._async_client.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """
        Asynchronously get a checkpoint tuple from the memory service.

        Uses AsyncMemoryClient for native async HTTP calls (no thread pool overhead).

        Args:
            config: Runnable config containing thread_id

        Returns:
            CheckpointTuple if messages found, None otherwise
        """
        runtime_config = self._get_runtime_config(config)
        session_id = runtime_config.session_id

        checkpoint_id_from_config = config.get("configurable", {}).get("checkpoint_id")

        try:
            messages = await self._async_client.get_last_k_messages(
                session_id=session_id,
                k=self._max_messages,
                space_id=self._space_id
            )

        except Exception as e:
            logger.exception(f"Failed to get checkpoint tuple: {e}")
            return None
        if not messages:
            return None

        langgraph_messages = []
        for msg in messages:
            try:
                lg_msg = memory_to_langgraph_message(msg)
                langgraph_messages.append(lg_msg)
            except Exception as e:
                logger.debug(f"Failed to convert message: {e}")
                continue

        if not langgraph_messages:
            return None

        step = 0
        source = "loop"
        checkpoint_id = str(uuid.uuid4())
        checkpoint_ts = datetime.now(timezone.utc).isoformat()
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "meta") and last_msg.meta:
                try:
                    meta = json.loads(last_msg.meta)
                    step = meta.get("step", 0)
                    source = meta.get("source", "loop")
                    checkpoint_id = meta.get("checkpoint_id", checkpoint_id)
                    checkpoint_ts = meta.get("checkpoint_ts", checkpoint_ts)
                except (json.JSONDecodeError, TypeError):
                    logger.debug(f"Failed to parse meta: {last_msg.meta}")

        if checkpoint_id_from_config and checkpoint_id_from_config != checkpoint_id:
            logger.debug(
                f"Requested checkpoint_id {checkpoint_id_from_config} "
                f"does not match latest {checkpoint_id}"
            )
            return None

        checkpoint = Checkpoint(
            v=1,
            id=checkpoint_id,
            ts=checkpoint_ts,
            channel_values={"messages": langgraph_messages},
            channel_versions={"messages": 1},
            versions_seen={},
            step=-1,
            pending_sends=[],
            parents={},
        )

        metadata = CheckpointMetadata(
            source=source,
            step=step,
            writes={},
            parents={},
        )

        # Initialize persisted count from backend state (async version).
        self._persisted_count[session_id] = len(langgraph_messages)

        # Pending writes live in a dedicated session (see _writes_session_id)
        pending_writes: list[tuple[str, str, Any]] = []
        try:
            writes_messages = await self._async_client.get_last_k_messages(
                session_id=self._writes_session_id(session_id),
                k=self._max_messages,
                space_id=self._space_id,
            )
            if writes_messages:
                pending_writes = self._extract_pending_writes(
                    writes_messages, checkpoint_id
                )
        except Exception as e:
            logger.debug(f"Failed to retrieve pending writes: {e}")

        return CheckpointTuple(
            config=runtime_config.to_runnable_config(),
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=None,
            pending_writes=pending_writes if pending_writes else None,
        )

    async def aput(
            self,
            config: RunnableConfig,
            checkpoint: Checkpoint,
            metadata: CheckpointMetadata,
            new_versions: dict[str, str | int | float] | None = None,
    ) -> RunnableConfig:
        """
        Asynchronously store a checkpoint to the memory service.

        Uses AsyncMemoryClient for native async HTTP calls (no thread pool overhead).

        Args:
            config: Runnable config containing thread_id
            checkpoint: Checkpoint data to store
            metadata: Checkpoint metadata
            new_versions: New versions (optional)

        Returns:
            Updated config with checkpoint_id
        """
        runtime_config = self._get_runtime_config(config)
        session_id = runtime_config.session_id

        channel_values = checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])
        if not messages:
            return config

        # Delta tracking (async version) - see put() for explanation
        last_count = self._persisted_count.get(session_id, 0)
        if last_count > len(messages):
            last_count = 0
        new_messages = messages[last_count:]
        if not new_messages:
            # if no new messages to persist, skip sending to backend
            return config

        step = metadata.get("step", 0)
        source = metadata.get("source", "loop")
        checkpoint_id = checkpoint.get("id", str(uuid.uuid4()))
        checkpoint_ts = checkpoint.get("ts", datetime.now(timezone.utc).isoformat())
        checkpoint_meta = json.dumps({
            "step": step,
            "source": source,
            "checkpoint_id": checkpoint_id,
            "checkpoint_ts": checkpoint_ts,
        }, ensure_ascii=False)
        cloud_messages = langgraph_messages_to_memory(
            new_messages,
            runtime_config.actor_id,
            runtime_config.assistant_id,
            meta=checkpoint_meta
        )

        try:
            await self._async_client.add_messages(
                space_id=self._space_id,
                session_id=session_id,
                messages=cloud_messages
            )

            # Only update persisted count after successful aput to backend.
            self._persisted_count[session_id] = len(messages)

        except Exception as e:
            logger.exception(f"Failed to put checkpoint for session {session_id} with: {e}")

        return config

    async def aput_writes(
            self,
            config: RunnableConfig,
            writes: Sequence[tuple[str, Any]],
            task_id: str,
            task_path: str = "",
    ) -> None:
        """Async version of put_writes. See put_writes for details."""
        if not writes:
            return

        runtime_config = self._get_runtime_config(config)
        session_id = runtime_config.session_id
        writes_session_id = self._writes_session_id(session_id)
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id", "")

        writes_data = []
        for idx, (channel, value) in enumerate(writes):
            write_idx = WRITES_IDX_MAP.get(channel, idx)
            value_type, value_bytes = self.serde.dumps_typed(value)
            writes_data.append({
                "task_id": task_id,
                "task_path": task_path,
                "channel": channel,
                "write_idx": write_idx,
                "value_type": value_type,
                "value_data": base64.b64encode(value_bytes).decode("ascii"),
            })

        write_meta = json.dumps({
            "type": "pending_writes",
            "checkpoint_id": checkpoint_id,
            "writes": writes_data,
        }, ensure_ascii=False)

        cloud_message = TextMessage(
            role="system",
            content="pending_writes",
            meta=write_meta,
        )

        try:
            await self._async_client.add_messages(
                space_id=self._space_id,
                session_id=writes_session_id,
                messages=[cloud_message],
            )
        except APIException as e:
            if e.status_code == 404:
                logger.info(
                    f"Writes session {writes_session_id} not found, creating it"
                )
                try:
                    await self._async_client.create_memory_session(
                        space_id=self._space_id,
                        id=writes_session_id,
                    )
                except Exception:
                    pass
                try:
                    await self._async_client.add_messages(
                        space_id=self._space_id,
                        session_id=writes_session_id,
                        messages=[cloud_message],
                    )
                except Exception as e2:
                    logger.exception(
                        f"Failed to aput_writes for session {session_id} "
                        f"after retry: {e2}"
                    )
            else:
                logger.exception(
                    f"Failed to aput_writes for session {session_id}: {e}"
                )
        except Exception as e:
            logger.exception(f"Failed to aput_writes for session {session_id}: {e}")

    async def alist(
            self,
            config: RunnableConfig | None,
            *,
            filter: dict[str, Any] | None = None,
            before: RunnableConfig | None = None,
            limit: int | None = None,
    ) -> builtins.list[CheckpointTuple]:
        """
        Asynchronously list checkpoints for a given thread.

        Uses AsyncMemoryClient for native async HTTP calls (no thread pool overhead).

        Args:
            config: Runnable config containing thread_id
            filter: Optional filter criteria
            before: List checkpoints before this config
            limit: Maximum number of checkpoints to return

        Returns:
            List of CheckpointTuple objects
        """
        if config is None:
            return []

        runtime_config = self._get_runtime_config(config)
        session_id = runtime_config.session_id

        try:
            result = await self._async_client.list_messages(
                space_id=self._space_id,
                session_id=session_id,
                limit=limit or self._max_messages,
                offset=0
            )
        except Exception as e:
            logger.exception(f"Failed to list checkpoints: {e}")
            return []
        messages = result.items if hasattr(result, "items") else []

        if not messages:
            return []

        langgraph_messages = []
        for msg in messages:
            try:
                lg_msg = memory_to_langgraph_message(msg)
                langgraph_messages.append(lg_msg)
            except Exception as e:
                logger.debug(f"Failed to convert message: {e}")
                continue

        if not langgraph_messages:
            return []

        step = 0
        source = "loop"
        checkpoint_id = str(uuid.uuid4())
        checkpoint_ts = datetime.now(timezone.utc).isoformat()
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "meta") and last_msg.meta:
                try:
                    meta = json.loads(last_msg.meta)
                    step = meta.get("step", 0)
                    source = meta.get("source", "loop")
                    checkpoint_id = meta.get("checkpoint_id", checkpoint_id)
                    checkpoint_ts = meta.get("checkpoint_ts", checkpoint_ts)
                except (json.JSONDecodeError, TypeError):
                    logger.debug(f"Failed to parse meta: {last_msg.meta}")

        checkpoint = Checkpoint(
            v=1,
            id=checkpoint_id,
            ts=checkpoint_ts,
            channel_values={"messages": langgraph_messages},
            channel_versions={"messages": 1},
            versions_seen={},
            step=-1,
            pending_sends=[],
            parents={},
        )

        metadata = CheckpointMetadata(
            source=source,
            step=step,
            writes={},
            parents={},
        )

        # Pending writes live in a dedicated session (see _writes_session_id)
        pending_writes: list[tuple[str, str, Any]] = []
        try:
            writes_messages = await self._async_client.get_last_k_messages(
                session_id=self._writes_session_id(session_id),
                k=self._max_messages,
                space_id=self._space_id,
            )
            if writes_messages:
                pending_writes = self._extract_pending_writes(
                    writes_messages, checkpoint_id
                )
        except Exception as e:
            logger.debug(f"Failed to retrieve pending writes: {e}")

        return [
            CheckpointTuple(
                config=runtime_config.to_runnable_config(),
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=None,
                pending_writes=pending_writes if pending_writes else None,
            )
        ]

    async def adelete_thread(self, thread_id: str) -> None:
        """
        Asynchronously delete all checkpoints and writes for a thread.

        Args:
            thread_id: Thread ID (= session ID) to delete
        """
        try:
            await self._async_client.delete_session(
                space_id=self._space_id,
                session_id=thread_id,
            )
        except Exception as e:
            logger.exception(f"Failed to delete session for thread {thread_id}: {e}")

        writes_sid = self._writes_session_id(thread_id)
        try:
            await self._async_client.delete_session(
                space_id=self._space_id,
                session_id=writes_sid,
            )
        except Exception as e:
            logger.debug(f"Failed to delete writes session for thread {thread_id}: {e}")

        self._persisted_count.pop(thread_id, None)
