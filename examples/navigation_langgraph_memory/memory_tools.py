"""
Navigation Agent Demo - Memory Recall Tool

Exposes a single LangChain tool, recall_memory, that performs
semantic search over the AgentArts Memory service to retrieve
long-term memories (user preferences, historical facts, etc.).

This is the ON-DEMAND component of the hybrid recall architecture.
The AUTO-INJECTION component is the auto_recall node in nav_agent.py,
which searches AgentArtsMemoryStore before each LLM call and injects
relevant memories into the system prompt. recall_memory is for deeper
or more specific queries beyond the auto-injected context.

No save_memory tool is needed: the AgentArtsMemorySessionSaver
checkpointer persists all conversation messages, and the backend's
builtin strategies auto-extract memories (semantic, episodic,
user_preference, summary).
"""

from langchain_core.tools import tool

import config  # noqa: F401  (sets env vars as side effect)
from agentarts.sdk import MemoryClient
from agentarts.sdk.memory import MemorySearchFilter
from config import API_KEY, SPACE_ID, VERIFY_SSL

# Current session ID — set by nav_agent.py at startup via set_current_session().
# NOTE: Currently unused by recall_memory() by design: long-term memories
# are cross-session (see comment in recall_memory). Reserved for potential
# future session-scoped queries.
_current_session_id = None


def set_current_session(session_id: str):
    """Set the active session ID for recall_memory searches.

    Called by nav_agent.py when a session is selected or created.
    """
    global _current_session_id
    _current_session_id = session_id


@tool
def recall_memory(query: str) -> str:
    """Search long-term memories with a targeted query.

    The [Memory Context] in the system prompt is a lightweight auto-injected
    preview (top 3). This tool returns more results (top 5) with a specific
    query. Call it when the preview doesn't contain what the user is asking
    about, or when the user references past preferences or prior conversations.

    Args:
        query: Natural language description of what to recall,
            e.g. "user travel preferences" or "previous destinations"

    Returns:
        Bullet list of matching memories, or a "no memories" message.
    """
    if not SPACE_ID or not API_KEY:
        return "Memory service not configured (SPACE_ID/API_KEY missing)."

    client = MemoryClient(api_key=API_KEY, verify_ssl=VERIFY_SSL)
    try:
        # NOTE: Do NOT filter by session_id here. Long-term memories
        # (user preferences, semantic facts) are extracted across ALL
        # sessions and should be recallable from any conversation.
        # Filtering by session_id would scope the search to only memories
        # extracted from the current session, making cross-conversation
        # recall impossible.
        search_filter = MemorySearchFilter(
            query=query,
            top_k=5,
        )
        results = client.search_memories(space_id=SPACE_ID, filters=search_filter)

        items = getattr(results, "results", None) or getattr(results, "items", None) or []
        if not items:
            return "No relevant memories found."

        memories = []
        for r in items:
            record = r.get("record", r) if isinstance(r, dict) else {}
            content = record.get("content", "")
            strategy = record.get("strategy_type", "")
            if content:
                tag = f"[{strategy}] " if strategy else ""
                memories.append(f"- {tag}{content}")

        if not memories:
            return "No relevant memories found."
        return "\n".join(memories)
    except Exception as e:
        return f"Memory recall failed: {e}"
    finally:
        client.close()
