"""Unit tests for MemoryHttpService / AsyncMemoryHttpService exception semantics.

Covers the service-layer exception fixes (service-exception-fix-plan.md Part A):
- Network errors (timeout / connection refused) -> MemoryAPIException(status_code=0, NETWORK_ERROR)
  with original exception chained via __cause__
- Real HTTP errors (503 / 404) keep their actual status_code
- 2xx success unchanged
- 2xx with invalid JSON body -> MemoryAPIException(status_code=<actual>, PARSE_ERROR)
- is_network_error / retryable properties
"""

import httpx
import pytest
from requests.exceptions import ConnectionError, Timeout

from agentarts.sdk.service.http_client import (
    APIException,
    MemoryAPIException,
)
from agentarts.sdk.service.memory_service import MemoryHttpService
from agentarts.sdk.service.memory_service_async import AsyncMemoryHttpService


def _sync_service() -> MemoryHttpService:
    """Create a data-plane MemoryHttpService (no AK/SK signing needed)."""
    return MemoryHttpService(
        region_name="cn-north-4",
        endpoint_type="data",
        api_key="test-api-key",
        verify_ssl=False,
    )


def _async_service() -> AsyncMemoryHttpService:
    """Create a data-plane AsyncMemoryHttpService."""
    return AsyncMemoryHttpService(
        region_name="cn-north-4",
        endpoint_type="data",
        api_key="test-api-key",
        verify_ssl=False,
    )


def _sync_resp(mocker, status_code, json_data=None, text="", raise_json=False):
    """Create a sync requests-like response mock.

    Note: real requests.Response.headers is case-insensitive, so the mock must
    expose the lowercase key the production code looks up ("content-type").
    """
    mock_resp = mocker.MagicMock()
    mock_resp.status_code = status_code
    mock_resp.ok = 200 <= status_code < 300
    mock_resp.headers = {"content-type": "application/json"}
    if raise_json:
        mock_resp.json.side_effect = ValueError("Invalid JSON")
    else:
        mock_resp.json.return_value = json_data
    mock_resp.text = text
    mock_resp.content = text.encode()
    return mock_resp


class _FakeAsyncClient:
    """Fake httpx.AsyncClient: request() delegates to a handler.

    httpx.Response.headers is also case-insensitive, so handlers build
    responses with lowercase "content-type" key.
    """

    def __init__(self, handler):
        self._handler = handler

    async def request(self, *args, **kwargs):
        return await self._handler(*args, **kwargs)


class _FakeAsyncResp:
    """Fake httpx.Response with a case-insensitive-style headers dict."""

    def __init__(self, status_code, json_data=None, text="", raise_json=False):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.headers = {"content-type": "application/json"}
        self._json_data = json_data
        self._text = text
        self._raise_json = raise_json

    def json(self):
        if self._raise_json:
            raise ValueError("Invalid JSON")
        return self._json_data

    @property
    def text(self):
        return self._text


def _patch_async_client(mocker, service, handler):
    """Patch _get_client to return a fake client whose request() is the handler."""
    mocker.patch.object(
        service, "_get_client", return_value=_FakeAsyncClient(handler)
    )


class TestSyncExceptionSemantics:
    """Sync MemoryHttpService exception wrapping semantics."""

    def test_network_timeout(self, mocker):
        """Timeout -> MemoryAPIException(status_code=0, NETWORK_ERROR), __cause__ preserved."""
        service = _sync_service()
        mocker.patch.object(
            service.session, "request", side_effect=Timeout("read timeout")
        )

        with pytest.raises(MemoryAPIException) as exc_info:
            service._make_request("GET", "/v1/core/spaces", space_id="s1")

        exc = exc_info.value
        assert exc.status_code == 0
        assert exc.error_code == "NETWORK_ERROR"
        assert exc.is_network_error is True
        assert exc.retryable is True
        assert isinstance(exc.__cause__, Timeout)

    def test_connection_error(self, mocker):
        """ConnectionError -> MemoryAPIException(status_code=0, NETWORK_ERROR)."""
        service = _sync_service()
        mocker.patch.object(
            service.session, "request", side_effect=ConnectionError("conn refused")
        )

        with pytest.raises(MemoryAPIException) as exc_info:
            service._make_request("GET", "/v1/core/spaces", space_id="s1")

        exc = exc_info.value
        assert exc.status_code == 0
        assert exc.error_code == "NETWORK_ERROR"
        assert exc.is_network_error is True
        assert exc.retryable is True
        assert isinstance(exc.__cause__, ConnectionError)

    def test_real_503_keeps_status_code(self, mocker):
        """Real 503 -> status_code=503, error_code from backend body, NOT network error."""
        service = _sync_service()
        mock_resp = _sync_resp(
            mocker,
            503,
            json_data={"error_code": "INTERNAL_ERROR", "error_msg": "server busy"},
            text="server busy",
        )
        mocker.patch.object(service.session, "request", return_value=mock_resp)

        with pytest.raises(MemoryAPIException) as exc_info:
            service._make_request("GET", "/v1/core/spaces", space_id="s1")

        exc = exc_info.value
        assert exc.status_code == 503
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.is_network_error is False
        assert exc.retryable is True  # 503 is retryable

    def test_real_404_keeps_status_code(self, mocker):
        """Real 404 -> status_code=404, not misclassified."""
        service = _sync_service()
        mock_resp = _sync_resp(
            mocker,
            404,
            json_data={"error_code": "NOT_FOUND", "error_msg": "Session not found"},
            text="Session not found",
        )
        mocker.patch.object(service.session, "request", return_value=mock_resp)

        with pytest.raises(MemoryAPIException) as exc_info:
            service._make_request("GET", "/v1/core/spaces", space_id="s1")

        exc = exc_info.value
        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"
        assert exc.is_network_error is False
        assert exc.retryable is False  # 404 not retryable

    def test_2xx_success_unchanged(self, mocker):
        """2xx JSON response still returns parsed dict."""
        service = _sync_service()
        mock_resp = _sync_resp(mocker, 200, json_data={"ok": True}, text='{"ok": true}')
        mocker.patch.object(service.session, "request", return_value=mock_resp)

        result = service._make_request("GET", "/v1/core/spaces", space_id="s1")
        assert result == {"ok": True}

    def test_2xx_invalid_json_parse_error(self, mocker):
        """2xx + Content-Type json + invalid body -> PARSE_ERROR with actual status_code."""
        service = _sync_service()
        mock_resp = _sync_resp(
            mocker, 200, text="<html>gateway error</html>", raise_json=True
        )
        mocker.patch.object(service.session, "request", return_value=mock_resp)

        with pytest.raises(MemoryAPIException) as exc_info:
            service._make_request("GET", "/v1/core/spaces", space_id="s1")

        exc = exc_info.value
        assert exc.status_code == 200
        assert exc.error_code == "PARSE_ERROR"
        assert exc.is_network_error is False
        assert exc.retryable is False  # parse error: no point retrying

    def test_204_no_content(self, mocker):
        """204 -> empty dict, no exception."""
        service = _sync_service()
        mock_resp = _sync_resp(mocker, 204)
        mocker.patch.object(service.session, "request", return_value=mock_resp)

        result = service._make_request("DELETE", "/v1/core/spaces/x", space_id="s1")
        assert result == {}


