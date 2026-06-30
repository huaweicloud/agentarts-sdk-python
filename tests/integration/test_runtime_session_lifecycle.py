"""Runtime data-plane session lifecycle (RUN_BILLABLE tier).

Starts a runtime session against a *pre-deployed* agent, runs one command,
then stops the session. ``stop_session`` is also registered with the resource
registry so the session is torn down even if a step crashes mid-flow. Requires
``AGENTARTS_TEST_RUNTIME_AGENT_NAME`` and ``AGENTARTS_RUNTIME_DATA_ENDPOINT``.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration


def test_runtime_start_exec_stop(
    runtime_client, allow_billable, runtime_agent_name, resource_registry
):
    agent_name = runtime_agent_name
    session_id = f"aa-it-{uuid.uuid4().hex[:8]}"

    started = runtime_client.start_session(agent_name=agent_name)
    # the backend may return its own session_id; prefer it when present
    backend_sid = started.get("session_id") if isinstance(started, dict) else None
    sid = backend_sid or session_id

    # safety net: always stop the session at session end, even on failure
    resource_registry.register(
        lambda: runtime_client.stop_session(agent_name=agent_name, session_id=sid),
        f"runtime_session:{agent_name}:{sid}",
    )

    result = runtime_client.exec_command(
        agent_name=agent_name, session_id=sid, command="echo aa-it"
    )
    assert isinstance(result, dict)

    runtime_client.stop_session(agent_name=agent_name, session_id=sid)
