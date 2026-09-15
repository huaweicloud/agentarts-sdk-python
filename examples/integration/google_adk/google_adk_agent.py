"""Google ADK Integration Example - ADK Agent with AgentArts persistence

Demonstrates:
- Session persistence across turns (AgentArtsSessionService)
- Memory ingestion + semantic search (AgentArtsMemoryService)
- Cross-session user preference recovery:
  preferences expressed in one session are recovered via memory search
  and injected into the next session through the ``{user:preferences?}``
  instruction template.

NOTE: user preference extraction is ASYNC on the AgentArts backend
(eventually consistent). A new session started immediately after the
preference is expressed may not see it yet. This example waits
``PREFERENCE_EXTRACT_WAIT_SECONDS`` (default 30) between the two sessions
to let extraction complete.
"""

import asyncio
import os
import sys
import time
import uuid
from datetime import datetime

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.genai import types
# Uncomment the following imports if you need to disable thinking mode for reasoning models
# (e.g., DeepSeek-V4-Flash) that return a `reasoning_content` field, which causes
# `Missing reasoning_content` errors in multi-turn conversations.
# from google.genai.types import GenerateContentConfig, HttpOptions

from agentarts.sdk.integration.google_adk import (
    AgentArtsMemoryService,
    AgentArtsSessionService,
)
from agentarts.sdk.memory import AsyncMemoryClient

# ============================================================================
# 1. Tool definitions
# ============================================================================


def calculate(expression: str) -> str:
    """Evaluate a mathematical expression.

    Use this tool for mathematical calculations. Input should be a valid
    Python math expression (e.g., "2 + 2", "3.14 * r**2").

    Args:
        expression: Mathematical expression to evaluate.

    Returns:
        The result of the calculation as a string.
    """
    import math

    allowed = {
        k: getattr(math, k)
        for k in (
            "sqrt", "sin", "cos", "tan", "log", "log10", "exp",
            "pi", "e", "floor", "ceil", "pow", "fabs",
        )
        if hasattr(math, k)
    }
    allowed.update({"abs": abs, "round": round, "min": min, "max": max})
    try:
        return str(eval(expression, {"__builtins__": {}}, allowed))
    except Exception as exc:
        return f"Error: {exc}"


