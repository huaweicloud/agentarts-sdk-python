"""Typer callbacks for ``agentarts memory install|uninstall|server``.

These callbacks are registered onto the shared ``memory_app`` in
``agentarts.toolkit.cli.memory.commands``.  The business logic is ported from
the original argparse-based ``agentarts-memory`` installer.
"""

from __future__ import annotations

import os
import sys
from typing import Annotated

import typer

from rich.console import Console

from agentarts.toolkit.utils.common import echo_error, echo_key_value, echo_success, echo_warning

from .platforms import detect_all, get_platform
from .platforms.hermes import hermes_home
from .utils import (
    EscapeInterrupt,
    add,
    confirm,
    ensure_credentials,
    expand,
    find,
    list_all,
    remove,
    select_one,
    set_yes,
)

console = Console()

VALID_TARGETS = ("hermes", "claude", "codex", "opencode", "openclaw")


def _select_scope(platform_name: str, yes: bool) -> str:
    """Determine install scope (project or global)."""
    platform = get_platform(platform_name)
    if platform and platform.fixed_user_level:
        return "global"
    if yes:
        return "project"
    idx = select_one(
        "Install scope",
        ["Project \u2014 this project only", "Global \u2014 all projects"],
        0,
    )
    return "project" if idx == 0 else "global"


def _degraded_scan(target: str) -> None:
    """Attempt to find and clean up files when manifest is missing."""
    candidates = {
        "hermes": [expand(os.path.join(hermes_home(), "plugins", "agentarts"))],
        "claude": [
            expand("~/.claude/agentarts-memory"),
            os.path.join(os.getcwd(), ".claude", "agentarts-memory"),
        ],
        "codex": [
            expand("~/.codex/agentarts-memory"),
            os.path.join(os.getcwd(), ".codex", "agentarts-memory"),
        ],
        "opencode": [expand("~/.config/opencode/plugins/agentarts-memory-capture.ts")],
    }

    found = candidates.get(target, [])
    any_found = False
    for path in found:
        if os.path.exists(path):
            any_found = True
            console.print(f"  Found leftover: {os.path.normpath(path)}")
            if sys.platform == "win32":
                console.print(
                    f"  Remove manually: [yellow]Remove-Item -Recurse -Force '{os.path.normpath(path)}'[/yellow]"
                )
            else:
                console.print(
                    f"  Remove manually: [yellow]rm -rf {os.path.normpath(path)}[/yellow]"
                )

    if not any_found:
        console.print(f"  No leftover {target} files found.")


def _do_install(target: str | None, global_scope: bool, yes: bool) -> int:
    """Handle the install flow. Returns process exit code."""
    if target is not None and target not in VALID_TARGETS:
        echo_error(f"Invalid target '{target}'. Choose from: {', '.join(VALID_TARGETS)}")
        return 2

    if target == "openclaw":
        echo_warning("openclaw not yet implemented")
        return 0

    if target is None:
        detected = detect_all(global_scope)
        if not detected:
            console.print("\nNo supported platforms detected.")
            console.print(
                "Install Claude Code, Codex, OpenCode, or Hermes Agent, "
                "then run [cyan]agentarts memory install[/cyan] again."
            )
            return 1
        console.print("Detecting platforms...")
        for _, p in detected:
            console.print(f"  [green]\u221a[/green] {p.display}")
        options = [p.display for _, p in detected]
        idx = select_one("\nSelect platform", options, 0)
        target = detected[idx][0]

    platform = get_platform(target)
    if platform is None:
        echo_error(f"Unknown platform '{target}'")
        return 2

    console.print("\nChecking credentials...")
    creds = ensure_credentials(yes)

    scope = "global" if global_scope else _select_scope(target, yes)

    console.print(f"\nInstalling {platform.display} ({scope})...")
    result = platform.install(scope, creds, yes)

    add(
        {
            "platform": target,
            "scope": scope,
            "config_dir": result.config_dir,
            "scripts_dir": result.scripts_dir,
            "files": result.files,
            "config_files": result.config_files,
        }
    )

    echo_success(f"Install complete: {platform.display} ({scope})")
    echo_key_value("Config dir", result.config_dir)
    if result.scripts_dir:
        echo_key_value("Scripts", result.scripts_dir)
    echo_key_value("Files", f"{len(result.files)} deployed")
    if result.config_files:
        echo_key_value("Config", ", ".join(result.config_files))
    console.print("\nRestart the platform to activate.")
    return 0


def _do_uninstall(target: str | None, global_scope: bool, yes: bool) -> int:
    """Handle the uninstall flow. Returns process exit code."""
    if target is not None and target not in VALID_TARGETS:
        echo_error(f"Invalid target '{target}'. Choose from: {', '.join(VALID_TARGETS)}")
        return 2

    if target == "openclaw":
        echo_warning("openclaw not yet implemented")
        return 0

    scope = "global" if global_scope else None

    entry = None
    if target is not None:
        entry = find(target, scope, None)
        if entry is None:
            console.print(f"\nNo {target} installation found in manifest.")
            console.print("Attempting degraded scan...")
            _degraded_scan(target)
            return 1
    else:
        all_installs = list_all()
        if not all_installs:
            console.print("\nNo installations found.")
            return 1
        console.print("\nInstalled platforms:")
        options = [
            f"{i['platform']} ({i.get('scope', '?')}) \u2014 {os.path.normpath(i.get('config_dir', '?'))}"
            for i in all_installs
        ]
        idx = select_one("Select installation to remove", options, 0)
        entry = all_installs[idx]
        target = entry["platform"]

    platform = get_platform(target)
    if platform is None:
        echo_error(f"Unknown platform '{target}'")
        return 2

    if not yes and not confirm(
        f"Remove {platform.display} from {os.path.normpath(entry.get('config_dir', '?'))}?",
        default=True,
    ):
        console.print("[yellow]Cancelled.[/yellow]")
        return 0

    console.print(f"\nUninstalling {platform.display}...")
    platform.uninstall(entry)

    remove(
        target,
        entry.get("scope", ""),
        entry.get("config_dir", ""),
    )

    echo_success(f"Uninstall complete: {platform.display}")
    console.print("Restart the platform to apply changes.")
    return 0


def install_cmd(
    target: Annotated[
        str | None,
        typer.Argument(help=f"Platform ({', '.join(VALID_TARGETS)}). Omit to detect."),
    ] = None,
    global_scope: Annotated[
        bool, typer.Option("--global", help="Install to user-level config.")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Auto-confirm all prompts.")] = False,
) -> None:
    """Install the AgentArts Memory plugin for a supported AI agent."""
    set_yes(yes)
    try:
        code = _do_install(target, global_scope, yes)
    except EscapeInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        code = 0
    if code:
        raise typer.Exit(code)


def uninstall_cmd(
    target: Annotated[
        str | None,
        typer.Argument(help=f"Platform ({', '.join(VALID_TARGETS)}). Omit to select."),
    ] = None,
    global_scope: Annotated[
        bool, typer.Option("--global", help="Limit to user-level installs.")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Auto-confirm all prompts.")] = False,
) -> None:
    """Uninstall an AgentArts Memory plugin."""
    set_yes(yes)
    try:
        code = _do_uninstall(target, global_scope, yes)
    except EscapeInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        code = 0
    if code:
        raise typer.Exit(code)
