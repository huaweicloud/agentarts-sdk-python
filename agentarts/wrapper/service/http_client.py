"""
Base HTTP Client Module

Provides a base HTTP client for API calls. Other service implementations
should inherit from BaseHTTPClient to make HTTP requests.
"""

from typing import Any, Dict, Optional
from dataclasses import dataclass, field

import requests
from urllib.parse import urlparse

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.signer.signer import Signer
from huaweicloudsdkcore.sdk_request import SdkRequest


@dataclass
class RequestConfig:
    """Configuration for HTTP requests."""
    
    base_url: str = ""
    timeout: float = 30.0
    headers: Dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True


@dataclass
class RequestResult:
    """Result of an HTTP request."""
    
    success: bool
    status_code: int
    data: Any = None
    error: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)


class BaseHTTPClient:
    """
    Base HTTP client for making API calls.
    
    Subclass this to implement service-specific API clients.
    
    Features:
    - Synchronous requests via requests.Session
    - Automatic JSON/text response parsing
    - Timeout and error handling
    - Auth token management
    - Context manager support
    
    Usage:
        class MyAPIClient(BaseHTTPClient):
            def __init__(self):
                super().__init__(RequestConfig(base_url="https://api.example.com"))
            
            def get_user(self, user_id: str) -> RequestResult:
                return self.get(f"/users/{user_id}")
            
            def create_user(self, data: dict) -> RequestResult:
                return self.post("/users", json=data)
        
        with MyAPIClient() as client:
            client.set_auth_token("my-token")
            result = client.get_user("123")
            if result.success:
                print(result.data)
    """
    
    def __init__(self, config: Optional[RequestConfig] = None, open_ak_sk: bool = False):
        self._config = config or RequestConfig()
        self._session = requests.Session()
        self._session.headers.update(self._config.headers)
        self._open_ak_sk = open_ak_sk
        self._signer = None
        self._credentials = None
    
    def _sign_request(self, method: str, full_url: str, **kwargs) -> dict:
        """Sign the HTTP request using AK/SK."""
        # 使用 create_credential 获取凭证
        from agentarts.wrapper.utils.metadata import create_credential
        
        # 初始化签名器（如果还没有初始化）
        if not self._signer:
            self._credentials = create_credential()
            self._signer = Signer(self._credentials)
        
        # 解析URL
        parsed_url = urlparse(full_url)
        schema = parsed_url.scheme
        host = parsed_url.netloc
        resource_path = parsed_url.path
        if parsed_url.query:
            resource_path += f"?{parsed_url.query}"
        
        # 提取请求参数
        headers = kwargs.get('headers', {})
        data = kwargs.get('data')
        json_data = kwargs.get('json')
        
        # 处理请求体
        body = None
        if data is not None:
            if isinstance(data, dict):
                # 将字典转换为 form 数据字符串
                import urllib.parse
                body = urllib.parse.urlencode(data)
                # 设置 Content-Type 头
                if 'Content-Type' not in headers:
                    headers['Content-Type'] = 'application/x-www-form-urlencoded'
            else:
                body = data
        elif json_data is not None:
            # 将字典转换为 JSON 字符串
            import json
            body = json.dumps(json_data)
            # 设置 Content-Type 头
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'application/json'
        
        # 构造SdkRequest
        try:
            # 确保所有必要的参数都不为 None
            schema = schema or 'https'
            host = host or ''
            resource_path = resource_path or '/'
            headers = headers or {}
            
            # 确保 header_params 不为 None
            if headers is None:
                headers = {}
            
            # 提取查询参数
            query_params = kwargs.get('params', None)
            # 确保 query_params 不为 None
            if query_params is not None:
                # 将字典转换为列表形式 [(key, value), ...]
                query_params_list = []
                for key, value in query_params.items():
                    query_params_list.append((key, value))
            else:
                query_params_list = []
            
            sdk_request = SdkRequest(
                method=method,
                schema=schema,
                host=host,
                resource_path=resource_path,
                header_params=headers,
                body=body,
                query_params=query_params_list
            )
            
            # 签名
            signed_request = self._signer.sign(sdk_request)
            
            # 更新请求头
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            if hasattr(signed_request, 'header_params') and signed_request.header_params:
                kwargs['headers'].update(signed_request.header_params)
        except Exception as e:
            # 签名失败时，仍然继续发送请求，但记录错误
            print(f"Signature failed: {e}")
        
        return kwargs

    def _request(self, method: str, url: str, **kwargs) -> RequestResult:
        """Execute HTTP request and return a RequestResult."""
        full_url = self._config.base_url + url
        
        # 处理签名
        if self._open_ak_sk:
            kwargs = self._sign_request(method, full_url, **kwargs)
        
        try:
            response = self._session.request(
                method,
                full_url,
                timeout=self._config.timeout,
                verify=self._config.verify_ssl,
                **kwargs
            )
            
            try:
                data = response.json()
            except Exception:
                data = response.text if response.content else None
            
            return RequestResult(
                success=response.ok,
                status_code=response.status_code,
                data=data,
                headers=dict(response.headers),
            )
        
        except requests.Timeout as e:
            return RequestResult(
                success=False,
                status_code=0,
                error=f"Request timeout: {e}"
            )
        except requests.RequestException as e:
            return RequestResult(
                success=False,
                status_code=0,
                error=f"Request error: {e}"
            )
        except Exception as e:
            return RequestResult(
                success=False,
                status_code=0,
                error=f"Unexpected error: {e}"
            )
    
    def get(self, url: str, params: Optional[Dict] = None, **kwargs) -> RequestResult:
        """Send GET request."""
        if params:
            kwargs["params"] = params
        return self._request("GET", url, **kwargs)
    
    def post(self, url: str, data: Optional[Any] = None, json: Optional[Any] = None, **kwargs) -> RequestResult:
        """Send POST request."""
        if data is not None:
            kwargs["data"] = data
        if json is not None:
            kwargs["json"] = json
        return self._request("POST", url, **kwargs)
    
    def put(self, url: str, data: Optional[Any] = None, json: Optional[Any] = None, **kwargs) -> RequestResult:
        """Send PUT request."""
        if data is not None:
            kwargs["data"] = data
        if json is not None:
            kwargs["json"] = json
        return self._request("PUT", url, **kwargs)
    
    def patch(self, url: str, data: Optional[Any] = None, json: Optional[Any] = None, **kwargs) -> RequestResult:
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
