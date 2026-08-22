"""AgentArts Memory installer — utilities.

Consolidates: path expansion, JSON5-tolerant read, atomic write, hook
merge/strip, TOML text-level merge, .env dedup, status output, interactive
prompts, source-asset location, manifest (installed.json) CRUD, and
credential detection/validation/interactive fill.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from rich.console import Console

console = Console()

_YES: bool = False


try:
    import termios
    import tty

    _HAS_TTY = True
except ImportError:
    _HAS_TTY = False


class EscapeInterrupt(BaseException):
    """Raised when the user presses ESC during an interactive prompt."""


def set_yes(value: bool) -> None:
    """Set the global non-interactive flag."""
    global _YES
    _YES = value


# ── Path helpers ─────────────────────────────────────────────────────


def expand(path: str) -> str:
    """Expand ``~`` and environment variables in *path*."""
    return os.path.expandvars(os.path.expanduser(path))


# ── JSON5 tolerance ──────────────────────────────────────────────────


def strip_json5(text: str) -> str:
    """Remove ``//`` and ``/* */`` comments and trailing commas from *text*.

    Respects string literals so ``http://`` inside strings is preserved.
    """
    result: list[str] = []
    i = 0
    length = len(text)
    in_string = False
    string_char = ""

    while i < length:
        ch = text[i]

        # Handle string boundaries (skip escaped quotes).
        if in_string:
            result.append(ch)
            if ch == "\\" and i + 1 < length:
                result.append(text[i + 1])
                i += 2
                continue
            if ch == string_char:
                in_string = False
            i += 1
            continue

        # Enter string.
        if ch in ('"', "'"):
            in_string = True
            string_char = ch
            result.append(ch)
            i += 1
            continue

        # Line comment: // to end of line.
        if ch == "/" and i + 1 < length and text[i + 1] == "/":
            while i < length and text[i] != "\n":
                i += 1
            continue

        # Block comment: /* to */
        if ch == "/" and i + 1 < length and text[i + 1] == "*":
            i += 2
            while i < length and not (text[i] == "*" and i + 1 < length and text[i + 1] == "/"):
                i += 1
            i += 2  # skip closing */
            continue

        result.append(ch)
        i += 1

    cleaned = "".join(result)
    # Remove trailing commas before } or ].
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def read_json(path: str) -> dict:
    """Read a JSON file with comment/trailing-comma tolerance.

    Returns ``{}`` if the file does not exist.
    """
    p = Path(path)
    if not p.exists():
        return {}
    raw = p.read_text(encoding="utf-8")
    return cast(dict, json.loads(strip_json5(raw)))


def write_json_atomic(path: str, data: dict, indent: int = 2) -> None:
    """Atomically write *data* as JSON to *path* (write tmp + os.replace)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=indent, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, p)


# ── Hook merge / strip ──────────────────────────────────────────────


def _command_contains_scripts_dir(hook_entry: dict, scripts_dir: str) -> bool:
    """Check whether a single hook entry's command references *scripts_dir*."""
    cmd = hook_entry.get("command", "")
    return scripts_dir in cmd


def strip_hooks(hooks_obj: dict, scripts_dir: str) -> dict:
    """Remove all hook entries whose command contains *scripts_dir*.

    *hooks_obj* is the value of the ``"hooks"`` key, i.e. a dict mapping
    event names to lists of hook groups.  Empty groups / events are removed.
    """
    result: dict[str, list] = {}
    for event, groups in hooks_obj.items():
        new_groups: list[dict] = []
        for group in groups:
            inner_hooks = group.get("hooks", [])
            filtered = [h for h in inner_hooks if not _command_contains_scripts_dir(h, scripts_dir)]
            if filtered:
                new_group = dict(group)
                new_group["hooks"] = filtered
                new_groups.append(new_group)
        if new_groups:
            result[event] = new_groups
    return result


