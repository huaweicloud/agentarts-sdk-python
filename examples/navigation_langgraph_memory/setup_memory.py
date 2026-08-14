"""
Navigation Agent Demo - Memory Space Setup (run once)

Creates a new AgentArts Memory space with all four builtin extraction
strategies. Prints the Space ID and API Key that must be exported as
environment variables before running nav_agent.py.

Sessions are NOT created here — session_manager.py creates a new
AgentArts Memory session for each conversation at agent startup.

Usage:
    uv run python examples/navigation_langgraph_memory/setup_memory.py
"""

import json
import os
import time

import config  # noqa: F401  (sets env vars as side effect)
from agentarts.sdk import MemoryClient

from config import BUILTIN_STRATEGIES, SPACE_DESCRIPTION, SPACE_NAME


def _check_and_clear_sessions_json():
    """Check if sessions.json exists and prompt user to clear it.

    Sessions are bound to a specific space. When creating a new space,
    old session IDs from sessions.json won't work with the new space.
    """
    sessions_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions.json")

    if not os.path.exists(sessions_file):
        return

    try:
        with open(sessions_file, encoding="utf-8") as f:
            data = json.load(f)
            sessions = data.get("sessions", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return

    if not sessions:
        return

    print(f"\n[!] Found {len(sessions)} existing session(s) in sessions.json.")
    print("    Sessions are bound to a specific space. Old sessions won't work")
    print("    with the new space you just created.")
    print()

    while True:
        choice = input("Clear sessions.json? [y/N]: ").strip().lower()
        if choice in ("y", "yes"):
            with open(sessions_file, "w", encoding="utf-8") as f:
                json.dump({"sessions": []}, f, ensure_ascii=False, indent=2)
            print("[OK] sessions.json cleared.")
            return
        elif choice in ("n", "no", ""):
            print("[WARN] sessions.json not cleared. Old sessions will not work")
            print("       with the new space. You may need to manually delete")
            print("       sessions.json or create new sessions in nav_agent.py.")
            return
        else:
            print("Please enter 'y' or 'n'.")


def main():
    """Create memory space and write credentials to .env file."""
    print("=" * 60)
    print("Navigation Agent - Memory Space Setup")
    print("=" * 60)

    # --- Phase 1: Control plane - create space (no api_key needed) ---
    print("\n[1/2] Creating memory space...")
    client = MemoryClient(verify_ssl=config.VERIFY_SSL)
    try:
        space = client.create_space(
            name=SPACE_NAME,
            memory_strategies_builtin=BUILTIN_STRATEGIES,
            memory_extract_idle_seconds=30,
            description=SPACE_DESCRIPTION,
        )
    finally:
        client.close()

    print(f"  Space ID:   {space.id}")
    print(f"  API Key:    {space.api_key}")
    print(f"  Strategies: {space.memory_strategies_builtin}")

    # Wait for API key to propagate to the data plane
    print("\n  Waiting 5s for API key propagation...")
    time.sleep(5)

    # --- Phase 2: Write .env file ---
    print("\n[2/2] Setup complete.")

    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

    # Read existing .env if present, merge new values
    existing_lines = []
    if os.path.exists(env_file):
        with open(env_file, encoding="utf-8") as f:
            existing_lines = f.readlines()

    new_vars = {
        "AGENTARTS_MEMORY_SPACE_ID": space.id,
        "HUAWEICLOUD_SDK_MEMORY_API_KEY": space.api_key,
    }

    updated_keys = set()
    output_lines = []
    for line in existing_lines:
        stripped = line.strip()
        matched = False
        for key, val in new_vars.items():
            if stripped.startswith(f"{key}="):
                output_lines.append(f'{key}="{val}"\n')
                updated_keys.add(key)
                matched = True
                break
        if not matched:
            output_lines.append(line)

    # Append any keys not yet in the file
    for key, val in new_vars.items():
        if key not in updated_keys:
            output_lines.append(f'{key}="{val}"\n')

    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print(f"  Written to: {env_file}")
    print(f"  Space ID:   {space.id}")
    print(f"  API Key:    {space.api_key}")

    # Check if sessions.json needs to be cleared
    _check_and_clear_sessions_json()

    print("\nThen start the agent:")
    print("  uv run python examples/navigation_langgraph_memory/nav_agent.py")


if __name__ == "__main__":
    main()
