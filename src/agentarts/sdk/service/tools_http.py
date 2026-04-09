""" AgentArts Tools HTTP Client"""

from typing import Any, Dict, Optional

from .http_client import BaseHTTPClient, RequestConfig
from src.agentarts.sdk.utils.constant import HUAWEICLOUD_SDK_AK, HUAWEICLOUD_SDK_SK

class ToolsAPIError(BaseException):
    
    def __init__(self, status_code: int, error_msg: str):
        """
        初始化ToolsAPIError异常

        Args:
            status_code (int): HTTP状态码
            error_msg (str): 错误信息
        """
        self.status_code = status_code
        self.error_msg = error_msg
        super().__init__(f"Tools API Error: {error_msg}")

class ControlToolsHttpClient(BaseHTTPClient):
    def __init__(self, region_name: str, endpoint_url: str):
        request_config = RequestConfig(base_url=endpoint_url, verify_ssl=False)
        if not HUAWEICLOUD_SDK_AK or not HUAWEICLOUD_SDK_SK:
            raise RuntimeError("HUAWEICLOUD_SDK_AK and HUAWEICLOUD_SDK_SK are required")
        super().__init__(request_config, open_ak_sk=True)
        self.region_name = region_name
    
    def create_code_interpreter(self, params: Dict) -> Dict[Any, Any]:
        """POST v1/core/code-interpreters/
        
        创建代码解释器

        """
        endpoint = f"v1/core/code-interpreters/"
        response = self.post(url=endpoint, data=params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        else:
            return response.data

    def list_code_interpreters(self, params: Dict) -> Dict[Any, Any]:
        """GET v1/core/code-interpreters/
        
        列出所有代码解释器

        """
        endpoint = f"v1/core/code-interpreters/"
        response = self.get(url=endpoint, params=params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        else:
            return response.data

    def update_code_interpreter(self, code_interpreter_id: str, request_params: Dict) -> Dict[Any, Any]:
        """PUT v1/core/code-interpreters/{code_interpreter_id}
        
        更新代码解释器

        """
        endpoint = f"v1/core/code-interpreters/{code_interpreter_id}"
        response = self.put(url=endpoint, data=request_params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        else:
            return response.data
    
    def get_code_interpreter(self, code_interpreter_id: str) -> Dict[Any, Any]:
        """GET v1/core/code-interpreters/{code_interpreter_id}
        
        获取代码解释器详情

        """ 
        endpoint = f"v1/core/code-interpreters/{code_interpreter_id}"
        response = self.get(url=endpoint)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        else:
            return response.data

    def delete_code_interpreter(self, code_interpreter_id: str) -> Dict[Any, Any]:
        """DELETE v1/core/code-interpreters/{code_interpreter_id}
        
        删除代码解释器

        """
        endpoint = f"v1/core/code-interpreters/{code_interpreter_id}"
        response = self.delete(url=endpoint)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)


class DataToolsHttpClient(BaseHTTPClient):
    def __init__(self, region_name: str, endpoint_url: str):
        super().__init__(RequestConfig(base_url=endpoint_url))
        self.region_name = region_name
    
    def start_session(self, code_interpreter_name: str, api_key: str, request_params: Dict) -> Dict[Any, Any]:
        """POST v1/code-interpreters/{code_interpreter_name}/sessions-start
        
        启动代码解释器会话
        """ 
        endpoint = f"v1/code-interpreters/{code_interpreter_name}/sessions-start"
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        response = self.post(url=endpoint, data=request_params, headers=headers)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        else:
            return response.data

    def stop_session(self, code_interpreter_name: str, session_id: str, api_key: str) -> Dict[Any, Any]:
        """POST v1/code-interpreters/{code_interpreter_name}/sessions-stop
        
        停止代码解释器会话
        """
        endpoint = f"v1/code-interpreters/{code_interpreter_name}/sessions-stop"
        headers = {
            "x-HW-Agentarts-Code-Interpreter-Session-Id": session_id,
            "Authorization": f"Bearer {api_key}"
        }
        response = self.put(url=endpoint, headers=headers)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        else:
            return response.data

    def get_session(self, code_interpreter_name: str, session_id: str, api_key: str) -> Dict[Any, Any]:
        """GET v1/code-interpreters/{code_interpreter_name}/sessions-get
        
        获取代码解释器会话详情
        """
        endpoint = f"v1/code-interpreters/{code_interpreter_name}/sessions-get"
        headers = {
            "x-HW-Agentarts-Code-Interpreter-Session-Id": session_id,
            "Authorization": f"Bearer {api_key}"
        }
        response = self.get(url=endpoint, headers=headers)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        else:
            return response.data
    
    def invoke(
            self,
            code_interpreter_name: str,
            session_id: str,
            api_key: str,
            arguments: Optional[Dict] = None,
    ) -> Dict[Any, Any]:
        """POST v1/code-interpreters/{code_interpreter_name}/invoke
        
        调用代码解释器会话
        """
        endpoint = f"v1/code-interpreters/{code_interpreter_name}/invoke"
        headers = {
            "x-HW-Agentarts-Code-Interpreter-Session-Id": session_id,
            "Authorization": f"Bearer {api_key}"
        }
        response = self.post(url=endpoint, headers=headers, data=arguments)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        else:
            return response.data

