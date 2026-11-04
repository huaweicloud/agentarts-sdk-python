"""
Finance Agent Demo - Memory Tools

recall_memory tool for on-demand deep memory search.
Uses AgentArtsMemoryService.search_memory() (not the Store API,
since we're in ADK, not LangGraph).
"""

from google.adk.tools import FunctionTool

import config


async def recall_memory_impl(query: str) -> str:
    """Search long-term memories with a targeted query.

    Use this when the [Memory Context] preview doesn't contain
    what you need, or when the user references past preferences
    or prior conversations.

    Args:
        query: The search query describing what you want to find.

    Returns:
        Formatted memory results (up to 5 matches).
    """
    # 延迟导入，避免循环: finance_agent → finance_tools → memory_tools → finance_agent
    from finance_agent import get_memory_service

    memory_service = get_memory_service()
    if memory_service is None:
        return "Memory service not available."

    response = await memory_service.search_memory(
        app_name=config.SPACE_ID,  # AgentArtsSessionService expects space_id (UUID) as app_name
        user_id=config.ACTOR_ID,
        query=query,
    )

    if not response.memories:
        return "No relevant memories found."

    lines = [f"Found {len(response.memories)} memories:"]
    for i, mem in enumerate(response.memories, 1):
        score = mem.custom_metadata.get("score", "N/A") if mem.custom_metadata else "N/A"
        lines.append(f"\n[{i}] (score: {score})")
        # MemoryEntry.content 是 types.Content 对象，需从 parts[0].text 提取
        text = ""
        if mem.content and mem.content.parts:
            text = mem.content.parts[0].text or ""
        lines.append(f"    {text}")

    return "\n".join(lines)


recall_memory = FunctionTool(func=recall_memory_impl)
