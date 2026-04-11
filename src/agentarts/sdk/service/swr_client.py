"""
SWR (SoftWare Repository for Container) Client

Provides a high-level client for interacting with Huawei Cloud SWR service.
Used for managing container image repositories during deployment.

Usage::

    from agentarts.sdk.service import SWRClient

    client = SWRClient(region="cn-north-4")

    # Create or get organization
    org = client.create_or_get_organization("my-org")

    # Create or get repository
    repo = client.create_or_get_repository("my-org", "my-repo")

    # Create SWR secret for Docker login
    login_server, username, password = client.create_swr_secret()

    # Get full image name
    image_name = client.get_full_image_name("my-org", "my-repo", "v1.0.0")
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, Optional, Tuple

from huaweicloudsdkcore.region.region import Region

from agentarts.sdk.utils.constant import get_swr_endpoint

log = logging.getLogger(__name__)


class SWRClient:
    """
    Client for Huawei Cloud SWR (SoftWare Repository for Container) service.

    Provides high-level methods for managing container image repositories,
    including organization and repository management, authentication,
    and image deployment.

    Args:
        region: Huawei Cloud region (e.g., "cn-north-4").
        endpoint: Override SWR endpoint URL.
            If ``None``, the URL is derived from the region.
    """

    def __init__(
        self,
        region: str,
        endpoint: Optional[str] = None,
    ) -> None:
        from agentarts.sdk.utils.constant import get_swr_endpoint

        self._region = region
        self._endpoint = endpoint or get_swr_endpoint(region)
        self._swr_registry = f"swr.{region}.myhuaweicloud.com"
        self._client = None
        self._credentials = None

    def _get_credentials(self):
        """Get or create credentials."""
        if self._credentials is not None:
            return self._credentials

        from agentarts.sdk.utils.metadata import create_credential

        self._credentials = create_credential()
        return self._credentials

    def _get_client(self):
        """Get or create SWR client instance."""
        if self._client is not None:
            return self._client

        try:
            from huaweicloudsdkcore.http.http_config import HttpConfig
            from huaweicloudsdkswr.v2 import SwrClient
            from huaweicloudsdkswr.v2.region.swr_region import SwrRegion

            credentials = self._get_credentials()

            http_config = HttpConfig.get_default_config()
            http_config.ignore_ssl_verification = True

            try:
                swr_region = SwrRegion.value_of(self._region)
            except Exception:
                swr_region = Region(id=self._region, endpoint=get_swr_endpoint())

            self._client = SwrClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(swr_region) \
                .with_http_config(http_config) \
                .build()

            return self._client

        except ImportError as e:
            raise ImportError(
                "Huawei Cloud SWR SDK not installed. "
                "Install it with: pip install huaweicloudsdkswr"
            ) from e

    @staticmethod
    def _get_attr_value(obj: Any, attr: str) -> Any:
        """Get attribute value from object safely."""
        if obj is None:
            return None
        if hasattr(obj, attr):
                return getattr(obj, attr)
        if isinstance(obj, dict):
            return obj.get(attr)
        return None

    def get_organization(self, organization: str) -> Optional[Dict[str, Any]]:
        """
        Get organization details.

        Args:
            organization: Organization name.

        Returns:
            Organization details dict, or None if not found.
        """
        try:
            from huaweicloudsdkswr.v2 import ShowNamespaceRequest

            client = self._get_client()
            request = ShowNamespaceRequest(namespace=organization)
            response = client.show_namespace(request)

            return {
                "id": response.id,
                "name": response.name,
                "creator_name": response.creator_name,
            }

        except Exception as e:
            log.debug("Organization '%s' not found: %s", organization, e)
            return None

    def create_organization(
        self,
        organization: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new organization.

        Args:
            organization: Organization name.

        Returns:
            Created organization details dict, or None if failed.
        """
        try:
            from huaweicloudsdkswr.v2 import (
                CreateNamespaceRequest,
                CreateNamespaceRequestBody,
            )

            client = self._get_client()

            body = CreateNamespaceRequestBody(namespace=organization)
            request = CreateNamespaceRequest(body=body)
            response = client.create_namespace(request)

            log.info("Created SWR organization: %s", organization)

            return {
                "id": response.id,
                "name": response.name,
                "creator_name": response.creator_name,
            }

        except Exception as e:
            log.error("Failed to create organization '%s': %s", organization, e)
            return None

    def create_or_get_organization(
        self,
        organization: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Create or get organization.

        If the organization already exists, returns its details.
        Otherwise, creates a new organization.

        Args:
            organization: Organization name.

        Returns:
            Organization details dict, or None if failed.
        """
        existing = self.get_organization(organization)
        if existing is not None:
            log.debug("Organization '%s' already exists", organization)
            return existing

        return self.create_organization(organization)

    def get_repository(
        self,
        organization: str,
        repository: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get repository details.

        Args:
            organization: Organization name.
            repository: Repository name.

        Returns:
            Repository details dict, or None if not found.
        """
        try:
            from huaweicloudsdkswr.v2 import ShowRepoRequest

            client = self._get_client()
            request = ShowRepoRequest(namespace=organization, repository=repository)
            response = client.show_repo(request)

            return {
                "id": response.id,
                "name": response.name,
                "namespace": response.namespace,
                "is_public": response.is_public,
            }

        except Exception as e:
            log.debug("Repository '%s/%s' not found: %s", organization, repository, e)
            return None

    def create_repository(
        self,
        organization: str,
        repository: str,
        is_public: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new repository.

        Args:
            organization: Organization name.
            repository: Repository name.
            is_public: Whether the repository is public.

        Returns:
            Created repository details dict, or None if failed.
        """
        try:
            from huaweicloudsdkswr.v2 import (
                CreateRepoRequest,
                CreateRepoRequestBody,
            )

            client = self._get_client()

            body = CreateRepoRequestBody(
                repository=repository,
                is_public=is_public,
            )
            request = CreateRepoRequest(namespace=organization, body=body)
            response = client.create_repo(request)

            log.info("Created SWR repository: %s/%s", organization, repository)

            return {
                "id": response.id,
                "name": response.name,
                "namespace": response.namespace,
                "is_public": response.is_public,
            }

        except Exception as e:
            log.error("Failed to create repository '%s/%s': %s", organization, repository, e)
            return None

    def create_or_get_repository(
        self,
        organization: str,
        repository: str,
        is_public: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Create or get repository.

        If the repository already exists, returns her details.
        Otherwise, creates a new repository.

        Args:
            organization: Organization name.
            repository: Repository name.
            is_public: Whether the repository is public (only used when creating).

        Returns:
            Repository details dict, or None if failed.
        """
        existing = self.get_repository(organization, repository)
        if existing is not None:
            log.debug("Repository '%s/%s' already exists", organization, repository)
            return existing

        return self.create_repository(organization, repository, is_public)

    def create_swr_secret(self) -> Tuple[str, str, str]:
        """
        Create SWR secret for Docker login.

        Uses SWR SDK to create a secret that contains Docker login credentials.

        Returns:
            Tuple of (login_server, username, password) if successful,
            Tuple of (login_server, "", "") if failed.
        """
        login_server = self._swr_registry

        try:
            from huaweicloudsdkswr.v2 import CreateSecretRequest

            request = CreateSecretRequest()
            request.projectname = self._region.split(".")[0]
            response = self._get_client().create_secret(request)

            auths = self._get_attr_value(response, "auths")
            auth_info = self._get_attr_value(auths, login_server)
            auth_data = self._get_attr_value(auth_info, "auth")

            if auth_data:
                decoded_auth = base64.b64decode(auth_data).decode("utf-8")
                username, password = decoded_auth.split(":", 1)
                log.info("Created SWR secret for region: %s", self._region)
                return login_server, username, password

            log.warning("No auth data found in SWR secret response")
            return login_server, "", ""

        except Exception as e:
            log.error("Failed to create SWR secret: %s", e)
            return login_server, "", ""

    def get_full_image_name(
        self,
        organization: str,
        repository: str,
        tag: str = "latest",
    ) -> str:
        """
        Get full SWR image name.

        Args:
            organization: Organization name.
            repository: Repository name.
            tag: Image tag.

        Returns:
            Full image name (e.g., swr.cn-north-4.myhuaweicloud.com/org/repo:tag).
        """
        return f"{self._swr_registry}/{organization}/{repository}:{tag}"
