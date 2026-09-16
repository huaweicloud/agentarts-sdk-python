"""Unit tests for the bounded retry mechanism in the transport layer.

Covers:
- BaseHTTPClient._request retry (network error / 429 / 5xx)
- MemoryHttpService._make_request retry
- MemoryServiceAsync._make_request retry
- Retry semantics: no retry on 4xx, no retry on streaming,
  max_retries=0 disables retry.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentarts.sdk.service import BaseHTTPClient, RequestConfig
from agentarts.sdk.service.http_client import MemoryAPIException
from agentarts.sdk.service.memory_service import MemoryHttpService
from agentarts.sdk.service.memory_service_async import AsyncMemoryHttpService


def _mock_response(status_code=200, json_data=None, content_type="application/json"):
    """Helper to create a mock requests response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.ok = 200 <= status_code < 300
    if json_data is not None:
        mock_resp.json.return_value = json_data
    else:
        mock_resp.json.side_effect = ValueError("Not JSON")
    mock_resp.text = str(json_data) if json_data is not None else ""
    mock_resp.content = b""
    # 代码用 headers.get("Content-Type")（http_client）和
    # headers.get("content-type")（memory_service）两种键；requests 真实
    # 响应大小写不敏感，mock 需同时提供两种键以覆盖两个路径。
    mock_resp.headers = {
        "Content-Type": content_type,
        "content-type": content_type,
    }
    return mock_resp


# ============================================================
# BaseHTTPClient._request retry
# ============================================================

class TestBaseHTTPClientRetry:
    """Tests for _request bounded retry."""

    @patch("agentarts.sdk.service.http_client.time.sleep")
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_retry_until_success(self, mock_request, mock_sleep):
        """500 -> 500 -> 200: succeeds after 2 retries with max_retries=2."""
        mock_request.side_effect = [
            _mock_response(500, {"error": "boom"}),
            _mock_response(500, {"error": "boom"}),
            _mock_response(200, {"ok": True}),
        ]
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.get("/users")

        assert result.success is True
        assert result.data == {"ok": True}
        assert mock_request.call_count == 3  # 1 initial + 2 retries
        assert mock_sleep.call_count == 2

    @patch("agentarts.sdk.service.http_client.time.sleep")
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_retry_exhausted_returns_last_failure(self, mock_request, mock_sleep):
        """500 repeated: max_retries=1 -> 2 attempts, last failure returned."""
        mock_request.side_effect = [
            _mock_response(500, {"error": "boom"}),
            _mock_response(500, {"error": "boom"}),
        ]
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.get("/users", max_retries=1)

        assert result.success is False
        assert result.status_code == 500
        assert mock_request.call_count == 2  # 1 initial + 1 retry
        assert mock_sleep.call_count == 1

    @patch("agentarts.sdk.service.http_client.time.sleep")
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_max_retries_zero_no_retry(self, mock_request, mock_sleep):
        """max_retries=0 disables retry entirely."""
        mock_request.return_value = _mock_response(503, {"error": "unavailable"})
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.get("/users", max_retries=0)

        assert result.success is False
        assert result.status_code == 503
        mock_request.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("agentarts.sdk.service.http_client.time.sleep")
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_network_error_retried(self, mock_request, mock_sleep):
        """Network error (status_code=0) is retried and can recover."""
        mock_request.side_effect = [
            ConnectionError("Connection refused"),
            _mock_response(200, {"ok": True}),
        ]
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.get("/users")

        assert result.success is True
        assert result.data == {"ok": True}
        assert mock_request.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("agentarts.sdk.service.http_client.time.sleep")
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_4xx_not_retried(self, mock_request, mock_sleep):
        """400 validation error is not retried."""
        mock_request.return_value = _mock_response(400, {"error": "bad request"})
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.get("/users")

        assert result.success is False
        assert result.status_code == 400
        mock_request.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("agentarts.sdk.service.http_client.time.sleep")
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_streaming_response_not_retried(self, mock_request, mock_sleep):
        """Streaming responses are never retried (stream cannot be replayed)."""
        mock_request.return_value = _mock_response(
            500, content_type="text/event-stream"
        )
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.get("/events")

        assert result.success is False
        assert result.streaming is True
        mock_request.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("agentarts.sdk.service.http_client.time.sleep")
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_per_call_max_retries_overrides_config(self, mock_request, mock_sleep):
        """Per-call max_retries overrides RequestConfig default."""
        mock_request.return_value = _mock_response(503, {"error": "unavailable"})
        # Config default is 2, but per-call 0 disables retry.
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.get("/users", max_retries=0)

        mock_request.assert_called_once()
        assert result.status_code == 503

    @patch("agentarts.sdk.service.http_client.time.sleep")
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_retry_requests_identical_payload(self, mock_request, mock_sleep):
        """Retried requests carry the same URL/payload (no mutation between
        attempts), so write operations with idempotency keys are safe."""
        mock_request.side_effect = [
            _mock_response(500, {"error": "boom"}),
            _mock_response(200, {"ok": True}),
        ]
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        client.post("/messages", json={"msg": "hello"})

        assert mock_request.call_count == 2
        first_kwargs = mock_request.call_args_list[0][1]
        second_kwargs = mock_request.call_args_list[1][1]
        assert first_kwargs["json"] == second_kwargs["json"] == {"msg": "hello"}


