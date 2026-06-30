"""Local ASGI tests for ``AgentArtsRuntimeApp`` — no cloud, no credentials.

These run in the default tier. They exercise the runtime HTTP/WebSocket surface
via Starlette's ``TestClient``: ``/ping``, ``/invocations`` (JSON + SSE
streaming + error paths) and ``/ws``.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from agentarts.sdk import AgentArtsRuntimeApp, PingStatus
from agentarts.sdk.runtime.model import SESSION_HEADER

pytestmark = pytest.mark.integration


# --------------------------------------------------------------------------- #
# /ping
# --------------------------------------------------------------------------- #
def test_ping_default_healthy():
    app = AgentArtsRuntimeApp()
    with TestClient(app) as client:
        resp = client.get("/ping")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == PingStatus.HEALTHY.value
    assert "time_of_last_update" in body


def test_ping_force_unhealthy():
    app = AgentArtsRuntimeApp()
    app.force_ping_status(PingStatus.UNHEALTHY)
    with TestClient(app) as client:
        resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.json()["status"] == PingStatus.UNHEALTHY.value


def test_ping_custom_handler():
    app = AgentArtsRuntimeApp()

    @app.ping
    def _ping():
        return PingStatus.HEALTHY_BUSY

    with TestClient(app) as client:
        resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.json()["status"] == PingStatus.HEALTHY_BUSY.value


# --------------------------------------------------------------------------- #
# /invocations — happy path + error paths
# --------------------------------------------------------------------------- #
def test_invocation_returns_handler_result():
    app = AgentArtsRuntimeApp()

    @app.entrypoint
    def handler(payload: dict):
        return {"echo": payload["message"]}

    with TestClient(app) as client:
        resp = client.post("/invocations", json={"message": "hello"})
    assert resp.status_code == 200
    assert resp.json()["echo"] == "hello"
    # session header is echoed back on the response
    assert SESSION_HEADER in resp.headers


def test_invocation_no_entrypoint_returns_404():
    app = AgentArtsRuntimeApp()  # no @app.entrypoint
    with TestClient(app) as client:
        resp = client.post("/invocations", json={"message": "hi"})
    assert resp.status_code == 404


def test_invocation_invalid_json_returns_400():
    app = AgentArtsRuntimeApp()

    @app.entrypoint
    def handler(payload: dict):
        return {"ok": True}

    with TestClient(app) as client:
        resp = client.post("/invocations", content=b"{not json", headers={"content-type": "application/json"})
    assert resp.status_code == 400


def test_invocation_handler_raises_returns_500():
    app = AgentArtsRuntimeApp()

    @app.entrypoint
    def handler(payload: dict):
        raise RuntimeError("boom")

    with TestClient(app) as client:
        resp = client.post("/invocations", json={"x": 1})
    assert resp.status_code == 500


def test_invocation_sync_generator_streams_sse():
    app = AgentArtsRuntimeApp()

    @app.entrypoint
    def handler(payload: dict):
        for word in ["a", "b", "c"]:
            yield {"token": word}

    with TestClient(app) as client:
        resp = client.post("/invocations", json={})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    body = resp.text
    # each yielded item is serialised into an SSE `data:` line
    assert body.count("data:") >= 3
    assert "a" in body and "c" in body


def test_invocation_async_generator_streams_sse():
    app = AgentArtsRuntimeApp()

    @app.entrypoint
    async def handler(payload: dict):
        for word in ["x", "y"]:
            yield {"token": word}

    with TestClient(app) as client:
        resp = client.post("/invocations", json={})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    assert resp.text.count("data:") >= 2


# --------------------------------------------------------------------------- #
# /ws
# --------------------------------------------------------------------------- #
def test_websocket_without_handler_closes_1011():
    app = AgentArtsRuntimeApp()  # no @app.websocket
    with TestClient(app) as client:
        with pytest.raises(Exception):  # WebSocketDisconnect / close 1011
            with client.websocket_connect("/ws") as ws:
                ws.receive_json()


def test_websocket_echo_handler():
    app = AgentArtsRuntimeApp()

    @app.websocket
    async def ws_handler(websocket, request_context):  # noqa: ANN001
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_json()
                await websocket.send_json({"echo": data})
        except Exception:  # noqa: BLE001
            pass

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"msg": "ping"})
            assert ws.receive_json() == {"echo": {"msg": "ping"}}
