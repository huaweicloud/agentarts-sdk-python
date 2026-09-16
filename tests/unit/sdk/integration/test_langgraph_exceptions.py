"""Unit tests for the LangGraph integration exception hierarchy."""

from __future__ import annotations

import pytest

from agentarts.sdk.integration.langgraph.exceptions import (
    AgentArtsAuthenticationError,
    AgentArtsIntegrationError,
    AgentArtsNetworkError,
    AgentArtsResourceNotFoundError,
    AgentArtsServiceError,
    AgentArtsValidationError,
    map_exception,
)
from agentarts.sdk.service import APIException, MemoryAPIException


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        # Network: status_code=0 marks "no HTTP response at all"
        (MemoryAPIException(0, "NETWORK_ERROR", "timeout"), AgentArtsNetworkError),
        (APIException(0, "NETWORK_ERROR", "connection refused"), AgentArtsNetworkError),
        # Auth
        (MemoryAPIException(401, "Unauthorized", "bad api key"), AgentArtsAuthenticationError),
        (MemoryAPIException(403, "Forbidden", "no permission"), AgentArtsAuthenticationError),
        # Validation
        (MemoryAPIException(400, "BadRequest", "invalid body"), AgentArtsValidationError),
        (MemoryAPIException(422, "UnprocessableEntity", "schema"), AgentArtsValidationError),
        # Not found
        (MemoryAPIException(404, "NotFound", "missing"), AgentArtsResourceNotFoundError),
        # Service / throttle
        (MemoryAPIException(429, "TooManyRequests", "slow down"), AgentArtsServiceError),
        (MemoryAPIException(500, "InternalError", "boom"), AgentArtsServiceError),
        (MemoryAPIException(503, "Unavailable", "maintenance"), AgentArtsServiceError),
        # Anything else falls back to the base class
        (MemoryAPIException(418, "Teapot", "n/a"), AgentArtsIntegrationError),
    ],
)
def test_map_exception_status_matrix(exc, expected):
    """Each status code family maps to its dedicated exception type."""
    mapped = map_exception(exc)

    assert type(mapped) is expected
    assert isinstance(mapped, AgentArtsIntegrationError)


def test_map_exception_keeps_cause_and_message():
    """The original exception and its message are preserved on the mapped one."""
    original = MemoryAPIException(503, "Unavailable", "maintenance")

    mapped = map_exception(original)

    assert mapped.cause is original
    assert "Unavailable" in str(mapped)
    assert "503" in str(mapped)
    assert "maintenance" in str(mapped)


def test_map_exception_sets_exception_chain():
    """``raise map_exception(e) from e`` keeps the original in ``__cause__``."""
    original = MemoryAPIException(500, "InternalError", "boom")

    with pytest.raises(AgentArtsServiceError) as exc_info:
        raise map_exception(original) from original

    assert exc_info.value.__cause__ is original


def test_exception_hierarchy_is_exported_from_package():
    """The hierarchy is importable from the package root."""
    import agentarts.sdk.integration.langgraph as langgraph_pkg

    assert langgraph_pkg.AgentArtsIntegrationError is AgentArtsIntegrationError
    assert issubclass(langgraph_pkg.AgentArtsNetworkError, AgentArtsIntegrationError)
    assert langgraph_pkg.map_exception is map_exception


def test_subtypes_are_catchable_as_base():
    """Catching the base class also catches every subtype."""
    for exc in (
        AgentArtsNetworkError("net"),
        AgentArtsAuthenticationError("auth"),
        AgentArtsValidationError("validation"),
        AgentArtsServiceError("service"),
        AgentArtsResourceNotFoundError("not found"),
    ):
        with pytest.raises(AgentArtsIntegrationError):
            raise exc
