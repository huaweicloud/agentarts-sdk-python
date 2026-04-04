"""
Integration tests for AgentArts Runtime Application.

Tests verify end-to-end behaviour by spinning up a real ASGI test
client (httpx.AsyncClient with ASGITransport) against a fully
initialised :class:`AgentArtsRuntimeApp`.  This exercises routing,
middleware, request parsing, response serialisation, and WebSocket
lifecycle without needing an external HTTP server.

Test scenarios:
1. Simple sync agent – POST /invocations returns JSON result
2. Simple async agent – POST /invocations returns JSON result
3. Sync streaming agent – POST /invocations returns SSE stream
4. Async streaming agent – POST /invocations returns SSE stream
5. Agent with context – POST /invocations passes RequestContext
6. Health check – GET /ping returns status
7. WebSocket – bidirectional communication
8. Error handling – invalid JSON, handler exceptions, no entrypoint
9. LangGraph agent – real LangGraph graph wrapped by app (skip if not installed)
"""

import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient

try:
    from httpx import AsyncClient as _AC
    _test_client = _AC()
    _HAS_WS = hasattr(_test_client, "websocket_connect")
    _test_client.close()
except Exception:
    _HAS_WS = False

from agentarts.wrapper.runtime.app import AgentArtsRuntimeApp
from agentarts.wrapper.runtime.model import PingStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sync_app():
    """Create an app with a simple sync entrypoint."""
    app = AgentArtsRuntimeApp()

    @app.entrypoint
    def handle(payload: dict):
        return {"echo": payload.get("input", ""), "processed": True}

    return app


@pytest.fixture
def async_app():
    """Create an app with an async entrypoint."""
    app = AgentArtsRuntimeApp()

    @app.entrypoint
    async def handle(payload: dict):
        await asyncio.sleep(0.01)
        return {"echo": payload.get("input", ""), "async": True}

    return app


@pytest.fixture
def streaming_app():
    """Create an app with a sync generator entrypoint."""
    app = AgentArtsRuntimeApp()

    @app.entrypoint
    def handle(payload: dict):
        for i in range(3):
            yield {"chunk": i, "input": payload.get("input", "")}

    return app


@pytest.fixture
def async_streaming_app():
    """Create an app with an async generator entrypoint."""
    app = AgentArtsRuntimeApp()

    @app.entrypoint
    async def handle(payload: dict):
        for i in range(3):
            await asyncio.sleep(0.01)
            yield {"chunk": i, "input": payload.get("input", "")}

    return app


@pytest.fixture
def context_app():
    """Create an app whose handler accepts a RequestContext."""
    app = AgentArtsRuntimeApp()

    @app.entrypoint
    def handle(payload: dict, context):
        return {
            "session_id": context.session_id,
            "request_id": context.request_id,
            "input": payload.get("input", ""),
        }

    return app


@pytest.fixture
def error_app():
    """Create an app whose handler always raises."""
    app = AgentArtsRuntimeApp()

    @app.entrypoint
    def handle(payload: dict):
        raise RuntimeError("Intentional failure for testing")

    return app


@pytest.fixture
def ws_app():
    """Create an app with a WebSocket handler."""
    app = AgentArtsRuntimeApp()

    @app.websocket
    async def ws_handler(websocket, context):
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_json()
                await websocket.send_json({"reply": data.get("message", "")})
        except Exception:
            pass

    return app


# ---------------------------------------------------------------------------
# 1. Simple sync agent
# ---------------------------------------------------------------------------

