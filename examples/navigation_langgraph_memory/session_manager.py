"""
Navigation Agent Demo - Session Manager

Manages multiple conversation sessions locally. Each session maps to
an AgentArts Memory session (via session_id). Session metadata is
persisted to sessions.json so sessions survive restarts.

Usage:
    from session_manager import select_session_interactive
    session_id = select_session_interactive()
"""

import json
import os
from datetime import datetime

import cli_flags  # noqa: F401
import config  # noqa: F401  (sets env vars as side effect)
from agentarts.sdk import MemoryClient

SESSIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions.json")


def load_sessions() -> list[dict]:
    """Load session metadata from local JSON file."""
    try:
        with open(SESSIONS_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("sessions", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_sessions(sessions: list[dict]):
    """Save session metadata to local JSON file."""
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump({"sessions": sessions}, f, ensure_ascii=False, indent=2)


def list_sessions() -> list[dict]:
    """Return all sessions sorted by last_active (newest first)."""
    sessions = load_sessions()
    sessions.sort(key=lambda s: s.get("last_active", ""), reverse=True)
    return sessions


def create_new_session(title: str = "") -> dict:
    """Create a new AgentArts Memory session and add to local store.

    Args:
        title: Optional session title. If empty, auto-generated from
            the session ID prefix (updated later from first message).

    Returns:
        Session metadata dict with session_id, title, timestamps.
    """
    client = MemoryClient(api_key=config.API_KEY, verify_ssl=config.VERIFY_SSL)
    try:
        session = client.create_memory_session(
            space_id=config.SPACE_ID,
            actor_id=config.ACTOR_ID,
            assistant_id=config.ASSISTANT_ID,
        )
    finally:
        client.close()

    now = datetime.now().isoformat(timespec="seconds")
    entry = {
        "session_id": session.id,
        "title": title or f"Session {session.id[:8]}",
        "created_at": now,
        "last_active": now,
        "message_count": 0,
    }

    sessions = load_sessions()
    sessions.append(entry)
    save_sessions(sessions)

    return entry


def update_session(session_id: str, message_count: int = 0):
    """Update last_active timestamp and message_count for a session."""
    sessions = load_sessions()
    now = datetime.now().isoformat(timespec="seconds")
    for s in sessions:
        if s["session_id"] == session_id:
            s["last_active"] = now
            if message_count:
                s["message_count"] = message_count
            break
    save_sessions(sessions)


def update_session_title(session_id: str, title: str):
    """Update the title for a session (e.g. from first user message)."""
    sessions = load_sessions()
    for s in sessions:
        if s["session_id"] == session_id:
            s["title"] = title[:50]
            break
    save_sessions(sessions)


def validate_session(session_id: str) -> bool:
    """Check if a session exists in the current space.

    Calls list_messages with limit=1 to verify the session is accessible.
    Returns True if the API call succeeds (session exists, may be empty),
    False if the API call fails (session doesn't exist in this space).
    """
    client = MemoryClient(api_key=config.API_KEY, verify_ssl=config.VERIFY_SSL)
    try:
        client.list_messages(
            space_id=config.SPACE_ID,
            session_id=session_id,
            limit=1,
            offset=0,
        )
        return True
    except Exception as e:
        if cli_flags.DEBUG:
            print(f"[DEBUG] Session validation failed: {e}")
        return False
    finally:
        client.close()


def select_session_interactive() -> tuple[str, str]:
    """Interactive CLI: show menu, let user pick or create a session.

    Returns:
        Tuple of (session_id, session_title).
    """
    sessions = list_sessions()

    print("\n" + "=" * 60)
    print("Session Manager")
    print("=" * 60)
    print("[1] Start new session")

    start_index = 2
    if sessions:
        print("[2] Resume existing session:\n")
        for i, s in enumerate(sessions):
            title = s.get("title", "untitled")
            ts = s.get("last_active", "?")
            count = s.get("message_count", 0)
            print(f"    [{i + 3}] {title}")
            print(f"        last: {ts}, messages: {count}")
        start_index = 3
    else:
        print("    (no existing sessions)")

    choice = input("\nChoice: ").strip()

    if choice == "1":
        title = input("Session title (optional, Enter to auto-generate): ").strip()
        session = create_new_session(title)
        print(f"\n[OK] New session created: {session['session_id']}")
        return session["session_id"], session["title"]

    if choice == "2" and not sessions:
        print("[ERR] No existing sessions. Creating new one.")
        session = create_new_session("")
        return session["session_id"], session["title"]

    # Numeric choice for existing session
    if choice.isdigit():
        idx = int(choice) - 3  # offset: [3] is first session
        if 0 <= idx < len(sessions):
            s = sessions[idx]
            print(f"\n[OK] Resuming session: {s['title']}")
            return s["session_id"], s["title"]

    print("[ERR] Invalid choice, creating new session.")
    session = create_new_session("")
    return session["session_id"], session["title"]
