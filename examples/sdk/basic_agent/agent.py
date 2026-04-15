"""Basic Agent Example - Simple agent using AgentArts SDK"""

import os
from fastapi import FastAPI
from pydantic import BaseModel

from agentarts.sdk import AgentApp, AgentContext
from agentarts.sdk.memory import TextMessage

app = FastAPI(title="Basic Agent Example")


class ChatRequest(BaseModel):
    message: str
    session_id: str = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Simple chat endpoint that echoes back the message.
    
    This is a minimal example showing how to create an agent
    using AgentArts SDK with FastAPI.
    """
    session_id = request.session_id or "default-session"
    
    response_text = f"You said: {request.message}"
    
    return ChatResponse(
        response=response_text,
        session_id=session_id,
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)