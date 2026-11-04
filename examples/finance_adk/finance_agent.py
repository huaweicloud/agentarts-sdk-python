"""
Finance Agent Demo - Agent Construction & CLI Entry Point

Builds a Google ADK LlmAgent with:
- AgentArtsSessionService as session backend
- AgentArtsMemoryService as memory backend
- before_model_callback for auto memory injection
- after_agent_callback for triggering memory extraction
- 5 FunctionTools (expense, analysis, chart, memory recall)

Usage:
    uv run python examples/finance_adk/finance_agent.py
    uv run python examples/finance_adk/finance_agent.py --debug
"""

import asyncio
import os
import sys

# ---------------------------------------------------------------------------
# 日志级别配置（必须在导入 SDK 之前设置）
# ---------------------------------------------------------------------------
# 检查是否有 --debug 参数
_debug_mode = "--debug" in sys.argv
if _debug_mode:
    os.environ["AGENTARTS_LOG_LEVEL"] = "DEBUG"
else:
    os.environ["AGENTARTS_LOG_LEVEL"] = "WARNING"

# LlmAgent provides before_model_callback / after_agent_callback
# (plain Agent does not).
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmRequest
from google.adk.runners import Runner
from google.genai import types

import config
from agentarts.sdk.memory import AsyncMemoryClient
from agentarts.sdk.integration.google_adk import (
    AgentArtsMemoryService,
    AgentArtsSessionService,
)

import cli_flags  # noqa: F401
from finance_tools import all_tools
from prompts import SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Module-level service instances (lazily initialized)
# ---------------------------------------------------------------------------
_memory_client: AsyncMemoryClient | None = None
_session_service: AgentArtsSessionService | None = None
_memory_service: AgentArtsMemoryService | None = None


def _get_memory_client() -> AsyncMemoryClient:
    """Create or return the shared AsyncMemoryClient instance.

    Both AgentArtsSessionService and AgentArtsMemoryService take a
    single AsyncMemoryClient in their constructors (not space_id/api_key).
    """
    global _memory_client
    if _memory_client is None:
        _memory_client = AsyncMemoryClient(
            api_key=config.API_KEY,
            verify_ssl=config.VERIFY_SSL,
        )
    return _memory_client


def get_session_service() -> AgentArtsSessionService:
    global _session_service
    if _session_service is None:
        _session_service = AgentArtsSessionService(_get_memory_client())
    return _session_service


def get_memory_service() -> AgentArtsMemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = AgentArtsMemoryService(_get_memory_client())
    return _memory_service


# ---------------------------------------------------------------------------
# Helper: extract text from MemoryEntry
# ---------------------------------------------------------------------------
def _extract_memory_text(mem) -> str:
    """从 MemoryEntry 中提取文本内容。

    MemoryEntry.content 是 types.Content 对象（不是字符串），
    需要 .content.parts[0].text 提取文本。
    """
    if mem.content and mem.content.parts:
        return mem.content.parts[0].text or ""
    return ""


# ---------------------------------------------------------------------------
# before_model_callback: Auto memory injection
# ---------------------------------------------------------------------------
async def _inject_memory_context(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
):
    """Search memory and inject results into system instruction."""
    if not config.AUTO_RECALL_ENABLED:
        return None

    # Extract user's current query
    user_content = callback_context.user_content
    if not user_content or not user_content.parts:
        return None

    query_text = ""
    for part in user_content.parts:
        if hasattr(part, "text") and part.text:
            query_text = part.text
            break

    if not query_text:
        return None

    # Search memory using SPACE_ID as app_name (AgentArtsSessionService expects UUID)
    try:
        response = await get_memory_service().search_memory(
            app_name=config.SPACE_ID,
            user_id=config.ACTOR_ID,
            query=query_text,
        )
    except Exception as e:
        if cli_flags.DEBUG:
            print(f"[DEBUG] Memory search failed: {e}")
        return None  # Fail silently, don't block the agent

    if not response.memories:
        return None

    # Format memory context
    lines = [f"\n\n[Memory Context]"]
    for i, mem in enumerate(response.memories[:config.AUTO_RECALL_TOP_K], 1):
        lines.append(f"{i}. {_extract_memory_text(mem)}")
    memory_text = "\n".join(lines)

    # Append to system instruction
    current_instruction = llm_request.config.system_instruction or ""
    llm_request.config.system_instruction = current_instruction + memory_text

    return None  # Don't skip model call


