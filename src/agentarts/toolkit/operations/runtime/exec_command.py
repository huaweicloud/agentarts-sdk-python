"""Runtime exec-command operation"""

import logging
import shlex
import uuid
from collections.abc import Iterator
from typing import Any

from agentarts.sdk.service.http_client import SignMode
from agentarts.sdk.service.runtime_client import RuntimeClient
from agentarts.toolkit.operations.runtime.invoke import _get_data_endpoint, _resolve_agent_info
from agentarts.toolkit.utils.common import echo_error

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60
MAX_TIMEOUT = 3600

# Shell-only operators that the backend's exec-form (Docker JSON-array) cannot
# interpret: when present *outside quotes*, the command is meant for a shell, so
# we wrap it as ["sh", "-c", "<original string>"] and let sh re-parse quotes /
# redirection / pipes consistently. Glob chars (* ? [) are deliberately NOT here
# — a bare * is ambiguous (literal pattern vs glob); leave that to --shell.
_SHELL_OPERATOR_CHARS = "><|;&`"


def _needs_shell(command: str) -> bool:
    """Return True if ``command`` uses shell-only constructs outside quotes.

    Scans with single/double-quote and backslash-escape awareness so that
    quoted metacharacters (e.g. ``echo "a > b"``) do not trigger a wrap.
    """
    i, n = 0, len(command)
    while i < n:
        c = command[i]
        if c == "'":
            # single-quoted: no escaping, ends at next '
            i += 1
            while i < n and command[i] != "'":
                i += 1
            i += 1  # skip closing quote (or run to end)
            continue
        if c == '"':
            i += 1
            while i < n:
                if command[i] == "\\" and i + 1 < n:
                    i += 2
                    continue
                if command[i] == '"':
                    break
                i += 1
            i += 1
            continue
        if c == "\\":  # unquoted escape: skip next char
            i += 2
            continue
        if c in _SHELL_OPERATOR_CHARS:
            return True
        if c == "$" and i + 1 < n and command[i + 1] == "(":
            return True  # $(...) command substitution
        i += 1
    return False


def build_command_array(command: str) -> list[str]:
    """Turn a command string into the argv the backend exec-form expects.

    - Plain command -> ``shlex.split`` -> exec-form array (Docker exec-form).
    - Shell constructs (redirection/pipe/``&&``/``;``/``$()``/backtick, outside
      quotes) -> ``["sh", "-c", command]`` using the *original* string so sh
      re-parses quotes and operators consistently. (Note: ``sh -c`` only treats
      its first arg as the script, so the array must be exactly these three.)
    """
    if _needs_shell(command):
        logger.info("exec-command: command contains shell operators; wrapping as sh -c %r", command)
        return ["sh", "-c", command]
    parts = shlex.split(command)
    if not parts:
        raise ValueError("Command cannot be empty")
    return parts


def exec_runtime_command(
    command: str,
    agent_name: str | None = None,
    session_id: str | None = None,
    chunked: bool = False,
    bearer_token: str | None = None,
    region: str | None = None,
    endpoint: str | None = None,
    skip_ssl_verification: bool = False,
    user_id: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any] | Iterator[str]:
    """
    Execute command in runtime.

    Args:
        command: Command string to execute
        agent_name: Agent name
        session_id: Session ID
        chunked: Use chunked streaming mode
        bearer_token: Optional bearer token for authentication
        region: Region name
        endpoint: Optional endpoint name
        skip_ssl_verification: Skip SSL certificate verification
        user_id: Optional user ID for OAuth2 outbound credentials
        timeout: Request timeout in seconds (default: 60, max: 3600)

    Returns:
        dict for normal mode, Iterator[str] for chunked mode
    """
    if not command:
        raise ValueError("Command is required")

    command_array = build_command_array(command)

    # Auto-generate a session id when none was provided, mirroring `invoke`.
    # Without this the V11 signer hits `session_id.strip()` on a None header
    # value and raises an opaque AttributeError.
    if not session_id:
        session_id = str(uuid.uuid4())


    if timeout <= 0:
        raise ValueError(f"Timeout must be a positive number: {timeout}")
    if timeout > MAX_TIMEOUT:
        raise ValueError(f"Timeout exceeds maximum allowed value ({MAX_TIMEOUT}): {timeout}")

    agent_name, region, agent_id, auth_type = _resolve_agent_info(agent_name, region)

    if agent_name is None:
        echo_error("No agent specified and no default agent configured")
        raise ValueError("Agent name is required")

    verify_ssl = not skip_ssl_verification
    data_endpoint = _get_data_endpoint(agent_name, region or "", agent_id, verify_ssl)

    if not data_endpoint:
        raise ValueError(f"No data endpoint for agent {agent_name}")

    sign_mode = SignMode.SDK_HMAC_SHA256
    if auth_type and auth_type.upper() == "IAM":
        sign_mode = SignMode.V11_HMAC_SHA256

    client = RuntimeClient(
        data_endpoint=data_endpoint,
        region_id=region or "",
        verify_ssl=verify_ssl,
        sign_mode=sign_mode,
    )
    if bearer_token:
        client.set_auth_token(bearer_token)

    return client.exec_command(
        agent_name=agent_name,
        session_id=session_id,
        command=command_array,
        chunked=chunked,
        bearer_token=bearer_token,
        endpoint=endpoint,
        user_id=user_id,
        timeout=timeout,
    )
