"""Memory Service Example - Agent with conversation history using Memory Service"""

import os
from agentarts.sdk import AgentArtsRuntimeApp
from agentarts.sdk.memory import (
    MemoryClient,
    TextMessage,
    SessionCreateRequest,
)

app = AgentArtsRuntimeApp()

memory_client = MemoryClient(
    region_name=os.getenv("HUAWEICLOUD_SDK_REGION", "cn-southwest-2"),
    api_key=os.getenv("HUAWEICLOUD_SDK_MEMORY_API_KEY"),
)


@app.entrypoint
def handler(payload: dict):
    """
    Chat entrypoint with conversation history stored in Memory Service.
    
    This example demonstrates:
    - Creating conversation sessions
    - Storing messages in Memory Service
    - Retrieving conversation history
    
    Required environment variables:
    - HUAWEICLOUD_SDK_MEMORY_API_KEY: API Key for Memory Service
    - HUAWEICLOUD_SDK_REGION: Region (default: cn-southwest-2)
    - AGENTARTS_MEMORY_SPACE_ID: Space ID (or pass in payload)
    
    Args:
        payload: The input payload containing:
            - message: The user message
            - session_id: Optional session ID
            - space_id: Optional space ID
            
    Returns:
        dict: Response with reply and history
    """
    message = payload.get("message", "")
    session_id = payload.get("session_id")
    space_id = payload.get("space_id") or os.getenv("AGENTARTS_MEMORY_SPACE_ID")
    
    if not space_id:
        return {
            "error": "space_id is required. Set AGENTARTS_MEMORY_SPACE_ID env var or pass in payload.",
            "session_id": session_id or "error",
            "history": [],
        }
    
    if not session_id:
        session_req = SessionCreateRequest(space_id=space_id)
        session = memory_client.create_memory_session(session_req)
        session_id = session.session_id
    
    user_message = TextMessage(
        role="user",
        content=message,
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
    
    response_text = f"You said: {message}. I remember our conversation!"
    
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
    
    return {
        "response": response_text,
        "session_id": session_id,
        "history": history_dicts,
    }


@app.ping
def health_check():
    """Health check handler."""
    return "healthy"


if __name__ == "__main__":
    print("Starting Agent with Memory Example...")
    print("Required environment variables:")
    print("  - HUAWEICLOUD_SDK_MEMORY_API_KEY: API Key for Memory Service")
    print("  - HUAWEICLOUD_SDK_REGION: Region (default: cn-southwest-2)")
    print("  - AGENTARTS_MEMORY_SPACE_ID: Space ID (optional, can pass in payload)")
    print("")
    print("Endpoints:")
    print("  - POST /invocations - Invoke the agent")
    print("  - GET  /ping         - Health check")
    
    handler.run(host="0.0.0.0", port=8080)