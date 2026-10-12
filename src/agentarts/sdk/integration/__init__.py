"""
AgentArts Framework Integration Module

Provides adapters for popular agent frameworks with lazy loading support.

Supported frameworks:
- LangGraph
- Google ADK

Usage:
    from agentarts.sdk.integration import AgentArtsMemorySessionSaver
    saver = AgentArtsMemorySessionSaver(config)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentarts.sdk.integration.google_adk import (
        AgentArtsMemoryService,
        AgentArtsSessionService,
    )
    from agentarts.sdk.integration.langgraph import (
        AgentArtsMemorySessionSaver,
        AgentArtsMemoryStore,
        CheckpointerConfig,
    )

__all__ = [
    "AgentArtsMemoryService",
    "AgentArtsMemorySessionSaver",
    "AgentArtsMemoryStore",
    "AgentArtsSessionService",
    "CheckpointerConfig",
]

_ADAPTER_MODULES = {
    "AgentArtsMemoryService": "agentarts.sdk.integration.google_adk",
    "AgentArtsMemorySessionSaver": "agentarts.sdk.integration.langgraph",
    "AgentArtsMemoryStore": "agentarts.sdk.integration.langgraph",
    "AgentArtsSessionService": "agentarts.sdk.integration.google_adk",
    "CheckpointerConfig": "agentarts.sdk.integration.langgraph",
}

_EXTRA_FOR_MODULE = {
    "agentarts.sdk.integration.google_adk": "google-adk",
    "agentarts.sdk.integration.langgraph": "langgraph",
}


def __getattr__(name: str):
    """
    Lazy import adapters with friendly error messages.

    Only imports the corresponding module when the user actually uses
    a specific adapter. Provides clear installation instructions if
    dependencies are missing.
    """
    if name not in _ADAPTER_MODULES:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)

    module_path = _ADAPTER_MODULES[name]

    try:
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, name)
    except ImportError as e:
        extra = _EXTRA_FOR_MODULE.get(module_path)
        if extra is None:
            raise
        msg = (
            f"{name} requires the {extra!r} extra to be installed. "
            f"Install it with:\n"
            f"  pip install agentarts-sdk[{extra}]\n"
            f"Original error: {e}"
        )
        raise ImportError(
            msg
        ) from e
