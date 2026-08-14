"""CLI subcommands for the agentarts_memory provider.

This module registers ``hermes agentarts_memory <subcommand>`` commands via
the ``register_cli(subparser)`` convention. The commands are only available
when this provider is the active ``memory.provider`` in Hermes configuration.
"""

import json
import os

from provider import (
    ENV_API_KEY,
    ENV_REGION,
    ENV_SPACE_ID,
    AgentArtsMemoryProvider,
)


def _status(args) -> None:
    """Show provider status: availability, env vars, and active config."""
    provider = AgentArtsMemoryProvider()
    available = provider.is_available()

    print("AgentArts Memory Provider — Status")
    print(f"  Provider name : {provider.name}")
    print(f"  Available     : {'yes' if available else 'no'}")
    print()
    print("Environment variables:")

    env_info = [
        ("HUAWEICLOUD_SDK_MEMORY_API_KEY", ENV_API_KEY, False),
        ("AGENTARTS_MEMORY_SPACE_ID", ENV_SPACE_ID, False),
        ("HUAWEICLOUD_SDK_REGION", ENV_REGION, True),
    ]

    all_set = True
    for display_name, env_var, optional in env_info:
        value = os.getenv(env_var)
        if value:
            if optional:
                print(f"  {display_name} = {value}")
            else:
                print(f"  {display_name} = {'*' * min(len(value), 8)}…({len(value)} chars)")
        else:
            label = "(optional)" if optional else "(MISSING)"
            print(f"  {display_name} = <not set> {label}")
            if not optional:
                all_set = False

    if not all_set:
        print()
        print("Warning: Some required environment variables are not set.")
        print("Run 'hermes memory setup' to configure the provider.")


def _config(args) -> None:
    """Show the non-secret configuration saved to agentarts.json."""
    hermes_home = os.environ.get("HERMES_HOME", "")
    if not hermes_home:
        print("HERMES_HOME is not set. Cannot locate configuration file.")
        print("Run this command from within a Hermes session context.")
        return

    config_path = os.path.join(hermes_home, "agentarts.json")
    if not os.path.exists(config_path):
        print(f"No configuration file found at: {config_path}")
        print("Run 'hermes memory setup' to configure the provider.")
        return

    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)

    print("AgentArts Memory Provider — Configuration")
    print(f"  Config file: {config_path}")
    print()
    if data:
        for key, value in data.items():
            print(f"  {key} = {value}")
    else:
        print("  (empty — no non-secret values saved)")


def _test_connection(args) -> None:
    """Test connectivity by initializing the provider and checking the client."""
    provider = AgentArtsMemoryProvider()

    if not provider.is_available():
        print("AgentArts Memory Provider — Connection Test: FAILED")
        print("Required environment variables are not set.")
        print("Run 'hermes memory setup' to configure the provider.")
        return

    print("AgentArts Memory Provider — Connection Test")
    print("  Environment variables: OK")
    print("  Initializing MemoryClient...")

    try:
        provider.initialize("cli-test-session", hermes_home=os.environ.get("HERMES_HOME", ""))
        print("  MemoryClient initialized: OK")
        print("  Memory session created: OK")
        print()
        print("Connection test: PASSED")
        provider.shutdown()
    except Exception as e:
        print(f"  Error: {e}")
        print()
        print("Connection test: FAILED")


def _handle_command(args) -> None:
    """Dispatch to the appropriate subcommand handler."""
    sub = getattr(args, "agentarts_memory_command", None)
    if sub == "status":
        _status(args)
    elif sub == "config":
        _config(args)
    elif sub == "test":
        _test_connection(args)
    else:
        print("Usage: hermes agentarts_memory <status|config|test>")


def register_cli(subparser) -> None:
    """Build the argparse tree for 'hermes agentarts_memory' commands.

    Called by discover_plugin_cli_commands() during argparse initialization.
    """
    subs = subparser.add_subparsers(dest="agentarts_memory_command")
    subs.add_parser("status", help="Show provider status and environment variables")
    subs.add_parser("config", help="Show saved non-secret configuration")
    subs.add_parser("test", help="Test provider connectivity")
    subparser.set_defaults(func=_handle_command)
