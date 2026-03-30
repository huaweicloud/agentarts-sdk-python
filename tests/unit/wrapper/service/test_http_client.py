"""Comprehensive unit tests for HTTP client module"""

import json

import pytest
import requests
from requests.exceptions import Timeout, RequestException, ConnectionError
from unittest.mock import MagicMock, patch, call
from dataclasses import dataclass, field

from agentarts.wrapper.service import (
    BaseHTTPClient,
    RequestConfig,
    RequestResult,
)


# ============================================================
# RequestConfig Tests
# ============================================================

class TestRequestConfig:
    """Tests for RequestConfig dataclass."""

    def test_default_values(self):
        """Test all default configuration values."""
        config = RequestConfig()
        assert config.base_url == ""
        assert config.timeout == 30.0
        assert config.headers == {}
        assert config.verify_ssl is True

    def test_custom_base_url(self):
        """Test custom base_url."""
        config = RequestConfig(base_url="https://api.example.com")
        assert config.base_url == "https://api.example.com"

    def test_custom_timeout(self):
        """Test custom timeout."""
        config = RequestConfig(timeout=60.0)
        assert config.timeout == 60.0

    def test_custom_headers(self):
        """Test custom headers."""
        config = RequestConfig(headers={"X-Custom": "value", "Authorization": "Bearer token"})
        assert config.headers["X-Custom"] == "value"
        assert config.headers["Authorization"] == "Bearer token"

    def test_verify_ssl_false(self):
        """Test disabling SSL verification."""
        config = RequestConfig(verify_ssl=False)
        assert config.verify_ssl is False

    def test_full_custom_config(self):
        """Test fully customized configuration."""
        config = RequestConfig(
            base_url="https://api.example.com",
            timeout=120.0,
            headers={"Content-Type": "application/json"},
            verify_ssl=False,
        )
        assert config.base_url == "https://api.example.com"
        assert config.timeout == 120.0
        assert config.headers["Content-Type"] == "application/json"
        assert config.verify_ssl is False


# ============================================================
# RequestResult Tests
# ============================================================

class TestRequestResult:
    """Tests for RequestResult dataclass."""

    def test_success_result_with_json_data(self):
        """Test successful result with JSON data."""
        result = RequestResult(
            success=True,
            status_code=200,
            data={"id": 1, "name": "test"},
            headers={"Content-Type": "application/json"},
        )
        assert result.success is True
        assert result.status_code == 200
        assert result.data == {"id": 1, "name": "test"}
        assert result.error is None
        assert result.headers["Content-Type"] == "application/json"

    def test_success_result_with_text_data(self):
        """Test successful result with text data."""
        result = RequestResult(
            success=True,
            status_code=200,
            data="plain text response",
        )
        assert result.success is True
        assert result.data == "plain text response"

    def test_success_result_with_none_data(self):
        """Test successful result with no data."""
        result = RequestResult(success=True, status_code=204)
        assert result.success is True
        assert result.data is None
        assert result.error is None
        assert result.headers == {}

    def test_error_result(self):
        """Test error result."""
        result = RequestResult(
            success=False,
            status_code=500,
            error="Internal Server Error",
        )
        assert result.success is False
        assert result.status_code == 500
        assert result.error == "Internal Server Error"

    def test_timeout_error_result(self):
        """Test timeout error result."""
        result = RequestResult(
            success=False,
            status_code=0,
            error="Request timeout: 30s",
        )
        assert result.success is False
        assert result.status_code == 0

    def test_connection_error_result(self):
        """Test connection error result."""
        result = RequestResult(
            success=False,
            status_code=0,
            error="Request error: Connection refused",
        )
        assert result.success is False
        assert result.status_code == 0


# ============================================================
# BaseHTTPClient Initialization Tests
# ============================================================

