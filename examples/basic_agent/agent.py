"""Basic Agent Example - Simple agent using AgentArts SDK"""

from agentarts.sdk import AgentArtsRuntimeApp

app = AgentArtsRuntimeApp()


@app.entrypoint
def handler(payload: dict):
    """
    Simple entrypoint that echoes back the message.

    This is a minimal example showing how to create an agent
    using AgentArts SDK Runtime App.

    Args:
        payload: The input payload containing 'message' field

    Returns:
        dict: Response with echoed message
    """
    message = payload.get("message", "")
    session_id = payload.get("session_id", "default-session")

    response_text = f"You said: {message}"

    return {
        "response": response_text,
        "session_id": session_id,
    }


if __name__ == "__main__":
    print("Starting Basic Agent Example...")
    print("Endpoints:")
    print("  - POST /invocations - Invoke the agent")
    print("  - GET  /ping         - Health check")

    handler.run(host="0.0.0.0", port=8080)