# ============================================================
# MemoryHttpService._make_request retry
# ============================================================

class TestMemoryHttpServiceRetry:
    """Tests for MemoryHttpService._make_request bounded retry."""

    def _make_service(self, max_retries=2):
        service = MemoryHttpService(
            region_name="cn-southwest-2",
            endpoint="https://memory.example.com",
            endpoint_type="data",
            api_key="test-key",
            max_retries=max_retries,
        )
        # Avoid real credential lookup for data plane; session is mocked anyway.
        return service

    @patch("agentarts.sdk.service.memory_service.time.sleep")
    @patch("agentarts.sdk.service.memory_service.requests.Session.request")
    def test_retry_until_success(self, mock_request, mock_sleep):
        """500 -> 200: succeeds after 1 retry with max_retries=2."""
        mock_request.side_effect = [
            _mock_response(500, {"error": "boom"}),
            _mock_response(200, {"id": "space-1"}),
        ]
        service = self._make_service()

        result = service.create_space({"name": "test"})

        assert result == {"id": "space-1"}
        assert mock_request.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("agentarts.sdk.service.memory_service.time.sleep")
    @patch("agentarts.sdk.service.memory_service.requests.Session.request")
    def test_retry_exhausted_raises(self, mock_request, mock_sleep):
        """500 repeated: max_retries=1 -> raises MemoryAPIException."""
        mock_request.side_effect = [
            _mock_response(500, {"error": "boom"}),
            _mock_response(500, {"error": "boom"}),
        ]
        service = self._make_service(max_retries=1)

        with pytest.raises(MemoryAPIException) as exc_info:
            service.create_space({"name": "test"})

        assert exc_info.value.status_code == 500
        assert mock_request.call_count == 2

    @patch("agentarts.sdk.service.memory_service.time.sleep")
    @patch("agentarts.sdk.service.memory_service.requests.Session.request")
    def test_4xx_not_retried(self, mock_request, mock_sleep):
        """400 validation error is not retried."""
        mock_request.return_value = _mock_response(400, {"error": "bad request"})
        service = self._make_service()

        with pytest.raises(MemoryAPIException) as exc_info:
            service.create_space({"name": "test"})

        assert exc_info.value.status_code == 400
        mock_request.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("agentarts.sdk.service.memory_service.time.sleep")
    @patch("agentarts.sdk.service.memory_service.requests.Session.request")
    def test_network_error_retried(self, mock_request, mock_sleep):
        """Network error (status_code=0) is retried and can recover."""
        mock_request.side_effect = [
            ConnectionError("Connection refused"),
            _mock_response(200, {"id": "space-2"}),
        ]
        service = self._make_service()

        result = service.create_space({"name": "test"})

        assert result == {"id": "space-2"}
        assert mock_request.call_count == 2

    @patch("agentarts.sdk.service.memory_service.time.sleep")
    @patch("agentarts.sdk.service.memory_service.requests.Session.request")
    def test_max_retries_zero_no_retry(self, mock_request, mock_sleep):
        """max_retries=0 disables retry."""
        mock_request.return_value = _mock_response(503, {"error": "unavailable"})
        service = self._make_service(max_retries=0)

        with pytest.raises(MemoryAPIException) as exc_info:
            service.create_space({"name": "test"})

        assert exc_info.value.status_code == 503
        mock_request.assert_called_once()
        mock_sleep.assert_not_called()


# ============================================================
# MemoryServiceAsync._make_request retry
# ============================================================

