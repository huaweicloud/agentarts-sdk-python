"""
Base HTTP Client Module

Provides a base HTTP client for API calls. Other service implementations
should inherit from BaseHTTPClient to make HTTP requests.

The client automatically detects streaming responses based on the
response ``Content-Type`` header:

- **Regular** (JSON / text): ``data`` is a parsed ``dict`` or ``str``.
- **Streaming** (``text/event-stream``): ``data`` is ``None``; use
  ``iter_lines()`` or ``iter_bytes()`` to consume the body incrementally.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urlparse

import requests
from typing_extensions import Self

from agentarts.sdk.utils.signer import SDKSigner
from agentarts.sdk.utils.signer_v11 import V11Signer

_STREAM_CONTENT_TYPES = {"text/event-stream", "application/x-ndjson"}


class APIException(Exception):
    """Exception for API errors."""

    def __init__(self, status_code: int, error_code: str, error_msg: str):
        self.status_code = status_code
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(f"[{error_code}] HTTP {status_code}: {error_msg}")


class SignMode(Enum):
    """Signature mode for AK/SK authentication."""

    SDK_HMAC_SHA256 = "sdk"
    V11_HMAC_SHA256 = "v11"


@dataclass
class RequestConfig:
    """Configuration for HTTP requests.

    Attributes:
        base_url: Base URL for API requests.
        timeout: Request timeout in seconds.
        headers: Default headers for all requests.
        verify_ssl: SSL verification setting.
            - True: Verify SSL certificates using system CA bundle (default)
            - False: Skip SSL verification (not recommended for production)
            - str: Path to custom CA certificate file
    """

    base_url: str = ""
    timeout: float = 30.0
    headers: dict[str, str] = field(default_factory=dict)
    verify_ssl: bool | str = True


@dataclass
class RequestResult:
    """
    Result of an HTTP request.

    Attributes:
        success: Whether the request completed successfully (2xx).
        status_code: HTTP status code.
        data: Parsed response body.  For regular responses this is a
            ``dict`` (JSON) or ``str``.  For streaming responses this
            is ``None``; use ``iter_lines()`` / ``iter_bytes()`` instead.
        error: Error message if the request failed.
        headers: Response headers as a dict.
        streaming: ``True`` when the response Content-Type indicates a
            streaming payload (e.g. ``text/event-stream``).
    """

    success: bool
    status_code: int
    data: Any = None
    error: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    streaming: bool = False
    _raw_response: Any = field(default=None, repr=False)

    def iter_lines(self) -> Iterator[str]:
        """
        Iterate over decoded text lines.

        Only valid for streaming results.  Each yielded value is a
        single line (without the trailing newline).

        The underlying response is automatically closed after the
        iterator is exhausted.
        """
        if not self.streaming or self._raw_response is None:
            msg = "iter_lines() is only available for streaming results"
            raise RuntimeError(msg)

        yield from self._raw_response.iter_lines()

    def iter_bytes(self) -> Iterator[bytes]:
        """
        Iterate over raw byte chunks.

        Only valid for streaming results.  Each yielded value is a
        chunk of bytes as received from the server.

        The underlying response is automatically closed after the
        iterator is exhausted.
        """
        if not self.streaming or self._raw_response is None:
            msg = "iter_bytes() is only available for streaming results"
            raise RuntimeError(msg)

        for chunk in self._raw_response.iter_content(chunk_size=None):
            if chunk:
                yield chunk

    def close(self) -> None:
        """Close the underlying HTTP response (streaming only)."""
        if self._raw_response is not None:
            self._raw_response.close()
            self._raw_response = None


class BaseHTTPClient:
    """
    Base HTTP client for making API calls.

    Subclass this to implement service-specific API clients.

    Features:
    - Synchronous requests via requests.Session
    - Automatic JSON/text response parsing
    - Auto-detected streaming for ``text/event-stream`` responses
    - Timeout and error handling
    - Auth token management
    - Context manager support
    - Optional Huawei Cloud AK/SK signing (SDK-HMAC-SHA256 or V11-HMAC-SHA256)

    Usage::

        class MyAPIClient(BaseHTTPClient):
            def __init__(self):
                super().__init__(RequestConfig(base_url="https://api.example.com"))

            def get_user(self, user_id: str) -> RequestResult:
                return self.get(f"/users/{user_id}")

            def invoke(self, payload: dict) -> RequestResult:
                return self.post("/invoke", json=payload)

        with MyAPIClient() as client:
            result = client.get_user("123")
            if result.success:
                print(result.data)

            result = client.invoke({"input": "hello"})
            if result.success:
                if result.streaming:
                    for line in result.iter_lines():
                        print(line)
                else:
                    print(result.data)
    """

    def __init__(
        self,
        config: RequestConfig | None = None,
        open_ak_sk: bool = False,
        sign_mode: SignMode = SignMode.SDK_HMAC_SHA256,
        region_id: str = "",
    ):
        self._config = config or RequestConfig()
        self._session = requests.Session()
        self._session.headers.update(self._config.headers)
        self._open_ak_sk = open_ak_sk
        self._sign_mode = sign_mode
        self._region_id = region_id
        self._signer = None
        self._credentials = None
        self._sdk_signer = None

    def _get_security_token(self) -> str | None:
        """Get security token from credentials if available.

        Returns:
            Security token string or None if not available.
        """
        if not self._credentials:
            return None

        security_token = getattr(self._credentials, "security_token", None)
        if security_token:
            return security_token

        security_token = getattr(self._credentials, "securityToken", None)
        if security_token:
            return security_token

        return None

    def _sign_request_v11(self, method: str, full_url: str, **kwargs) -> dict:
        """Sign the HTTP request using V11-HMAC-SHA256 algorithm (without body)."""
        if not self._credentials:
            from agentarts.sdk.utils.metadata import create_credential
            self._credentials = create_credential()

        if not self._region_id:
            msg = "region_id is required for V11-HMAC-SHA256 signing"
            raise ValueError(msg)

        parsed_url = urlparse(full_url)
        host = parsed_url.netloc
        path = parsed_url.path or "/"

        query_params = kwargs.get("params", {})

        headers = kwargs.get("headers", {}) or {}
        headers["host"] = host
        headers["x-sdk-content-sha256"] = "UNSIGNED-PAYLOAD"

        data = kwargs.get("data")
        json_data = kwargs.get("json")

        if data is not None:
            if isinstance(data, dict):
                import urllib.parse
                urllib.parse.urlencode(data)
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                pass
        elif json_data is not None:
            import json
            json.dumps(json_data)
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"


        security_token = self._get_security_token()
        if security_token:
            headers["X-Security-Token"] = security_token

        signer = V11Signer(
            ak=self._credentials.ak,
            sk=self._credentials.sk,
            region_id=self._region_id
        )

        headers = signer.sign(
            method=method,
            path=path,
            query_params=query_params,
            headers=headers
        )

        if "headers" not in kwargs or kwargs["headers"] is None:
            kwargs["headers"] = {}
        kwargs["headers"] = headers

        return kwargs

    def _sign_request_sdk(self, method: str, full_url: str, **kwargs) -> dict:
        """Sign the HTTP request using SDK-HMAC-SHA256 algorithm (with body)."""
        if not self._sdk_signer:
            from agentarts.sdk.utils.metadata import create_credential
            self._sdk_signer = SDKSigner(credentials=create_credential())

        headers = kwargs.get("headers", {}) or {}
        data = kwargs.get("data")
        json_data = kwargs.get("json")

        body = None
        if data is not None:
            if isinstance(data, dict):
                import urllib.parse
                body = urllib.parse.urlencode(data)
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                body = data
        elif json_data is not None:
            import json
            body = json.dumps(json_data)
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"

        query_params = kwargs.get("params")
        params_list = None
        if query_params:
            params_list = [(k, v) for k, v in query_params.items()]

        signed_headers = self._sdk_signer.sign(
            method=method,
            url=full_url,
            headers=headers,
            body=body,
            query_params=params_list,
        )

        if "headers" not in kwargs or kwargs["headers"] is None:
            kwargs["headers"] = {}
        kwargs["headers"].update(signed_headers)

        return kwargs

    def _sign_request(self, method: str, full_url: str, **kwargs) -> dict:
        """Sign the HTTP request using AK/SK based on sign_mode."""
        if self._sign_mode == SignMode.V11_HMAC_SHA256:
            return self._sign_request_v11(method, full_url, **kwargs)
        return self._sign_request_sdk(method, full_url, **kwargs)

    def _request(self, method: str, url: str, **kwargs) -> RequestResult:
        """
        Execute HTTP request and return a RequestResult.

        The response body is **not** consumed immediately.  Instead the
        ``Content-Type`` header is inspected:

        - If it matches a streaming type (e.g. ``text/event-stream``),
          a streaming ``RequestResult`` is returned.  The caller must
          consume the body via ``iter_lines()`` / ``iter_bytes()`` and
          eventually call ``close()`` (or let the iterator exhaust).

        - Otherwise the body is read into memory and parsed as JSON
          (falling back to plain text).

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Relative URL path (appended to base_url).
            **kwargs: Additional arguments forwarded to
                ``requests.Session.request`` (e.g. ``json``, ``data``,
                ``params``, ``headers``).

        Returns:
            A RequestResult with status, headers, and parsed/streaming body.
        """
        full_url = self._config.base_url + url

        if self._open_ak_sk:
            kwargs = self._sign_request(method, full_url, **kwargs)

        timeout = kwargs.pop("timeout", self._config.timeout)

        try:
            response = self._session.request(
                method,
                full_url,
                timeout=timeout,
                verify=self._config.verify_ssl,
                stream=True,
                **kwargs,
            )

            content_type = response.headers.get("Content-Type", "")
            is_stream = any(ct in content_type for ct in _STREAM_CONTENT_TYPES)

            if is_stream:
                return RequestResult(
                    success=response.ok,
                    status_code=response.status_code,
                    data=None,
                    headers=dict(response.headers),
                    streaming=True,
                    _raw_response=response,
                )

            try:
                data = response.json()
            except Exception:
                data = response.text if response.content else None
            response.close()

            error_msg = None
            if not response.ok:
                if isinstance(data, dict):
                    error_msg = data.get("error") or data.get("message") or data.get("error_msg") or response.text
                else:
                    error_msg = response.text or f"HTTP {response.status_code}"

            return RequestResult(
                success=response.ok,
                status_code=response.status_code,
                data=data,
                error=error_msg,
                headers=dict(response.headers),
            )

        except requests.Timeout as e:
            return RequestResult(
                success=False,
                status_code=0,
                error=f"Request timeout: {e}",
            )
        except requests.RequestException as e:
            return RequestResult(
                success=False,
                status_code=0,
                error=f"Request error: {e}",
            )
        except Exception as e:
            return RequestResult(
                success=False,
                status_code=0,
                error=f"Unexpected error: {e}",
            )

    def get(self, url: str, params: dict | None = None, **kwargs) -> RequestResult:
        """Send GET request."""
        if params:
            kwargs["params"] = params
        return self._request("GET", url, **kwargs)

    def post(
        self, url: str, data: Any | None = None, json: Any | None = None, **kwargs
    ) -> RequestResult:
        """Send POST request."""
        if data is not None:
            kwargs["data"] = data
        if json is not None:
            kwargs["json"] = json
        return self._request("POST", url, **kwargs)

    def put(
        self, url: str, data: Any | None = None, json: Any | None = None, **kwargs
    ) -> RequestResult:
        """Send PUT request."""
        if data is not None:
            kwargs["data"] = data
        if json is not None:
            kwargs["json"] = json
        return self._request("PUT", url, **kwargs)

    def patch(
        self, url: str, data: Any | None = None, json: Any | None = None, **kwargs
    ) -> RequestResult:
        """Send PATCH request."""
        if data is not None:
            kwargs["data"] = data
        if json is not None:
            kwargs["json"] = json
        return self._request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs) -> RequestResult:
        """Send DELETE request."""
        return self._request("DELETE", url, **kwargs)

    def request(self, method: str, url: str, **kwargs) -> RequestResult:
        """Send request with custom HTTP method."""
        return self._request(method, url, **kwargs)

    def set_header(self, key: str, value: str):
        """Set default header for all subsequent requests."""
        self._config.headers[key] = value
        self._session.headers[key] = value

    def set_auth_token(self, token: str, scheme: str = "Bearer"):
        """Set authorization token for all subsequent requests."""
        self.set_header("Authorization", f"{scheme} {token}")

    def clear_auth(self):
        """Remove authorization header."""
        self._config.headers.pop("Authorization", None)
        self._session.headers.pop("Authorization", None)

    def close(self):
        """Close the underlying HTTP session."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