class TestBaseHTTPClientInit:
    """Tests for BaseHTTPClient initialization."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        client = BaseHTTPClient()
        assert client._config.base_url == ""
        assert client._config.timeout == 30.0
        assert client._config.verify_ssl is True
        assert client._session is not None

    def test_init_with_request_config(self):
        """Test initialization with RequestConfig object."""
        config = RequestConfig(base_url="https://api.example.com", timeout=60.0)
        client = BaseHTTPClient(config)
        assert client._config.base_url == "https://api.example.com"
        assert client._config.timeout == 60.0

    def test_init_headers_applied_to_session(self):
        """Test that config headers are applied to the session."""
        config = RequestConfig(headers={"X-API-Key": "abc123"})
        client = BaseHTTPClient(config)
        assert client._session.headers["X-API-Key"] == "abc123"


# ============================================================
# BaseHTTPClient Header & Auth Tests
# ============================================================

class TestBaseHTTPClientHeaders:
    """Tests for header and auth management."""

    def test_set_header(self):
        """Test setting a custom header."""
        client = BaseHTTPClient()
        client.set_header("X-Custom", "value")
        assert client._config.headers["X-Custom"] == "value"
        assert client._session.headers["X-Custom"] == "value"

    def test_set_header_overwrite(self):
        """Test overwriting an existing header."""
        client = BaseHTTPClient()
        client.set_header("X-Custom", "value1")
        client.set_header("X-Custom", "value2")
        assert client._config.headers["X-Custom"] == "value2"

    def test_set_multiple_headers(self):
        """Test setting multiple headers."""
        client = BaseHTTPClient()
        client.set_header("X-Key-1", "val1")
        client.set_header("X-Key-2", "val2")
        assert len(client._config.headers) == 2

    def test_set_auth_token_bearer(self):
        """Test setting Bearer auth token (default scheme)."""
        client = BaseHTTPClient()
        client.set_auth_token("my-token")
        assert client._config.headers["Authorization"] == "Bearer my-token"
        assert client._session.headers["Authorization"] == "Bearer my-token"

    def test_set_auth_token_custom_scheme(self):
        """Test setting auth token with custom scheme."""
        client = BaseHTTPClient()
        client.set_auth_token("my-token", scheme="Basic")
        assert client._config.headers["Authorization"] == "Basic my-token"

    def test_set_auth_token_overwrite(self):
        """Test overwriting auth token."""
        client = BaseHTTPClient()
        client.set_auth_token("token1")
        client.set_auth_token("token2")
        assert client._config.headers["Authorization"] == "Bearer token2"

    def test_clear_auth(self):
        """Test clearing auth header."""
        client = BaseHTTPClient()
        client.set_auth_token("my-token")
        client.clear_auth()
        assert "Authorization" not in client._config.headers
        assert "Authorization" not in client._session.headers

    def test_clear_auth_when_not_set(self):
        """Test clearing auth when it was never set (no error)."""
        client = BaseHTTPClient()
        client.clear_auth()
        assert "Authorization" not in client._config.headers


# ============================================================
# BaseHTTPClient Request Method Tests
# ============================================================

class TestBaseHTTPClientRequests:
    """Tests for HTTP request methods with mocked responses."""

    def _mock_response(self, status_code=200, json_data=None, text_data=None, content=b""):
        """Helper to create a mock response object."""
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.ok = 200 <= status_code < 300
        mock_resp.content = content

        if json_data is not None:
            mock_resp.json.return_value = json_data
            mock_resp.text = json.dumps(json_data)
        elif text_data is not None:
            mock_resp.json.side_effect = ValueError("Not JSON")
            mock_resp.text = text_data
            mock_resp.content = text_data.encode()
        else:
            mock_resp.json.side_effect = ValueError("Not JSON")
            mock_resp.text = ""
            mock_resp.content = b""

        mock_resp.headers = {"Content-Type": "application/json"}
        return mock_resp

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_get_request_success(self, mock_request):
        """Test successful GET request."""
        mock_request.return_value = self._mock_response(200, {"id": 1})
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.get("/users/1")

        assert result.success is True
        assert result.status_code == 200
        assert result.data == {"id": 1}
        mock_request.assert_called_once_with(
            "GET",
            "https://api.example.com/users/1",
            timeout=30.0,
            verify=True,
        )

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_get_request_with_params(self, mock_request):
        """Test GET request with query parameters."""
        mock_request.return_value = self._mock_response(200, [])
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.get("/users", params={"page": 1, "size": 10})

        assert result.success is True
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"] == {"page": 1, "size": 10}

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_post_request_json(self, mock_request):
        """Test POST request with JSON body."""
        mock_request.return_value = self._mock_response(201, {"created": True})
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.post("/users", json={"name": "test"})

        assert result.success is True
        assert result.status_code == 201
        assert result.data == {"created": True}
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["json"] == {"name": "test"}

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_post_request_form_data(self, mock_request):
        """Test POST request with form data."""
        mock_request.return_value = self._mock_response(200, {"ok": True})
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.post("/form", data={"key": "value"})

        assert result.success is True
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["data"] == {"key": "value"}

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_put_request(self, mock_request):
        """Test PUT request."""
        mock_request.return_value = self._mock_response(200, {"updated": True})
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.put("/users/1", json={"name": "updated"})

        assert result.success is True
        assert result.data == {"updated": True}
        mock_request.assert_called_once()
        assert mock_request.call_args[0][0] == "PUT"

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_patch_request(self, mock_request):
        """Test PATCH request."""
        mock_request.return_value = self._mock_response(200, {"patched": True})
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.patch("/users/1", json={"name": "patched"})

        assert result.success is True
        assert result.data == {"patched": True}
        mock_request.assert_called_once()
        assert mock_request.call_args[0][0] == "PATCH"

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_delete_request(self, mock_request):
        """Test DELETE request."""
        mock_request.return_value = self._mock_response(204)
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.delete("/users/1")

        assert result.success is True
        assert result.status_code == 204
        mock_request.assert_called_once()
        assert mock_request.call_args[0][0] == "DELETE"

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_custom_method_request(self, mock_request):
        """Test request with custom HTTP method."""
        mock_request.return_value = self._mock_response(200, {"ok": True})
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        result = client.request("HEAD", "/resource")

        assert result.success is True
        mock_request.assert_called_once()
        assert mock_request.call_args[0][0] == "HEAD"


# ============================================================
# BaseHTTPClient Response Parsing Tests
# ============================================================

class TestBaseHTTPClientResponseParsing:
    """Tests for response parsing behavior."""

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_json_response_parsed(self, mock_request):
        """Test that JSON response body is parsed to dict."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {"message": "hello"}
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_request.return_value = mock_resp

        client = BaseHTTPClient()
        result = client.get("/test")

        assert isinstance(result.data, dict)
        assert result.data["message"] == "hello"

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_text_response_fallback(self, mock_request):
        """Test that non-JSON response falls back to text."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.side_effect = ValueError("Not JSON")
        mock_resp.text = "plain text"
        mock_resp.content = b"plain text"
        mock_resp.headers = {"Content-Type": "text/plain"}
        mock_request.return_value = mock_resp

        client = BaseHTTPClient()
        result = client.get("/test")

        assert result.data == "plain text"

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_empty_response(self, mock_request):
        """Test that empty response returns None data."""
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.ok = True
        mock_resp.json.side_effect = ValueError("Not JSON")
        mock_resp.text = ""
        mock_resp.content = b""
        mock_resp.headers = {}
        mock_request.return_value = mock_resp

        client = BaseHTTPClient()
        result = client.get("/test")

        assert result.data is None

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_4xx_response_marked_as_failure(self, mock_request):
        """Test that 4xx responses are marked as not successful."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.ok = False
        mock_resp.json.return_value = {"error": "Not found"}
        mock_resp.headers = {}
        mock_request.return_value = mock_resp

        client = BaseHTTPClient()
        result = client.get("/not-found")

        assert result.success is False
        assert result.status_code == 404
        assert result.data == {"error": "Not found"}

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_5xx_response_marked_as_failure(self, mock_request):
        """Test that 5xx responses are marked as not successful."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.ok = False
        mock_resp.json.return_value = {"error": "Internal error"}
        mock_resp.headers = {}
        mock_request.return_value = mock_resp

        client = BaseHTTPClient()
        result = client.get("/error")

        assert result.success is False
        assert result.status_code == 500

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_response_headers_captured(self, mock_request):
        """Test that response headers are captured in result."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {}
        mock_resp.headers = {"Content-Type": "application/json", "X-Request-Id": "abc"}
        mock_request.return_value = mock_resp

        client = BaseHTTPClient()
        result = client.get("/test")

        assert result.headers["Content-Type"] == "application/json"
        assert result.headers["X-Request-Id"] == "abc"


