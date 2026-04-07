"""Space operations - CRUD for Memory Space."""

import logging
from typing import Any, Dict, List, Optional

from agentarts.sdk.memory import (
    MemoryClient,
    SpaceInfo,
)
from .models import SpaceListResult, SpaceResult

logger = logging.getLogger(__name__)


def _get_client(region: Optional[str] = None) -> MemoryClient:
    """Get MemoryClient instance.

    Uses Huawei Cloud SDK Core credential provider chain (AK/SK).
    Credentials can be provided via:
    - Environment variables: HUAWEICLOUD_SDK_AK, HUAWEICLOUD_SDK_SK
    - Configuration file
    - Metadata service

    Args:
        region: Region name (optional, defaults to cn-north-4)

    Returns:
        MemoryClient instance
    """
    kwargs = {}
    if region:
        kwargs["region_name"] = region
    return MemoryClient(**kwargs)


def _space_info_to_dict(space: SpaceInfo) -> Dict[str, Any]:
    """Convert SpaceInfo object to dictionary for backward compatibility."""
    return {
        "id": space.id,
        "name": space.name,
        "description": space.description,
        "message_ttl_hours": space.message_ttl_hours,
        "status": space.status,
        "created_at": space.created_at,
        "updated_at": space.updated_at,
        "memory_extract_enabled": space.memory_extract_enabled,
        "memory_extract_idle_seconds": space.memory_extract_idle_seconds,
        "memory_extract_max_tokens": space.memory_extract_max_tokens,
        "memory_extract_max_messages": space.memory_extract_max_messages,
        "memory_strategies_builtin": space.memory_strategies_builtin,
        "memory_strategies_customized": space.memory_strategies_customized,
        "api_key": space.api_key,
        "api_key_id": space.api_key_id,
        "public_access": space.public_access,
        "private_access": space.private_access,
    }


def create_space(
        name: str,
        message_ttl_hours: int = 168,
        description: Optional[str] = None,
        memory_extract_idle_seconds: Optional[int] = None,
        memory_extract_max_tokens: Optional[int] = None,
        memory_extract_max_messages: Optional[int] = None,
        memory_strategies_builtin: Optional[List[str]] = None,
        memory_strategies_customized: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[Dict[str, str]]] = None,
        public_access_enable: bool = True,
        private_vpc_id: Optional[str] = None,
        private_subnet_id: Optional[str] = None,
        region: Optional[str] = None,
        **kwargs,
) -> SpaceResult:
    """Create a Memory Space.

    Uses AK/SK authentication via environment variables:
    - HUAWEICLOUD_SDK_AK: Access Key
    - HUAWEICLOUD_SDK_SK: Secret Key

    Args:
        name: Space name, required (1-128 characters)
        message_ttl_hours: Message TTL in hours (default: 168, range: 1-8760)
        description: Space description (optional)
        memory_extract_idle_seconds: Memory extraction idle time in seconds (optional)
        memory_extract_max_tokens: Memory extraction max tokens (optional)
        memory_extract_max_messages: Memory extraction max messages (optional)
        memory_strategies_builtin: Built-in memory strategies (optional list)
        memory_strategies_customized: Custom memory strategies (optional list of dicts)
        tags: Tags for the space (optional list of key-value dicts)
        public_access_enable: Enable public access (default: True)
        private_vpc_id: Private VPC ID (requires private_subnet_id)
        private_subnet_id: Private subnet ID (requires private_vpc_id)
        region: Region name (optional, defaults to cn-north-4)
        **kwargs: Additional parameters (ignored, for backward compatibility)

    Returns:
        SpaceResult with space_id and space details
    """
    try:
        client = _get_client(region=region)

        # 使用关键字参数调用 create_space（适配新 API）
        space = client.create_space(
            name=name,
            message_ttl_hours=message_ttl_hours,
            description=description,
            memory_extract_idle_seconds=memory_extract_idle_seconds,
            memory_extract_max_tokens=memory_extract_max_tokens,
            memory_extract_max_messages=memory_extract_max_messages,
            memory_strategies_builtin=memory_strategies_builtin,
            memory_strategies_customized=memory_strategies_customized,
            tags=tags,
            public_access_enable=public_access_enable,
            private_vpc_id=private_vpc_id,
            private_subnet_id=private_subnet_id,
        )

        space_id = space.id
        space_dict = _space_info_to_dict(space)

        logger.info(f"Space created successfully: {space_id}")
        return SpaceResult(
            success=True,
            space_id=space_id,
            space=space_dict,
        )
    except Exception as e:
        logger.error(f"Failed to create space: {e}")
        return SpaceResult(
            success=False,
            error=str(e),
        )


