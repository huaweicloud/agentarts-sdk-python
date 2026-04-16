"""SDK Request Signing Utilities.

This module provides signing utilities for Huawei Cloud API requests.
"""

import logging
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SDKSigner:
    """SDK-HMAC-SHA256 signer for Huawei Cloud API requests.

    This class encapsulates the signing logic using huaweicloudsdkcore.
    """

    def __init__(self, credentials=None):
        """
        Initialize the SDK signer.

        Args:
            credentials: Huawei Cloud credentials (BasicCredentials).
                        If not provided, will be loaded from environment.
        """
        self._credentials = credentials
        self._signer = None

        if credentials:
            self._init_signer()

    def _init_signer(self):
        """Initialize the signer with credentials."""
        try:
            from huaweicloudsdkcore.signer.signer import Signer
            self._signer = Signer(self._credentials)
        except ImportError as e:
            msg = (
                "Huawei Cloud SDK is required for AK/SK signing. "
                "Install it with: pip install huaweicloudsdkcore>=3.1.0"
            )
            raise ImportError(
                msg
            ) from e

    def _ensure_signer(self):
        """Ensure signer is initialized."""
        if not self._signer:
            if not self._credentials:
                from agentarts.sdk.utils.metadata import create_credential
                self._credentials = create_credential()
            self._init_signer()

    @property
    def credentials(self):
        """Get credentials."""
        return self._credentials

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

    def sign(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: str | None = None,
        query_params: list[tuple[str, Any]] | None = None,
    ) -> dict[str, str]:
        """
        Sign an HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL
            headers: Request headers (will be updated with signature)
            body: Request body as string
            query_params: Query parameters as list of tuples [(key, value), ...]

        Returns:
            Updated headers dict with signature
        """
        self._ensure_signer()

        from huaweicloudsdkcore.sdk_request import SdkRequest

        parsed_url = urlparse(url)
        schema = parsed_url.scheme or "https"
        host = parsed_url.netloc
        resource_path = parsed_url.path or "/"

        sdk_request = SdkRequest(
            method=method,
            schema=schema,
            host=host,
            resource_path=resource_path,
            header_params=headers.copy(),
            body=body,
            query_params=query_params or [],
        )

        signed_request = self._signer.sign(sdk_request)

        if hasattr(signed_request, "header_params") and signed_request.header_params:
            headers.update(signed_request.header_params)

        security_token = self._get_security_token()
        if security_token:
            headers["X-Security-Token"] = security_token

        return headers


def create_sdk_signer(credentials=None) -> SDKSigner:
    """
    Create an SDK signer instance.

    Args:
        credentials: Optional credentials. If not provided, will load from environment.

    Returns:
        SDKSigner instance
    """
    return SDKSigner(credentials=credentials)


def sign_request(
    method: str,
    url: str,
    headers: dict[str, str],
    body: str | None = None,
    query_params: dict[str, Any] | None = None,
    credentials=None,
) -> dict[str, str]:
    """
    Sign an HTTP request using SDK-HMAC-SHA256 algorithm.

    This is a convenience function that creates a signer and signs the request.
    For repeated signing, it's more efficient to create a SDKSigner instance.

    Args:
        method: HTTP method
        url: Full URL
        headers: Request headers
        body: Request body as string
        query_params: Query parameters as dict
        credentials: Optional credentials

    Returns:
        Updated headers dict with signature
    """
    signer = SDKSigner(credentials=credentials)

    params_list = None
    if query_params:
        params_list = [(k, v) for k, v in query_params.items()]

    return signer.sign(
        method=method,
        url=url,
        headers=headers,
        body=body,
        query_params=params_list,
    )