# ============================================================
# BaseHTTPClient Error Handling Tests
# ============================================================

class TestBaseHTTPClientErrors:
    """Tests for error handling."""

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_timeout_error(self, mock_request):
        """Test that Timeout exception returns a failed result."""
        mock_request.side_effect = Timeout("Connection timed out")

        client = BaseHTTPClient()
        result = client.get("/slow")

        assert result.success is False
        assert result.status_code == 0
        assert "timeout" in result.error.lower()

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_connection_error(self, mock_request):
        """Test that ConnectionError returns a failed result."""
        mock_request.side_effect = ConnectionError("Connection refused")

        client = BaseHTTPClient()
        result = client.get("/unreachable")

        assert result.success is False
        assert result.status_code == 0
        assert "error" in result.error.lower()

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_generic_request_exception(self, mock_request):
        """Test that generic RequestException returns a failed result."""
        mock_request.side_effect = RequestException("Something went wrong")

        client = BaseHTTPClient()
        result = client.get("/fail")

        assert result.success is False
        assert result.status_code == 0
        assert "error" in result.error.lower()

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_unexpected_exception(self, mock_request):
        """Test that unexpected exceptions are caught and returned."""
        mock_request.side_effect = RuntimeError("Unexpected")

        client = BaseHTTPClient()
        result = client.get("/unexpected")

        assert result.success is False
        assert result.status_code == 0
        assert "unexpected" in result.error.lower()


