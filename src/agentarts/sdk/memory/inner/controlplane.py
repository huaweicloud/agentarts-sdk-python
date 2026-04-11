"""
Agent Memory SDK - Control Plane

Control plane: manages Space resource creation, query, update, deletion and policy management.
"""

import logging
from typing import Optional

from ...service.memory_service import MemoryHttpService
from .config import (
    SpaceCreateRequest,
    SpaceUpdateRequest,
    SpaceInfo,
    SpaceListResponse,
    ApiKeyInfo
)

logger = logging.getLogger(__name__)


class _ControlPlane:
    """
    Control Plane API - Space resource management.

    Usage:
        >>> # Generally used through MemoryClient, do not instantiate ControlPlane directly
        >>> # This class is used internally by MemoryClient
    """

    def __init__(self, region_name: Optional[str] = None):
        """
        Initialize control plane.

        Args:
            region_name: Huawei Cloud region name (optional)
        """
        self.client = MemoryHttpService(
            region_name=region_name,
            endpoint_type="manager"
        )
        logger.info("ControlPlane initialized")

    def _create_api_key(self) -> ApiKeyInfo:
        """
        Create API Key.
        
        Returns:
            API Key information, containing id and api_key fields
            
        Raises:
            Exception: If API Key creation fails
        """
        logger.info("Creating API Key")

        result = self.client.create_api_key()
        logger.info(f"API Key created successfully. ID: {result.get('id')}")
        return ApiKeyInfo.from_dict(result)

    def create_space(self, request: SpaceCreateRequest) -> SpaceInfo:
        """
        Create Space.

        Args:
            request: Space creation request, containing required fields:
                - name: Space name
                - message_ttl_hours: Message TTL (hours)

        Returns:
            Created Space information, containing id and auto-generated api_key fields

        Example:
            >>> # Basic creation (public access enabled by default)
            >>> request = SpaceCreateRequest(
            ...     name="my-space",
            ...     message_ttl_hours=168
            ... )
            >>> space = cp.create_space(request)
            >>> print(space['id'])
            
            >>> # Create Space with private network access
            >>> request = SpaceCreateRequest(
            ...     name="private-space",
            ...     message_ttl_hours=168,
            ...     private_vpc_id="vpc-123",
            ...     private_subnet_id="subnet-456"
            ... )
            >>> space = cp.create_space(request)
            
            >>> # Disable public access
            >>> request = SpaceCreateRequest(
            ...     name="no-public-space",
            ...     message_ttl_hours=168,
            ...     public_access_enable=False
            ... )
        """
        api_key_info = self._create_api_key()
        api_key_id = api_key_info.id
        api_key = api_key_info.api_key

        logger.info(f"Creating space: {request.name}")

        api_request_dict = request.to_dict()
        api_request_dict["api_key_id"] = api_key_id

        result = self.client.create_space(api_request_dict)

        result["api_key"] = api_key
        result["api_key_id"] = api_key_id
        logger.info(f"Space created: {result.get('id')}")
        return SpaceInfo.from_dict(result)

    def get_space(self, space_id: str) -> SpaceInfo:
        """
        Get Space details.

        Args:
            space_id: Space ID

        Returns:
            Space detailed information
        """
        logger.info(f"Getting space: {space_id}")
        result = self.client.get_space(space_id)
        return SpaceInfo.from_dict(result)

    def list_spaces(
            self,
            limit: int = 20,
            offset: int = 0
    ) -> SpaceListResponse:
        """
        List Spaces.

        Args:
            limit: Number per page (1-100)
            offset: Offset

        Returns:
            Dictionary containing items and total

        Example:
            >>> result = cp.list_spaces()
            >>> for space in result['items']:
            ...     print(space['id'], space.get('status'))
        """
        logger.info(f"Listing spaces (limit={limit}, offset={offset})")
        result = self.client.list_spaces(limit, offset)
        return SpaceListResponse.from_dict(result)

    def update_space(self, space_id: str, request: SpaceUpdateRequest) -> SpaceInfo:
        """
        Update Space configuration.

        Args:
            space_id: Space ID
            request: Space update request

        Returns:
            Updated Space information

        Example:
            >>> request = SpaceUpdateRequest(
            ...     message_ttl_hours=336,
            ...     enable_memory_extract=True
            ... )
            >>> space = cp.update_space("space-123", request)
        """
        logger.info(f"Updating space: {space_id}")
        result = self.client.update_space(space_id, request.to_dict())
        logger.info(f"Space updated: {space_id}")
        return SpaceInfo.from_dict(result)

    def delete_space(self, space_id: str) -> None:
        """
        Delete Space.

        Args:
            space_id: Space ID
        """
        logger.info(f"Deleting space: {space_id}")

        self.client.delete_space(space_id)

        logger.info(f"Space deleted: {space_id}")
