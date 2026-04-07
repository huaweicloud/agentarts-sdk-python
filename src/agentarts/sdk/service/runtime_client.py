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
from typing import Any, Dict, Iterator, List, Optional, Union

from agentarts.sdk.service.http_client import BaseHTTPClient, RequestConfig, RequestResult
from agentarts.sdk.utils.constant import (
    get_control_plane_endpoint,
    get_data_plane_endpoint,
)

log = logging.getLogger(__name__)


class RuntimeClient(BaseHTTPClient):
    """
    Client for the AgentArts runtime service.

    Wraps :class:`BaseHTTPClient` and provides typed methods for every
    control-plane and data-plane API exposed by the AgentArts platform.

    Args:
        control_endpoint: Override the control plane base URL.
            If ``None``, the URL is derived from environment variables
            via :func:`~agentarts.sdk.utils.constant.get_control_plane_endpoint`.
        data_endpoint: Override the data plane base URL.
            If ``None``, the URL is derived from environment variables
            via :func:`~agentarts.sdk.utils.constant.get_data_plane_endpoint`.
        access_token: Bearer token for API authentication.
            Can also be set later via :meth:`set_auth_token`.
        timeout: Default request timeout in seconds.
    """

    def __init__(
        self,
        control_endpoint: Optional[str] = None,
        data_endpoint: Optional[str] = None,
        access_token: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self._control_base = control_endpoint or get_control_plane_endpoint()
        self._data_base = data_endpoint or get_data_plane_endpoint()

        super().__init__(RequestConfig(base_url=self._control_base, timeout=timeout))

        if access_token:
            self.set_auth_token(access_token)

    def _control(self, method: str, path: str, **kwargs: Any) -> RequestResult:
        """Send a request to the control plane."""
        old_base = self._config.base_url
        self._config.base_url = self._control_base
        try:
            return self._request(method, path, **kwargs)
        finally:
            self._config.base_url = old_base

    def _data(self, method: str, path: str, **kwargs: Any) -> RequestResult:
        """Send a request to the data plane."""
        old_base = self._config.base_url
        self._config.base_url = self._data_base
        try:
            return self._request(method, path, **kwargs)
        finally:
            self._config.base_url = old_base

    @staticmethod
    def _check(result: RequestResult, operation: str) -> Dict[str, Any]:
        """Raise on unsuccessful response and return parsed data."""
        if not result.success:
            log.error(
                "%s failed: status=%s, error=%s",
                operation,
                result.status_code,
                result.error,
            )
            raise RuntimeError(
                f"{operation} failed (HTTP {result.status_code}): {result.error}"
            )
        return result.data if isinstance(result.data, dict) else {}

    @staticmethod
    def _is_stream_response(result: RequestResult) -> bool:
        """Check if the response Content-Type is text/event-stream."""
        content_type = result.headers.get("Content-Type", "")
        return "text/event-stream" in content_type

    def _dispatch_response(
        self, result: RequestResult, operation: str
    ) -> Union[Dict[str, Any], Iterator[str]]:
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
                "%s failed: status=%s, error=%s",
                operation,
                result.status_code,
                result.error,
            )
            raise RuntimeError(
                f"{operation} failed (HTTP {result.status_code}): {result.error}"
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
        artifact_source_config: Optional[Dict] = None,
        env_vars: Optional[Dict] = None,
        identity_config: Optional[Dict] = None,
        execution_agency_name: Optional[str] = None,
        network_config: Optional[Dict] = None,
        agent_gateway_id: Optional[str] = None,
        invoke_config: Optional[Dict] = None,
        observability_config: Optional[Dict] = None,
        tags_config: Optional[Dict] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        """
        Create a new agent.

        Args:
            name: Agent name (unique within the workspace).
            description: Human-readable description.
            artifact_source_config: Configuration for the agent's artifact source.
            env_vars: Environment variables to inject into the agent runtime.
            identity_config: Identity and authentication configuration.
            execution_agency_name: Name of the execution agency.
            network_config: Network access configuration.
            agent_gateway_id: ID of the agent gateway to attach.
            invoke_config: Invocation-related configuration.
            observability_config: Observability (tracing, metrics) configuration.
            tags_config: Tags and labels for the agent.
            **extra: Additional fields forwarded to the API.

        Returns:
            The created agent object from the API.
        """
        payload: Dict[str, Any] = {"name": name, **extra}
        if description:
            payload["description"] = description
        if artifact_source_config is not None:
            payload["artifact_source_config"] = artifact_source_config
        if env_vars is not None:
            payload["env_vars"] = env_vars
        if identity_config is not None:
            payload["identity_config"] = identity_config
        if execution_agency_name is not None:
            payload["execution_agency_name"] = execution_agency_name
        if network_config is not None:
            payload["network_config"] = network_config
        if agent_gateway_id is not None:
            payload["agent_gateway_id"] = agent_gateway_id
        if invoke_config is not None:
            payload["invoke_config"] = invoke_config
        if observability_config is not None:
            payload["observability_config"] = observability_config
        if tags_config is not None:
            payload["tags_config"] = tags_config

        result = self._control("POST", "/v1/agents", json=payload)
        return self._check(result, "create_agent")

    def update_agent(
        self,
        agent_id: str,
        description: str = "",
        artifact_source_config: Optional[Dict] = None,
        env_vars: Optional[Dict] = None,
        execution_agency_name: Optional[str] = None,
        network_config: Optional[Dict] = None,
        agent_gateway_id: Optional[str] = None,
        invoke_config: Optional[Dict] = None,
        observability_config: Optional[Dict] = None,
        tags_config: Optional[Dict] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        """
        Update an existing agent.

        Args:
            agent_id: The unique agent identifier.
            description: New description (omit to keep unchanged).
            artifact_source_config: Configuration for the agent's artifact source.
            env_vars: Environment variables to inject into the agent runtime.
            execution_agency_name: Name of the execution agency.
            network_config: Network access configuration.
            agent_gateway_id: ID of the agent gateway to attach.
            invoke_config: Invocation-related configuration.
            observability_config: Observability (tracing, metrics) configuration.
            tags_config: Tags and labels for the agent.
            **extra: Additional fields forwarded to the API.

        Returns:
            The updated agent object.
        """
        payload: Dict[str, Any] = {"agent_id": agent_id, **extra}
        if description is not None:
            payload["description"] = description
        if artifact_source_config is not None:
            payload["artifact_source_config"] = artifact_source_config
        if env_vars is not None:
            payload["env_vars"] = env_vars
        if execution_agency_name is not None:
            payload["execution_agency_name"] = execution_agency_name
        if network_config is not None:
            payload["network_config"] = network_config
        if agent_gateway_id is not None:
            payload["agent_gateway_id"] = agent_gateway_id
        if invoke_config is not None:
            payload["invoke_config"] = invoke_config
        if observability_config is not None:
            payload["observability_config"] = observability_config
        if tags_config is not None:
            payload["tags_config"] = tags_config

        result = self._control("PUT", f"/v1/agents/{agent_id}", json=payload)
        return self._check(result, "update_agent")

    def create_or_update_agent(
        self,
        agent_name: str,
        description: str = "",
        artifact_source_config: Optional[Dict] = None,
        env_vars: Optional[Dict] = None,
        identity_config: Optional[Dict] = None,
        execution_agency_name: Optional[str] = None,
        network_config: Optional[Dict] = None,
        agent_gateway_id: Optional[str] = None,
        invoke_config: Optional[Dict] = None,
        observability_config: Optional[Dict] = None,
        tags_config: Optional[Dict] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        """
        Create or update an agent (upsert semantics).

        Queries the agent by *agent_name* first.  If an agent with that
        name already exists it will be updated via ``PUT``; otherwise a
        new agent is created via ``POST``.

        Args:
            agent_name: Agent name (used as the lookup key).
            description: Human-readable description.
            artifact_source_config: Configuration for the agent's artifact source.
            env_vars: Environment variables to inject into the agent runtime.
            identity_config: Identity and authentication configuration.
            execution_agency_name: Name of the execution agency.
            network_config: Network access configuration.
            agent_gateway_id: ID of the agent gateway to attach.
            invoke_config: Invocation-related configuration.
            observability_config: Observability (tracing, metrics) configuration.
            tags_config: Tags and labels for the agent.
            **extra: Additional fields forwarded to the API.

        Returns:
            The agent object from the API.
        """
        payload: Dict[str, Any] = {"name": agent_name, **extra}
        if description:
            payload["description"] = description
        if artifact_source_config is not None:
            payload["artifact_source_config"] = artifact_source_config
        if env_vars is not None:
            payload["env_vars"] = env_vars
        if identity_config is not None:
            payload["identity_config"] = identity_config
        if execution_agency_name is not None:
            payload["execution_agency_name"] = execution_agency_name
        if network_config is not None:
            payload["network_config"] = network_config
        if agent_gateway_id is not None:
            payload["agent_gateway_id"] = agent_gateway_id
        if invoke_config is not None:
            payload["invoke_config"] = invoke_config
        if observability_config is not None:
            payload["observability_config"] = observability_config
        if tags_config is not None:
            payload["tags_config"] = tags_config

        existing = self.find_agent_by_name(agent_name)
        agent_id = existing.get("agent_id")
        if agent_id:
            log.debug("Agent '%s' found (ID: %s), updating", agent_name, agent_id)
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
    ) -> List[Dict[Any, Any]]:
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
        params: Dict[str, Any] = {"offset": offset, "limit": limit, **extra}
        if agent_name:
            params["agent_name"] = agent_name

        result = self._control("GET", "/v1/agents", params=params)
        data = self._check(result, "get_agents")
        if isinstance(data, dict):
            return data.get("items", data.get("agents", []))
        if isinstance(data, list):
            return data
        return []

    def find_agent_by_name(
        self,
        agent_name: str,
    ) -> Optional[Dict[Any, Any]]:
        """
        Find an agent by its name.

        Args:
            agent_name: Agent name to search for.

        Returns:
            The matching agent object, or raises if not found.
        """
        params: Dict[str, Any] = {"name": agent_name}

        result = self._control("GET", "/v1/agents/find", params=params)
        return self._check(result, "find_agent_by_name")

    def find_agent_by_id(self, agent_id: str) -> Optional[Dict[Any, Any]]:
        """
        Find an agent by its unique identifier.

        Args:
            agent_id: The agent ID.

        Returns:
            The agent object.
        """
        result = self._control("GET", f"/v1/agents/{agent_id}")
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
        params: Dict[str, Any] = {"name": agent_name}

        result = self._control("DELETE", "/v1/agents", params=params)
        self._check(result, "delete_agent_by_name")
        return True

    def create_agent_endpoint(
        self,
        agent_id: str,
        endpoint_name: str,
        endpoint_type: str = "invocations",
        config: Optional[Dict[str, Any]] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
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
        payload: Dict[str, Any] = {
            "agent_id": agent_id,
            "endpoint_name": endpoint_name,
            "endpoint_type": endpoint_type,
            **extra,
        }
        if config is not None:
            payload["config"] = config

        result = self._control(
            "POST", f"/v1/agents/{agent_id}/endpoints", json=payload
        )
        return self._check(result, "create_agent_endpoint")

    def update_agent_endpoint(
        self,
        agent_id: str,
        endpoint_name: str,
        config: Optional[Dict[str, Any]] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
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
        payload: Dict[str, Any] = {"endpoint_name": endpoint_name, **extra}
        if config is not None:
            payload["config"] = config

        result = self._control(
            "PUT", f"/v1/agents/{agent_id}/endpoints/{endpoint_name}", json=payload
        )
        return self._check(result, "update_agent_endpoint")

    def delete_agent_endpoint(
        self,
        agent_id: str,
        endpoint_name: str,
    ) -> Dict[str, Any]:
        """
        Delete an agent endpoint.

        Args:
            agent_id: The agent the endpoint belongs to.
            endpoint_name: Name of the endpoint to delete.

        Returns:
            The deletion response.
        """
        result = self._control(
            "DELETE", f"/v1/agents/{agent_id}/endpoints/{endpoint_name}"
        )
        return self._check(result, "delete_agent_endpoint")

    def find_agent_endpoint(
        self,
        agent_id: str,
        endpoint_name: str,
    ) -> Dict[str, Any]:
        """
        Find an agent endpoint by name.

        Args:
            agent_id: The agent the endpoint belongs to.
            endpoint_name: Name of the endpoint.

        Returns:
            The endpoint object.
        """
        result = self._control(
            "GET", f"/v1/agents/{agent_id}/endpoints/{endpoint_name}"
        )
        return self._check(result, "find_agent_endpoint")

    def invoke_agent(
        self,
        agent_name: str,
        session_id: str,
        payload: str,
        bearer_token: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: int = 900,
        **extra: Any,
    ) -> Union[Dict[str, Any], Iterator[str]]:
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

        path = f"/agents/{agent_name}/invocations"
        params: Dict[str, Any] = {}
        if endpoint:
            params["endpoint"] = endpoint

        headers: Dict[str, str] = {
            SESSION_HEADER: session_id,
            "Content-Type": "application/json",
        }
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        old_base = self._config.base_url
        self._config.base_url = self._data_base
        try:
            result = self._request(
                "POST",
                path,
                data=payload,
                params=params if params else None,
                headers=headers,
                timeout=timeout,
            )
        finally:
            self._config.base_url = old_base

        return self._dispatch_response(result, "invoke_agent")

    def ping_agent(
        self,
        agent_name: str,
        bearer_token: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: int = 900,
    ) -> Union[Dict[str, Any], Iterator[str]]:
        """
        Health-check an agent on the data plane.

        If the server responds with ``Content-Type: text/event-stream``, the
        return value is an :term:`iterator` that yields one decoded SSE event
        string per iteration.  Otherwise a parsed JSON ``dict`` is returned.

        Args:
            agent_name: The agent to ping.
            bearer_token: Optional bearer token for ``Authorization`` header.
            endpoint: Optional endpoint name, appended as a query parameter.
            timeout: Request timeout in seconds.

        Returns:
            A ``dict`` with at least a ``status`` field (e.g. ``"Healthy"``),
            or an ``Iterator[str]`` for SSE streaming responses.
        """
        headers: Dict[str, str] = {}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        params: Dict[str, Any] = {}
        if endpoint:
            params["endpoint"] = endpoint

        old_base = self._config.base_url
        self._config.base_url = self._data_base
        try:
            result = self._request(
                "GET",
                f"/agents/{agent_name}/ping",
                params=params if params else None,
                headers=headers if headers else None,
                timeout=timeout,
            )
        finally:
            self._config.base_url = old_base

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
        session_id: Optional[str] = None,
        bearer_token: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Union[Dict[str, Any], Iterator[str]]:
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
        params: Dict[str, Any] = {}
        if endpoint:
            params["endpoint"] = endpoint

        headers: Dict[str, str] = {"Content-Type": "application/json"}
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
                raise RuntimeError(
                    f"Cannot connect to local endpoint at {self._base_url}. "
                    f"Make sure the Docker container is running on port {self._port}."
                )
            raise RuntimeError(f"invoke_agent failed (HTTP {result.status_code}): {result.error}")

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
        bearer_token: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Health-check a local agent.

        Args:
            bearer_token: Optional bearer token for ``Authorization`` header.
            endpoint: Optional endpoint name.
            timeout: Request timeout in seconds.

        Returns:
            A ``dict`` with a ``status`` field indicating health status.
        """
        path = "/ping"

        headers: Dict[str, str] = {}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        params: Dict[str, Any] = {}
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
                raise RuntimeError(
                    f"Cannot connect to local endpoint at {self._base_url}. "
                    f"Make sure the Docker container is running on port {self._port}."
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