# ============================================================
# BaseHTTPClient Config Propagation Tests
# ============================================================

class TestBaseHTTPClientConfigPropagation:
    """Tests that config values are correctly passed to requests."""

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_base_url_prepended(self, mock_request):
        """Test that base_url is prepended to the request URL."""
        mock_request.return_value = self._create_mock_response()
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))

        client.get("/users")

        called_url = mock_request.call_args[0][1]
        assert called_url == "https://api.example.com/users"

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_timeout_passed_to_request(self, mock_request):
        """Test that timeout config is passed to requests."""
        mock_request.return_value = self._create_mock_response()
        client = BaseHTTPClient(RequestConfig(timeout=99.0))

        client.get("/test")

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["timeout"] == 99.0

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_verify_ssl_disabled(self, mock_request):
        """Test that verify_ssl=False is passed to requests."""
        mock_request.return_value = self._create_mock_response()
        client = BaseHTTPClient(RequestConfig(verify_ssl=False))

        client.get("/test")

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["verify"] is False

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_auth_header_sent_with_request(self, mock_request):
        """Test that auth token is sent with requests."""
        mock_request.return_value = self._create_mock_response()
        client = BaseHTTPClient(RequestConfig(base_url="https://api.example.com"))
        client.set_auth_token("secret-token")

        client.get("/protected")

        assert client._session.headers["Authorization"] == "Bearer secret-token"

    @staticmethod
    def _create_mock_response():
        """Helper to create a basic successful mock response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {}
        mock_resp.headers = {}
        return mock_resp


# ============================================================
# BaseHTTPClient Lifecycle Tests
# ============================================================

class TestBaseHTTPClientLifecycle:
    """Tests for client lifecycle (context manager, close)."""

    def test_close(self):
        """Test that close() closes the session."""
        client = BaseHTTPClient()
        session = client._session
        assert session is not None

        client.close()

        assert client._session is None
        session.close.assert_called_once()

    def test_close_idempotent(self):
        """Test that calling close() twice does not raise."""
        client = BaseHTTPClient()
        client.close()
        client.close()
        assert client._session is None

    def test_context_manager_enter(self):
        """Test that __enter__ returns the client itself."""
        client = BaseHTTPClient()
        with client as ctx:
            assert ctx is client

    def test_context_manager_exit_closes_session(self):
        """Test that __exit__ closes the session."""
        client = BaseHTTPClient()
        with client:
            pass
        assert client._session is None

    def test_context_manager_preserves_session_inside_block(self):
        """Test that session is available inside the context block."""
        client = BaseHTTPClient()
        with client:
            assert client._session is not None
        assert client._session is None


# ============================================================
# BaseHTTPClient Inheritance Tests
# ============================================================

class TestBaseHTTPClientInheritance:
    """Tests that BaseHTTPClient can be properly subclassed."""

    def test_subclass_basic_usage(self):
        """Test creating a subclass with custom methods."""
        class MyAPIClient(BaseHTTPClient):
            def __init__(self):
                super().__init__(RequestConfig(base_url="https://api.example.com"))

            def get_user(self, user_id: str) -> RequestResult:
                return self.get(f"/users/{user_id}")

        client = MyAPIClient()
        assert client._config.base_url == "https://api.example.com"
        assert hasattr(client, "get_user")

    @patch("agentarts.wrapper.service.http_client.requests.Session.request")
    def test_subclass_method_calls_base(self, mock_request):
        """Test that subclass method correctly calls base HTTP methods."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.json.return_value = {"id": "123", "name": "test"}
        mock_resp.headers = {}
        mock_request.return_value = mock_resp

        class MyAPIClient(BaseHTTPClient):
            def __init__(self):
                super().__init__(RequestConfig(base_url="https://api.example.com"))

            def get_user(self, user_id: str) -> RequestResult:
                return self.get(f"/users/{user_id}")

        client = MyAPIClient()
        result = client.get_user("123")

        assert result.success is True
        assert result.data["id"] == "123"
        mock_request.assert_called_with(
            "GET",
            "https://api.example.com/users/123",
            timeout=30.0,
            verify=True,
        )
