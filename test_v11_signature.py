"""Test V11-HMAC-SHA256 signature implementation based on official SDK."""

import hashlib
import hmac
import datetime
from urllib.parse import quote, unquote
from typing import Any, Dict, Optional


class MockCredentials:
    """Mock credentials for testing."""

    def __init__(self, ak: str, sk: str):
        self.ak = ak
        self.sk = sk


class V11SignatureTester:
    """Test V11 signature generation based on official ApiGateway SDK."""

    def __init__(self, ak: str, sk: str, region_id: str):
        self._credentials = MockCredentials(ak, sk)
        self._region_id = region_id

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

    def sign_request(self, method: str, url: str, headers: Optional[Dict[str, str]] = None, query_params: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Sign the HTTP request using V11-HMAC-SHA256 algorithm."""
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        host = parsed_url.netloc
        path = parsed_url.path or "/"

        timestamp = self._get_timestamp()
        date_str = timestamp[:8]

        headers = headers or {}
        headers["host"] = host
        headers["X-Sdk-Date"] = timestamp
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
        return headers


def test_v11_signature():
    """Test V11 signature generation."""
    ak = "TEST_ACCESS_KEY"
    sk = "TEST_SECRET_KEY"
    region_id = "cn-southwest-2"

    tester = V11SignatureTester(ak, sk, region_id)

    url = "https://example.cn-southwest-2.myhuaweicloud.com/api/v1/test"
    method = "POST"
    query_params = {"param1": "value1", "param2": "value2"}

    headers = tester.sign_request(method, url, query_params=query_params)

    print("=" * 70)
    print("V11-HMAC-SHA256 Signature Test (Based on Official SDK)")
    print("=" * 70)
    print()
    print("Request Info:")
    print(f"  Method: {method}")
    print(f"  URL: {url}")
    print(f"  Query Params: {query_params}")
    print()
    print("Generated Headers:")
    print("-" * 50)
    for key, value in sorted(headers.items()):
        if key == "Authorization":
            print(f"  {key}:")
            parts = value.replace("V11-HMAC-SHA256 ", "").split(", ")
            for part in parts:
                print(f"      {part}")
        else:
            print(f"  {key}: {value}")
    print()
    print("=" * 70)
    print()
    print("Signature Components:")
    print("-" * 50)
    print(f"  Algorithm: V11-HMAC-SHA256")
    print(f"  Access Key: {ak}")
    print(f"  Region ID: {region_id}")
    print(f"  Timestamp: {headers['X-Sdk-Date']}")
    print(f"  Content SHA256: {headers['x-sdk-content-sha256']}")
    auth = headers["Authorization"]
    credential = auth.split("Credential=")[1].split(",")[0]
    print(f"  Credential Scope: {credential}")
    print()
    print("=" * 70)


def test_v11_signature_with_custom_headers():
    """Test V11 signature with custom headers."""
    ak = "MY_AK_12345"
    sk = "MY_SK_67890"
    region_id = "cn-north-4"

    tester = V11SignatureTester(ak, sk, region_id)

    url = "https://agentarts.cn-north-4.myhuaweicloud.com/v1/core/runtimes"
    method = "GET"

    custom_headers = {
        "Content-Type": "application/json",
        "X-Custom-Header": "custom-value",
    }

    headers = tester.sign_request(method, url, custom_headers)

    print("=" * 70)
    print("V11-HMAC-SHA256 Signature Test (with custom headers)")
    print("=" * 70)
    print()
    print("Request Info:")
    print(f"  Method: {method}")
    print(f"  URL: {url}")
    print()
    print("Generated Headers:")
    print("-" * 50)
    for key, value in sorted(headers.items()):
        if key == "Authorization":
            print(f"  {key}:")
            parts = value.replace("V11-HMAC-SHA256 ", "").split(", ")
            for part in parts:
                print(f"      {part}")
        else:
            print(f"  {key}: {value}")
    print()
    print("=" * 70)


if __name__ == "__main__":
    test_v11_signature()
    print()
    test_v11_signature_with_custom_headers()
