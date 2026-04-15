"""LangGraph Integration Example - Agent with persistent state using AgentArts Memory"""

import os
from typing import Annotated
from fastapi import FastAPI
from pydantic import BaseModel

from langgraph.graph import StateGraph, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from agentarts.sdk.integration.langgraph import (
    AgentArtsMemorySessionSaver,
    CheckpointerConfig,
)

app = FastAPI(title="LangGraph Agent with AgentArts Memory")


class ChatRequest(BaseModel):
    message: str
    thread_id: str = None


class ChatResponse(BaseModel):
    response: str
    thread_id: str


def create_agent_with_memory():
    """
    Create a LangGraph agent with AgentArts Memory Service for state persistence.
    
    This example demonstrates:
    - Using AgentArtsMemorySessionSaver as checkpoint saver
    - Persisting conversation state across sessions
    - Integrating with LangChain OpenAI model
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
    
    memory_config = CheckpointerConfig(
        space_id=os.getenv("AGENTARTS_MEMORY_SPACE_ID"),
        endpoint=os.getenv("AGENTARTS_MEMORY_DATA_ENDPOINT"),
    )
    
    checkpointer = AgentArtsMemorySessionSaver(config=memory_config)
    
    return workflow.compile(checkpointer=checkpointer)


def create_agent_with_local_memory():
    """
    Create a LangGraph agent with local in-memory checkpoint saver.
    
    Use this for local development and testing.
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
    
    checkpointer = MemorySaver()
    
    return workflow.compile(checkpointer=checkpointer)


USE_AGENTARTS_MEMORY = os.getenv("USE_AGENTARTS_MEMORY", "false").lower() == "true"

if USE_AGENTARTS_MEMORY:
    agent = create_agent_with_memory()
else:
    agent = create_agent_with_local_memory()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint using LangGraph agent with persistent state.
    
    The conversation state is persisted using:
    - AgentArts Memory Service (when USE_AGENTARTS_MEMORY=true)
    - Local in-memory saver (default for development)
    """
    thread_id = request.thread_id or os.urandom(8).hex()
    
    config = {"configurable": {"thread_id": thread_id}}
    
    result = agent.invoke(
        {"messages": [HumanMessage(content=request.message)]},
        config=config,
    )
    
    last_message = result["messages"][-1]
    response_text = last_message.content if hasattr(last_message, "content") else str(last_message)
    
    return ChatResponse(
        response=response_text,
        thread_id=thread_id,
    )


@app.get("/threads/{thread_id}/history")
async def get_thread_history(thread_id: str):
    """Get conversation history for a thread."""
    config = {"configurable": {"thread_id": thread_id}}
    
    state = agent.get_state(config)
    
    messages = []
    for msg in state.values.get("messages", []):
        messages.append({
            "role": msg.type if hasattr(msg, "type") else "unknown",
            "content": msg.content if hasattr(msg, "content") else str(msg),
        })
    
    return {
        "thread_id": thread_id,
        "messages": messages,
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "memory_mode": "agentarts" if USE_AGENTARTS_MEMORY else "local",
    }


if __name__ == "__main__":
    import uvicorn
    
    print(f"Starting LangGraph agent with memory mode: {'AgentArts' if USE_AGENTARTS_MEMORY else 'Local'}")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)