"""
Agent Memory SDK - Control Plane
控制面：管理Space资源的创建、查询、更新、删除以及策略管理

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
    控制面API - Space资源管理

    使用方式:
        >>> # 一般通过 MemoryClient 使用，不直接实例化 ControlPlane
        >>> # 此类由 MemoryClient 内部使用
    """

    def __init__(self, region_name: Optional[str] = None):
        """
        初始化控制面

        Args:
            region_name: 华为云区域名称（可选）
        """
        self.client = MemoryHttpService(
            region_name=region_name,
            endpoint_type="manager"
        )
        logger.info("ControlPlane initialized")

    def _create_api_key(self) -> ApiKeyInfo:
        """
        创建API Key
        
        Returns:
            API Key信息，包含id和api_key字段
            
        Raises:
            Exception: 如果API Key创建失败
        """
        logger.info("Creating API Key")

        # 调用API创建API Key
        # 如果不需要请求体，直接向 /v1/core/spaces/key 发送POST请求
        result = self.client.create_api_key()
        logger.info(f"API Key created successfully. ID: {result.get('id')}")
        return ApiKeyInfo.from_dict(result)

    # ==================== Space 管理 ====================

    def create_space(self, request: SpaceCreateRequest) -> SpaceInfo:
        """
        创建Space

        Args:
            request: Space创建请求，包含必填字段:
                - name: Space名称
                - message_ttl_hours: 消息TTL（小时）

        Returns:
            创建的Space信息，包含id和自动生成的api_key等字段

        Example:
            >>> # 基本创建（默认开启公网访问）
            >>> request = SpaceCreateRequest(
            ...     name="my-space",
            ...     message_ttl_hours=168
            ... )
            >>> space = cp.create_space(request)
            >>> print(space['id'])
            
            >>> # 创建带有内网访问的Space
            >>> request = SpaceCreateRequest(
            ...     name="private-space",
            ...     message_ttl_hours=168,
            ...     private_vpc_id="vpc-123",
            ...     private_subnet_id="subnet-456"
            ... )
            >>> space = cp.create_space(request)
            
            >>> # 禁用公网访问
            >>> request = SpaceCreateRequest(
            ...     name="no-public-space",
            ...     message_ttl_hours=168,
            ...     public_access_enable=False
            ... )
        """
        # 自动创建API Key并获取其ID
        api_key_info = self._create_api_key()
        api_key_id = api_key_info.id
        api_key = api_key_info.api_key

        logger.info(f"Creating space: {request.name}")

        # 直接使用用户请求的to_dict()方法，并在结果中添加api_key_id
        api_request_dict = request.to_dict()
        api_request_dict["api_key_id"] = api_key_id

        result = self.client.create_space(api_request_dict)

        result["api_key"] = api_key
        result["api_key_id"] = api_key_id
        logger.info(f"Space created: {result.get('id')}")
        return SpaceInfo.from_dict(result)

    def get_space(self, space_id: str) -> SpaceInfo:
        """
        获取Space详情

        Args:
            space_id: Space ID

        Returns:
            Space详细信息
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
        列出Spaces

        Args:
            limit: 每页数量 (1-100)
            offset: 偏移量

        Returns:
            包含items和total的字典

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
        更新Space配置

        Args:
            space_id: Space ID
            request: Space更新请求

        Returns:
            更新后的Space信息

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
        删除Space

        Args:
            space_id: Space ID
        """
        logger.info(f"Deleting space: {space_id}")

        self.client.delete_space(space_id)

        logger.info(f"Space deleted: {space_id}")
