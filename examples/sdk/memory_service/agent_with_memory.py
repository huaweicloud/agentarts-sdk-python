"""Memory Service Example - Agent with conversation history using Memory Service"""

import os
from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel

from agentarts.sdk.memory import (
    MemoryClient,
    TextMessage,
    SessionCreateRequest,
)

app = FastAPI(title="Agent with Memory Example")

memory_client = MemoryClient(
    region_name=os.getenv("HUAWEICLOUD_SDK_REGION", "cn-southwest-2"),
    api_key=os.getenv("HUAWEICLOUD_SDK_MEMORY_API_KEY"),
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = None
    space_id: str = None


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
    
    Required environment variables:
    - HUAWEICLOUD_SDK_MEMORY_API_KEY: API Key for Memory Service
    - HUAWEICLOUD_SDK_REGION: Region (default: cn-southwest-2)
    """
    space_id = request.space_id or os.getenv("AGENTARTS_MEMORY_SPACE_ID")
    if not space_id:
        return ChatResponse(
            response="Error: space_id is required. Set AGENTARTS_MEMORY_SPACE_ID env var or pass in request.",
            session_id=request.session_id or "error",
            history=[],
        )
    
    session_id = request.session_id
    if not session_id:
        session_req = SessionCreateRequest(space_id=space_id)
        session = memory_client.create_memory_session(session_req)
        session_id = session.session_id
    
    user_message = TextMessage(
        role="user",
        content=request.message,
    )
    
    memory_client.add_messages(
        space_id=space_id,
        session_id=session_id,
        messages=[user_message],
    )
    
    history = memory_client.get_last_k_messages(
        space_id=space_id,
        session_id=session_id,
        k=10,
    )
    
    response_text = f"You said: {request.message}. I remember our conversation!"
    
    assistant_message = TextMessage(
        role="assistant",
        content=response_text,
    )
    memory_client.add_messages(
        space_id=space_id,
        session_id=session_id,
        messages=[assistant_message],
    )
    
    history_dicts = [
        {"role": msg.role, "content": msg.content}
        for msg in history.messages
    ]
    
    return ChatResponse(
        response=response_text,
        session_id=session_id,
        history=history_dicts,
    )


@app.get("/spaces/{space_id}/sessions/{session_id}/history")
async def get_history(space_id: str, session_id: str, k: int = 10):
    """Get conversation history for a session."""
    messages = memory_client.get_last_k_messages(
        space_id=space_id,
        session_id=session_id,
        k=k,
    )
    
    return {
        "session_id": session_id,
        "messages": [
            {"role": msg.role, "content": msg.content}
            for msg in messages.messages
        ],
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    print("Starting Agent with Memory Example...")
    print("Required environment variables:")
    print("  - HUAWEICLOUD_SDK_MEMORY_API_KEY: API Key for Memory Service")
    print("  - HUAWEICLOUD_SDK_REGION: Region (default: cn-southwest-2)")
    print("  - AGENTARTS_MEMORY_SPACE_ID: Space ID (optional, can pass in request)")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)