# ---------------------------------------------------------------------------
# after_agent_callback: Trigger memory extraction
# ---------------------------------------------------------------------------
async def _trigger_memory_extraction(callback_context: CallbackContext):
    """Trigger async memory extraction after agent completes."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        if cli_flags.DEBUG:
            print(f"[DEBUG] Memory extraction trigger failed: {e}")
        # Fail silently - extraction is async, failure is non-critical


# ---------------------------------------------------------------------------
# Build agent
# ---------------------------------------------------------------------------
def build_agent() -> LlmAgent:
    """Build the finance assistant LlmAgent."""
    # LiteLLM reads the API key / base URL from environment variables,
    # and config.py has already prefixed the model name with "openai/".
    os.environ.setdefault("OPENAI_API_KEY", config.LLM_API_KEY or "")
    if config.LLM_BASE_URL:
        os.environ.setdefault("OPENAI_BASE_URL", config.LLM_BASE_URL)

    # 可选：禁用推理模式（thinking）。
    # 若使用 DeepSeek 等推理模型且多轮对话报 `Missing reasoning_content` 错误，
    # 可取消下方注释并传入 generate_content_config。
    # 注意：不同模型的参数名称和取值并不相同，请以实际平台和模型为准。
    # generate_config = types.GenerateContentConfig(
    #     http_options=types.HttpOptions(
    #         extra_body={"thinking": {"type": "disabled"}}
    #     )
    # )

    agent = LlmAgent(
        name="finance_assistant",
        model=config.MODEL_NAME,  # 直接传字符串，如 "openai/deepseek-v4-flash"
        instruction=SYSTEM_PROMPT,
        tools=all_tools,
        before_model_callback=_inject_memory_context,
        after_agent_callback=_trigger_memory_extraction,
        # generate_content_config=generate_config,  # 配合上方注释使用
    )
    return agent


def build_runner() -> Runner:
    """Build the ADK Runner with AgentArts services."""
    agent = build_agent()
    runner = Runner(
        agent=agent,
        session_service=get_session_service(),
        memory_service=get_memory_service(),
        app_name=config.SPACE_ID,  # AgentArtsSessionService expects space_id (UUID) as app_name
        auto_create_session=True,  # ADK default is False, must enable
    )
    return runner


# ---------------------------------------------------------------------------
# CLI interaction loop
# ---------------------------------------------------------------------------
async def run_cli():
    """Run the agent in CLI mode."""
    import session_manager

    print("=" * 60)
    print("Finance Agent (Google ADK + AgentArts Memory)")
    print("=" * 60)

    # Session selection
    session_id, session_title = session_manager.select_session_interactive()
    user_id = config.ACTOR_ID

    print(f"\nSession: {session_title}")
    print(f"Session ID: {session_id}")
    print("=" * 60)
    print("Type 'quit' to exit, 'history' to view conversation history.\n")

    runner = build_runner()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "history":
            # Fetch and display session history
            session = await get_session_service().get_session(
                app_name=config.SPACE_ID,  # AgentArtsSessionService expects space_id (UUID) as app_name
                user_id=user_id,
                session_id=session_id,
            )
            for event in session.events:
                if event.content and event.content.parts:
                    author = event.author or "?"
                    text = " ".join(
                        p.text for p in event.content.parts
                        if hasattr(p, "text") and p.text
                    )
                    if text.strip():
                        print(f"  [{author}]: {text}")
            continue

        # Run agent
        content = types.Content(
            role="user",
            parts=[types.Part(text=user_input)],
        )

        print("Assistant: ", end="", flush=True)
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(part.text, end="", flush=True)
        print()  # newline after response


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Finance Agent Demo")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    cli_flags.DEBUG = args.debug

    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
    