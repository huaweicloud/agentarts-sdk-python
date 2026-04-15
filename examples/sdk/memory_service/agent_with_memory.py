"""Basic Agent Example - Agent with conversation history using Memory Service"""

import os
from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel

from agentarts.sdk import AgentApp, AgentContext
from agentarts.sdk.memory import (
    MemoryClient,
    TextMessage,
    ConversationSession,
    ConversationMessage,
)

app = FastAPI(title="Agent with Memory Example")

memory_client = MemoryClient()


class ChatRequest(BaseModel):
    message: str
    session_id: str = None
    user_id: str = "default-user"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    history: List[dict]


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint with conversation history stored in Memory Service.
    
    This example demonstrates:
    - Creating conversation sessions
    - Storing messages in Memory Service
    - Retrieving conversation history
    """
    session_id = request.session_id or os.urandom(8).hex()
    
    session = ConversationSession(
        session_id=session_id,
        user_id=request.user_id,
    )
    
    user_message = ConversationMessage(
        role="user",
        content=request.message,
    )
    
    memory_client.add_message(session, user_message)
    
    history = memory_client.get_messages(session)
    
    response_text = f"You said: {request.message}. I remember our conversation!"
    
    assistant_message = ConversationMessage(
        role="assistant",
        content=response_text,
    )
    memory_client.add_message(session, assistant_message)
    
    history_dicts = [
        {"role": msg.role, "content": msg.content}
        for msg in history
    ]
    
    return ChatResponse(
        response=response_text,
        session_id=session_id,
        history=history_dicts,
    )


@app.get("/sessions/{session_id}/history")
async def get_history(session_id: str, user_id: str = "default-user"):
    """Get conversation history for a session."""
    session = ConversationSession(
        session_id=session_id,
        user_id=user_id,
    )
    
    messages = memory_client.get_messages(session)
    
    return {
        "session_id": session_id,
        "messages": [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
    }


@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str, user_id: str = "default-user"):
    """Clear conversation history for a session."""
    session = ConversationSession(
        session_id=session_id,
        user_id=user_id,
    )
    
    memory_client.clear_session(session)
    
    return {"status": "cleared", "session_id": session_id}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)