def get_current_time() -> str:
    """Get the current date and time.

    Returns:
        Current date and time as a formatted string.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================================
# 2. Environment variable validation
# ============================================================================

_required_vars = ["HUAWEICLOUD_SDK_MEMORY_API_KEY", "OPENAI_API_KEY"]
_missing_vars = [v for v in _required_vars if not os.getenv(v)]
if _missing_vars:
    print(f"ERROR: Missing required environment variables: {', '.join(_missing_vars)}")
    print("Please set them before running this example.")
    sys.exit(1)

# ============================================================================
# 3. AgentArts services setup
# ============================================================================

# AsyncMemoryClient reads credentials from environment variables:
#   HUAWEICLOUD_SDK_MEMORY_API_KEY  - API Key for authentication
#   HUAWEICLOUD_SDK_REGION_NAME     - Region (optional, auto-detected)
# SSL verification uses the SDK default (verify_ssl=True).
_memory_client = AsyncMemoryClient()

# User preference recovery is enabled by default. Pass
# user_state_recovery_enabled=False to disable it (session persistence
# still works, but preferences are not recalled across sessions).
_session_service = AgentArtsSessionService(_memory_client)
_memory_service = AgentArtsMemoryService(_memory_client)

SPACE_ID = os.getenv("AGENTARTS_MEMORY_SPACE_ID", "default")

# Wait between expressing a preference and starting the next session,
# giving the backend's async extraction a chance to complete.
PREFERENCE_EXTRACT_WAIT_SECONDS = float(
    os.getenv("PREFERENCE_EXTRACT_WAIT_SECONDS", "30")
)

# ============================================================================
# 4. ADK Agent definition
# ============================================================================

# Agent.model accepts a string in LiteLLM format: "provider/model-name"
# OpenAI:   "openai/gpt-4o-mini"   (requires OPENAI_API_KEY)
# Gemini:   "gemini/gemini-2.0-flash" (requires GOOGLE_API_KEY)
_model_name = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-4o-mini")
MODEL_NAME = _model_name if "/" in _model_name else f"openai/{_model_name}"

# The instruction template references {user:preferences?}. The "?" makes
# the reference OPTIONAL: on the first conversation there are no recovered
# preferences yet, so the placeholder renders as an empty string instead
# of raising a KeyError. Once preferences are recovered, they
# are injected here and the agent can reference them when advising.
agent = Agent(
    name="assistant",
    model=MODEL_NAME,
    description="A helpful assistant with calculator and time tools.",
    instruction=(
        "You are a helpful assistant with calculator and time tools. "
        "The user's known preferences from past conversations are:\n"
        "{user:preferences?}\n"
        "Use these preferences when giving advice (e.g. spending advice)."
    ),
    tools=[calculate, get_current_time],
    # Uncomment below to disable thinking mode for reasoning models (e.g., DeepSeek-V4-Flash).
    # The exact parameter names and values depend on the LLM API you are using.
    # generate_content_config=GenerateContentConfig(
    #     http_options=HttpOptions(
    #         extra_body={"thinking": {"type": "disabled"}}
    #     )
    # ),
)

# ============================================================================
# 5. ADK Runner (wired with AgentArts services)
# ============================================================================

runner = Runner(
    app_name=SPACE_ID,
    agent=agent,
    session_service=_session_service,
    memory_service=_memory_service,
    auto_create_session=True,
)


# ============================================================================
# 6. Helper: run a single turn and collect the text response
# ============================================================================


async def run_turn(session_id: str, user_message: str) -> str:
    """Send a user message and collect the agent's text response."""
    new_message = types.Content(role="user", parts=[types.Part(text=user_message)])

    response_text = ""
    async for event in runner.run_async(
        user_id="demo-user",
        session_id=session_id,
        new_message=new_message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    return response_text


# ============================================================================
# 7. Demo
# ============================================================================


async def demo():
    """Demonstrate session persistence and cross-session user preferences.

    Session 1: exercise tools + express a user preference.
    Session 2 (new session id): the agent recovers the preference from
    memory via the {user:preferences?} template and uses it.
    """
    # --- Session 1: tools + express a preference ---
    session1 = uuid.uuid4().hex[:8]
    print(f"Session 1: {session1}")
    print("-" * 40)

    turns1 = [
        "Hello! What tools do you have?",
        "I have a monthly budget of 5000 CNY, and I want to track spending carefully.",
    ]
    for msg in turns1:
        print(f"\nUser: {msg}")
        reply = await run_turn(session1, msg)
        print(f"Agent: {reply}")

    # --- Wait for async extraction ---
    print()
    print(f"[..] Waiting {PREFERENCE_EXTRACT_WAIT_SECONDS:.0f}s for async "
          "preference extraction...")
    time.sleep(PREFERENCE_EXTRACT_WAIT_SECONDS)

    # --- Session 2 (new session id): preference recovered ---
    session2 = uuid.uuid4().hex[:8]
    print(f"\nSession 2 (new session): {session2}")
    print("-" * 40)
    print("(Preference should be recovered from memory and injected "
          "via {user:preferences?})")
    print()

    turns2 = [
        "Is a 35 CNY coffee reasonable given my monthly budget?",
    ]
    for msg in turns2:
        print(f"User: {msg}")
        reply = await run_turn(session2, msg)
        print(f"Agent: {reply}")


if __name__ == "__main__":
    print("Google ADK + AgentArts Integration Example")
    print()
    print("Required environment variables:")
    print("  HUAWEICLOUD_SDK_MEMORY_API_KEY  - AgentArts API Key")
    print("  AGENTARTS_MEMORY_SPACE_ID       - Memory Space ID (default: 'default')")
    print("  OPENAI_API_KEY                  - OpenAI API Key")
    print("  OPENAI_MODEL_NAME               - Model name (default: openai/gpt-4o-mini)")
    print("  OPENAI_BASE_URL                 - API Base URL (optional)")
    print()
    print("Optional:")
    print("  PREFERENCE_EXTRACT_WAIT_SECONDS - Wait before session 2 (default: 30)")
    print()

    asyncio.run(demo())
