"""
AgentArts Framework Integration Module

Provides adapters for popular agent frameworks with lazy loading support.

Supported frameworks:
- LangGraph (Priority)
- LangChain
- AutoGen
- CrewAI

Usage:
    from agentarts.wrapper.integration import LangGraphAdapter
    adapter = LangGraphAdapter()
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentarts.wrapper.integration.base import BaseAdapter, WrappedAgent
    from agentarts.wrapper.integration.langgraph import LangGraphAdapter

__all__ = [
    "BaseAdapter",
    "WrappedAgent",
    "LangGraphAdapter",
]

_ADAPTER_MODULES = {
    "BaseAdapter": "agentarts.wrapper.integration.base",
    "WrappedAgent": "agentarts.wrapper.integration.base",
    "LangGraphAdapter": "agentarts.wrapper.integration.langgraph",
}


def __getattr__(name: str):
    """
    Lazy import adapters with friendly error messages.
    
    Only imports the corresponding module when the user actually uses
    a specific adapter. Provides clear installation instructions if
    dependencies are missing.
    """
    if name not in _ADAPTER_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    
    module_path = _ADAPTER_MODULES[name]
    
    try:
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, name)
    except ImportError as e:
        if name == "LangGraphAdapter":
            raise ImportError(
                f"{name} requires the 'langgraph' extra to be installed. "
                f"Install it with:\n"
                f"  pip install huaweicloud-agentarts-sdk[langgraph]\n"
                f"Original error: {e}"
            ) from e
        raise
