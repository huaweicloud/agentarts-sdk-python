"""Shared helpers for integration tests.

Kept dependency-free (stdlib only) so it can be imported from anywhere,
including ``conftest.py``.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

# Prefix for every resource created by this suite. Makes leaked resources
# greppable for manual cleanup:  `list_* | grep aa-it-`
RESOURCE_PREFIX = "aa-it"

# Env vars that flip the three-tier safety model on/off.
ENV_ALLOW_CREATE = "AGENTARTS_TEST_ALLOW_CREATE"
ENV_RUN_BILLABLE = "AGENTARTS_TEST_RUN_BILLABLE"
ENV_RUN_ID = "AGENTARTS_TEST_RUN_ID"

# Credential / scenario env vars.
ENV_AK = "HUAWEICLOUD_SDK_AK"
ENV_SK = "HUAWEICLOUD_SDK_SK"
ENV_REGION = "HUAWEICLOUD_SDK_REGION"
ENV_MEMORY_API_KEY = "HUAWEICLOUD_SDK_MEMORY_API_KEY"
ENV_CODE_INTERPRETER_API_KEY = "HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY"
ENV_PRE_WORKLOAD_IDENTITY = "AGENTARTS_TEST_WORKLOAD_IDENTITY_NAME"
ENV_RUNTIME_AGENT_NAME = "AGENTARTS_TEST_RUNTIME_AGENT_NAME"

_TRUTHY = {"1", "true", "yes", "on"}


def env_truthy(name: str) -> bool:
    """True if env var ``name`` is set to a truthy value (1/true/yes/on)."""
    return os.getenv(name, "").strip().lower() in _TRUTHY


def require_env(name: str) -> str:
    """Return env var ``name`` or raise — used inside gated fixtures only."""
    value = os.getenv(name)
    if not value:
        msg = f"Required env var {name} is not set"
        raise RuntimeError(msg)
    return value


def unique_name(kind: str, run_id: str, max_len: int = 40) -> str:
    """Build a run-scoped resource name.

    ``kind`` should be short and lowercase (e.g. ``"wi"``, ``"space"``,
    ``"ci"``). The result is guaranteed to satisfy the strictest naming rule
    in the SDK (code-interpreter: ``[a-z][a-z0-9-]{0,38}[a-z0-9]``).
    """
    raw = f"{RESOURCE_PREFIX}-{run_id}-{kind}"
    if len(raw) > max_len:
        raw = raw[:max_len]
    # ensure it ends with a lowercase letter/digit (trim trailing hyphens)
    return raw.rstrip("-")


def wait_for(
    predicate: Callable[[], Any],
    *,
    timeout: float = 60.0,
    interval: float = 2.0,
    desc: str = "condition",
) -> Any:
    """Poll ``predicate`` until it returns truthy or ``timeout`` elapses.

    Returns the last truthy result. Raises ``TimeoutError`` if it never does.
    """
    deadline = time.monotonic() + timeout
    last: Any = None
    while time.monotonic() < deadline:
        try:
            last = predicate()
        except Exception:  # noqa: BLE001 - transient cloud errors are expected
            last = None
        if last:
            return last
        time.sleep(interval)
    msg = f"Timed out after {timeout}s waiting for {desc}"
    raise TimeoutError(msg)


def safe_delete(deleter: Callable[[], Any], desc: str) -> None:
    """Run a cleanup callable, swallowing+logging errors.

    Cleanup must never crash the suite — a leaked resource is preferable to a
    masked test failure. Leaked resources are greppable via ``RESOURCE_PREFIX``.
    """
    try:
        deleter()
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger("agentarts.integration").warning(
            "cleanup FAILED for %s: %s — resource may leak (grep '%s')",
            desc,
            exc,
            RESOURCE_PREFIX,
        )
