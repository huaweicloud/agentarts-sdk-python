#
# Copyright (c) Huawei Technologies CO., Ltd. 2025. All rights reserved.
#

import hashlib
import hmac
from datetime import datetime, timezone
from urllib.parse import quote, unquote

APIC = "apic"
UTF8 = "utf-8"
DATE_FORMAT = "%Y%m%dT%H%M%SZ"
ALGORITHM = "V11-HMAC-SHA256"


class V11Signer:
    """V11-HMAC-SHA256 signer for Huawei Cloud API requests."""

    def __init__(self, ak: str, sk: str, region_id: str):
        """
        Initialize V11 signer.

        Args:
            ak: Access Key
            sk: Secret Key
            region_id: Region ID (e.g., cn-southwest-2)
        """
        self.ak = ak
        self.sk = sk
        self.region_id = region_id
        self.hash_func = hashlib.sha256
        self.algorithm = ALGORITHM
        self._credential_scope = ""

    def _urlencode(self, s: str) -> str:
        """URL encode with safe characters."""
        return quote(s, safe="~")

    def _get_timestamp(self) -> str:
        """Get current timestamp in SDK format."""
        return datetime.now(timezone.utc).strftime(DATE_FORMAT)

    def _hex_encode_sha256(self, data: bytes) -> str:
        """Hex encode SHA256 hash."""
        return hashlib.sha256(data).hexdigest()

    def _hkdf(self, key: str, secret: str, info: str, length: int = 32) -> str:
        """Derive signing key using HKDF algorithm."""
        salt = bytearray(key, UTF8)
        ikm = bytearray(secret, UTF8)
        info_bytes = bytearray(info, UTF8)

        prk = hmac.new(salt, ikm, self.hash_func).digest()

        okm = b""
        t = b""
        for i in range(1, (length + 32) // 32 + 1):
            new_info = t + info_bytes + bytes([i])
            t = hmac.new(prk, new_info, self.hash_func).digest()
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

    def _canonical_query_string(self, query_params: dict | None) -> str:
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

    def _canonical_headers(self, headers: dict[str, str], signed_headers: list[str]) -> str:
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

    def _signed_headers(self, headers: dict[str, str]) -> list[str]:
        """Get sorted list of signed header names."""
        arr = [k.lower() for k in headers]
        arr.sort()
        return arr

    def _set_credential_scope(self, time_str: str):
        """Set credential scope from timestamp."""
        formatted_date = time_str[:8]
        self._credential_scope = f"{formatted_date}/{self.region_id}/{APIC}"

    def _get_string_to_sign(self, canonical_request: str, time_str: str) -> str:
        """Build string to sign."""
        hashed_canonical_request = self._hex_encode_sha256(canonical_request.encode(UTF8))
        self._set_credential_scope(time_str)
        return f"{self.algorithm}\n{time_str}\n{self._credential_scope}\n{hashed_canonical_request}"

    def _sign_string_to_sign(self, real_use_secret: str, string_to_sign: str) -> str:
        """Sign the string to sign."""
        return hmac.new(
            real_use_secret.encode(UTF8),
            string_to_sign.encode(UTF8),
            self.hash_func
        ).hexdigest()

    def _get_real_use_secret(self) -> str:
        """Get derived signing key."""
        return self._hkdf(self.ak, self.sk, self._credential_scope)

    def _get_auth_header_value(self, signed_headers: list[str], signature: str) -> str:
        """Build Authorization header value."""
        return f"{self.algorithm} Credential={self.ak}/{self._credential_scope}, SignedHeaders={';'.join(signed_headers)}, Signature={signature}"

    def sign(
        self,
        method: str,
        path: str,
        query_params: dict | None,
        headers: dict[str, str],
    ) -> dict[str, str]:
        """
        Sign an HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            query_params: Query parameters
            headers: Request headers (will be updated with signature)

        Returns:
            Updated headers dict with signature
        """
        timestamp = self._get_timestamp()

        headers["x-sdk-date"] = timestamp

        signed_headers = self._signed_headers(headers)

        canonical_request = (
            f"{method.upper()}\n"
            f"{self._canonical_uri(path)}\n"
            f"{self._canonical_query_string(query_params)}\n"
            f"{self._canonical_headers(headers, signed_headers)}\n"
            f"{';'.join(signed_headers)}\n"
            f"UNSIGNED-PAYLOAD"
        )

        string_to_sign = self._get_string_to_sign(canonical_request, timestamp)
        real_use_secret = self._get_real_use_secret()
        signature = self._sign_string_to_sign(real_use_secret, string_to_sign)
        auth_value = self._get_auth_header_value(signed_headers, signature)

        headers["Authorization"] = auth_value

        return headers


def create_v11_signer(ak: str, sk: str, region_id: str) -> V11Signer:
    """
    Create a V11 signer instance.

    Args:
        ak: Access Key
        sk: Secret Key
        region_id: Region ID

    Returns:
        V11Signer instance
    """
    return V11Signer(ak=ak, sk=sk, region_id=region_id)
