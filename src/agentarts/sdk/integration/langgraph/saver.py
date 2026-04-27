"""
AgentArts Memory Session Saver for LangGraph

Provides a checkpoint saver implementation that uses AgentArts Memory service
for persisting LangGraph conversation state.
"""

from __future__ import annotations

import asyncio
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
from agentarts.sdk.memory import MemoryClient
from agentarts.sdk.utils.constant import get_region

if TYPE_CHECKING:
    import builtins
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

try:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.base import (
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

    Architecture:
        - Checkpoints are stored as messages in the Memory service
        - Each checkpoint is tagged with metadata for retrieval
        - Thread ID is used directly as session ID

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
        >>> # Use with LangGraph
        >>> from langgraph.graph import StateGraph
        >>> graph = StateGraph(...)
        >>> compiled = graph.compile(checkpointer=checkpointer)
        >>>
        >>> # Run with thread_id for stateful conversation
        >>> result = compiled.invoke(
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
        self._client = MemoryClient(
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

        return CheckpointTuple(
            config=runtime_config.to_runnable_config(),
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=None,
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
            messages,
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

        Note: This method is not fully supported with Memory service backend.
        Writes are typically handled through the normal message flow.

        Args:
            config: Runnable config containing thread_id
            writes: List of writes to store (channel, value) pairs
            task_id: Task identifier
            task_path: Task path (optional)
        """
        logger.warning(
            "AgentArtsMemorySessionSaver.put_writes() is not fully implemented. "
            "Writes are handled through normal message flow."
        )

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

        return [
            CheckpointTuple(
                config=runtime_config.to_runnable_config(),
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=None,
            )
        ]

    def delete(self, config: RunnableConfig) -> None:
        """
        Delete session for a given thread.

        Note: Memory service does not support direct session deletion.
        Sessions will be cleaned up based on TTL configuration.

        Args:
            config: Runnable config containing thread_id
        """
        logger.warning(
            "AgentArtsMemorySessionSaver.delete() is not supported. "
            "Sessions are cleaned up automatically based on TTL."
        )

    def close(self) -> None:
        """
        Close the underlying MemoryClient connection.

        Releases all underlying connection resources.
        """
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """
        Asynchronously get a checkpoint tuple from the memory service.

        Args:
            config: Runnable config containing thread_id

        Returns:
            CheckpointTuple if messages found, None otherwise
        """
        return await asyncio.to_thread(self.get_tuple, config)

    async def aput(
            self,
            config: RunnableConfig,
            checkpoint: Checkpoint,
            metadata: CheckpointMetadata,
            new_versions: dict[str, str | int | float] | None = None,
    ) -> RunnableConfig:
        """
        Asynchronously store a checkpoint to the memory service.

        Args:
            config: Runnable config containing thread_id
            checkpoint: Checkpoint data to store
            metadata: Checkpoint metadata
            new_versions: New versions (optional)

        Returns:
            Updated config with checkpoint_id
        """
        return await asyncio.to_thread(
            self.put, config, checkpoint, metadata, new_versions
        )

    async def aput_writes(
            self,
            config: RunnableConfig,
            writes: Sequence[tuple[str, Any]],
            task_id: str,
            task_path: str = "",
    ) -> None:
        """
        Asynchronously store intermediate writes linked to a checkpoint.

        Note: This method is not fully supported with Memory service backend.

        Args:
            config: Runnable config containing thread_id
            writes: List of writes to store (channel, value) pairs
            task_id: Task identifier
            task_path: Task path (optional)
        """
        return await asyncio.to_thread(
            self.put_writes, config, writes, task_id, task_path
        )

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

        Args:
            config: Runnable config containing thread_id
            filter: Optional filter criteria
            before: List checkpoints before this config
            limit: Maximum number of checkpoints to return

        Returns:
            List of CheckpointTuple objects
        """
        return await asyncio.to_thread(
            self.list, config, filter=filter, before=before, limit=limit
        )

    async def adelete(self, config: RunnableConfig) -> None:
        """
        Asynchronously delete session for a given thread.

        Note: Memory service does not support direct session deletion.

        Args:
            config: Runnable config containing thread_id
        """
        return await asyncio.to_thread(self.delete, config)