class TestSyncAgentIntegration:

    @pytest.mark.asyncio
    async def test_invocation_returns_json(self, sync_app):
        transport = ASGITransport(app=sync_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/invocations", json={"input": "hello"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["echo"] == "hello"
        assert body["processed"] is True

    @pytest.mark.asyncio
    async def test_invocation_empty_payload(self, sync_app):
        transport = ASGITransport(app=sync_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/invocations", json={})

        assert resp.status_code == 200
        body = resp.json()
        assert body["processed"] is True


# ---------------------------------------------------------------------------
# 2. Simple async agent
# ---------------------------------------------------------------------------

class TestAsyncAgentIntegration:

    @pytest.mark.asyncio
    async def test_invocation_returns_json(self, async_app):
        transport = ASGITransport(app=async_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/invocations", json={"input": "world"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["echo"] == "world"
        assert body["async"] is True


# ---------------------------------------------------------------------------
# 3. Sync streaming agent
# ---------------------------------------------------------------------------

class TestSyncStreamingIntegration:

    @pytest.mark.asyncio
    async def test_invocation_returns_sse_stream(self, streaming_app):
        transport = ASGITransport(app=streaming_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/invocations", json={"input": "stream"})

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        text = resp.text
        lines = [l for l in text.strip().split("\n") if l.startswith("data: ")]
        assert len(lines) == 3

        for i, line in enumerate(lines):
            data = json.loads(line.replace("data: ", ""))
            assert data["chunk"] == i
            assert data["input"] == "stream"


# ---------------------------------------------------------------------------
# 4. Async streaming agent
# ---------------------------------------------------------------------------

class TestAsyncStreamingIntegration:

    @pytest.mark.asyncio
    async def test_invocation_returns_sse_stream(self, async_streaming_app):
        transport = ASGITransport(app=async_streaming_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/invocations", json={"input": "astream"})

        assert resp.status_code == 200

        text = resp.text
        lines = [l for l in text.strip().split("\n") if l.startswith("data: ")]
        assert len(lines) == 3

        for i, line in enumerate(lines):
            data = json.loads(line.replace("data: ", ""))
            assert data["chunk"] == i


# ---------------------------------------------------------------------------
# 5. Agent with context
# ---------------------------------------------------------------------------

class TestContextIntegration:

    @pytest.mark.asyncio
    async def test_invocation_passes_session_header(self, context_app):
        transport = ASGITransport(app=context_app)
        headers = {"x-hw-agentarts-session-id": "session-int-001"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/invocations", json={"input": "ctx"}, headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "session-int-001"
        assert body["input"] == "ctx"
        assert body["request_id"] is not None


# ---------------------------------------------------------------------------
# 6. Health check
# ---------------------------------------------------------------------------

class TestPingIntegration:

    @pytest.mark.asyncio
    async def test_ping_returns_healthy(self, sync_app):
        transport = ASGITransport(app=sync_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ping")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "Healthy"

    @pytest.mark.asyncio
    async def test_ping_with_custom_handler(self):
        app = AgentArtsRuntimeApp()

        @app.entrypoint
        def handle(payload):
            return {"ok": True}

        @app.ping
        def health():
            return "HealthyBusy"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ping")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "HealthyBusy"

    @pytest.mark.asyncio
    async def test_ping_with_running_async_task(self):
        app = AgentArtsRuntimeApp()

        @app.entrypoint
        def handle(payload):
            return {"ok": True}

        @app.async_task
        async def slow_task():
            await asyncio.sleep(5)

        task_started = asyncio.Event()

        async def run_task():
            task_started.set()
            await slow_task()

        t = asyncio.create_task(run_task())
        await task_started.wait()

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/ping")

            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "HealthyBusy"
        finally:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass


# ---------------------------------------------------------------------------
# 7. WebSocket
# ---------------------------------------------------------------------------

class TestWebSocketIntegration:

    @pytest.mark.skipif(not _HAS_WS, reason="httpx websocket support not available")
    @pytest.mark.asyncio
    async def test_websocket_echo(self, ws_app):
        transport = ASGITransport(app=ws_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with client.websocket_connect("/ws") as ws:
                ws.send_json({"message": "hello ws"})
                resp = ws.receive_json()
                assert resp["reply"] == "hello ws"

                ws.send_json({"message": "second"})
                resp = ws.receive_json()
                assert resp["reply"] == "second"


# ---------------------------------------------------------------------------
# 8. Error handling
# ---------------------------------------------------------------------------

class TestErrorHandlingIntegration:

    @pytest.mark.asyncio
    async def test_no_entrypoint_returns_404(self):
        app = AgentArtsRuntimeApp()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/invocations", json={"input": "test"})

        assert resp.status_code == 404
        body = resp.json()
        assert "No entrypoint" in body["error"]

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self, sync_app):
        transport = ASGITransport(app=sync_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/invocations",
                content=b"not json at all",
                headers={"content-type": "application/json"},
            )

        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "Invalid JSON payload"

    @pytest.mark.asyncio
    async def test_handler_exception_returns_500(self, error_app):
        transport = ASGITransport(app=error_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/invocations", json={"input": "test"})

        assert resp.status_code == 500
        body = resp.json()
        assert body["error"] == "RuntimeError"
        assert "Intentional failure" in body["message"]

    @pytest.mark.skipif(not _HAS_WS, reason="httpx websocket support not available")
    @pytest.mark.asyncio
    async def test_websocket_no_handler_closes(self):
        app = AgentArtsRuntimeApp()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with pytest.raises(Exception):
                async with client.websocket_connect("/ws") as ws:
                    await ws.receive_json()


# ---------------------------------------------------------------------------
# 9. LangGraph agent (skip if langgraph not installed)
# ---------------------------------------------------------------------------

try:
    import langgraph  # noqa: F401
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False


@pytest.mark.skipif(not HAS_LANGGRAPH, reason="langgraph is not installed")


class TestLangGraphAgentIntegration:

    @pytest.mark.asyncio
    async def test_langgraph_agent_invocation(self):
        from langgraph.graph import StateGraph, START, END
        from typing import Annotated
        from typing_extensions import TypedDict

        class AgentState(TypedDict):
            messages: list[str]
            result: str

        def node_a(state: AgentState) -> dict:
            messages = state.get("messages", [])
            return {"messages": messages + ["node_a_processed"], "result": "processed_by_langgraph"}

        builder = StateGraph(AgentState)
        builder.add_node("a", node_a)
        builder.add_edge(START, "a")
        builder.add_edge("a", END)
        graph = builder.compile()

        app = AgentArtsRuntimeApp()

        @app.entrypoint
        def handle(payload: dict):
            input_data = payload.get("input", "")
            result = graph.invoke({"messages": [input_data], "result": ""})
            return {
                "framework": "langgraph",
                "result": result["result"],
                "messages": result["messages"],
            }

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/invocations", json={"input": "hello langgraph"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["framework"] == "langgraph"
        assert body["result"] == "processed_by_langgraph"
        assert "node_a_processed" in body["messages"]

    @pytest.mark.asyncio
    async def test_langgraph_agent_with_ping(self):
        from langgraph.graph import StateGraph, START, END
        from typing_extensions import TypedDict

        class State(TypedDict):
            query: str
            answer: str

        def responder(state: State) -> dict:
            return {"answer": f"Response to: {state['query']}"}

        builder = StateGraph(State)
        builder.add_node("respond", responder)
        builder.add_edge(START, "respond")
        builder.add_edge("respond", END)
        graph = builder.compile()

        app = AgentArtsRuntimeApp()

        @app.entrypoint
        def handle(payload: dict):
            result = graph.invoke({"query": payload.get("query", ""), "answer": ""})
            return {"answer": result["answer"]}

        @app.ping
        def health():
            return "Healthy"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ping_resp = await client.get("/ping")
            assert ping_resp.status_code == 200
            assert ping_resp.json()["status"] == "Healthy"

            invoke_resp = await client.post("/invocations", json={"query": "test query"})
            assert invoke_resp.status_code == 200
            assert invoke_resp.json()["answer"] == "Response to: test query"