class TestAsyncExceptionSemantics:
    """Async AsyncMemoryHttpService exception wrapping semantics."""

    @pytest.mark.asyncio
    async def test_async_network_timeout(self, mocker):
        """Async timeout -> MemoryAPIException(status_code=0, NETWORK_ERROR)."""
        service = _async_service()

        async def _handler(*args, **kwargs):
            raise httpx.TimeoutException("async read timeout")

        _patch_async_client(mocker, service, _handler)

        with pytest.raises(MemoryAPIException) as exc_info:
            await service._make_request("GET", "/v1/core/spaces", space_id="s1")

        exc = exc_info.value
        assert exc.status_code == 0
        assert exc.error_code == "NETWORK_ERROR"
        assert exc.is_network_error is True
        assert exc.retryable is True
        assert isinstance(exc.__cause__, httpx.TimeoutException)

    @pytest.mark.asyncio
    async def test_async_real_503(self, mocker):
        """Async real 503 keeps status_code, not network error."""
        service = _async_service()

        async def _handler(*args, **kwargs):
            return _FakeAsyncResp(
                503,
                json_data={"error_code": "INTERNAL_ERROR", "error_msg": "server busy"},
                text="server busy",
            )

        _patch_async_client(mocker, service, _handler)

        with pytest.raises(MemoryAPIException) as exc_info:
            await service._make_request("GET", "/v1/core/spaces", space_id="s1")

        exc = exc_info.value
        assert exc.status_code == 503
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.is_network_error is False
        assert exc.retryable is True

    @pytest.mark.asyncio
    async def test_async_2xx_invalid_json_parse_error(self, mocker):
        """Async 2xx + invalid JSON -> PARSE_ERROR."""
        service = _async_service()

        async def _handler(*args, **kwargs):
            return _FakeAsyncResp(200, text="<html>bad</html>", raise_json=True)

        _patch_async_client(mocker, service, _handler)

        with pytest.raises(MemoryAPIException) as exc_info:
            await service._make_request("GET", "/v1/core/spaces", space_id="s1")

        exc = exc_info.value
        assert exc.status_code == 200
        assert exc.error_code == "PARSE_ERROR"
        assert exc.is_network_error is False

    @pytest.mark.asyncio
    async def test_async_2xx_success(self, mocker):
        """Async 2xx success unchanged."""
        service = _async_service()

        async def _handler(*args, **kwargs):
            return _FakeAsyncResp(200, json_data={"ok": True}, text='{"ok": true}')

        _patch_async_client(mocker, service, _handler)

        result = await service._make_request("GET", "/v1/core/spaces", space_id="s1")
        assert result == {"ok": True}


class TestMemoryAPIExceptionProperties:
    """MemoryAPIException property semantics."""

    def test_network_error_property(self):
        exc = MemoryAPIException(status_code=0, error_code="NETWORK_ERROR", error_msg="timeout")
        assert exc.is_network_error is True
        assert exc.retryable is True

    def test_429_retryable(self):
        exc = MemoryAPIException(
            status_code=429, error_code="RATE_LIMITED", error_msg="rate limited"
        )
        assert exc.is_network_error is False
        assert exc.retryable is True

    def test_500_retryable(self):
        exc = MemoryAPIException(status_code=500, error_code="INTERNAL_ERROR", error_msg="internal")
        assert exc.retryable is True

    def test_400_not_retryable(self):
        exc = MemoryAPIException(
            status_code=400, error_code="BAD_REQUEST", error_msg="bad request"
        )
        assert exc.is_network_error is False
        assert exc.retryable is False

    def test_is_subclass_of_api_exception(self):
        """MemoryAPIException must remain a subclass of APIException (backward compat)."""
        exc = MemoryAPIException(status_code=0, error_code="NETWORK_ERROR", error_msg="x")
        assert isinstance(exc, APIException)

    def test_str_contains_details(self):
        exc = MemoryAPIException(
            status_code=404, error_code="NOT_FOUND", error_msg="Session not found"
        )
        assert "404" in str(exc)
        assert "Session not found" in str(exc)
