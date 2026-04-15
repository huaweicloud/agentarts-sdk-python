"""HTTP client service for Huawei Memory API interactions.

This module provides a service class for interacting with Huawei Cloud's Memory API
using requests and HTTP authentication.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

import requests

from .http_client import APIException
from ..utils.constant import get_memory_endpoint, get_region

logger = logging.getLogger(__name__)


class AuthenticationStrategy(ABC):
    """Abstract authentication strategy interface."""
    
    @abstractmethod
    def setup_credentials(self, region_name: str):
        """Setup authentication credentials."""
        pass
    
    @abstractmethod
    def setup_session_hooks(self, session: requests.Session):
        """Setup session hooks."""
        pass
    
    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        pass
    
    @abstractmethod
    def get_endpoint_type(self) -> str:
        """Get endpoint type."""
        pass
    
    def sign_request(self, method: str, url: str, headers: Dict[str, str], 
                     body: Optional[bytes] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Sign the HTTP request. Override in subclasses that need signing.
        
        Args:
            method: HTTP method
            url: Full URL
            headers: Request headers (will be modified in place)
            body: Request body as bytes
            params: Query parameters as dict
            
        Returns:
            Updated headers dict with signature
        """
        return headers


class DataPlaneAuthenticationStrategy(AuthenticationStrategy):
    """Data plane authentication strategy."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.credentials = None
        self._api_key = api_key
    
    def setup_credentials(self, region_name: str):
        """Data plane does not require AK/SK credentials."""
        self.credentials = None
        logger.info("Data plane endpoint: credentials will be handled via HUAWEICLOUD_SDK_MEMORY_API_KEY in headers")
    
    def setup_session_hooks(self, session: requests.Session):
        """Data plane does not require special session hooks."""
        session.hooks = {}
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with API_KEY authentication."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "agentarts-sdk-python/0.0.1",
        }
        
        api_key = self._api_key or os.getenv('HUAWEICLOUD_SDK_MEMORY_API_KEY')
        if not api_key:
            raise ValueError(
                "API Key is required for data plane operations. "
                "Either pass api_key parameter or set HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable."
            )
        headers["Authorization"] = f"Bearer {api_key}"
        
        if hasattr(self, 'client_request_id'):
            headers["X-Client-Request-ID"] = self.client_request_id
            
        return headers
    
    def get_endpoint_type(self) -> str:
        return "data"


class ControlPlaneAuthenticationStrategy(AuthenticationStrategy):
    """Control plane authentication strategy with AK/SK signing using SDK-HMAC-SHA256."""
    
    def __init__(self):
        self.credentials = None
        self._region_name = None
        self._signer = None
    
    def setup_credentials(self, region_name: str):
        """Setup AK/SK credentials and signer."""
        self._region_name = region_name
        try:
            from agentarts.sdk.utils.metadata import create_credential
            from huaweicloudsdkcore.signer.signer import Signer
            
            self.credentials = create_credential()
            self._signer = Signer(self.credentials)
            logger.info(f"Successfully loaded AK/SK credentials for region {region_name}")
        except ImportError as e:
            raise ValueError(
                f"Huawei Cloud SDK is required for control plane signing. "
                f"Install it with: pip install huaweicloudsdkcore>=3.1.0. "
                f"Error: {e}"
            )
        except Exception as e:
            raise ValueError(
                f"Failed to load AK/SK credentials for control plane. "
                f"Please set HUAWEICLOUD_SDK_AK and HUAWEICLOUD_SDK_SK environment variables. "
                f"Error: {e}"
            )
    
    def setup_session_hooks(self, session: requests.Session):
        """Setup control plane authentication hooks."""
        pass
    
    def get_headers(self) -> Dict[str, str]:
        """Get base headers for control plane requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "agentarts-sdk/0.0.1",
        }
        
        if hasattr(self, 'client_request_id'):
            headers["X-Client-Request-ID"] = self.client_request_id
            
        return headers
    
    def get_endpoint_type(self) -> str:
        return "control"
    
    def sign_request(self, method: str, url: str, headers: Dict[str, str],
                     body: Optional[bytes] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Sign the HTTP request using SDK-HMAC-SHA256 algorithm.
        
        This method uses the same signing approach as BaseHTTPClient._sign_request_sdk(),
        leveraging huaweicloudsdkcore.signer.signer.Signer for request signing.
        
        Args:
            method: HTTP method
            url: Full URL
            headers: Request headers
            body: Request body as bytes
            params: Query parameters as dict
            
        Returns:
            Updated headers dict with signature
        """
        if not self._signer:
            return headers
        
        from huaweicloudsdkcore.sdk_request import SdkRequest
        
        parsed_url = urlparse(url)
        schema = parsed_url.scheme or "https"
        host = parsed_url.netloc
        resource_path = parsed_url.path or "/"
        
        query_params_list = []
        if params:
            for key, value in params.items():
                query_params_list.append((key, value))
        
        sdk_request = SdkRequest(
            method=method,
            schema=schema,
            host=host,
            resource_path=resource_path,
            header_params=headers,
            body=body.decode('utf-8') if body else None,
            query_params=query_params_list,
        )
        
        signed_request = self._signer.sign(sdk_request)
        
        if hasattr(signed_request, 'header_params') and signed_request.header_params:
            headers.update(signed_request.header_params)
        
        return headers


class MemoryAPIException(APIException):
    """Custom exception for Memory API errors."""
    pass


class MemoryHttpService:
    """HTTP client for Huawei Memory API operations with AK/SK authentication.
    
    Compatible with HttpClient interface from memory/inner/httpclient.py
    """

    def __init__(
            self,
            region_name: Optional[str] = None,
            endpoint: Optional[str] = None,
            endpoint_type: str = "control",
            timeout: int = 30,
            api_key: Optional[str] = None,
            verify_ssl: bool = False,
    ):
        """Initialize Memory HTTP service with region and authentication strategy.
        
        Args:
            region_name: Huawei Cloud region name, auto-detected from environment if not provided
            endpoint: Custom endpoint URL (for development/testing)
            endpoint_type: "control" for control plane, "data" for data plane
            timeout: Request timeout in seconds
            api_key: API Key for data plane authentication (optional, falls back to environment variable)
            verify_ssl: Whether to verify SSL certificates (default: False)
            
        Raises:
            ValueError: If required credentials are not available
        """
        self.region_name = region_name or get_region()
        self._endpoint = endpoint
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._api_key = api_key

        self.session = requests.Session()

        self._auth_strategy = self._create_authentication_strategy(endpoint_type)

        self._auth_strategy.setup_credentials(self.region_name)
        self.credentials = self._auth_strategy.credentials
        
        self._auth_strategy.setup_session_hooks(self.session)
        
        if hasattr(self, 'client_request_id'):
            self._auth_strategy.client_request_id = self.client_request_id

    def _create_authentication_strategy(self, endpoint_type: str) -> AuthenticationStrategy:
        """Create authentication strategy instance."""
        if endpoint_type == "data":
            return DataPlaneAuthenticationStrategy(api_key=self._api_key)
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
        base_url = self._get_base_url(space_id)
        url = f"{base_url}{path}"

        final_headers = self._get_headers()
        if headers:
            final_headers.update(headers)

        body_bytes = None
        json_data = None
        text_data = None
        if data is not None:
            if isinstance(data, dict):
                import json
                json_data = data
                body_bytes = json.dumps(data).encode('utf-8')
            else:
                text_data = data
                body_bytes = data.encode('utf-8') if isinstance(data, str) else data

        final_headers = self._auth_strategy.sign_request(
            method=method,
            url=url,
            headers=final_headers,
            body=body_bytes,
            params=params,
        )

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

            if response.status_code == 200:
                if response.headers.get("content-type", "").startswith("application/json"):
                    return response.json()
                else:
                    return {"response": response.text}
            elif response.status_code == 201:
                if response.headers.get("content-type", "").startswith("application/json"):
                    return response.json()
                else:
                    return {"response": response.text}
            elif response.status_code == 204:
                return {}
            else:
                try:
                    error_data = response.json()
                    error_code = error_data.get("error_code", "UNKNOWN_ERROR")
                    error_msg = error_data.get("error_msg", str(error_data))
                except (ValueError, AttributeError):
                    error_code = "UNKNOWN_ERROR"
                    error_msg = response.text or f"HTTP {response.status_code}"

                raise MemoryAPIException(
                    status_code=response.status_code,
                    error_code=error_code,
                    error_msg=error_msg
                )

        except Exception as e:
            if isinstance(e, MemoryAPIException):
                raise
            logger.error(f"HTTP request failed: {e}")
            raise MemoryAPIException(
                status_code=503,
                error_code="NETWORK_ERROR",
                error_msg=str(e)
            )

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
        params = {}
        if isinstance(limit, int) and limit > 0:
            params['limit'] = limit
        if isinstance(offset, int) and offset >= 0:
            params['offset'] = offset
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
            filters: Filter conditions

        Returns:
            List of memories
        """
        params = {}
        if limit is not None:
            params['limit'] = limit
        if offset is not None:
            params['offset'] = offset

        if filters:
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
        """Get current endpoint."""
        if self._endpoint:
            return self._endpoint.rstrip('/')
        else:
            return get_memory_endpoint(
                self._auth_strategy.get_endpoint_type(), 
                self.region_name
            ).rstrip('/')

    @property
    def region(self) -> str:
        """Get region."""
        return self.region_name
    
    @property
    def endpoint_type(self) -> str:
        """Get endpoint type."""
        return self._auth_strategy.get_endpoint_type()