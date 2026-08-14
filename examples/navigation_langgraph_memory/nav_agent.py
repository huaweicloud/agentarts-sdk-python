"""
Navigation Agent Demo - LangGraph Agent with AgentArts Memory

A local interactive navigation assistant that can:
  - Search for POIs (gas stations, restaurants, parking, etc.)
  - Plan routes (driving/walking/riding/transit)
  - Generate map visualization links
  - Recall long-term user preferences and history via AgentArts Memory

Conversation state is persisted through AgentArtsMemorySessionSaver
(native SDK LangGraph checkpointer). The backend auto-extracts
memories using the four builtin strategies. Long-term recall uses a
hybrid approach: an auto_recall node searches AgentArtsMemoryStore
(SDK LangGraph Store) before each LLM call to inject relevant memories,
and the recall_memory tool provides on-demand deep search for specific
queries beyond the auto-injected context.

Prerequisites:
  1. Install dependencies:
       uv sync --extra langgraph --extra tui
       uv pip install langchain-openai
     Or: pip install -r examples/navigation_langgraph_memory/requirements.txt
  2. Copy env template and fill in credentials:
       cp examples/navigation_langgraph_memory/.env.example examples/navigation_langgraph_memory/.env
  3. Create memory space (writes SPACE_ID + API_KEY to .env):
       uv run python examples/navigation_langgraph_memory/setup_memory.py
  4. Fill in LLM credentials in .env (OPENAI_API_KEY, etc.)
  5. (Optional) Set AMAP_KEY in .env for real AMap API calls

Usage:
  uv run python examples/navigation_langgraph_memory/nav_agent.py          # TUI mode (default)
  uv run python examples/navigation_langgraph_memory/nav_agent.py --cli    # Classic CLI mode (no SDK logs)
  uv run python examples/navigation_langgraph_memory/nav_agent.py --debug  # CLI mode + SDK INFO logs
"""

import os
import sys

import config  # noqa: F401  (sets env vars as side effect)
from config import (
    ACTOR_ID,
    API_KEY,
    ASSISTANT_ID,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL_NAME,
    SPACE_ID,
    VERIFY_SSL,
)


def _check_env():
    """Validate that required env vars are set before building the agent."""
    missing = []
    if not SPACE_ID:
        missing.append("AGENTARTS_MEMORY_SPACE_ID")
    if not API_KEY:
        missing.append("HUAWEICLOUD_SDK_MEMORY_API_KEY")
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")

    if missing:
        print("[ERR] Missing required environment variables:")
        for v in missing:
            print(f"    - {v}")
        print("\nRun setup first:  uv run python examples/navigation_langgraph_memory/setup_memory.py")
        print("Then export the printed variables and your OPENAI_API_KEY.")
        sys.exit(1)


