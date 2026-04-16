"""
Configuration for AgentArts LangGraph Integration

Provides configuration classes for checkpoint saver and other LangGraph
integration components.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

try:
    from langchain_core.runnables import RunnableConfig

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    RunnableConfig = dict[str, Any]


class CheckpointerConfig(BaseModel):
    """
    Runtime configuration for checkpoint operations.

    This class holds runtime parameters extracted from LangGraph's RunnableConfig,
    used during checkpoint save/load operations.

    Attributes:
        thread_id: Thread/conversation ID for session management
        actor_id: Actor/user ID participating in the conversation
        checkpoint_ns: Checkpoint namespace for isolation
        checkpoint_id: Specific checkpoint ID for retrieval

    Class Methods:
        from_runnable_config: Extract configuration from LangGraph RunnableConfig

    Usage:
        >>> # From RunnableConfig
        >>> runnable_config = {"configurable": {"thread_id": "conv-123"}}
        >>> config = CheckpointerConfig.from_runnable_config(runnable_config)
        >>> print(config.thread_id)  # "conv-123"
    """

    thread_id: str
    actor_id: str = ""
    assistant_id: str = ""
    checkpoint_ns: str | None = None
    checkpoint_id: str | None = None

    @property
    def session_id(self)->str:
        return self.thread_id

    @classmethod
    def from_runnable_config(cls, config: RunnableConfig) -> CheckpointerConfig:
        """
        Extract CheckpointerConfig from LangGraph RunnableConfig.

        Args:
            config: LangGraph RunnableConfig containing configurable parameters

        Returns:
            CheckpointerConfig instance with extracted parameters
        """
        configurable = config.get("configurable", {})
        if not configurable:
            msg = "RunableConfig has no configurable parameters in AgentArtsMemorySessionSaver"
            raise ValueError(msg)
        thread_id = configurable.get("thread_id")
        if not thread_id:
            msg = "RunableConfig has no thread_id parameter in AgentArtsMemorySessionSaver"
            raise ValueError(msg)

        return cls(
            thread_id=thread_id,
            actor_id=configurable.get("actor_id", ""),
            assistant_id=configurable.get("assistant_id", ""),
            checkpoint_ns=configurable.get("checkpoint_ns"),
            checkpoint_id=configurable.get("checkpoint_id"),
        )

    def to_runnable_config(self) -> RunnableConfig:
        """
        Convert to LangGraph RunnableConfig format.

        Returns:
            RunnableConfig dictionary with configurable parameters
        """
        configurable: dict[str, Any] = {"thread_id": self.thread_id}

        if self.actor_id:
            configurable["actor_id"] = self.actor_id
        if self.checkpoint_ns is not None:
            configurable["checkpoint_ns"] = self.checkpoint_ns
        if self.checkpoint_id is not None:
            configurable["checkpoint_id"] = self.checkpoint_id

        return {"configurable": configurable}
