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

import hashlib
import hmac
import datetime
from enum import Enum
from typing import Any, Dict, Iterator, Optional
from dataclasses import dataclass, field
from urllib.parse import urlparse, quote, unquote

import requests

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
    """Configuration for HTTP requests."""

    base_url: str = ""
    timeout: float = 30.0
    headers: Dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True


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
    error: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
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
            raise RuntimeError("iter_lines() is only available for streaming results")

        for line in self._raw_response.iter_lines():
            yield line

    def iter_bytes(self) -> Iterator[bytes]:
        """
        Iterate over raw byte chunks.

        Only valid for streaming results.  Each yielded value is a
        chunk of bytes as received from the server.

        The underlying response is automatically closed after the
        iterator is exhausted.
        """
        if not self.streaming or self._raw_response is None:
            raise RuntimeError("iter_bytes() is only available for streaming results")

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
        config: Optional[RequestConfig] = None,
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

    def _urlencode(self, s: str) -> str:
        """URL encode with safe characters."""
        return quote(s, safe="~")

    def _get_timestamp(self) -> str:
        """Get current timestamp in SDK format."""
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    def _hex_encode_sha256(self, data: bytes) -> str:
        """Hex encode SHA256 hash."""
        return hashlib.sha256(data).hexdigest()

    def _hkdf(self, key: str, secret: str, info: str, length: int = 32) -> str:
        """Derive signing key using HKDF algorithm."""
        salt = bytearray(key, "utf-8")
        ikm = bytearray(secret, "utf-8")
        info_bytes = bytearray(info, "utf-8")

        prk = hmac.new(salt, ikm, hashlib.sha256).digest()

        okm = b""
        t = b""
        for i in range(1, (length + 32) // 32 + 1):
            new_info = t + info_bytes + bytes([i])
            t = hmac.new(prk, new_info, hashlib.sha256).digest()
            okm += t

        return okm[:length].hex()

    def _canonical_uri(self, path: str) -> str:
        """Build canonical URI path."""
        patterns = unquote(path).split("/")
        uri = []
        for value in patterns:
            uri.append(self._urlencode(value))
        url_path = "/".join(uri)
        if url_path and url_path[-1] != "/":
            url_path = url_path + "/"
        return url_path

    def _canonical_query_string(self, query_params: Optional[Dict[str, Any]]) -> str:
        """Build canonical query string."""
        if not query_params:
            return ""

        keys = sorted(query_params.keys())
        arr = []
        for key in keys:
            ke = self._urlencode(key)
            value = query_params[key]
            if isinstance(value, list):
                sorted_values = sorted(str(v) for v in value)
                for v in sorted_values:
                    arr.append(f"{ke}={self._urlencode(v)}")
            else:
                arr.append(f"{ke}={self._urlencode(str(value))}")
        return "&".join(arr)

    def _canonical_headers(self, headers: Dict[str, str], signed_headers: list) -> str:
        """Build canonical headers string."""
        _headers = {}
        for k, v in headers.items():
            key_lower = k.lower()
            value_stripped = v.strip()
            _headers[key_lower] = value_stripped

        arr = []
        for k in signed_headers:
            arr.append(f"{k}:{_headers.get(k, '')}")
        return "\n".join(arr) + "\n"

    def _signed_headers(self, headers: Dict[str, str]) -> list:
        """Get sorted list of signed header names."""
        arr = [k.lower() for k in headers.keys()]
        arr.sort()
        return arr

    def _sign_request_v11(self, method: str, full_url: str, **kwargs) -> dict:
        """Sign the HTTP request using V11-HMAC-SHA256 algorithm (without body)."""
        if not self._credentials:
            from agentarts.sdk.utils.metadata import create_credential
            self._credentials = create_credential()

        if not self._region_id:
            raise ValueError("region_id is required for V11-HMAC-SHA256 signing")

        parsed_url = urlparse(full_url)
        host = parsed_url.netloc
        path = parsed_url.path or "/"

        query_params = kwargs.get("params", {})

        timestamp = self._get_timestamp()
        date_str = timestamp[:8]

        headers = kwargs.get("headers", {}) or {}
        headers["host"] = host
        headers["x-sdk-date"] = timestamp
        headers["x-sdk-content-sha256"] = "UNSIGNED-PAYLOAD"

        signed_headers = self._signed_headers(headers)
        canonical_request = (
            f"{method.upper()}\n"
            f"{self._canonical_uri(path)}\n"
            f"{self._canonical_query_string(query_params)}\n"
            f"{self._canonical_headers(headers, signed_headers)}\n"
            f"{';'.join(signed_headers)}\n"
            f"UNSIGNED-PAYLOAD"
        )

        credential_scope = f"{date_str}/{self._region_id}/apic"
        hashed_canonical_request = self._hex_encode_sha256(canonical_request.encode("utf-8"))

        string_to_sign = (
            f"V11-HMAC-SHA256\n"
            f"{timestamp}\n"
            f"{credential_scope}\n"
            f"{hashed_canonical_request}"
        )

        real_use_secret = self._hkdf(self._credentials.ak, self._credentials.sk, credential_scope)
        signature = hmac.new(
            real_use_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        authorization = (
            f"V11-HMAC-SHA256 "
            f"Credential={self._credentials.ak}/{credential_scope}, "
            f"SignedHeaders={';'.join(signed_headers)}, "
            f"Signature={signature}"
        )

        headers["Authorization"] = authorization

        if "headers" not in kwargs or kwargs["headers"] is None:
            kwargs["headers"] = {}
        kwargs["headers"].update(headers)

        return kwargs

    def _sign_request_sdk(self, method: str, full_url: str, **kwargs) -> dict:
        """Sign the HTTP request using SDK-HMAC-SHA256 algorithm (with body)."""
        try:
            from huaweicloudsdkcore.signer.signer import Signer
            from huaweicloudsdkcore.sdk_request import SdkRequest
        except ImportError as e:
            raise ImportError(
                "Huawei Cloud SDK is required for AK/SK signing. "
                "Install it with: pip install huaweicloudsdkcore>=3.1.0"
            ) from e

        from agentarts.sdk.utils.metadata import create_credential

        if not self._signer:
            self._credentials = create_credential()
            self._signer = Signer(self._credentials)

        parsed_url = urlparse(full_url)
        schema = parsed_url.scheme
        host = parsed_url.netloc
        resource_path = parsed_url.path
        if parsed_url.query:
            resource_path += f"?{parsed_url.query}"

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

        schema = schema or "https"
        host = host or ""
        resource_path = resource_path or "/"

        query_params_list = []
        query_params = kwargs.get("params")
        if query_params:
            for key, value in query_params.items():
                query_params_list.append((key, value))

        sdk_request = SdkRequest(
            method=method,
            schema=schema,
            host=host,
            resource_path=resource_path,
            header_params=headers,
            body=body,
            query_params=query_params_list,
        )

        signed_request = self._signer.sign(sdk_request)

        if "headers" not in kwargs or kwargs["headers"] is None:
            kwargs["headers"] = {}
        if hasattr(signed_request, "header_params") and signed_request.header_params:
            kwargs["headers"].update(signed_request.header_params)

        return kwargs

    def _sign_request(self, method: str, full_url: str, **kwargs) -> dict:
        """Sign the HTTP request using AK/SK based on sign_mode."""
        if self._sign_mode == SignMode.V11_HMAC_SHA256:
            return self._sign_request_v11(method, full_url, **kwargs)
        else:
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

    def get(self, url: str, params: Optional[Dict] = None, **kwargs) -> RequestResult:
        """Send GET request."""
        if params:
            kwargs["params"] = params
        return self._request("GET", url, **kwargs)

    def post(
        self, url: str, data: Optional[Any] = None, json: Optional[Any] = None, **kwargs
    ) -> RequestResult:
        """Send POST request."""
        if data is not None:
            kwargs["data"] = data
        if json is not None:
            kwargs["json"] = json
        return self._request("POST", url, **kwargs)

    def put(
        self, url: str, data: Optional[Any] = None, json: Optional[Any] = None, **kwargs
    ) -> RequestResult:
        """Send PUT request."""
        if data is not None:
            kwargs["data"] = data
        if json is not None:
            kwargs["json"] = json
        return self._request("PUT", url, **kwargs)

    def patch(
        self, url: str, data: Optional[Any] = None, json: Optional[Any] = None, **kwargs
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

    def __enter__(self) -> "BaseHTTPClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