def build_agent():
    """Build and compile the LangGraph navigation agent."""
    # Imports are deferred so _check_env() runs first and fails fast
    # without importing heavy modules.
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
    from langgraph.graph import END, MessagesState, START, StateGraph
    from langgraph.prebuilt import ToolNode
    from langgraph.store.base import BaseStore

    from agentarts.sdk.integration.langgraph import (
        AgentArtsMemorySessionSaver,
        AgentArtsMemoryStore,
    )

    from amap_tools import generate_map_link, geocode_address, plan_route, search_poi
    from memory_tools import recall_memory
    from prompts import SYSTEM_PROMPT

    class NavAgentState(MessagesState):
        """State with memory_context for auto-injected long-term memories.

        memory_context holds formatted memory text from the auto_recall
        node. It uses the default (replace) reducer: each auto_recall
        invocation overwrites the previous value.
        """

        memory_context: str

    all_tools = [geocode_address, search_poi, plan_route, generate_map_link, recall_memory]

    llm = ChatOpenAI(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL or None,
        temperature=0,
    )
    llm_with_tools = llm.bind_tools(all_tools)

    def auto_recall(state: NavAgentState, *, store: BaseStore) -> dict:
        """Search Store for relevant long-term memories, inject as context.

        Runs before the agent node each turn. Searches the
        AgentArtsMemoryStore for memories matching the user's latest
        message, filtered by actor_id (cross-session, user-scoped).
        Results are stored in state["memory_context"] and appended to
        the system prompt by call_model. Failures are silent -- the
        agent continues without memories.
        """
        if not config.AUTO_RECALL_ENABLED:
            return {"memory_context": ""}

        last_msg = state["messages"][-1]
        if not isinstance(last_msg, HumanMessage):
            return {"memory_context": ""}

        query = last_msg.content
        try:
            items = store.search(
                (),
                query=query,
                filter={"actor_id": config.ACTOR_ID},
                limit=config.AUTO_RECALL_TOP_K,
            )
        except Exception as e:
            # Graceful degradation: never block the agent
            import logging
            logging.getLogger(__name__).warning(
                f"Auto-recall failed, continuing without memories: {e}")
            return {"memory_context": ""}

        if not items:
            return {"memory_context": ""}

        lines = []
        for item in items:
            content = item.value.get("content", "")
            strategy = item.value.get("strategy_type", "")
            if content:
                tag = f"[{strategy}] " if strategy else ""
                lines.append(f"- {tag}{content}")

        if not lines:
            return {"memory_context": ""}
        return {"memory_context": "\n".join(lines)}

    def call_model(state: NavAgentState):
        """Invoke LLM with system prompt, memory context, and message state."""
        system_content = SYSTEM_PROMPT
        memory_ctx = state.get("memory_context", "")
        if memory_ctx:
            system_content += f"\n\n[Memory Context]\n{memory_ctx}"
        messages = [SystemMessage(content=system_content)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: NavAgentState) -> str:
        """Route to tools node if LLM made tool calls, else end."""
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    # Build graph: START -> auto_recall -> agent -> (tools?) -> agent/END
    workflow = StateGraph(NavAgentState)
    workflow.add_node("auto_recall", auto_recall)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(all_tools))
    workflow.add_edge(START, "auto_recall")
    workflow.add_edge("auto_recall", "agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")

    # Checkpointer: conversation persists to AgentArts Memory
    # thread_id == session_id (created on-demand by session_manager.py)
    checkpointer = AgentArtsMemorySessionSaver(
        space_id=SPACE_ID,
        api_key=API_KEY,
        verify_ssl=VERIFY_SSL,
        max_messages=20,
    )

    # Store: cross-session long-term memory for auto-injection
    store = AgentArtsMemoryStore(
        space_id=SPACE_ID,
        api_key=API_KEY,
        verify_ssl=VERIFY_SSL,
    )

    return workflow.compile(checkpointer=checkpointer, store=store), checkpointer, store


