"""
Comprehensive unit tests for agentarts.sdk.runtime.app module.

Tests cover:
- Decorators (entrypoint, ping, websocket, async_task)
- Task management (_add_task, _complete_task, has_running_tasks)
- Request context helpers (_build_request_context, _task_context)
- Invocation endpoint (_handle_invocation, _invoke_handler)
- Serialization (_safe_serialize_to_json_string, _convert_to_sse)
- Stream generators (_sync_stream_handler, _async_stream_handler)
- Ping endpoint (_handle_ping, get_current_ping_status, force_ping_status)
- WebSocket endpoint (_handle_websocket)
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.routing import WebSocket
from starlette.websockets import WebSocketDisconnect

from agentarts.sdk.runtime.app import AgentArtsRuntimeApp
from agentarts.sdk.runtime.context import AgentArtsRuntimeContext, RequestContext
from agentarts.sdk.runtime.model import PingStatus


class TestAgentArtsRuntimeAppInit:
    """Tests for AgentArtsRuntimeApp initialization."""

    def test_init_default_values(self):
        """Test default initialization values."""
        app = AgentArtsRuntimeApp()
        assert app.handlers == {}
        assert app._ping_handler is None
        assert app._ws_handler is None
        assert app.protocol == "http"
        assert app._active_tasks == {}
        assert app._force_ping_status is None

    def test_init_custom_protocol(self):
        """Test initialization with custom protocol."""
        app = AgentArtsRuntimeApp(protocol="https")
        assert app.protocol == "https"

    def test_init_debug_mode(self):
        """Test initialization with debug mode."""
        app = AgentArtsRuntimeApp(debug=True)
        assert app.debug is True


class TestDecorators:
    """Tests for decorator methods."""

    def test_entrypoint_decorator(self):
        """Test entrypoint decorator registers handler."""
        app = AgentArtsRuntimeApp()

        @app.entrypoint
        def my_handler(payload):
            return {"result": "ok"}

        assert app.handlers["main"] == my_handler
        assert hasattr(my_handler, "run")
        assert my_handler.__name__ == "my_handler"

    def test_ping_decorator(self):
        """Test ping decorator registers handler."""
        app = AgentArtsRuntimeApp()

        @app.ping
        def health_check():
            return "Healthy"

        assert app._ping_handler == health_check

    def test_websocket_decorator(self):
        """Test websocket decorator registers handler."""
        app = AgentArtsRuntimeApp()

        @app.websocket
        async def ws_handler(websocket):
            pass

        assert app._ws_handler == ws_handler

    def test_async_task_decorator_sync_function_raises(self):
        """Test async_task decorator raises for sync functions."""
        app = AgentArtsRuntimeApp()

        with pytest.raises(ValueError, match="must be used with async functions"):
            @app.async_task
            def sync_func():
                pass

    @pytest.mark.asyncio
    async def test_async_task_decorator(self):
        """Test async_task decorator tracks execution."""
        app = AgentArtsRuntimeApp()

        @app.async_task
        async def background_job(payload):
            return {"result": payload}

        assert hasattr(background_job, "_is_async_task")
        assert background_job._is_async_task is True

        result = await background_job({"input": "test"})
        assert result == {"result": {"input": "test"}}
        assert not app.has_running_tasks()

    @pytest.mark.asyncio
    async def test_async_task_decorator_with_exception(self):
        """Test async_task decorator handles exceptions."""
        app = AgentArtsRuntimeApp()

        @app.async_task
        async def failing_task():
            msg = "Task failed"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="Task failed"):
            await failing_task()

        assert not app.has_running_tasks()


class TestTaskManagement:
    """Tests for task management methods."""

    def test_add_task(self):
        """Test _add_task registers task."""
        app = AgentArtsRuntimeApp()

        task_id = app._add_task("test_task", {"key": "value"})

        assert isinstance(task_id, int)
        assert task_id in app._active_tasks
        assert app._active_tasks[task_id]["name"] == "test_task"
        assert app._active_tasks[task_id]["metadata"] == {"key": "value"}

    def test_add_task_multiple(self):
        """Test _add_task registers multiple tasks."""
        app = AgentArtsRuntimeApp()

        task_id1 = app._add_task("task1")
        task_id2 = app._add_task("task2")

        assert task_id1 != task_id2
        assert len(app._active_tasks) == 2

    def test_complete_task(self):
        """Test _complete_task removes task."""
        app = AgentArtsRuntimeApp()

        task_id = app._add_task("test_task")
        result = app._complete_task(task_id)

        assert result is True
        assert task_id not in app._active_tasks

    def test_complete_task_not_found(self):
        """Test _complete_task returns False for unknown task."""
        app = AgentArtsRuntimeApp()

        result = app._complete_task(99999)

        assert result is False

    def test_has_running_tasks(self):
        """Test has_running_tasks returns correct status."""
        app = AgentArtsRuntimeApp()

        assert not app.has_running_tasks()

        app._add_task("running_task")
        assert app.has_running_tasks()

    def test_has_running_tasks_after_complete(self):
        """Test has_running_tasks after task completion."""
        app = AgentArtsRuntimeApp()

        task_id = app._add_task("test_task")
        assert app.has_running_tasks()

        app._complete_task(task_id)
        assert not app.has_running_tasks()


class TestBuildContext:
    """Tests for _build_request_context method."""

    def test_build_request_context_with_headers(self):
        """Test _build_request_context extracts headers."""
        app = AgentArtsRuntimeApp()

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {
            "X-HW-AgentGateway-Workload-Access-Token": "test-token",
            "x-hw-agentarts-session-id": "session-123",
            "X-Hw-AgentArts-Runtime-User-Id": "user-456",
            "X-Request-Id": "req-789",
        }

        context = app._build_request_context(mock_request)

        assert context.session_id == "session-123"
        assert context.request_id == "req-789"
        assert context.request == mock_request

    def test_build_request_context_generates_request_id(self):
        """Test _build_request_context generates request_id if not provided."""
        app = AgentArtsRuntimeApp()

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        context = app._build_request_context(mock_request)

        assert context.request_id is not None
        assert len(context.request_id) == 36  # UUID format

    def test_build_request_context_sets_runtime_context(self):
        """Test _build_request_context sets AgentArtsRuntimeContext values."""
        app = AgentArtsRuntimeApp()

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {
            "X-HW-AgentGateway-Workload-Access-Token": "workload-token",
            "x-hw-agentarts-session-id": "session-abc",
            "X-Hw-AgentArts-Runtime-User-Id": "user-xyz",
        }

        app._build_request_context(mock_request)

        assert AgentArtsRuntimeContext.get_workload_access_token() == "workload-token"
        assert AgentArtsRuntimeContext.get_session_id() == "session-abc"
        assert AgentArtsRuntimeContext.get_user_id() == "user-xyz"

        AgentArtsRuntimeContext.clear()


class TestTaskContext:
    """Tests for _task_context method."""

    def test_task_context_with_context_param(self):
        """Test _task_context returns True for handler with context param."""
        app = AgentArtsRuntimeApp()

        def handler(payload, context):
            pass

        assert app._task_context(handler) is True

    def test_task_context_without_context_param(self):
        """Test _task_context returns False for handler without context param."""
        app = AgentArtsRuntimeApp()

        def handler(payload):
            pass

        assert app._task_context(handler) is False

    def test_task_context_wrong_param_name(self):
        """Test _task_context returns False when second param is not 'context'."""
        app = AgentArtsRuntimeApp()

        def handler(payload, other):
            pass

        assert app._task_context(handler) is False


class TestSerialization:
    """Tests for serialization methods."""

    def test_safe_serialize_to_json_string_dict(self):
        """Test _safe_serialize_to_json_string with dict."""
        app = AgentArtsRuntimeApp()

        result = app._safe_serialize_to_json_string({"key": "value"})
        assert json.loads(result) == {"key": "value"}

    def test_safe_serialize_to_json_string_list(self):
        """Test _safe_serialize_to_json_string with list."""
        app = AgentArtsRuntimeApp()

        result = app._safe_serialize_to_json_string([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]

    def test_safe_serialize_to_json_string_with_datetime(self):
        """Test _safe_serialize_to_json_string with datetime object."""
        from datetime import datetime

        app = AgentArtsRuntimeApp()

        now = datetime(2024, 1, 1, 12, 0, 0)
        result = app._safe_serialize_to_json_string({"time": now})

        parsed = json.loads(result)
        assert "2024-01-01" in parsed["time"]

    def test_convert_to_sse(self):
        """Test _convert_to_sse formats SSE correctly."""
        app = AgentArtsRuntimeApp()

        result = app._convert_to_sse({"data": "test"})

        assert isinstance(result, bytes)
        assert result.startswith(b"data: ")
        assert result.endswith(b"\n\n")


class TestSyncStreamHandler:
    """Tests for _sync_stream_handler method."""

    def test_sync_stream_handler(self):
        """Test _sync_stream_handler yields SSE formatted data."""
        app = AgentArtsRuntimeApp()

        def generator():
            yield {"chunk": 1}
            yield {"chunk": 2}

        results = list(app._sync_stream_handler(generator()))

        assert len(results) == 2
        assert all(r.startswith(b"data: ") for r in results)
        assert all(r.endswith(b"\n\n") for r in results)

    def test_sync_stream_handler_with_exception(self):
        """Test _sync_stream_handler handles exceptions."""
        app = AgentArtsRuntimeApp()

        def failing_generator():
            yield {"chunk": 1}
            msg = "Generator error"
            raise RuntimeError(msg)

        results = list(app._sync_stream_handler(failing_generator()))

        assert len(results) == 2
        error_data = json.loads(results[1].decode("utf-8").replace("data: ", "").strip())
        assert "error" in error_data


class TestAsyncStreamHandler:
    """Tests for _async_stream_handler method."""

    @pytest.mark.asyncio
    async def test_async_stream_handler(self):
        """Test _async_stream_handler yields SSE formatted data."""
        app = AgentArtsRuntimeApp()

        async def async_generator():
            yield {"chunk": 1}
            yield {"chunk": 2}

        results = []
        async for chunk in app._async_stream_handler(async_generator()):
            results.append(chunk)

        assert len(results) == 2
        assert all(r.startswith(b"data: ") for r in results)

    @pytest.mark.asyncio
    async def test_async_stream_handler_with_exception(self):
        """Test _async_stream_handler handles exceptions."""
        app = AgentArtsRuntimeApp()

        async def failing_async_generator():
            yield {"chunk": 1}
            msg = "Async generator error"
            raise RuntimeError(msg)

        results = []
        async for chunk in app._async_stream_handler(failing_async_generator()):
            results.append(chunk)

        assert len(results) == 2
        error_data = json.loads(results[1].decode("utf-8").replace("data: ", "").strip())
        assert "error" in error_data


class TestHandleInvocation:
    """Tests for _handle_invocation endpoint."""

    @pytest.mark.asyncio
    async def test_handle_invocation_no_entrypoint(self):
        """Test _handle_invocation returns 404 when no entrypoint defined."""
        app = AgentArtsRuntimeApp()

        mock_request = MagicMock(spec=Request)
        mock_request.json = AsyncMock(return_value={"input": "test"})
        mock_request.headers = {}

        response = await app._handle_invocation(mock_request)

        assert response.status_code == 404
        assert json.loads(response.body) == {"error": "No entrypoint defined"}

    @pytest.mark.asyncio
    async def test_handle_invocation_success(self):
        """Test _handle_invocation with valid entrypoint."""
        app = AgentArtsRuntimeApp()

        @app.entrypoint
        def handler(payload):
            return {"result": payload["input"].upper()}

        mock_request = MagicMock(spec=Request)
        mock_request.json = AsyncMock(return_value={"input": "test"})
        mock_request.headers = {}

        response = await app._handle_invocation(mock_request)

        assert response.status_code == 200
        assert json.loads(response.body) == {"result": "TEST"}

    @pytest.mark.asyncio
    async def test_handle_invocation_async_handler(self):
        """Test _handle_invocation with async entrypoint."""
        app = AgentArtsRuntimeApp()

        @app.entrypoint
        async def async_handler(payload):
            return {"result": payload["input"] * 2}

        mock_request = MagicMock(spec=Request)
        mock_request.json = AsyncMock(return_value={"input": "ab"})
        mock_request.headers = {}

        response = await app._handle_invocation(mock_request)

        assert response.status_code == 200
        assert json.loads(response.body) == {"result": "abab"}

    @pytest.mark.asyncio
    async def test_handle_invocation_invalid_json(self):
        """Test _handle_invocation returns 400 for invalid JSON."""
        app = AgentArtsRuntimeApp()

        @app.entrypoint
        def handler(payload):
            return {"result": "ok"}

        mock_request = MagicMock(spec=Request)
        mock_request.json = AsyncMock(side_effect=json.JSONDecodeError("test", "test", 0))
        mock_request.headers = {}

        response = await app._handle_invocation(mock_request)

        assert response.status_code == 400
        body = json.loads(response.body)
        assert body["error"] == "Invalid JSON payload"

    @pytest.mark.asyncio
    async def test_handle_invocation_handler_exception(self):
        """Test _handle_invocation returns 500 for handler exception."""
        app = AgentArtsRuntimeApp()

        @app.entrypoint
        def failing_handler(payload):
            msg = "Handler error"
            raise ValueError(msg)

        mock_request = MagicMock(spec=Request)
        mock_request.json = AsyncMock(return_value={"input": "test"})
        mock_request.headers = {}

        response = await app._handle_invocation(mock_request)

        assert response.status_code == 500
        body = json.loads(response.body)
        assert body["error"] == "ValueError"


class TestHandlePing:
    """Tests for _handle_ping endpoint."""

    @pytest.mark.asyncio
    async def test_handle_ping_default_healthy(self):
        """Test _handle_ping returns healthy status by default."""
        app = AgentArtsRuntimeApp()

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        response = await app._handle_ping(mock_request)

        assert response.status_code == 200
        body = json.loads(response.body)
        assert body["status"] == "Healthy"

    @pytest.mark.asyncio
    async def test_handle_ping_with_custom_handler(self):
        """Test _handle_ping uses custom ping handler."""
        app = AgentArtsRuntimeApp()

        @app.ping
        def custom_ping():
            return "HealthyBusy"

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        response = await app._handle_ping(mock_request)

        body = json.loads(response.body)
        assert body["status"] == "HealthyBusy"

    @pytest.mark.asyncio
    async def test_handle_ping_with_running_tasks(self):
        """Test _handle_ping returns HealthyBusy when tasks running."""
        app = AgentArtsRuntimeApp()
        app._add_task("running_task")

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        response = await app._handle_ping(mock_request)

        body = json.loads(response.body)
        assert body["status"] == "HealthyBusy"


class TestGetCurrentPingStatus:
    """Tests for get_current_ping_status method."""

    def test_get_current_ping_status_healthy(self):
        """Test get_current_ping_status returns HEALTHY by default."""
        app = AgentArtsRuntimeApp()

        status = app.get_current_ping_status()

        assert status == PingStatus.HEALTHY

    def test_get_current_ping_status_busy_with_tasks(self):
        """Test get_current_ping_status returns HEALTHY_BUSY with tasks."""
        app = AgentArtsRuntimeApp()
        app._add_task("test_task")

        status = app.get_current_ping_status()

        assert status == PingStatus.HEALTHY_BUSY

    def test_get_current_ping_status_forced(self):
        """Test get_current_ping_status respects forced status."""
        app = AgentArtsRuntimeApp()
        app.force_ping_status(PingStatus.UNHEALTHY)

        status = app.get_current_ping_status()

        assert status == PingStatus.UNHEALTHY


class TestForcePingStatus:
    """Tests for force_ping_status method."""

    def test_force_ping_status(self):
        """Test force_ping_status sets forced status."""
        app = AgentArtsRuntimeApp()

        app.force_ping_status(PingStatus.UNHEALTHY)

        assert app._force_ping_status == PingStatus.UNHEALTHY
        assert app.get_current_ping_status() == PingStatus.UNHEALTHY

    def test_force_ping_status_overrides_tasks(self):
        """Test forced status overrides task status."""
        app = AgentArtsRuntimeApp()
        app._add_task("test_task")

        app.force_ping_status(PingStatus.HEALTHY)

        assert app.get_current_ping_status() == PingStatus.HEALTHY


class TestHandleWebsocket:
    """Tests for _handle_websocket endpoint."""

    @pytest.mark.asyncio
    async def test_handle_websocket_no_handler(self):
        """Test _handle_websocket closes connection when no handler."""
        app = AgentArtsRuntimeApp()

        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {}
        mock_websocket.close = AsyncMock()

        await app._handle_websocket(mock_websocket)

        mock_websocket.close.assert_called_once_with(code=1011)

    @pytest.mark.asyncio
    async def test_handle_websocket_with_handler(self):
        """Test _handle_websocket calls registered handler."""
        app = AgentArtsRuntimeApp()

        @app.websocket
        async def ws_handler(websocket, context):
            await websocket.accept()
            await websocket.close()

        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {}
        mock_websocket.accept = AsyncMock()
        mock_websocket.close = AsyncMock()

        await app._handle_websocket(mock_websocket)

        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_websocket_disconnect(self):
        """Test _handle_websocket handles WebSocketDisconnect."""
        app = AgentArtsRuntimeApp()

        @app.websocket
        async def disconnecting_handler(websocket, context):
            raise WebSocketDisconnect

        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.headers = {}

        await app._handle_websocket(mock_websocket)


class TestRun:
    """Tests for run method."""

    def test_run_default_host(self):
        """Test run uses default host."""
        app = AgentArtsRuntimeApp()

        with patch("uvicorn.run") as mock_run:
            app.run()
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["host"] == "127.0.0.1"
            assert call_kwargs["port"] == 8080

    def test_run_custom_host_port(self):
        """Test run uses custom host and port."""
        app = AgentArtsRuntimeApp()

        with patch("uvicorn.run") as mock_run:
            app.run(host="0.0.0.0", port=9000)
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["host"] == "0.0.0.0"
            assert call_kwargs["port"] == 9000

    def test_run_docker_environment(self):
        """Test run uses 0.0.0.0 in Docker environment."""
        app = AgentArtsRuntimeApp()

        with patch("os.path.exists", return_value=True), patch("uvicorn.run") as mock_run:
            app.run()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["host"] == "0.0.0.0"


class TestInvokeHandler:
    """Tests for _invoke_handler method."""

    @pytest.mark.asyncio
    async def test_invoke_handler_sync_function(self):
        """Test _invoke_handler with sync function."""
        app = AgentArtsRuntimeApp()

        def sync_handler(payload):
            return {"result": payload["input"]}

        context = RequestContext(session_id="test", request_id="req-1", request=None)
        result = await app._invoke_handler(sync_handler, context, False, {"input": "test"})

        assert result == {"result": "test"}

    @pytest.mark.asyncio
    async def test_invoke_handler_async_function(self):
        """Test _invoke_handler with async function."""
        app = AgentArtsRuntimeApp()

        async def async_handler(payload):
            return {"result": payload["input"]}

        context = RequestContext(session_id="test", request_id="req-1", request=None)
        result = await app._invoke_handler(async_handler, context, False, {"input": "async"})

        assert result == {"result": "async"}

    @pytest.mark.asyncio
    async def test_invoke_handler_with_context(self):
        """Test _invoke_handler passes context when required."""
        app = AgentArtsRuntimeApp()

        def handler_with_context(payload, context):
            return {"session": context.session_id}

        context = RequestContext(session_id="session-123", request_id="req-1", request=None)
        result = await app._invoke_handler(handler_with_context, context, True, {})

        assert result == {"session": "session-123"}

    @pytest.mark.asyncio
    async def test_invoke_handler_exception(self):
        """Test _invoke_handler propagates exceptions."""
        app = AgentArtsRuntimeApp()

        def failing_handler(payload):
            msg = "Handler failed"
            raise RuntimeError(msg)

        context = RequestContext(session_id="test", request_id="req-1", request=None)

        with pytest.raises(RuntimeError, match="Handler failed"):
            await app._invoke_handler(failing_handler, context, False, {})
