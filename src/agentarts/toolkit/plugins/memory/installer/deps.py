"""Runtime dependency checks for the memory plugin installer.

Claude Code, Codex, and OpenCode launch the local MCP server
(``python -m agentarts.toolkit.plugins.memory.mcp.server``), which imports the
optional ``mcp`` package. Hermes deploys a provider that talks to the cloud SDK
directly, so it does not need it.

``mcp`` is an optional extra of the SDK (``agentarts-sdk[mcp]``). When a
platform that needs the server is installed, make sure the package is present
in the same interpreter that will launch the server.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version

from rich.console import Console

console = Console()

MCP_REQUIRED_SPEC = "mcp>=2.0.0"
MCP_MIN_MAJOR_VERSION = 2

# Platforms whose generated config launches the local MCP server.
MCP_PLATFORMS = frozenset({"claude", "codex", "opencode"})


def needs_mcp(target: str) -> bool:
    """Return True when installing *target* requires the MCP server package."""
    return target in MCP_PLATFORMS


def is_mcp_available() -> bool:
    """Return True when a supported ``mcp`` version is importable."""
    if importlib.util.find_spec("mcp") is None:
        return False

    try:
        installed = version("mcp")
    except PackageNotFoundError:
        # Distribution metadata can be missing for vendored/editable installs.
        return True

    try:
        major = int(installed.split(".", 1)[0])
    except ValueError:
        return True
    return major >= MCP_MIN_MAJOR_VERSION


def install_command() -> list[str] | None:
    """Build the command that installs ``mcp`` into the running interpreter.

    Prefers pip (always targets ``sys.executable``). uv-managed environments
    often ship without pip, so fall back to ``uv pip`` when available.
    """
    if importlib.util.find_spec("pip") is not None:
        return [sys.executable, "-m", "pip", "install", MCP_REQUIRED_SPEC]

    uv = shutil.which("uv")
    if uv:
        return [uv, "pip", "install", "--python", sys.executable, MCP_REQUIRED_SPEC]

    return None


def ensure_mcp_installed() -> bool:
    """Install ``mcp`` if it is missing or older than the supported major.

    Returns:
        True when a supported ``mcp`` is available afterwards.
    """
    if is_mcp_available():
        return True

    command = install_command()
    if command is None:
        console.print(
            f"  [red]×[/red] Cannot install '{MCP_REQUIRED_SPEC}': pip and uv were not found."
        )
        console.print(
            f'  Install it manually: [cyan]{sys.executable} -m pip install '
            f'"{MCP_REQUIRED_SPEC}"[/cyan]'
        )
        return False

    console.print(f"  Installing required dependency [cyan]{MCP_REQUIRED_SPEC}[/cyan] ...")
    try:
        result = subprocess.run(command, check=False)
    except OSError as exc:
        console.print(f"  [red]×[/red] Failed to run installer: {exc}")
        return False

    if result.returncode != 0 or not is_mcp_available():
        console.print(f"  [red]×[/red] Failed to install '{MCP_REQUIRED_SPEC}'.")
        console.print(
            f'  Install it manually: [cyan]{sys.executable} -m pip install '
            f'"{MCP_REQUIRED_SPEC}"[/cyan]'
        )
        return False

    console.print("  [green]√[/green] Installed mcp")
    return True
