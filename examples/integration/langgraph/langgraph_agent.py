"""LangGraph Integration Example - Agent with persistent state using AgentArts Memory"""

import os

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph

from agentarts.sdk import AgentArtsRuntimeApp
from agentarts.sdk.integration.langgraph import AgentArtsMemorySessionSaver

app = AgentArtsRuntimeApp()


def create_agent():
    """
    Create a LangGraph agent with AgentArts Memory Service for state persistence.

    This example demonstrates:
    - Using AgentArtsMemorySessionSaver as checkpoint saver
    - Persisting conversation state across sessions
    - Production-ready memory persistence

    Required environment variables:
    - AGENTARTS_MEMORY_SPACE_ID: Memory Space ID
    - HUAWEICLOUD_SDK_MEMORY_API_KEY: API Key for Memory Service
    """
    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )

    def call_model(state: MessagesState):
        response = model.invoke(state["messages"])
        return {"messages": [response]}

    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", call_model)
    workflow.set_entry_point("agent")
    workflow.set_finish_point("agent")

    checkpointer = AgentArtsMemorySessionSaver(
        space_id=os.getenv("AGENTARTS_MEMORY_SPACE_ID"),
        api_key=os.getenv("HUAWEICLOUD_SDK_MEMORY_API_KEY"),
    )

    return workflow.compile(checkpointer=checkpointer)


agent = create_agent()


@app.entrypoint
def handler(payload: dict):
    """
    Chat entrypoint using LangGraph agent with persistent state.

    The conversation state is persisted using AgentArts Memory Service.

    Args:
        payload: The input payload containing:
            - message: The user message
            - thread_id: Optional thread ID for conversation continuity

    Returns:
        dict: Response with reply and thread_id
    """
    message = payload.get("message", "")
    thread_id = payload.get("thread_id")

    if not message:
        return {
            "error": "message is required",
            "thread_id": thread_id or "",
        }

    import os as _os
    thread_id = thread_id or _os.urandom(8).hex()

    config = {"configurable": {"thread_id": thread_id}}

    result = agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )

    last_message = result["messages"][-1]
    response_text = last_message.content if hasattr(last_message, "content") else str(last_message)

    return {
        "response": response_text,
        "thread_id": thread_id,
    }


if __name__ == "__main__":
    print("Starting LangGraph agent with AgentArts Memory")
    print("")
    print("Required environment variables:")
    print("  - OPENAI_API_KEY: OpenAI API Key")
    print("  - OPENAI_MODEL_NAME: Model name (default: gpt-4o-mini)")
    print("  - OPENAI_BASE_URL: API Base URL (optional)")
    print("  - AGENTARTS_MEMORY_SPACE_ID: Memory Space ID")
    print("  - HUAWEICLOUD_SDK_MEMORY_API_KEY: API Key for Memory Service")
    print("")
    print("Endpoints:")
    print("  - POST /invocations - Invoke the agent")

    handler.run(host="0.0.0.0", port=8080)
