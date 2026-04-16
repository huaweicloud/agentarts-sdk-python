"""
AgentArts Runtime Client

Provides a high-level client for interacting with the AgentArts control
plane and data plane APIs.

The client is divided into two logical groups:

- **Control Plane** – agent and endpoint lifecycle management
  (create, update, delete, query agents and endpoints).

- **Data Plane** – runtime invocation (invoke an agent, health-check).

Usage::

    from agentarts.sdk.service import RuntimeClient

    client = RuntimeClient()

    # Control plane
    agent = client.create_agent(name="my-agent", description="A test agent")
    agents = client.get_agents()

    # Data plane
    result = client.invoke_agent(agent_id="xxx", payload={"input": "hello"})
    health = client.ping_agent(agent_id="xxx")

    # Local runtime
    local_client = LocalRuntimeClient(port=8080)
    result = local_client.invoke_agent(payload={"input": "hello"})
    health = local_client.ping_agent()
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from agentarts.sdk.service.http_client import BaseHTTPClient, RequestConfig, RequestResult, SignMode
from agentarts.sdk.utils.constant import (
    get_control_plane_endpoint,
    get_runtime_data_plane_endpoint,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

log = logging.getLogger(__name__)


class RuntimeClient:
    """
    Client for the AgentArts runtime service.

    Provides typed methods for every control-plane and data-plane API
    exposed by the AgentArts platform. Uses separate HTTP clients for
    control and data planes to ensure thread-safety in concurrent scenarios.

    Args:
        control_endpoint: Override the control plane base URL.
            If ``None``, the URL is derived from environment variables
            via :func:`~agentarts.sdk.utils.constant.get_control_plane_endpoint`.
        data_endpoint: Override the data plane base URL.
            If ``None``, the URL is derived from environment variables
            via :func:`~agentarts.sdk.utils.constant.get_runtime_data_plane_endpoint`.
        access_token: Bearer token for API authentication.
            Can also be set later via :meth:`set_auth_token`.
        timeout: Default request timeout in seconds.
        verify_ssl: Whether to verify SSL certificates.
        sign_mode: Signature mode for data plane requests (SDK_HMAC_SHA256 or V11_HMAC_SHA256).
        region_id: Region ID for V11 signature mode.
    """

    def __init__(
        self,
        control_endpoint: str | None = None,
        data_endpoint: str | None = None,
        access_token: str | None = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        sign_mode: SignMode = SignMode.SDK_HMAC_SHA256,
        region_id: str = "",
    ) -> None:
        self._control_base = control_endpoint or get_control_plane_endpoint()
        self._data_base = data_endpoint or get_runtime_data_plane_endpoint()
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._access_token = access_token
        self._sign_mode = sign_mode
        self._region_id = region_id

        self._control_client = BaseHTTPClient(RequestConfig(
            base_url=self._control_base,
            timeout=timeout,
            verify_ssl=verify_ssl,
        ), open_ak_sk=True)

        self._data_client = BaseHTTPClient(RequestConfig(
            base_url=self._data_base,
            timeout=timeout,
            verify_ssl=verify_ssl,
        ), open_ak_sk=(sign_mode == SignMode.V11_HMAC_SHA256), sign_mode=sign_mode, region_id=region_id)

        if access_token:
            self.set_auth_token(access_token)

    def set_auth_token(self, token: str) -> None:
        """Set the Bearer token for authentication."""
        self._access_token = token
        self._data_client.set_auth_token(token)

    def _control(self, method: str, path: str, **kwargs: Any) -> RequestResult:
        """Send a request to the control plane."""
        return self._control_client._request(method, path, **kwargs)

    def _data(self, method: str, path: str, **kwargs: Any) -> RequestResult:
        """Send a request to the data plane."""
        return self._data_client._request(method, path, **kwargs)

    @staticmethod
    def _check(result: RequestResult, operation: str) -> dict[str, Any]:
        """Raise on unsuccessful response and return parsed data."""
        if not result.success:
            log.error(
                "%s failed: status=%s, data=%s, error=%s",
                operation,
                result.status_code,
                result.data,
                result.error,
            )
            msg = f"{operation} failed (HTTP {result.status_code}): {result.error}"
            raise RuntimeError(
                msg
            )
        return result.data if isinstance(result.data, dict) else {}

    @staticmethod
    def _is_stream_response(result: RequestResult) -> bool:
        """Check if the response Content-Type is text/event-stream."""
        content_type = result.headers.get("Content-Type", "")
        return "text/event-stream" in content_type

    def _dispatch_response(
        self, result: RequestResult, operation: str
    ) -> dict[str, Any] | Iterator[str]:
        """
        Dispatch response based on streaming state.

        When ``result.streaming`` is ``True`` the Content-Type header is
        inspected:

        - ``text/event-stream`` → returns an ``Iterator[str]`` that yields
          one decoded SSE event payload per iteration.
        - Other content types → the body is fully consumed, the response
          is closed, and a parsed JSON ``dict`` is returned.

        For non-streaming results the existing ``result.data`` is returned
        directly (parsed as JSON when possible).
        """
        if not result.success:
            log.error(
                "%s failed: status=%s, data=%s error=%s",
                operation,
                result.status_code,
                result.data,
                result.error,
            )
            msg = f"{operation} failed (HTTP {result.status_code}): {result.error}"
            raise RuntimeError(
                msg
            )

        if result.streaming:
            if self._is_stream_response(result):
                return self._parse_sse_stream(result.iter_lines())

            body = b"".join(result.iter_bytes())
            result.close()
            try:
                return json.loads(body)
            except (json.JSONDecodeError, ValueError):
                return {"raw": body.decode("utf-8", errors="replace")}

        data = result.data
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            try:
                return json.loads(data)
            except (json.JSONDecodeError, ValueError):
                return {"raw": data}
        return {"data": data}

    @staticmethod
    def _parse_sse_stream(line_iterator: Iterator[str]) -> Iterator[str]:
        """
        Parse decoded text lines into SSE event payloads.

        Each yielded value is the content of a single ``data:`` line
        (without the ``data: `` prefix).

        The underlying streaming response is automatically closed after
        the iterator is exhausted (handled by ``RequestResult.iter_lines``).
        """
        buffer = ""
        for line in line_iterator:
            if line == "":
                if buffer:
                    for event_line in buffer.splitlines():
                        if event_line.startswith("data: "):
                            payload = event_line[6:]
                            if payload.strip() == "[DONE]":
                                return
                            yield payload
                    buffer = ""
            else:
                if buffer:
                    buffer += "\n"
                buffer += line

    def create_agent(
        self,
        name: str,
        description: str = "",
        artifact_source_config: dict | None = None,
        env_vars: list[dict] | None = None,
        identity_config: dict | None = None,
        execution_agency_name: str | None = None,
        network_config: dict | None = None,
        agent_gateway_id: str | None = None,
        invoke_config: dict | None = None,
        observability_config: dict | None = None,
        tags_config: list[dict] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """
        Create a new agent.

        Args:
            name: Agent name (unique within the workspace).
            description: Human-readable description.
            artifact_source_config: Configuration for the agent's artifact source.
            env_vars: Environment variables as list of {"key": "K", "value": "V"} dicts.
            identity_config: Identity and authentication configuration.
            execution_agency_name: Name of the execution agency.
            network_config: Network access configuration.
            agent_gateway_id: ID of the agent gateway to attach.
            invoke_config: Invocation-related configuration.
            observability_config: Observability (tracing, metrics) configuration.
            tags_config: Tags as list of {"key": "K", "value": "V"} dicts.
            **extra: Additional fields forwarded to the API.

        Returns:
            The created agent object from the API.
        """
        payload: dict[str, Any] = {"name": name, **extra}
        if description:
            payload["description"] = description
        if artifact_source_config is not None:
            payload["artifact_source"] = artifact_source_config
        if env_vars is not None:
            payload["environment_variables"] = env_vars
        if identity_config is not None:
            payload["identity_configuration"] = identity_config
        if execution_agency_name is not None:
            payload["execution_agency_name"] = execution_agency_name
        if network_config is not None:
            payload["network_config"] = network_config
        if agent_gateway_id is not None:
            payload["agent_gateway_id"] = agent_gateway_id
        if invoke_config is not None:
            payload["invoke_config"] = invoke_config
        if observability_config is not None:
            payload["observability"] = observability_config
        if tags_config is not None:
            payload["tags"] = tags_config

        result = self._control("POST", "/v1/core/runtimes", json=payload)
        return self._check(result, "create_agent")

    def update_agent(
        self,
        agent_id: str,
        description: str = "",
        artifact_source_config: dict | None = None,
        env_vars: list[dict] | None = None,
        execution_agency_name: str | None = None,
        network_config: dict | None = None,
        agent_gateway_id: str | None = None,
        invoke_config: dict | None = None,
        observability_config: dict | None = None,
        tags_config: list[dict] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """
        Update an existing agent.

        Args:
            agent_id: The unique agent identifier.
            description: New description (omit to keep unchanged).
            artifact_source_config: Configuration for the agent's artifact source.
            env_vars: Environment variables as list of {"key": "K", "value": "V"} dicts.
            execution_agency_name: Name of the execution agency.
            network_config: Network access configuration.
            agent_gateway_id: ID of the agent gateway to attach.
            invoke_config: Invocation-related configuration.
            observability_config: Observability (tracing, metrics) configuration.
            tags_config: Tags as list of {"key": "K", "value": "V"} dicts.
            **extra: Additional fields forwarded to the API.

        Returns:
            The updated agent object.
        """
        payload: dict[str, Any] = {**extra}
        if description is not None:
            payload["description"] = description
        if artifact_source_config is not None:
            payload["artifact_source"] = artifact_source_config
        if env_vars is not None:
            payload["environment_variables"] = env_vars
        if execution_agency_name is not None:
            payload["execution_agency_name"] = execution_agency_name
        if network_config is not None:
            payload["network_config"] = network_config
        if agent_gateway_id is not None:
            payload["agent_gateway_id"] = agent_gateway_id
        if invoke_config is not None:
            payload["invoke_config"] = invoke_config
        if observability_config is not None:
            payload["observability"] = observability_config
        if tags_config is not None:
            payload["tags"] = tags_config

        result = self._control("PUT", f"/v1/core/runtimes/{agent_id}", json=payload)
        return self._check(result, "update_agent")

    def create_or_update_agent(
        self,
        agent_name: str,
        description: str = "",
        artifact_source_config: dict | None = None,
        env_vars: list[dict] | None = None,
        identity_config: dict | None = None,
        execution_agency_name: str | None = None,
        network_config: dict | None = None,
        agent_gateway_id: str | None = None,
        invoke_config: dict | None = None,
        observability_config: dict | None = None,
        tags_config: list[dict] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """
        Create or update an agent (upsert semantics).

        Queries the agent by *agent_name* first.  If an agent with that
        name already exists it will be updated via ``PUT``; otherwise a
        new agent is created via ``POST``.

        Args:
            agent_name: Agent name (used as the lookup key).
            description: Human-readable description.
            artifact_source_config: Configuration for the agent's artifact source.
            env_vars: Environment variables as list of {"key": "K", "value": "V"} dicts.
            identity_config: Identity and authentication configuration.
            execution_agency_name: Name of the execution agency.
            network_config: Network access configuration.
            agent_gateway_id: ID of the agent gateway to attach.
            invoke_config: Invocation-related configuration.
            observability_config: Observability (tracing, metrics) configuration.
            tags_config: Tags as list of {"key": "K", "value": "V"} dicts.
            **extra: Additional fields forwarded to the API.

        Returns:
            The agent object from the API.
        """

        existing = self.find_agent_by_name(agent_name)

        if existing:
            agent_id = existing.get("id")
            log.info("Agent '%s' found (ID: %s), updating", agent_name, agent_id)
            return self.update_agent(
                agent_id=agent_id,
                description=description,
                artifact_source_config=artifact_source_config,
                env_vars=env_vars,
                execution_agency_name=execution_agency_name,
                network_config=network_config,
                agent_gateway_id=agent_gateway_id,
                invoke_config=invoke_config,
                observability_config=observability_config,
                tags_config=tags_config,
                **extra,
            )

        log.debug("Agent '%s' not found, creating", agent_name)
        return self.create_agent(
            name=agent_name,
            description=description,
            artifact_source_config=artifact_source_config,
            env_vars=env_vars,
            identity_config=identity_config,
            execution_agency_name=execution_agency_name,
            network_config=network_config,
            agent_gateway_id=agent_gateway_id,
            invoke_config=invoke_config,
            observability_config=observability_config,
            tags_config=tags_config,
            **extra,
        )

    def get_agents(
        self,
        agent_name: str = "",
        offset: int = 0,
        limit: int = 10,
        **extra: Any,
    ) -> list[dict[Any, Any]]:
        """
        List agents.

        Args:
            agent_name: Filter by agent name (fuzzy match).
            offset: Pagination offset.
            limit: Maximum number of results.
            **extra: Additional query parameters.

        Returns:
            A list of agent dicts.
        """
        params: dict[str, Any] = {"offset": offset, "limit": limit, **extra}
        if agent_name:
            params["agent_name"] = agent_name

        result = self._control("GET", "/v1/core/runtimes", params=params)
        data = self._check(result, "get_agents")
        if isinstance(data, dict):
            return data.get("items", data.get("agents", []))
        if isinstance(data, list):
            return data
        return []

    def find_agent_by_name(
        self,
        agent_name: str,
    ) -> dict[Any, Any] | None:
        """
        Find an agent by its name.

        Args:
            agent_name: Agent name to search for.

        Returns:
            The matching agent object, or raises if not found.
        """
        params: dict[str, Any] = {"name": agent_name, "match_type" : "EXACT"}

        result = self._control("GET", "/v1/core/runtimes", params=params)
        response_data = self._check(result, "find_agent_by_name")
        # Extract list from response
        agents = []
        if isinstance(response_data, dict):
            agents = response_data.get("items", [])
        elif isinstance(response_data, list):
            agents = response_data

        # Find matching agent by name
        for agent in agents:
            if isinstance(agent, dict) and agent.get("name") == agent_name:
                return agent
        return None

    def find_agent_by_id(self, agent_id: str) -> dict[Any, Any] | None:
        """
        Find an agent by its unique identifier.

        Args:
            agent_id: The agent ID.

        Returns:
            The agent object.
        """
        result = self._control("GET", f"/v1/core/runtimes/{agent_id}")
        return self._check(result, "find_agent_by_id")

    def delete_agent_by_name(
        self,
        agent_name: str,
    ) -> bool:
        """
        Delete an agent by its name.

        Args:
            agent_name: Agent name to delete.

        Returns:
            True if the agent was deleted successfully.
        """
        existing = self.find_agent_by_name(agent_name)
        agent_id = existing.get("id")
        if not agent_id:
            log.warning("Agent '%s' not found, nothing to delete", agent_name)
            return False

        result = self._control("DELETE", f"/v1/core/runtimes/{agent_id}")
        self._check(result, "delete_agent_by_name")
        return True

    def create_agent_endpoint(
        self,
        agent_id: str,
        endpoint_name: str,
        endpoint_type: str = "invocations",
        config: dict[str, Any] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """
        Create an endpoint for an agent.

        Args:
            agent_id: The agent to attach the endpoint to.
            endpoint_name: Endpoint name.
            endpoint_type: Type of endpoint (e.g. ``"invocations"``).
            config: Endpoint-specific configuration.
            **extra: Additional fields forwarded to the API.

        Returns:
            The created endpoint object.
        """
        payload: dict[str, Any] = {
            "agent_id": agent_id,
            "endpoint_name": endpoint_name,
            "endpoint_type": endpoint_type,
            **extra,
        }
        if config is not None:
            payload["config"] = config

        result = self._control(
            "POST", f"/v1/core/runtimes/{agent_id}/endpoints", json=payload
        )
        return self._check(result, "create_agent_endpoint")

    def update_agent_endpoint(
        self,
        agent_id: str,
        endpoint_name: str,
        config: dict[str, Any] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """
        Update an existing agent endpoint.

        Args:
            agent_id: The agent the endpoint belongs to.
            endpoint_name: Name of the endpoint to update.
            config: New endpoint configuration.
            **extra: Additional fields forwarded to the API.

        Returns:
            The updated endpoint object.
        """
        payload: dict[str, Any] = {"endpoint_name": endpoint_name, **extra}
        if config is not None:
            payload["config"] = config

        result = self._control(
            "PUT", f"/v1/core/runtimes/{agent_id}/endpoints/{endpoint_name}", json=payload
        )
        return self._check(result, "update_agent_endpoint")

    def delete_agent_endpoint(
        self,
        agent_id: str,
        endpoint_name: str,
    ) -> dict[str, Any]:
        """
        Delete an agent endpoint.

        Args:
            agent_id: The agent the endpoint belongs to.
            endpoint_name: Name of the endpoint to delete.

        Returns:
            The deletion response.
        """
        result = self._control(
            "DELETE", f"/v1/core/runtimes/{agent_id}/endpoints/{endpoint_name}"
        )
        return self._check(result, "delete_agent_endpoint")

    def find_agent_endpoint(
        self,
        agent_id: str,
        endpoint_name: str,
    ) -> dict[str, Any]:
        """
        Find an agent endpoint by name.

        Args:
            agent_id: The agent the endpoint belongs to.
            endpoint_name: Name of the endpoint.

        Returns:
            The endpoint object.
        """
        result = self._control(
            "GET", f"/v1/core/runtimes/{agent_id}/endpoints/{endpoint_name}"
        )
        return self._check(result, "find_agent_endpoint")

    def invoke_agent(
        self,
        agent_name: str,
        session_id: str,
        payload: str,
        bearer_token: str | None = None,
        endpoint: str | None = None,
        timeout: int = 900,
        **extra: Any,
    ) -> dict[str, Any] | Iterator[str]:
        """
        Invoke an agent on the data plane.

        If the server responds with ``Content-Type: text/event-stream``, the
        return value is an :term:`iterator` that yields one decoded SSE event
        string per iteration.  Otherwise a parsed JSON ``dict`` is returned.

        Args:
            agent_name: The agent to invoke.
            session_id: Session identifier for stateful agents,
                passed as the ``SESSION_HEADER`` header.
            payload: Input data for the agent (JSON string).
            bearer_token: Optional bearer token for ``Authorization`` header.
            endpoint: Optional endpoint name, appended as a query parameter
                ``?endpoint=xxx``.
            timeout: Request timeout in seconds.
            **extra: Additional fields merged into the request.

        Returns:
            A ``dict`` for JSON responses, or an ``Iterator[str]`` for
            SSE streaming responses.
        """
        from agentarts.sdk.runtime.model import SESSION_HEADER

        path = f"/agent/{agent_name}/invocations"
        params: dict[str, Any] = {}
        if endpoint:
            params["endpoint"] = endpoint

        headers: dict[str, str] = {
            SESSION_HEADER: session_id,
            "Content-Type": "application/json",
        }
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        result = self._data(
            "POST",
            path,
            data=payload,
            params=params if params else None,
            headers=headers,
            timeout=timeout,
        )

        return self._dispatch_response(result, "invoke_agent")

    def ping_agent(
        self,
        agent_name: str,
        bearer_token: str | None = None,
        endpoint: str | None = None,
        session_id: str | None = None,
        timeout: int = 900,
    ) -> dict[str, Any] | Iterator[str]:
        """
        Health-check an agent on the data plane.

        If the server responds with ``Content-Type: text/event-stream``, the
        return value is an :term:`iterator` that yields one decoded SSE event
        string per iteration.  Otherwise a parsed JSON ``dict`` is returned.

        Args:
            agent_name: The agent to ping.
            bearer_token: Optional bearer token for ``Authorization`` header.
            endpoint: Optional endpoint name, appended as a query parameter.
            session_id: Session identifier for stateful agents,
                passed as the ``SESSION_HEADER`` header.
            timeout: Request timeout in seconds.

        Returns:
            A ``dict`` with at least a ``status`` field (e.g. ``"Healthy"``),
            or an ``Iterator[str]`` for SSE streaming responses.
        """
        from agentarts.sdk.runtime.model import SESSION_HEADER

        headers: dict[str, str] = {}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        if session_id:
            headers[SESSION_HEADER] = session_id

        params: dict[str, Any] = {}
        if endpoint:
            params["endpoint"] = endpoint

        result = self._data(
            "GET",
            f"/agent/{agent_name}/ping",
            params=params if params else None,
            headers=headers if headers else None,
            timeout=timeout,
        )


        return self._dispatch_response(result, "ping_agent")


class LocalRuntimeClient(BaseHTTPClient):
    """
    Client for invoking local Docker container runtime.

    Provides methods to invoke and health-check agents running in
    local Docker containers.

    Args:
        port: Local port where the agent is running (default: 8080).
        host: Host address (default: localhost).
        timeout: Default request timeout in seconds.
    """

    def __init__(
        self,
        port: int = 8080,
        host: str = "localhost",
        timeout: float = 300.0,
    ) -> None:
        self._port = port
        self._host = host
        self._base_url = f"http://{host}:{port}"
        super().__init__(RequestConfig(base_url=self._base_url, timeout=timeout))

    def invoke_agent(
        self,
        payload: str,
        session_id: str | None = None,
        bearer_token: str | None = None,
        endpoint: str | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any] | Iterator[str]:
        """
        Invoke a local agent.

        Args:
            payload: Input data for the agent (JSON string).
            session_id: Session identifier for stateful agents.
            bearer_token: Optional bearer token for ``Authorization`` header.
            endpoint: Optional endpoint name.
            timeout: Request timeout in seconds.

        Returns:
            A ``dict`` for JSON responses, or an ``Iterator[str]`` for
            SSE streaming responses.
        """
        from agentarts.sdk.runtime.model import SESSION_HEADER

        path = "/invocations"
        params: dict[str, Any] = {}
        if endpoint:
            params["endpoint"] = endpoint

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if session_id:
            headers[SESSION_HEADER] = session_id
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        request_timeout = timeout or self._config.timeout

        result = self._request(
            "POST",
            path,
            data=payload,
            params=params if params else None,
            headers=headers,
            timeout=request_timeout,
        )

        if not result.success:
            if result.status_code == 0:
                msg = (
                    f"Cannot connect to local endpoint at {self._base_url}. "
                    f"Make sure the Docker container is running on port {self._port}."
                )
                raise RuntimeError(
                    msg
                )
            msg = f"invoke_agent failed (HTTP {result.status_code}): {result.error}"
            raise RuntimeError(msg)

        if result.streaming:
            content_type = result.headers.get("Content-Type", "")
            if "text/event-stream" in content_type:
                return self._parse_sse_stream(result.iter_lines())
            body = b"".join(result.iter_bytes())
            result.close()
            try:
                return json.loads(body)
            except (json.JSONDecodeError, ValueError):
                return {"raw": body.decode("utf-8", errors="replace")}

        data = result.data
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            try:
                return json.loads(data)
            except (json.JSONDecodeError, ValueError):
                return {"raw": data}
        return {"data": data}

    def ping_agent(
        self,
        bearer_token: str | None = None,
        endpoint: str | None = None,
        session_id: str | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """
        Health-check a local agent.

        Args:
            bearer_token: Optional bearer token for ``Authorization`` header.
            endpoint: Optional endpoint name.
            session_id: Session identifier for stateful agents.
            timeout: Request timeout in seconds.

        Returns:
            A ``dict`` with a ``status`` field indicating health status.
        """
        from agentarts.sdk.runtime.model import SESSION_HEADER

        path = "/ping"

        headers: dict[str, str] = {}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        if session_id:
            headers[SESSION_HEADER] = session_id

        params: dict[str, Any] = {}
        if endpoint:
            params["endpoint"] = endpoint

        request_timeout = timeout or 30

        result = self._request(
            "GET",
            path,
            params=params if params else None,
            headers=headers if headers else None,
            timeout=request_timeout,
        )

        if not result.success:
            if result.status_code == 0:
                msg = (
                    f"Cannot connect to local endpoint at {self._base_url}. "
                    f"Make sure the Docker container is running on port {self._port}."
                )
                raise RuntimeError(
                    msg
                )
            return {
                "status": "Unhealthy",
                "status_code": result.status_code,
                "error": result.error,
            }

        data = result.data
        if isinstance(data, dict):
            return {"status": data.get("status", "Healthy"), "details": data}
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                return {"status": parsed.get("status", "Healthy"), "details": parsed}
            except (json.JSONDecodeError, ValueError):
                return {"status": "Healthy", "raw": data}
        return {"status": "Healthy", "data": data}
