"""HTTP client service for Huawei Memory API interactions.

This module provides a service class for interacting with Huawei Cloud's Memory API
using requests and HTTP authentication.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

import requests

from .http_client import APIException
from ..utils.constant import get_memory_endpoint

logger = logging.getLogger(__name__)


class AuthenticationStrategy(ABC):
    """抽象认证策略接口"""
    
    @abstractmethod
    def setup_credentials(self, region_name: str):
        """设置认证凭据"""
        pass
    
    @abstractmethod
    def setup_session_hooks(self, session: requests.Session):
        """设置会话钩子"""
        pass
    
    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        pass
    
    @abstractmethod
    def get_endpoint_type(self) -> str:
        """获取端点类型"""
        pass


class DataPlaneAuthenticationStrategy(AuthenticationStrategy):
    """数据面认证策略"""
    
    def __init__(self):
        self.credentials = None
    
    def setup_credentials(self, region_name: str):
        """数据面不需要 AK/SK 凭据"""
        self.credentials = None
        logger.info("Data plane endpoint: credentials will be handled via API_KEY in headers")
    
    def setup_session_hooks(self, session: requests.Session):
        """数据面不需要特殊会话钩子"""
        session.hooks = {}
    
    def get_headers(self) -> Dict[str, str]:
        """获取 API_KEY 认证的请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "hw-agentrun-sdk/0.0.1",
        }
        
        api_key = os.getenv('HW_API_KEY')
        if not api_key:
            raise ValueError("HW_API_KEY environment variable is required for data plane operations")
        headers["X-Auth-Token"] = api_key
        
        # Add X-Client-Request-ID if available
        if hasattr(self, 'client_request_id'):
            headers["X-Client-Request-ID"] = self.client_request_id
            
        return headers
    
    def get_endpoint_type(self) -> str:
        return "data"


