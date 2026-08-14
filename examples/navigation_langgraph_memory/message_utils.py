"""Navigation Agent Demo - Message Utilities

Shared helpers for extracting message content and fetching session history.
Used by both CLI (nav_agent.py) and TUI (tui_app.py) to avoid duplication.
"""

from typing import List, Tuple

import config  # noqa: F401
from config import API_KEY, SPACE_ID, VERIFY_SSL


def extract_message_content(msg) -> str:
    """Extract text content from a message (dict or MessageInfo object).

    Handles SDK MessageInfo with 'parts' field: [{'type': 'text', 'text': '...'}].
    Falls back to 'content' field or str(msg) for other formats.
    """
    if isinstance(msg, dict):
        parts = msg.get("parts", [])
    else:
        parts = getattr(msg, "parts", [])

    if parts:
        texts = []
        for p in parts:
            if isinstance(p, dict):
                if p.get("type") == "text":
                    texts.append(p.get("text", ""))
            elif getattr(p, "type", None) == "text":
                texts.append(getattr(p, "text", ""))
        return " ".join(texts)

    # Fallback: try content field
    if isinstance(msg, dict):
        return msg.get("content", "")
    else:
        return getattr(msg, "content", "") or str(msg)


def fetch_session_history(
    session_id: str, k: int = 20
) -> List[Tuple[str, str]]:
    """Fetch recent messages from a session.

    Returns list of (role, content) tuples for user/assistant messages only.
    May raise exceptions on network/API failure — callers should handle them.
    """
    from agentarts.sdk import MemoryClient

    client = MemoryClient(api_key=API_KEY, verify_ssl=VERIFY_SSL)
    try:
        messages = client.get_last_k_messages(
            space_id=SPACE_ID,
            session_id=session_id,
            k=k,
        )

        result = []
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "")
            else:
                role = getattr(msg, "role", "")

            content = extract_message_content(msg)

            if role in ("user", "assistant") and content:
                result.append((role, content))

        return result
    finally:
        client.close()