def main():
    """Entry point - dispatches to TUI or CLI mode.

    --debug implies CLI mode: SDK INFO logs scroll naturally in the
    terminal instead of being wiped by TUI redraws.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Navigation Agent Demo (LangGraph + AgentArts Memory)")
    parser.add_argument(
        "--debug", action="store_true",
        help="CLI mode with SDK INFO logs visible (logs scroll in terminal)")
    parser.add_argument(
        "--cli", action="store_true",
        help="Use classic CLI interface without SDK logs (default: TUI)")
    args = parser.parse_args()

    import cli_flags
    cli_flags.DEBUG = args.debug

    if not cli_flags.DEBUG:
        os.environ["AGENTARTS_LOG_LEVEL"] = "WARNING"

    _check_env()

    # --debug implies CLI: SDK logs scroll naturally instead of being
    # wiped by TUI redraws
    if args.debug or args.cli:
        main_cli()
    else:
        main_tui()


def _print_debug_trace(event: dict):
    """Print a debug trace of a LangGraph stream event.

    Called per event from agent.stream(stream_mode="updates") in --debug
    mode. Each event is {node_name: node_output}. Returns the final AI
    reply text if this event contains the terminal agent response.
    """
    from langchain_core.messages import AIMessage, ToolMessage

    final_reply = None
    for node_name, update in event.items():
        if node_name == "auto_recall":
            ctx = update.get("memory_context", "")
            if ctx:
                print("  [trace auto_recall] memories injected:")
                for line in ctx.split("\n"):
                    print(f"    {line}")
            else:
                print("  [trace auto_recall] no memories injected")
        elif node_name == "agent":
            for msg in update.get("messages", []):
                if isinstance(msg, AIMessage):
                    tool_calls = getattr(msg, "tool_calls", None)
                    if tool_calls:
                        for tc in tool_calls:
                            name = tc.get("name", "?")
                            args = tc.get("args", {})
                            print(f"  [trace agent] -> tool call: {name}({args})")
                    elif msg.content:
                        final_reply = msg.content
        elif node_name == "tools":
            for msg in update.get("messages", []):
                if isinstance(msg, ToolMessage):
                    name = getattr(msg, "name", "?")
                    content = getattr(msg, "content", "")
                    preview = content[:500] + ("..." if len(content) > 500 else "")
                    print(f"  [trace tools] {name} -> {preview}")
    return final_reply


def main_cli():
    """Classic CLI mode - original implementation."""
    print("=" * 60)
    print("Navigation Agent Demo (LangGraph + AgentArts Memory)")
    print("=" * 60)
    print(f"  Space ID:   {SPACE_ID}")
    print(f"  Model:      {OPENAI_MODEL_NAME}")
    print(f"  AMap Key:   {'set' if config.AMAP_KEY else 'NOT set (using mock data)'}")
    print("=" * 60)

    # --- Session selection ---
    import session_manager
    session_id, session_title = session_manager.select_session_interactive()

    # Validate session exists in current space
    is_resume = session_manager.validate_session(session_id)
    if not is_resume:
        print(f"\n[WARN] Session {session_id[:8]}... not found in current space.")
        print("       This session may belong to a different space.")
        print("       Creating a new session...")
        new_session = session_manager.create_new_session(session_title)
        session_id = new_session["session_id"]
        session_title = new_session["title"]
        print(f"[OK] New session created: {session_id[:8]}...")

    # Set the active session for recall_memory tool
    import memory_tools
    memory_tools.set_current_session(session_id)

    print(f"\n  Active Session ID: {session_id}")
    print(f"  Session Title:     {session_title}")
    print("=" * 60)
    print("Type 'quit' / 'exit' to stop.")
    print()

    # Show recent message history for resumed sessions (matches TUI behavior)
    if is_resume:
        from message_utils import fetch_session_history

        try:
            history = fetch_session_history(session_id)
            if history:
                print("  --- Recent Messages ---")
                for role, content in history:
                    print(f"  {role}: {content}")
                print("  --- End History ---")
            else:
                print("  (No message history found.)")
        except Exception as e:
            print(f"  (Could not load message history: {e})")
        print()

    agent, checkpointer, store = build_agent()

    from langchain_core.messages import HumanMessage
    import cli_flags

    thread_config = {
        "configurable": {
            "thread_id": session_id,
            "actor_id": ACTOR_ID,
            "assistant_id": ASSISTANT_ID,
        }
    }

    message_count = 0
    # For resumed sessions, load existing count from sessions.json so we
    # accumulate onto the historical total instead of overwriting it with
    # this run's count (matches TUI behavior in tui_app.py).
    if is_resume:
        for s in session_manager.list_sessions():
            if s["session_id"] == session_id:
                message_count = s.get("message_count", 0)
                break
    title_auto_set = bool(session_title and not session_title.startswith("Session "))

    try:
        while True:
            try:
                user_input = input("you: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break

            # Auto-generate title from first message if not set
            if not title_auto_set:
                auto_title = user_input[:30] + ("..." if len(user_input) > 30 else "")
                session_manager.update_session_title(session_id, auto_title)
                session_title = auto_title
                title_auto_set = True

            if cli_flags.DEBUG:
                # Stream mode: trace each node's output in real time
                reply_text = None
                for event in agent.stream(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=thread_config,
                    stream_mode="updates",
                ):
                    reply = _print_debug_trace(event)
                    if reply:
                        reply_text = reply
                reply_text = reply_text or "(no response)"
            else:
                result = agent.invoke(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=thread_config,
                )
                reply = result["messages"][-1]
                reply_text = reply.content if hasattr(reply, "content") else str(reply)

            message_count += 1
            print(f"agent: {reply_text}\n")
    finally:
        # Update session metadata on exit
        session_manager.update_session(session_id, message_count)
        checkpointer.close()
        store.close()
        print(f"Session '{session_title}' ended. Conversation saved to AgentArts Memory.")


def main_tui():
    """TUI mode - Textual-based interactive interface."""
    import cli_flags
    from tui_encoding import ensure_utf8_streams
    from tui_app import NavAgentApp, TUIStdoutBridge

    ensure_utf8_streams()

    app = NavAgentApp(debug=cli_flags.DEBUG)

    # Redirect stdout to chat log
    bridge = TUIStdoutBridge(app)
    old_stdout = sys.stdout
    sys.stdout = bridge

    try:
        app.run()
    finally:
        sys.stdout = old_stdout  # Restore


if __name__ == "__main__":
    main()