def get_space(
        space_id: str,
        region: Optional[str] = None,
) -> SpaceResult:
    """Get Space details.

    Args:
        space_id: Space ID
        region: Region name (optional, defaults to cn-north-4)

    Returns:
        SpaceResult with space details
    """
    try:
        client = _get_client(region=region)
        space = client.get_space(space_id)
        space_dict = _space_info_to_dict(space)

        logger.info(f"Retrieved space: {space_id}")
        return SpaceResult(
            success=True,
            space_id=space_id,
            space=space_dict,
        )
    except Exception as e:
        logger.error(f"Failed to get space {space_id}: {e}")
        return SpaceResult(
            success=False,
            space_id=space_id,
            error=str(e),
        )


def list_spaces(
        limit: int = 20,
        offset: int = 0,
        region: Optional[str] = None,
) -> SpaceListResult:
    """List Spaces.

    Args:
        limit: Maximum number of spaces to return (default: 20)
        offset: Offset for pagination (default: 0)
        region: Region name (optional, defaults to cn-north-4)

    Returns:
        SpaceListResult with list of spaces
    """
    try:
        client = _get_client(region=region)
        result = client.list_spaces(limit=limit, offset=offset)

        # 转换为字典列表以保持向后兼容
        spaces = [_space_info_to_dict(space) for space in result.items]
        total = result.total

        logger.info(f"Listed {len(spaces)} spaces")
        return SpaceListResult(
            success=True,
            spaces=spaces,
            total=total,
        )
    except Exception as e:
        logger.error(f"Failed to list spaces: {e}")
        return SpaceListResult(
            success=False,
            error=str(e),
        )


def update_space(
        space_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        message_ttl_hours: Optional[int] = None,
        enable_memory_extract: Optional[bool] = None,
        memory_extract_idle_seconds: Optional[int] = None,
        memory_extract_max_tokens: Optional[int] = None,
        memory_extract_max_messages: Optional[int] = None,
        memory_strategies_builtin: Optional[List[str]] = None,
        tags: Optional[List[Dict[str, str]]] = None,
        region: Optional[str] = None,
        **kwargs,
) -> SpaceResult:
    """Update a Space.

    Args:
        space_id: Space ID
        name: New space name (optional)
        description: New space description (optional)
        message_ttl_hours: New message TTL in hours (optional)
        enable_memory_extract: Enable/disable memory extraction (optional)
        memory_extract_idle_seconds: Memory extraction idle time in seconds (optional)
        memory_extract_max_tokens: Memory extraction max tokens (optional)
        memory_extract_max_messages: Memory extraction max messages (optional)
        memory_strategies_builtin: Built-in memory strategies (optional list)
        tags: Tags for the space (optional list of key-value dicts)
        region: Region name (optional, defaults to cn-north-4)
        **kwargs: Additional update parameters (ignored, for backward compatibility)

    Returns:
        SpaceResult with updated space details
    """
    try:
        client = _get_client(region=region)

        # 使用关键字参数调用 update_space（适配新 API）
        space = client.update_space(
            space_id=space_id,
            name=name,
            description=description,
            message_ttl_hours=message_ttl_hours,
            memory_extract_enabled=enable_memory_extract,
            memory_extract_idle_seconds=memory_extract_idle_seconds,
            memory_extract_max_tokens=memory_extract_max_tokens,
            memory_extract_max_messages=memory_extract_max_messages,
            memory_strategies_builtin=memory_strategies_builtin,
            tags=tags,
        )

        space_dict = _space_info_to_dict(space)

        logger.info(f"Space updated successfully: {space_id}")
        return SpaceResult(
            success=True,
            space_id=space_id,
            space=space_dict,
        )
    except Exception as e:
        logger.error(f"Failed to update space {space_id}: {e}")
        return SpaceResult(
            success=False,
            space_id=space_id,
            error=str(e),
        )


def delete_space(
        space_id: str,
        region: Optional[str] = None,
) -> SpaceResult:
    """Delete a Space.

    Args:
        space_id: Space ID
        region: Region name (optional, defaults to cn-north-4)

    Returns:
        SpaceResult indicating success or failure
    """
    try:
        client = _get_client(region=region)
        client.delete_space(space_id)

        logger.info(f"Space deleted successfully: {space_id}")
        return SpaceResult(
            success=True,
            space_id=space_id,
        )
    except Exception as e:
        logger.error(f"Failed to delete space {space_id}: {e}")
        return SpaceResult(
            success=False,
            space_id=space_id,
            error=str(e),
        )
