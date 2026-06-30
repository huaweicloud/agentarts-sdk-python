"""Runtime data-plane session lifecycle (RUN_BILLABLE tier).

Starts a runtime session against a *pre-deployed* agent, runs a command,
round-trips a small file (upload→download), then stops the session.
``stop_session`` is also registered with the resource registry so the session
is torn down even if a step crashes mid-flow. Requires
``AGENTARTS_TEST_RUNTIME_AGENT_NAME`` and ``AGENTARTS_RUNTIME_DATA_ENDPOINT``.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration

_FILE_PATH = "/home/user/aa-it-uploaded.txt"
_FILE_CONTENT = "hello-aa-it"


def test_runtime_session_upload_download(
    runtime_client, allow_billable, runtime_agent_name, resource_registry
):
    agent_name = runtime_agent_name
    session_id = f"aa-it-{uuid.uuid4().hex[:8]}"

    started = runtime_client.start_session(agent_name=agent_name)
    backend_sid = started.get("session_id") if isinstance(started, dict) else None
    sid = backend_sid or session_id

    # safety net: always stop the session at session end, even on failure
    resource_registry.register(
        lambda: runtime_client.stop_session(agent_name=agent_name, session_id=sid),
        f"runtime_session:{agent_name}:{sid}",
    )

    # 1. exec_command
    cmd = runtime_client.exec_command(
        agent_name=agent_name, session_id=sid, command=f"echo {_FILE_CONTENT}"
    )
    assert isinstance(cmd, dict)

    # 2. upload_files (single file, content-based) then download_files round-trip
    up = runtime_client.upload_files(
        agent_name=agent_name,
        session_id=sid,
        files=[{"content": _FILE_CONTENT}],
        path=_FILE_PATH,
    )
    assert isinstance(up, dict)

    downloaded = runtime_client.download_files(
        agent_name=agent_name, session_id=sid, path=_FILE_PATH, recursive=False
    )
    body = b"".join(downloaded.iter_bytes()) if hasattr(downloaded, "iter_bytes") else downloaded
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    assert _FILE_CONTENT in str(body)

    runtime_client.stop_session(agent_name=agent_name, session_id=sid)
