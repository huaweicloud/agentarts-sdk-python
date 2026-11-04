"""
Finance Agent Demo - Code Interpreter Setup (run once)

Creates a Code Interpreter resource on the AgentArts platform.
Prints the interpreter name and API key that must be exported
as environment variables.

Usage:
    uv run python examples/finance_adk/setup_code_interpreter.py
"""

import json
import os
import time

import config  # noqa: F401
from agentarts.sdk import CodeInterpreter


def main():
    print("=" * 60)
    print("Finance Agent - Code Interpreter Setup")
    print("=" * 60)

    print("\n[1/2] Creating Code Interpreter resource...")
    client = CodeInterpreter(region=config.CODE_INTERPRETER_REGION, verify_ssl=config.VERIFY_SSL)
    try:
        result = client.create_code_interpreter(
            name="finance-demo-interpreter",
            auth_type="API_KEY",
            api_key_name="finance-demo-key",
            description="Code Interpreter for Finance Agent demo",
        )
    finally:
        client.close()

    interpreter_name = result.get("name", "finance-demo-interpreter")
    print(f"  Name:        {interpreter_name}")
    print(f"  ID:          {result.get('id', 'N/A')}")

    # Wait for resource to be ready
    print("\n  Waiting 10s for resource to be ready...")
    time.sleep(10)

    # --- Phase 2: Write to .env ---
    print("\n[2/2] Setup complete.")

    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

    # Read existing .env, merge new values (same pattern as setup_memory.py)
    existing_lines = []
    if os.path.exists(env_file):
        with open(env_file, encoding="utf-8") as f:
            existing_lines = f.readlines()

    new_vars = {
        "CODE_INTERPRETER_NAME": interpreter_name,
        "HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY": os.getenv(
            "HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY", ""
        ),
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

    for key, val in new_vars.items():
        if key not in updated_keys:
            output_lines.append(f'{key}="{val}"\n')

    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print(f"  Written to: {env_file}")
    print(f"  Interpreter Name: {interpreter_name}")
    print(f"\nThen start the agent:")
    print(f"  uv run python examples/finance_adk/finance_agent.py")


if __name__ == "__main__":
    main()
    