class ControlPlaneAuthenticationStrategy(AuthenticationStrategy):
    """管理面认证策略"""
    
    def __init__(self):
        self.credentials = None
    
    def setup_credentials(self, region_name: str):
        """设置 AK/SK 凭据"""
        try:
            from huaweicloudsdkcore.auth.provider import CredentialProviderChain
            self.credentials = CredentialProviderChain.get_basic_credential_provider_chain().get_credentials()
            logger.info(f"Successfully loaded AK/SK credentials for region {region_name}")
        except ImportError as e:
            raise ValueError(
                f"huaweicloudsdkcore is required for control plane operations. "
                f"Install it with: pip install huaweicloudsdkcore. "
                f"Error: {e}"
            )
        except Exception as e:
            raise ValueError(
                f"Failed to load AK/SK credentials for control plane. "
                f"Please set HUAWEICLOUD_SDK_AK and HUAWEICLOUD_SDK_SK environment variables. "
                f"Error: {e}"
            )
    
    def setup_session_hooks(self, session: requests.Session):
        """设置管理面认证钩子"""
        session.hooks = {'response': self._add_authentication}
    
    def _add_authentication(self, response, *args, **kwargs):
        """管理面通过华为云SDK自动添加 AK/SK 认证头"""
        pass
    
    def get_headers(self) -> Dict[str, str]:
        """管理面不需要额外设置请求头（通过SDK自动处理）"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "hw-agentrun-sdk/0.0.1",
        }
        
        # Add X-Client-Request-ID if available
        if hasattr(self, 'client_request_id'):
            headers["X-Client-Request-ID"] = self.client_request_id
            
        return headers
    
    def get_endpoint_type(self) -> str:
        return "manager"


class MemoryAPIException(APIException):
    """Custom exception for Memory API errors."""
    pass


class MemoryHttpService:
    """HTTP client for Huawei Memory API operations with AK/SK authentication.
    
    Compatible with HttpClient interface from memory/inner/httpclient.py
    """

    def __init__(self, region_name: str = "cn-north-4", endpoint: Optional[str] = None, endpoint_type: str = "manager",
                 timeout: int = 30):
        """Initialize Memory HTTP service with region and authentication strategy.
        
        Args:
            region_name: Huawei Cloud region name
            endpoint: Custom endpoint URL (for development/testing)
            endpoint_type: "manager" for control plane, "data" for data plane
            
        Raises:
            ValueError: If required credentials are not available
        """
        self.region_name = region_name
        self._endpoint = endpoint
        self.timeout = timeout
        self.verify_ssl = True

        # Create session
        self.session = requests.Session()

        # Create authentication strategy based on endpoint type
        self._auth_strategy = self._create_authentication_strategy(endpoint_type)

        # Setup credentials using strategy
        self._auth_strategy.setup_credentials(region_name)
        self.credentials = self._auth_strategy.credentials
        
        # Setup session with authentication hooks
        self._auth_strategy.setup_session_hooks(self.session)
        
        # 将 client_request_id 属性传递给策略（如果存在）
        if hasattr(self, 'client_request_id'):
            self._auth_strategy.client_request_id = self.client_request_id

    def _create_authentication_strategy(self, endpoint_type: str) -> AuthenticationStrategy:
        """创建认证策略实例"""
        if endpoint_type == "data":
            return DataPlaneAuthenticationStrategy()
        else:
            return ControlPlaneAuthenticationStrategy()

    def _get_headers(self) -> Dict[str, str]:
        """Get default headers for API requests."""
        return self._auth_strategy.get_headers()
    
    def _get_base_url(self, space_id: Optional[str] = None) -> str:
        """Get base URL based on authentication strategy."""
        return get_memory_endpoint(
            self._auth_strategy.get_endpoint_type(), 
            self.region_name, 
            space_id
        )

    def _make_request(
            self,
            method: str,
            path: str,
            params: Optional[Dict[str, Any]] = None,
            data: Optional[Union[str, Dict[str, Any]]] = None,
            headers: Optional[Dict[str, str]] = None,
            space_id: Optional[str] = None
    ) -> Any:
        """Make an HTTP request to the Memory API.
        
        Args:
            method: HTTP method
            path: API path
            params: Query parameters
            data: Request body
            headers: Custom headers
            space_id: Space ID for data plane requests
            
        Returns:
            API response data
            
        Raises:
            MemoryAPIException: If API request fails
        """
        # Build full URL using the authentication strategy
        base_url = self._get_base_url(space_id)
        url = f"{base_url}{path}"

        # Prepare headers
        final_headers = self._get_headers()
        if headers:
            final_headers.update(headers)

        # Prepare data
        json_data = None
        text_data = None
        if data is not None:
            if isinstance(data, dict):
                json_data = data
            else:
                text_data = data

        # Make HTTP request
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                data=text_data,
                headers=final_headers,
                verify=self.verify_ssl,
                timeout=60
            )

            # Handle response
            if response.status_code == 200:
                if response.headers.get("content-type", "").startswith("application/json"):
                    return response.json()
                else:
                    return {"response": response.text}
            elif response.status_code == 201:
                # Created resource
                if response.headers.get("content-type", "").startswith("application/json"):
                    return response.json()
                else:
                    return {"response": response.text}
            elif response.status_code == 204:
                return {}  # No content
            else:
                # Handle error responses
                try:
                    error_data = response.json()
                    error_code = error_data.get("error_code", "UNKNOWN_ERROR")
                    error_msg = error_data.get("error_msg", str(error_data))
                except (ValueError, AttributeError):
                    # If response is not JSON
                    error_code = "UNKNOWN_ERROR"
                    error_msg = response.text or f"HTTP {response.status_code}"

                raise MemoryAPIException(
                    status_code=response.status_code,
                    error_code=error_code,
                    error_msg=error_msg
                )

        except Exception as e:
            # Handle network errors
            if isinstance(e, MemoryAPIException):
                raise  # Re-raise MemoryAPIException as-is
            logger.error(f"HTTP request failed: {e}")
            raise MemoryAPIException(
                status_code=503,
                error_code="NETWORK_ERROR",
                error_msg=str(e)
            )

    # ==================== Management Plane Methods ====================

    def create_space(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new memory space.

        Args:
            data: Space creation data

        Returns:
            Created space information
        """
        return self._make_request(method="POST", path="/v1/core/spaces", data=data)

    def create_api_key(self) -> Dict[str, Any]:
        """Create a new API Key.

        Returns:
            API Key information containing id and api_key
        """
        return self._make_request(method="POST", path="/v1/core/space-keys")

    def get_space(self, space_id: str) -> Dict[str, Any]:
        """Get space information by ID.

        Args:
            space_id: Space ID

        Returns:
            Space information
        """
        return self._make_request(method="GET", path=f"/v1/core/spaces/{space_id}")

    def update_space(self, space_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update space information.

        Args:
            space_id: Space ID
            data: Update data

        Returns:
            Updated space information
        """
        return self._make_request(method="PUT", path=f"/v1/core/spaces/{space_id}", data=data)

    def delete_space(self, space_id: str) -> Dict[str, Any]:
        """Delete a space.

        Args:
            space_id: Space ID
        """
        return self._make_request(method="DELETE", path=f"/v1/core/spaces/{space_id}")

    def list_spaces(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """List all spaces.

        Args:
            limit: Number of spaces to return
            offset: Offset for pagination

        Returns:
            List of spaces
        """
        params = {"limit": limit, "offset": offset}
        return self._make_request(method="GET", path="/v1/core/spaces", params=params)

    # ==================== Data Plane Methods ====================

    def create_session(self, space_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new memory session.

        Args:
            space_id: Space ID
            data: Session creation data

        Returns:
            Created session information
        """
        return self._make_request(
            method="POST",
            path=f"/v1/core/spaces/{space_id}/sessions",
            data=data,
            space_id=space_id
        )

    def get_session(self, space_id: str, session_id: str) -> Dict[str, Any]:
        """Get session information.

        Args:
            space_id: Space ID
            session_id: Session ID

        Returns:
            Session information
        """
        return self._make_request(
            method="GET",
            path=f"/v1/core/spaces/{space_id}/sessions/{session_id}",
            space_id=space_id
        )

    def add_messages(
            self,
            space_id: str,
            session_id: str,
            data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add messages to a session.

        Args:
            space_id: Space ID
            session_id: Session ID
            data: Messages data

        Returns:
            Messages addition result
        """
        return self._make_request(
            method="POST",
            path=f"/v1/core/spaces/{space_id}/sessions/{session_id}/messages",
            data=data,
            space_id=space_id
        )

    def list_messages(
            self,
            space_id: str,
            session_id: Optional[str] = None,
            limit: int = 10,
            offset: int = 0,
            filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """List messages in a space or session.

        Args:
            space_id: Space ID
            session_id: Session ID (optional, to filter messages in a specific session)
            limit: Number of messages to return (default: 10)
            offset: Offset for pagination (default: 0)
            filters: Filter conditions for messages

        Returns:
            List of messages with pagination info
        """
        # Build query parameters
        params = {}
        if isinstance(limit, int) and limit > 0:
            params['limit'] = limit
        if isinstance(offset, int) and offset >= 0:
            params['offset'] = offset
        # Add filters as query parameters
        if filters:
            for key, value in filters.items():
                if value is not None:
                    params[key] = value

        path = f"/v1/core/spaces/{space_id}/sessions/{session_id}/messages"

        return self._make_request(
            method="GET",
            path=path,
            params=params,
            space_id=space_id
        )

    def search_memories(
            self,
            space_id: str,
            data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Search memories in a space.

        Args:
            space_id: Space ID
            data: Search data

        Returns:
            Search results
        """
        return self._make_request(
            method="POST",
            path=f"/v1/core/spaces/{space_id}/memories/search",
            data=data,
            space_id=space_id
        )

    def get_memory(self, space_id: str, memory_id: str) -> Dict[str, Any]:
        """Get a specific memory item.

        Args:
            space_id: Space ID
            memory_id: Memory ID

        Returns:
            Memory item information
        """
        return self._make_request(
            method="GET",
            path=f"/v1/core/spaces/{space_id}/memories/{memory_id}",
            space_id=space_id
        )

    def create_memory(self, space_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new memory item.

        Args:
            space_id: Space ID
            data: Memory creation data

        Returns:
            Created memory item information
        """
        return self._make_request(
            method="POST",
            path=f"/v1/core/spaces/{space_id}/memories",
            data=data,
            space_id=space_id
        )

    

    def update_memory(
            self,
            space_id: str,
            memory_id: str,
            data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a memory item.

        Args:
            space_id: Space ID
            memory_id: Memory ID
            data: Update data

        Returns:
            Updated memory item information
        """
        return self._make_request(
            method="PUT",
            path=f"/v1/core/spaces/{space_id}/memories/{memory_id}",
            data=data,
            space_id=space_id
        )

    def delete_memory(self, space_id: str, memory_id: str) -> Dict[str, Any]:
        """Delete a memory item.

        Args:
            space_id: Space ID
            memory_id: Memory ID
        """
        return self._make_request(
            method="DELETE",
            path=f"/v1/core/spaces/{space_id}/memories/{memory_id}",
            space_id=space_id
        )

    def get_message(self, space_id: str, session_id: str, message_id: str) -> Dict[str, Any]:
        """Get a specific message.

        Args:
            space_id: Space ID
            session_id: Session ID
            message_id: Message ID

        Returns:
            Message item information
        """
        return self._make_request(
            method="GET",
            path=f"/v1/core/spaces/{space_id}/sessions/{session_id}/messages/{message_id}",
            space_id=space_id
        )

    def list_memories(self, space_id: str, limit: Optional[int] = None, offset: Optional[int] = None,
                      filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """List all memories in a space.

        Args:
            space_id: Space ID
            limit: Number of items per page (1-20)
            offset: Offset for pagination
            filters: 过滤条件

        Returns:
            List of memories
        """
        # 构建查询参数
        params = {}
        if limit is not None:
            params['limit'] = limit
        if offset is not None:
            params['offset'] = offset

        # 处理过滤条件
        if filters:
            # 支持的过滤参数
            filter_mappings = {
                'strategy_type': 'strategy_type',
                'strategy_id': 'strategy_id',
                'actor_id': 'actor_id',
                'assistant_id': 'assistant_id',
                'session_id': 'session_id',
                'start_time': 'start_time',
                'end_time': 'end_time'
            }

            for filter_key, param_key in filter_mappings.items():
                if filter_key in filters and filters[filter_key] is not None:
                    params[param_key] = filters[filter_key]

        return self._make_request(method="GET", path=f"/v1/core/spaces/{space_id}/memories", params=params,
                                  space_id=space_id)

    @property
    def endpoint(self) -> str:
        """获取当前端点"""
        if self._endpoint:
            # 使用自定义端点
            return self._endpoint.rstrip('/')
        else:
            # 使用策略确定的基础端点
            return get_memory_endpoint(
                self._auth_strategy.get_endpoint_type(), 
                self.region_name
            ).rstrip('/')

    @property
    def region(self) -> str:
        """获取区域"""
        return self.region_name
    
    @property
    def endpoint_type(self) -> str:
        """获取端点类型"""
        return self._auth_strategy.get_endpoint_type()