def merge_hooks(existing: dict, incoming: dict, scripts_dir: str) -> dict:
    """Merge *incoming* hooks into *existing* (idempotent: strip then add).

    Both dicts may have a top-level ``"hooks"`` key.  The returned dict
    preserves all non-hooks keys from *existing*.
    """
    result = dict(existing)
    ex_hooks = result.get("hooks", {})
    in_hooks = incoming.get("hooks", {})

    # Strip old entries first (idempotent).
    ex_hooks = strip_hooks(ex_hooks, scripts_dir)

    # Append incoming groups to each event.
    for event, groups in in_hooks.items():
        if event not in ex_hooks:
            ex_hooks[event] = []
        ex_hooks[event].extend(groups)

    if ex_hooks:
        result["hooks"] = ex_hooks
    else:
        result.pop("hooks", None)

    return result


def remove_hooks_key(settings: dict, scripts_dir: str) -> dict:
    """Strip our hooks from *settings* and remove the hooks key if empty."""
    hooks = settings.get("hooks", {})
    cleaned = strip_hooks(hooks, scripts_dir)
    result = dict(settings)
    if cleaned:
        result["hooks"] = cleaned
    else:
        result.pop("hooks", None)
    return result


# ── TOML text-level merge ────────────────────────────────────────────


def merge_toml_features(
    text: str, key: str, value: str, *, deprecated_keys: list[str] | None = None
) -> str:
    """Ensure ``[features]`` section contains ``key = value``.

    Works at the text level (no toml library dependency).  Preserves
    existing keys and sections.  If *deprecated_keys* is provided, those
    keys are removed from the section first.
    """
    lines = text.splitlines()

    # Try to find existing [features] section.
    features_start = None
    features_end = len(lines)
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[features]":
            features_start = idx
            continue
        if features_start is not None and stripped.startswith("[") and stripped.endswith("]"):
            features_end = idx
            break

    if features_start is not None:
        # Check if key already exists in the section.
        section_lines = lines[features_start + 1 : features_end]
        key_line = f"{key} = {value}"

        # Remove deprecated keys.
        if deprecated_keys:
            section_lines = [
                line
                for line in section_lines
                if not any(line.strip().startswith(f"{dk} ") for dk in deprecated_keys)
            ]

        found = False
        for i, line in enumerate(section_lines):
            if line.strip().startswith(f"{key} "):
                section_lines[i] = key_line
                found = True
                break
        if not found:
            section_lines.append(key_line)
        lines = lines[: features_start + 1] + section_lines + lines[features_end:]
    else:
        # No [features] section — append one.
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append("[features]")
        lines.append(f"{key} = {value}")

    return "\n".join(lines) + "\n"


def strip_toml_feature(text: str, key: str) -> str:
    """Remove ``key = ...`` line from ``[features]`` section.

    If the section becomes empty, the section header is removed too.
    """
    lines = text.splitlines()
    features_start = None
    features_end = len(lines)
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[features]":
            features_start = idx
            continue
        if features_start is not None and stripped.startswith("[") and stripped.endswith("]"):
            features_end = idx
            break

    if features_start is None:
        return text

    section_lines = lines[features_start + 1 : features_end]
    section_lines = [l for l in section_lines if not l.strip().startswith(f"{key} ")]

    result = lines[: features_start + 1] + section_lines + lines[features_end:]
    # If section body is now empty (only whitespace), remove the header too.
    body = [l for l in section_lines if l.strip()]
    if not body:
        result = lines[:features_start] + lines[features_end:]

    # Ensure trailing newline.
    text_result = "\n".join(result)
    if text and text.endswith("\n") and not text_result.endswith("\n"):
        text_result += "\n"
    return text_result