class TestMemoryServiceAsyncRetry:
    """Tests for async _make_request bounded retry."""

    @pytest.mark.asyncio
    @patch("agentarts.sdk.service.memory_service_async.asyncio.sleep")
    @patch("agentarts.sdk.service.memory_service_async.httpx.AsyncClient")
    async def test_retry_until_success(self, mock_client_cls, mock_sleep):
        """500 -> 200: succeeds after 1 retry with max_retries=2."""
        mock_client = AsyncMock()
        # AsyncMock 的子属性默认也是 AsyncMock，_get_client 中同步调用
        # headers.get(...) 会返回未 await 的协程（RuntimeWarning）；
        # 覆盖为普通 dict 使其成为同步属性。
        mock_client.headers = {"User-Agent": "test"}
        mock_client_cls.return_value = mock_client

        first = MagicMock()
        first.status_code = 500
        first.headers = {"content-type": "application/json"}
        first.json.return_value = {"error": "boom"}

        second = MagicMock()
        second.status_code = 200
        second.headers = {"content-type": "application/json"}
        second.json.return_value = {"id": "space-1"}

        mock_client.request.side_effect = [first, second]

        service = AsyncMemoryHttpService(
            region_name="cn-southwest-2",
            endpoint="https://memory.example.com",
            endpoint_type="data",
            api_key="test-key",
            max_retries=2,
        )

        result = await service.create_space({"name": "test"})

        assert result == {"id": "space-1"}
        assert mock_client.request.call_count == 2
        mock_sleep.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("agentarts.sdk.service.memory_service_async.asyncio.sleep")
    @patch("agentarts.sdk.service.memory_service_async.httpx.AsyncClient")
    async def test_retry_exhausted_raises(self, mock_client_cls, mock_sleep):
        """500 repeated: max_retries=1 -> raises MemoryAPIException."""
        mock_client = AsyncMock()
        # AsyncMock 的子属性默认也是 AsyncMock，_get_client 中同步调用
        # headers.get(...) 会返回未 await 的协程（RuntimeWarning）；
        # 覆盖为普通 dict 使其成为同步属性。
        mock_client.headers = {"User-Agent": "test"}
        mock_client_cls.return_value = mock_client

        def _err():
            resp = MagicMock()
            resp.status_code = 500
            resp.headers = {"content-type": "application/json"}
            resp.json.return_value = {"error": "boom"}
            return resp

        mock_client.request.side_effect = [_err(), _err()]

        service = AsyncMemoryHttpService(
            region_name="cn-southwest-2",
            endpoint="https://memory.example.com",
            endpoint_type="data",
            api_key="test-key",
            max_retries=1,
        )

        with pytest.raises(MemoryAPIException) as exc_info:
            await service.create_space({"name": "test"})

        assert exc_info.value.status_code == 500
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    @patch("agentarts.sdk.service.memory_service_async.asyncio.sleep")
    @patch("agentarts.sdk.service.memory_service_async.httpx.AsyncClient")
    async def test_4xx_not_retried(self, mock_client_cls, mock_sleep):
        """400 validation error is not retried."""
        mock_client = AsyncMock()
        # AsyncMock 的子属性默认也是 AsyncMock，_get_client 中同步调用
        # headers.get(...) 会返回未 await 的协程（RuntimeWarning）；
        # 覆盖为普通 dict 使其成为同步属性。
        mock_client.headers = {"User-Agent": "test"}
        mock_client_cls.return_value = mock_client

        resp = MagicMock()
        resp.status_code = 400
        resp.headers = {"content-type": "application/json"}
        resp.json.return_value = {"error": "bad request"}

        mock_client.request.return_value = resp

        service = AsyncMemoryHttpService(
            region_name="cn-southwest-2",
            endpoint="https://memory.example.com",
            endpoint_type="data",
            api_key="test-key",
            max_retries=2,
        )

        with pytest.raises(MemoryAPIException) as exc_info:
            await service.create_space({"name": "test"})

        assert exc_info.value.status_code == 400
        mock_client.request.assert_awaited_once()
        mock_sleep.assert_not_awaited()


# ============================================================
# MemoryAPIException.retryable semantics
# ============================================================

class TestRetryableSemantics:
    """Tests for the retryable classification used by the retry loop."""

    def test_network_error_retryable(self):
        exc = MemoryAPIException(
            status_code=0, error_code="NETWORK_ERROR", error_msg="boom"
        )
        assert exc.retryable is True

    def test_429_retryable(self):
        exc = MemoryAPIException(status_code=429, error_code="THROTTLED", error_msg="slow")
        assert exc.retryable is True

    def test_5xx_retryable(self):
        for code in (500, 502, 503, 504):
            exc = MemoryAPIException(status_code=code, error_code="ERR", error_msg="x")
            assert exc.retryable is True, f"{code} should be retryable"

    def test_4xx_not_retryable(self):
        for code in (400, 401, 403, 404, 422):
            exc = MemoryAPIException(status_code=code, error_code="ERR", error_msg="x")
            assert exc.retryable is False, f"{code} should not be retryable"

    def test_2xx_parse_error_not_retryable(self):
        exc = MemoryAPIException(
            status_code=200, error_code="PARSE_ERROR", error_msg="bad json"
        )
        assert exc.retryable is False
