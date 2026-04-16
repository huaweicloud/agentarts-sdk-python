"""
Huawei Cloud AgentArts SDK

Build, deploy and manage AI agents with cloud capabilities.

Usage:
    from agentarts.sdk import AgentArtsRuntimeApp, CodeInterpreter, MemoryClient
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("agentarts-sdk")
except PackageNotFoundError:
    __version__ = "0.1.0"

__author__ = "Huawei Cloud AgentArts Team"

__all__ = [
    "__author__",
    "__version__",
]
