"""
AgentArts Framework Integration Module

Provides adapters for popular agent frameworks with lazy loading support.

Supported frameworks:
- LangGraph (Priority)
- LangChain
- AutoGen
- CrewAI

Usage:
    from agentarts.sdk.integration import LangGraphAdapter
    adapter = LangGraphAdapter()
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentarts.sdk.integration.base import BaseAdapter, WrappedAgent
    from agentarts.sdk.integration.langgraph import LangGraphAdapter

__all__ = [
    "BaseAdapter",
    "LangGraphAdapter",
    "WrappedAgent",
]

_ADAPTER_MODULES = {
    "BaseAdapter": "agentarts.sdk.integration.base",
    "WrappedAgent": "agentarts.sdk.integration.base",
    "LangGraphAdapter": "agentarts.sdk.integration.langgraph",
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
        if name == "LangGraphAdapter":
            msg = (
                f"{name} requires the 'langgraph' extra to be installed. "
                f"Install it with:\n"
                f"  pip install agentarts-sdk[langgraph]\n"
                f"Original error: {e}"
            )
            raise ImportError(
                msg
            ) from e
        raise
