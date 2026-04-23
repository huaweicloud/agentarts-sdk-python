"""
AgentArts Runtime Application

Provides the core HTTP/WebSocket server that wraps user-defined agent
entrypoints and exposes them through a standardised API surface
compatible with the Huawei Cloud AgentArts control plane.

Endpoints
---------
- ``POST /invocations``  – invoke the agent entrypoint
- ``GET  /ping``          – health-check / liveness probe
- ``WS   /ws``            – bidirectional streaming communication

The application uses :mod:`starlette` as the ASGI framework so that it
can run under any ASGI server (uvicorn, hypercorn, etc.) without
pulling in the full FastAPI dependency at runtime.
"""

from __future__ import annotations

import asyncio
import contextvars
import inspect
import json
import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
)

from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route, WebSocket, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from .context import AgentArtsRuntimeContext, RequestContext
from .model import ACCESS_TOKEN_HEADER, SESSION_HEADER, USER_ID_HEADER, PingStatus

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Generator, Sequence

    from starlette.middleware import Middleware
    from starlette.requests import Request
    from starlette.types import Lifespan

log = logging.getLogger(__name__)


class AgentArtsRuntimeApp(Starlette):
    """
    ASGI application that hosts an agent entrypoint behind a standardised
    HTTP / WebSocket interface.

    Usage::

        app = AgentArtsRuntimeApp()

        @app.entrypoint
        def my_handler(payload: dict):
            return {"result": payload["input"].upper()}

        @app.ping
        def health_check():
            return {"status": "ok"}

        @app.websocket
        async def ws_handler(websocket: WebSocket):
            await websocket.accept()
            while True:
                data = await websocket.receive_json()
                await websocket.send_json({"echo": data})
    """

    def __init__(
        self,
        debug: bool = False,
        lifespan: Lifespan | None = None,
        middleware: Sequence[Middleware] | None = None,
        protocol: Literal["http", "https"] = "http",
        max_concurrency: int = 15,
    ) -> None:
        self.handlers: dict[str, Callable] = {}
        self._ping_handler: Callable | None = None
        self._ws_handler: Callable | None = None
        self._last_status_update_time: float = time.time()
        self._force_ping_status: PingStatus | None = None
        self._active_tasks: dict[int, dict[str, Any]] = {}
        self._task_counter_lock :threading.Lock = threading.Lock()
        self._invocation_semaphore = asyncio.Semaphore(max_concurrency)
        self._invocation_executor = ThreadPoolExecutor(
            max_workers=max_concurrency, thread_name_prefix="invocation"
        )
        self.protocol = protocol
        self.logger = logging.getLogger("agentarts.runtime.app")

        routes = [
            Route("/invocations", self._handle_invocation, methods=["POST"]),
            Route("/ping", self._handle_ping, methods=["GET"]),
            WebSocketRoute("/ws", self._handle_websocket),
        ]
        super().__init__(
            debug=debug, lifespan=lifespan, middleware=middleware, routes=routes
        )

    # ------------------------------------------------------------------
    # Decorators
    # ------------------------------------------------------------------

    def entrypoint(self, func: Callable) -> Callable:
        """Register *func* as the main agent invocation handler."""
        self.handlers["main"] = func
        func.run = self.run
        return func

    def ping(self, func: Callable) -> Callable:
        """Register *func* as the health-check handler."""
        self._ping_handler = func
        return func

    def websocket(self, func: Callable) -> Callable:
        """Register *func* as the WebSocket handler."""
        self._ws_handler = func
        return func

    def async_task(self, func: Callable) -> Callable:
        """
        Register *func* as an async task handler.

        The decorated function will be tracked in ``_active_tasks`` during
        execution. When the task starts, it is registered; when it completes
        (successfully or with error), it is removed from the registry.

        Example::

            @app.async_task
            async def background_job(payload: dict):
                await asyncio.sleep(10)
                return {"result": "completed"}

        Use :meth:`has_running_tasks` to check if any async tasks are
        currently executing.

        Args:
            func: An async function to register as a background task.

        Returns:
            The wrapped function that tracks task execution.
        """
        if not asyncio.iscoroutinefunction(func):
            msg = "async_task decorator must be used with async functions"
            raise ValueError(
                msg
            )

        async def wrapper(*args, **kwargs):
            task_id = self._add_task(func.__name__)
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                self.logger.exception("Async task %s (ID: %s) error: %s", func.__name__, task_id, e)
                raise
            finally:
                self._complete_task(task_id)

        wrapper._is_async_task = True
        wrapper._original_func = func
        wrapper.__name__ = func.__name__
        return wrapper

    def _add_task(self, name: str, metadata: dict[str, Any] | None = None) -> int:
        """
        Register a new task in the active tasks registry.

        Args:
            metadata: Optional metadata to attach to the task.

        Returns:
            The generated task ID.
        """
        with self._task_counter_lock:
            task_id = hash(str(uuid.uuid4()))
            task_info = {
                "task_id": task_id,
                "name": name,
                "start_time": time.time(),
                "metadata": metadata,
            }
            self._active_tasks[task_id] = task_info
        self.logger.debug("Async task start: %s(ID: %s)", name, task_id)
        return task_id

    def _complete_task(self, task_id: int) -> bool:
        """
        Remove a task from the active tasks registry.

        Args:
            task_id: The ID of the task to remove.

        Returns:
            True if the task was found and removed, False otherwise.
        """
        with self._task_counter_lock:
            removed = self._active_tasks.pop(task_id, None)
            if removed:
                name = removed.get("name", "unknown")
                duration = time.time() - removed.get("start_time", time.time())
                self.logger.debug("Async task completed: %s(ID: %s, duration: %.3fs)", name, task_id, duration)
                return True
            self.logger.warning("Async task not found in registry: %s", task_id)
            return False
    def has_running_tasks(self) -> bool:
        """
        Check if there are any async tasks currently running.

        Returns:
            True if there is at least one task in the registry,
            False otherwise.
        """
        return len(self._active_tasks) > 0

    # ------------------------------------------------------------------
    # Request context helpers
    # ------------------------------------------------------------------

    def _build_request_context(self, request: Request | WebSocket) -> RequestContext:
        """
        Extract authentication and session headers from the incoming
        request or websocket and populate :class:`AgentArtsRuntimeContext`.

        Args:
            request: Either an HTTP Request or WebSocket connection.
        """
        workload_access_token = request.headers.get(
            ACCESS_TOKEN_HEADER
        ) or request.headers.get(ACCESS_TOKEN_HEADER.lower())
        if workload_access_token:
            AgentArtsRuntimeContext.set_workload_access_token(workload_access_token)

        session_id = request.headers.get(SESSION_HEADER) or request.headers.get(
            SESSION_HEADER.lower()
        )
        if session_id:
            AgentArtsRuntimeContext.set_session_id(session_id)

        user_id = request.headers.get(USER_ID_HEADER) or request.headers.get(
            USER_ID_HEADER.lower()
        )
        if user_id:
            AgentArtsRuntimeContext.set_user_id(user_id)

        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        AgentArtsRuntimeContext.set_request_id(request_id)

        return RequestContext(
            session_id=session_id,
            request_id=request_id,
            request=request,
        )

    def _task_context(self, handler: Callable) -> bool:
        """
        Return ``True`` if *handler* accepts a ``context`` as its
        second positional parameter.
        """
        try:
            params = list(inspect.signature(handler).parameters.keys())
            return len(params) >= 2 and params[1] == "context"
        except Exception:
            return False

    def _ping_task_context(self, handler: Callable) -> bool:
        """
        Return ``True`` if *handler* accepts a ``context`` as its
        first positional parameter.
        """
        try:
            params = list(inspect.signature(handler).parameters.keys())
            return len(params) >= 1 and params[0] == "context"
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Invocation endpoint
    # ------------------------------------------------------------------

    async def _handle_invocation(self, request: Request) -> Response:
        start_time = time.time()

        try:
            payload = await request.json()
            self.logger.debug("Processing invocation request")

            handler = self.handlers.get("main")
            if not handler:
                return JSONResponse(
                    status_code=404, content={"error": "No entrypoint defined"}
                )

            request_context = self._build_request_context(request)
            task_context = self._task_context(handler)
            handler_name = (
                handler.__name__ if hasattr(handler, "__name__") else "unknown"
            )
            self.logger.debug("Invoking handler %s", handler_name)

            result = await self._invoke_handler(
                handler, request_context, task_context, payload
            )
            duration = time.time() - start_time

            if isinstance(result, (StreamingResponse, JSONResponse, Response)):
                self.logger.debug(
                    "Returning predefined response type %s", type(result).__name__
                )
                return result

            if inspect.isgenerator(result):
                self.logger.info(
                    "Returning streaming response (generator) (%.3f s)", duration
                )
                return StreamingResponse(
                    self._sync_stream_handler(result),
                    media_type="text/event-stream",
                )

            if inspect.isasyncgen(result):
                self.logger.info(
                    "Returning streaming response (async generator) (%.3f s)", duration
                )
                return StreamingResponse(
                    self._async_stream_handler(result),
                    media_type="text/event-stream",
                )

            self.logger.info("Invocation completed (%.3f s)", duration)
            safe_json_string = self._safe_serialize_to_json_string(result)
            return Response(
                status_code=200,
                content=safe_json_string,
                headers={SESSION_HEADER: request_context.session_id or ""},
                media_type="application/json",
            )
        except json.JSONDecodeError as exc:
            duration = time.time() - start_time
            self.logger.warning(
                "Invalid JSON payload after %.3f s: %s",
                duration,
                str(exc),
            )
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid JSON payload", "message": str(exc)},
            )
        except Exception as exc:
            duration = time.time() - start_time
            self.logger.exception(
                "Invocation failed after %.3f s: %s: %s",
                duration,
                type(exc).__name__,
                exc,
            )
            return JSONResponse(
                status_code=500,
                content={"error": type(exc).__name__, "message": str(exc)},
            )

    async def _invoke_handler(
        self,
        handler: Callable,
        request_context: RequestContext,
        task_context: bool,
        payload: Any,
    ) -> Any:
        """
        Execute *handler* inside the concurrency semaphore.

        If the semaphore is already at capacity a ``503 Service Busy``
        response is returned immediately.
        """
        if self._invocation_semaphore.locked():
            return JSONResponse(
                status_code=503,
                content={"error": "Service busy - maximum concurrency reached"},
            )

        async with self._invocation_semaphore:
            try:
                args = (payload, request_context) if task_context else (payload,)
                if asyncio.iscoroutinefunction(handler):
                    return await handler(*args)
                loop = asyncio.get_event_loop()
                ctx = contextvars.copy_context()
                return await loop.run_in_executor(
                    self._invocation_executor, lambda: ctx.run(handler, *args)
                )
            except Exception as exc:
                handler_name = getattr(handler, "__name__", "unknown")
                self.logger.exception(
                    "Handler '%s' execution failed: %s: %s",
                    handler_name,
                    type(exc).__name__,
                    exc,
                )
                raise

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _safe_serialize_to_json_string(self, obj: Any) -> str:
        """
        Serialize *obj* to a JSON string, falling back gracefully for
        types that are not JSON-serialisable by default.

        The fallback strategy converts the object to ``str`` so that the
        response is always valid JSON and never causes a 500 error due
        to serialisation failures.
        """
        try:
            return json.dumps(obj, ensure_ascii=False, default=str)
        except (TypeError, ValueError, UnicodeEncodeError):
            try:
                return json.dumps(str(obj), ensure_ascii=False)
            except Exception as exc:
                self.logger.exception(
                    "JSON serialization failed, falling back to str: %s: %s",
                    exc,
                    type(exc).__name__,
                )
                return json.dumps({"error": "Serialization failed", "message": str(exc)}, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Stream generators
    # ------------------------------------------------------------------

    def _sync_stream_handler(
        self, gen: Generator
    ) -> Generator[str, None, None]:
        """
        Wrap a synchronous generator into an SSE (Server-Sent Events)
        byte stream.

        Each yielded value is formatted as an SSE ``data:`` line so
        that clients can consume the response with an ``EventSource``
        or equivalent.
        """
        try:
            for chunk in gen:
                yield self._convert_to_sse(chunk)
        except Exception as exc:
            self.logger.exception("Sync stream error: %s: %s", type(exc).__name__, exc)
            error_data = {
                "error": str(exc),
                "error_type": type(exc).__name__,
                "message": "Error occurred during sync stream generation",
            }
            yield self._convert_to_sse(error_data)

    async def _async_stream_handler(
        self, agen: AsyncGenerator
    ) -> AsyncGenerator[str, None]:
        """
        Wrap an asynchronous generator into an SSE byte stream.

        Behaves identically to :meth:`_sync_stream_handler` but
        iterates with ``async for`` instead of a plain ``for`` loop.
        """
        try:
            async for chunk in agen:
                yield self._convert_to_sse(chunk)
        except Exception as exc:
            self.logger.exception("Async stream error: %s: %s", type(exc).__name__, exc)
            error_data = {
                "error": str(exc),
                "error_type": type(exc).__name__,
                "message": "Error occurred during async stream generation",
            }
            yield self._convert_to_sse(error_data)

    def _convert_to_sse(self, obj) -> bytes:
        """Convert an object to SSE-formatted bytes."""
        json_str = self._safe_serialize_to_json_string(obj)
        sse_data = f"data: {json_str}\n\n"
        return sse_data.encode("utf-8")

    # ------------------------------------------------------------------
    # Ping / health-check endpoint
    # ------------------------------------------------------------------

    async def _handle_ping(self, request: Request) -> Response:
        """
        Respond to liveness / readiness probes.

        If a custom ``@app.ping`` handler is registered it will be
        called; otherwise a default ``{"status": "healthy"}`` response
        is returned.
        """
        try:
            request_context = self._build_request_context(request)
            status = self.get_current_ping_status(request_context)
            self.logger.debug(f"Ping request - status: {status}")
            return JSONResponse(
                content={
                    "status": status.value,
                    "time_of_last_update": int(self._last_status_update_time),
                },
            )
        except Exception as exc:
            self.logger.exception("Ping handler failed: %s: %s", type(exc).__name__, exc)
            return JSONResponse(
                content={
                    "status": PingStatus.UNHEALTHY.value,
                    "time_of_last_update": int(self._last_status_update_time),
                },
            )

    def get_current_ping_status(self, request_context: RequestContext | None = None) -> PingStatus:
        """
        Get the current status of the AgentArts runtime.

        Args:
            request_context: Optional request context to pass to the ping handler.

        Returns:
            PingStatus: The current health status of the runtime.
        """
        current_status = None

        if self._force_ping_status is not None:
            current_status = self._force_ping_status

        if self._ping_handler is not None:
            try:
                task_context = self._ping_task_context(self._ping_handler)
                args = (request_context,) if task_context and request_context else ()
                result = self._ping_handler(*args)
                current_status = PingStatus(result) if isinstance(result, str) else result
            except Exception as exc:
                self.logger.warning("Custom Ping handler failed: %s: %s", type(exc).__name__, exc)

        if current_status is None:
            if self.has_running_tasks():
                current_status = PingStatus.HEALTHY_BUSY
            else:
                current_status = PingStatus.HEALTHY

        if not hasattr(self, "_last_known_status") or self._last_known_status != current_status:
            self._last_known_status = current_status
            self._last_status_update_time = time.time()

        return current_status

    def force_ping_status(self, status: PingStatus) -> None:
        """
        Force a specific ping status.

        This can be used for graceful shutdown or maintenance mode.

        Args:
            status: The status to force.
        """
        self._force_ping_status = status
        self._last_status_update_time = time.time()
        self._last_known_status = status

    # ------------------------------------------------------------------
    # WebSocket endpoint
    # ------------------------------------------------------------------

    async def _handle_websocket(self, websocket: WebSocket) -> None:
        """
        Handle an incoming WebSocket connection.

        If a custom ``@app.websocket`` handler is registered it receives
        the raw :class:`~starlette.websockets.WebSocket` object and is
        responsible for the full connection lifecycle (accept, receive,
        send, close).

        If no custom handler is registered a default echo handler is
        used that echoes every incoming message back to the client as
        JSON ``{"echo": <message>}``.
        """
        request_context = self._build_request_context(websocket)
        try:
            handler = self._ws_handler
            if not handler:
                self.logger.error("No WebSocket handler registered. Default echo handler used.")
                await websocket.close(code=1011)
                return
            self.logger.debug("WebSocket connection accepted")
            await handler(websocket, request_context)
        except WebSocketDisconnect:
            self.logger.debug("WebSocket connection closed")
        except Exception as exc:
            self.logger.exception(
                "WebSocket handler failed: %s: %s", type(exc).__name__, exc
            )
            try:
                await websocket.close(code=1011)
            except Exception:
                self.logger.exception(
                    "WebSocket connection close failed: %s: %s", type(exc).__name__, exc
                )

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def run(self, host: str | None = None, port: int = 8080, **kwargs: Any) -> None:
        """
        Start the ASGI server (uvicorn) in a blocking call.

        This is attached to the entrypoint function via
        :meth:`entrypoint` so that users can do::

            @app.entrypoint
            def handler(payload):
                ...

            handler.run(host="0.0.0.0", port=8080)

        Args:
            host: Bind address. Defaults to eth0 IP in Docker environment,
                or ``"127.0.0.1"`` in local development.
                Can be overridden via ``AGENTARTS_BIND_IP`` environment variable.
            port: Bind port. Defaults to ``8080``.
            **kwargs: Additional keyword arguments forwarded to
                ``uvicorn.run`` (e.g. ``workers``, ``log_level``).
        """
        import subprocess

        import uvicorn

        if host is None:
            env_bind_ip = os.getenv("AGENTARTS_BIND_IP")
            if env_bind_ip:
                host = env_bind_ip
            elif os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER"):
                try:
                    result = subprocess.run(
                        "ip addr show eth0 | grep -oP 'inet \\K[\\d.]+'",
                        shell=True,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    ip = result.stdout.strip()
                    if ip:
                        host = ip
                    else:
                        host = "0.0.0.0"
                except Exception:
                    host = "0.0.0.0"
            else:
                host = "127.0.0.1"

        self.logger.info(
            "Starting AgentArts runtime on %s:%s (%s)", host, port, self.protocol
        )
        uvicorn.run(self, host=host, port=port, **kwargs)