def set_yaml_key(path: str, section: str, key: str, value: str) -> None:
    """Set ``section.key`` in a YAML file at the text level.

    Preserves all other content. Creates the file and section if absent.
    No external YAML library dependency.  Uses 2-space indentation.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    lines = text.splitlines()

    # Find the section header (top-level key, e.g. "memory:").
    section_start = None
    section_end = len(lines)
    for idx, line in enumerate(lines):
        stripped = line.strip()
        is_top = stripped and not line[:1].isspace()
        if section_start is None:
            if is_top and (stripped == f"{section}:" or stripped.startswith(f"{section}:")):
                section_start = idx
                continue
        else:
            if is_top and not stripped.startswith("#") and ":" in stripped:
                section_end = idx
                break

    # Format the key line.
    key_line = f"  {key}: {value}" if value else f"  {key}: ''"

    if section_start is not None:
        section_lines = lines[section_start + 1 : section_end]
        found = False
        for i, line in enumerate(section_lines):
            if line.strip().startswith(f"{key}:"):
                section_lines[i] = key_line
                found = True
                break
        if not found:
            section_lines.append(key_line)
        lines = lines[: section_start + 1] + section_lines + lines[section_end:]
    else:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append(f"{section}:")
        lines.append(key_line)

    p.parent.mkdir(parents=True, exist_ok=True)
    result = "\n".join(lines) + "\n"
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(result, encoding="utf-8")
    os.replace(tmp, p)


# ── .env file (dedup by key) ─────────────────────────────────────────
# ── MCP server config helpers ──────────────────────────────────────


def merge_mcp_servers(settings: dict, name: str, command: str, args: list[str], env: dict[str, str]) -> dict:
    """Merge an MCP server entry into settings dict (for Claude Code settings.json).

    Idempotent: strips existing entry with same name first.
    """
    result = dict(settings)
    mcp_servers = dict(result.get("mcpServers", {}))
    mcp_servers[name] = {"command": command, "args": args, "env": dict(env)}
    result["mcpServers"] = mcp_servers
    return result


def strip_mcp_servers(settings: dict, name: str) -> dict:
    """Remove an MCP server entry from settings dict.

    Returns settings without the named server. Removes mcpServers key if empty.
    """
    result = dict(settings)
    mcp_servers = dict(result.get("mcpServers", {}))
    mcp_servers.pop(name, None)
    if mcp_servers:
        result["mcpServers"] = mcp_servers
    else:
        result.pop("mcpServers", None)
    return result


def merge_toml_mcp_server(text: str, name: str, command: str, args: list[str], env: dict[str, str]) -> str:
    """Ensure config.toml contains [mcp_servers.{name}] section.

    Works at the text level (no toml library). Idempotent: removes existing
    section with same name first, then appends.
    """
    # First strip any existing section with this name.
    text = strip_toml_mcp_server(text, name)

    lines: list[str] = []
    # Format args as TOML array.
    args_str = ", ".join(f'"{a}"' for a in args)
    lines.append(f"[mcp_servers.{name}]")
    lines.append(f'command = "{command}"')
    lines.append(f"args = [{args_str}]")
    if env:
        lines.append("")
        for k, v in env.items():
            lines.append(f'{k} = "{v}"')
    lines.append("")

    result = text.rstrip()
    if result:
        result += "\n"
    result += "\n".join(lines) + "\n"
    return result


def strip_toml_mcp_server(text: str, name: str) -> str:
    """Remove [mcp_servers.{name}] section from TOML text.

    Handles both [mcp_servers.name] and [mcp_servers.name.env] sub-sections.
    """
    section_header = f"[mcp_servers.{name}"
    lines = text.splitlines()
    result: list[str] = []
    in_section = False

    for line in lines:
        stripped = line.strip()
        # Check if this line starts a new section.
        if stripped.startswith("[") and stripped.endswith("]"):
            if stripped.startswith(section_header):
                in_section = True
                continue
            else:
                in_section = False
        if in_section:
            continue
        result.append(line)

    text_result = "\n".join(result)
    # Clean up trailing blank lines.
    text_result = text_result.rstrip() + "\n" if text_result.strip() else ""
    return text_result


def merge_opencode_mcp(config: dict, name: str, command: list[str], env: dict[str, str]) -> dict:
    """Merge an MCP server entry into opencode.json config dict.

    Idempotent: strips existing entry with same name first.
    """
    result = dict(config)
    mcp = dict(result.get("mcp", {}))
    mcp[name] = {
        "type": "local",
        "command": command,
        "environment": dict(env),
    }
    result["mcp"] = mcp
    return result


def strip_opencode_mcp(config: dict, name: str) -> dict:
    """Remove an MCP server entry from opencode.json config.

    Returns config without the named server. Removes mcp key if empty.
    """
    result = dict(config)
    mcp = dict(result.get("mcp", {}))
    mcp.pop(name, None)
    if mcp:
        result["mcp"] = mcp
    else:
        result.pop("mcp", None)
    return result


# ── MCP server config constants ─────────────────────────────────────

MCP_SERVER_NAME = "agentarts_memory"
MCP_SERVER_MODULE = "agentarts.toolkit.plugins.memory.mcp.server"
MCP_SERVER_COMMAND = "python3"
MCP_SERVER_ARGS = ["-m", MCP_SERVER_MODULE]


def build_mcp_env(creds: dict, platform_name: str = "") -> dict[str, str]:
    """Build the env dict for MCP server config from credentials.

    Includes ``AGENTARTS_MEMORY_PLATFORM`` so the MCP server subprocess can
    resolve the correct default user_id (e.g. opencode-user, cc-user).
    """
    env: dict[str, str] = {}
    if platform_name:
        env["AGENTARTS_MEMORY_PLATFORM"] = platform_name
    if creds.get(ENV_API_KEY):
        env[ENV_API_KEY] = creds[ENV_API_KEY]
    if creds.get(ENV_SPACE_ID):
        env[ENV_SPACE_ID] = creds[ENV_SPACE_ID]
    if creds.get(ENV_REGION):
        env[ENV_REGION] = creds[ENV_REGION]
    return env
 
 


def write_env_file(path: str, entries: dict[str, str]) -> None:
    """Write *entries* to a .env file, deduplicating by key.

    Existing keys are updated; new keys are appended.  Other lines are
    preserved.  Atomic write.
    """
    p = Path(path)
    existing: dict[str, str] = {}
    other_lines: list[str] = []

    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v
            else:
                other_lines.append(line)

    existing.update(entries)
    p.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    # Preserve comment/blank lines first.
    lines.extend(other_lines)
    for k, v in existing.items():
        lines.append(f"{k}={v}")

    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def strip_env_keys(path: str, keys: list[str]) -> None:
    """Remove specified keys from a .env file.  Empty file is removed."""
    p = Path(path)
    if not p.exists():
        return
    keyset = set(keys)
    kept: list[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, _ = line.partition("=")
            if k.strip() in keyset:
                continue
        kept.append(line)
    if kept:
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text("\n".join(kept) + "\n", encoding="utf-8")
        os.replace(tmp, p)
    else:
        p.unlink(missing_ok=True)


# ── Empty file/dir cleanup ───────────────────────────────────────────


def remove_if_empty(path: str) -> None:
    """Remove *path* if it is an empty file or empty directory.

    For directories, recursively removes if all children are gone.
    """
    p = Path(path)
    if not p.exists():
        return
    if p.is_file():
        if p.stat().st_size == 0:
            p.unlink()
    elif p.is_dir():
        # Try to remove if empty (ignore failure = not empty).
        try:
            for child in sorted(p.rglob("*"), reverse=True):
                if child.is_file() and child.stat().st_size == 0:
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            p.rmdir()
        except OSError:
            pass


# ── Status output ────────────────────────────────────────────────────


def status_ok(label: str, path: str) -> None:
    console.print(f"  [green]\u221a[/green] {label} \u2192 {path}")


def status_err(label: str, err: str) -> None:
    console.print(f"  [red]\u00d7[/red] {label} \u2014 {err}")


def status_updated(label: str, path: str) -> None:
    console.print(f"  [yellow]\u21bb[/yellow] {label} (updated) \u2192 {path}")


# ── Interactive prompts ──────────────────────────────────────────────


def _input_with_esc(prompt: str) -> str:
    """Read a line of input with ESC detection.

    In raw terminal mode, detects ESC (``\\x1b``) and raises
    :class:`EscapeInterrupt` immediately.  Falls back to regular
    ``input()`` on non-Unix or when raw mode is unavailable.
    """
    if not _HAS_TTY:
        return input(prompt)

    fd = sys.stdin.fileno()
    try:
        old_settings = termios.tcgetattr(fd)
    except (termios.error, ValueError):
        return input(prompt)

    try:
        tty.setraw(fd)
        sys.stdout.write(prompt)
        sys.stdout.flush()
        buf: list[str] = []
        while True:
            ch = sys.stdin.read(1)
            if ch == "\x1b":  # ESC
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                raise EscapeInterrupt()
            elif ch in ("\r", "\n"):  # Enter
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                return "".join(buf)
            elif ch in ("\x7f", "\b"):  # Backspace / Delete
                if buf:
                    buf.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif ch == "\x03":  # Ctrl+C
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                raise KeyboardInterrupt()
            elif ch == "\x04":  # Ctrl+D
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                raise EOFError()
            elif "\x20" <= ch <= "\x7e":  # Printable ASCII
                buf.append(ch)
                sys.stdout.write(ch)
                sys.stdout.flush()
            # Ignore other control characters
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def confirm(prompt: str, default: bool = True) -> bool:
    """Yes/no confirmation.  Returns *default* when ``--yes`` or non-interactive."""
    if _YES or not sys.stdin.isatty():
        return default
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        raw = _input_with_esc(prompt + suffix).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    if not raw:
        return default
    return raw in ("y", "yes")


def prompt_input(prompt: str, default: str = "") -> str:
    """Text input prompt.  Returns *default* when ``--yes``."""
    if _YES:
        return default
    try:
        raw = _input_with_esc(prompt + ": ").strip()
    except (EOFError, KeyboardInterrupt):
        return default
    return raw if raw else default


def select_one(prompt: str, options: list[str], default_idx: int = 0) -> int:
    """Single-choice select.  Returns *default_idx* when ``--yes``."""
    if _YES or not sys.stdin.isatty():
        return default_idx
    console.print(prompt)
    for i, opt in enumerate(options):
        marker = "*" if i == default_idx else " "
        console.print(f"  {i + 1}) {opt} {marker}")
    try:
        raw = _input_with_esc(f"Choice (1-{len(options)}) [{default_idx + 1}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return default_idx
    if not raw:
        return default_idx
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            return idx
    except ValueError:
        pass
    return default_idx


# ── Source asset location ──────────────────────────────────────────


CODE_AGENT_SCRIPTS: list[str] = [
    "_shared.mjs",
    "prompt-submit.mjs",
    "pre-compact.mjs",
]


def installer_root() -> str:
    """Return the absolute path to the installer package directory."""
    return str(Path(__file__).resolve().parent)


def repo_root() -> str:
    """Return the absolute path to the repository root.

    Walks upward from this package looking for the directory containing
    ``pyproject.toml``.  In a source/editable checkout this resolves to the
    repo root; falls back to the installer package directory otherwise.
    """
    p = Path(__file__).resolve().parent
    while p.parent != p:
        if (p / "pyproject.toml").is_file():
            return str(p)
        p = p.parent
    return str(Path(__file__).resolve().parent)


def plugins_root() -> str:
    """Return the absolute path to the memory plugins package directory.

    This is ``agentarts/toolkit/plugins/memory`` — the directory that holds
    the ``hermes`` and ``code_agent`` plugin assets as siblings of the
    ``installer`` package.
    """
    return str(Path(__file__).resolve().parent.parent)


def hermes_source() -> str:
    """Return the hermes plugin source directory."""
    return str(Path(plugins_root()) / "ai_agent" / "hermes")


def code_agent_source() -> str:
    """Return the code_agent plugin source directory."""
    return str(Path(plugins_root()) / "resources")


# ── Hermes source files ──


def hermes_files() -> list[str]:
    """Return absolute paths of hermes files to deploy (provider, plugin.yaml, __init__)."""
    src = hermes_source()
    return [str(Path(src) / f) for f in ("provider.py", "plugin.yaml", "__init__.py")]


# ── Code_agent scripts ──


def code_agent_scripts() -> list[str]:
    """Return absolute paths of the 13 .mjs hook scripts."""
    scripts_dir = str(Path(plugins_root()) / "resources" / "scripts")
    return [str(Path(scripts_dir) / f) for f in CODE_AGENT_SCRIPTS]


def claude_hooks_template() -> str:
    """Return the path to the Claude hooks template (claude_code/hooks.json)."""
    return str(Path(plugins_root()) / "ai_agent" / "claude_code" / "hooks.json")


def codex_hooks_template() -> str:
    """Return the path to the Codex hooks template (codex/hooks.codex.json)."""
    return str(Path(plugins_root()) / "ai_agent" / "codex" / "hooks.codex.json")


# ── OpenCode source files ──


def opencode_files() -> dict[str, str]:
    """Return a mapping of target-relative-path → source-absolute-path.

    Keys are relative paths within the opencode config dir:
      ``plugins/agentarts-memory-capture.ts``
      ``commands/recall.md``
      ``commands/remember.md``
    """
    oc_dir = str(Path(plugins_root()) / "ai_agent" / "opencode")
    return {
        "plugins/agentarts-memory-capture.ts": str(Path(oc_dir) / "agentarts-memory-capture.ts"),
        "commands/recall.md": str(Path(oc_dir) / "commands" / "recall.md"),
        "commands/remember.md": str(Path(oc_dir) / "commands" / "remember.md"),
    }


# ── Manifest (installed.json) ──────────────────────────────────────


MANIFEST_DIR = "~/.agentarts"
MANIFEST_FILE = "installed.json"


def manifest_path() -> str:
    """Return the absolute path to installed.json."""
    return expand(os.path.join(MANIFEST_DIR, MANIFEST_FILE))


def load() -> dict:
    """Load the manifest.  Returns empty skeleton if file does not exist."""
    p = manifest_path()
    data = read_json(p)
    if not data:
        return {"version": 1, "installs": []}
    data.setdefault("version", 1)
    data.setdefault("installs", [])
    return data


def save(data: dict) -> None:
    """Atomically write the manifest."""
    write_json_atomic(manifest_path(), data)


def add(entry: dict) -> None:
    """Append an installation record to the manifest.

    Removes any existing record with the same platform/scope/config_dir
    to avoid duplicates (idempotent re-install).
    """
    data = load()
    installs = data.get("installs", [])

    # Remove existing matching record (idempotent).
    installs = [
        i
        for i in installs
        if not (
            i.get("platform") == entry.get("platform")
            and i.get("scope") == entry.get("scope")
            and i.get("config_dir") == entry.get("config_dir")
        )
    ]

    entry.setdefault("installed_at", datetime.now(timezone.utc).isoformat())
    installs.append(entry)
    data["installs"] = installs
    save(data)


def remove(platform: str, scope: str, config_dir: str) -> dict | None:
    """Remove a matching record.  Returns the removed entry or None."""
    data = load()
    installs = data.get("installs", [])
    removed: dict | None = None
    remaining: list[dict] = []

    for i in installs:
        if (
            i.get("platform") == platform
            and i.get("scope") == scope
            and i.get("config_dir") == config_dir
        ):
            removed = i
        else:
            remaining.append(i)

    data["installs"] = remaining
    save(data)

    # Clean up manifest file if no installs left.
    if not remaining:
        p = Path(manifest_path())
        if p.exists():
            p.unlink()
        # Also remove the directory if empty.
        d = p.parent
        try:
            d.rmdir()
        except OSError:
            pass

    return removed


def find(
    platform: str,
    scope: str | None = None,
    config_dir: str | None = None,
) -> dict | None:
    """Find a matching install record.

    Matches by platform (required) and optionally scope/config_dir.
    """
    data = load()
    for i in data.get("installs", []):
        if i.get("platform") != platform:
            continue
        if scope is not None and i.get("scope") != scope:
            continue
        if config_dir is not None and i.get("config_dir") != config_dir:
            continue
        return cast(dict, i)
    return None


def list_all() -> list[dict]:
    """Return all install records."""
    data = load()
    return cast(list[dict], data.get("installs", []))


# ── Credentials ─────────────────────────────────────────────────────


ENV_SPACE_ID = "AGENTARTS_MEMORY_SPACE_ID"
ENV_API_KEY = "HUAWEICLOUD_SDK_MEMORY_API_KEY"
ENV_REGION = "HUAWEICLOUD_SDK_REGION"

DEFAULT_REGION = "cn-southwest-2"

REQUIRED_VARS = (ENV_SPACE_ID, ENV_API_KEY)
OPTIONAL_VARS = (ENV_REGION,)


# ── Validators ──────────────────────────────────────────────────────


def validate_space_id(value: str) -> tuple[bool, str]:
    """Validate Space ID: non-empty, >= 8 characters."""
    if not value or not value.strip():
        return False, "Space ID cannot be empty"
    value = value.strip()
    if len(value) < 8:
        return False, "Space ID must be at least 8 characters"
    return True, value


def validate_api_key(value: str) -> tuple[bool, str]:
    """Validate API Key: non-empty, >= 16 characters."""
    if not value or not value.strip():
        return False, "API Key cannot be empty"
    value = value.strip()
    if len(value) < 16:
        return False, "API Key must be at least 16 characters"
    return True, value


def validate_region(value: str) -> tuple[bool, str]:
    """Validate region: three-part format (e.g. cn-southwest-2)."""
    if not value or not value.strip():
        return True, DEFAULT_REGION
    value = value.strip()
    parts = value.split("-")
    if len(parts) != 3:
        return False, "Region format should be like 'cn-southwest-2'"
    return True, value


VALIDATORS: dict[str, Callable[[str], tuple[bool, str]]] = {
    ENV_SPACE_ID: validate_space_id,
    ENV_API_KEY: validate_api_key,
    ENV_REGION: validate_region,
}

VAR_DESCRIPTIONS: dict[str, str] = {
    ENV_SPACE_ID: "AgentArts Memory Space ID",
    ENV_API_KEY: "AgentArts Memory API Key",
    ENV_REGION: "AgentArts Memory Region",
}


# ── Environment detection ────────────────────────────────────────────


def check_env() -> tuple[bool, dict[str, str]]:
    """Check if all required environment variables are set and valid.

    Returns ``(True, config_dict)`` if all required vars are valid,
    ``(False, partial_config)`` otherwise.  The partial config contains
    whatever was successfully validated.
    """
    config: dict[str, str] = {}
    all_ok = True

    for var in REQUIRED_VARS:
        value = os.getenv(var, "")
        validator = VALIDATORS[var]
        ok, result = validator(value)
        if ok:
            config[var] = result
        else:
            all_ok = False

    # Region is optional with default.
    region = os.getenv(ENV_REGION, "")
    ok, result = validate_region(region)
    config[ENV_REGION] = result if ok else DEFAULT_REGION

    return all_ok, config


def _mask(value: str, var_name: str) -> str:
    """Mask sensitive values for display."""
    if not value:
        return ""
    if "API_KEY" in var_name or "SECRET" in var_name or "SK" in var_name:
        return "*" * min(len(value), 8)
    if len(value) <= 8:
        return value
    return f"{value[:4]}...{value[-4:]}"


# ── Interactive fill ─────────────────────────────────────────────────


def interactive_fill(missing: list[str], yes: bool) -> dict[str, str]:
    """Interactively prompt for each missing variable.

    In ``--yes`` mode, returns defaults (empty strings) without prompting.
    """
    filled: dict[str, str] = {}

    for var in missing:
        desc = VAR_DESCRIPTIONS.get(var, var)
        is_optional = var in OPTIONAL_VARS
        default = DEFAULT_REGION if is_optional else ""
        validator = VALIDATORS.get(var)

        if yes:
            filled[var] = default
            continue

        while True:
            prompt_text = f"\n{desc}"
            if is_optional and default:
                prompt_text += f" (default: {default})"
            raw = prompt_input(prompt_text, default=default)

            if is_optional and not raw:
                raw = default

            if validator:
                ok, result = validator(raw)
                if not ok:
                    console.print(f"  [red]\u00d7[/red] {result}")
                    continue
                raw = result

            if not raw and not is_optional:
                console.print("  [red]\u00d7[/red] Value cannot be empty")
                continue

            display = _mask(raw, var)
            console.print(f"  [green]\u221a[/green] Configured: {display}")
            filled[var] = raw
            break

    return filled


def ensure_credentials(yes: bool) -> dict[str, str]:
    """Ensure all required credentials are available.

    1. Check environment variables.
    2. Prompt interactively for missing ones (skipped in --yes mode).
    3. Optionally write to shell rc for persistence.
    """
    all_ok, config = check_env()

    if not all_ok:
        missing = [v for v in REQUIRED_VARS if v not in config]
        filled = interactive_fill(missing, yes)
        config.update(filled)
        all_ok = all(v in config and config[v] for v in REQUIRED_VARS)

    if not all_ok:
        console.print("\n[yellow]\u26a0[/yellow]  Missing required credentials. Please set:")
        for var in REQUIRED_VARS:
            if not config.get(var):
                console.print(f"  {var}")
        return config

    # Optional: write to shell rc.
    if not yes:
        if confirm("Save configuration to shell rc for persistence?", default=True):
            write_shell_rc(config)
            console.print("  [green]\u221a[/green] Configuration saved to shell rc")
            console.print("  Run 'source' or restart terminal to apply.")
    elif all_ok:
        # In --yes mode, persist if we filled anything interactively (no-op if
        # everything came from env).
        pass

    return config


# ── Shell rc helpers ─────────────────────────────────────────────────


def get_shell_rc() -> str:
    """Detect the current shell's rc file path."""
    shell = os.getenv("SHELL", "")
    home = os.path.expanduser("~")
    if "zsh" in shell:
        return os.path.join(home, ".zshrc")
    elif "bash" in shell:
        return os.path.join(home, ".bashrc")
    # Fallback.
    return os.path.join(home, ".bashrc")


def write_shell_rc(entries: dict[str, str]) -> None:
    """Write export lines to shell rc, deduplicating by key."""
    rc_path = expand(get_shell_rc())
    existing: list[str] = []
    other_lines: list[str] = []

    if os.path.exists(rc_path):
        with open(rc_path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("export ") and "=" in stripped:
                    # export KEY=value
                    key_part = stripped[len("export ") :].split("=", 1)[0]
                    existing.append(key_part)
                    other_lines.append(line.rstrip("\n"))
                else:
                    other_lines.append(line.rstrip("\n"))

    # Build new content.
    new_lines = list(other_lines)
    existing_keys = set(existing)
    for key, value in entries.items():
        if key in existing_keys:
            # Replace the existing line.
            new_lines = [
                f"export {key}={value}" if line.strip().startswith(f"export {key}=") else line
                for line in new_lines
            ]
        else:
            new_lines.append(f"export {key}={value}")

    with open(rc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")
