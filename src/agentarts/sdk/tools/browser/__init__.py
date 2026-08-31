"""
AgentArts Browser Module

Provides browser automation in sandboxed environments:
- Browser: Standard sandbox browser client
- browser_session: Context manager for browser sessions
"""

from .browser_client import Browser, browser_session

__all__ = [
    "Browser",
    "browser_session",
]
