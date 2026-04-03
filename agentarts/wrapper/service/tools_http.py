
from typing import Any, Dict, Optional
import os

from .http_client import BaseHTTPClient, RequestConfig, RequestResult


class ToolsAPIError(BaseException):
    pass

class ControlToolsHttpClient(BaseHTTPClient):
    def __init__(self, region_name: str, endpoint_url: str, credentials: Dict[str, str]):
        super().__init__(RequestConfig(base_url=endpoint_url))
        self.region_name = region_name
        self.credentials = credentials
    
    def create_code_interpreter(self, params: Dict) -> Dict[Any, Any]:
        endpoint = f"v1/core/code-interpreters/"
        method = "POST"
        pass

    def list_code_interpreters(self, params: Dict) -> Dict[Any, Any]:
        endpoint = f"v1/core/code-interpreters/"
        method = "GET"
        pass

    def update_code_interpreter(self, code_interpreter_id: str, request_params: Dict) -> Dict[Any, Any]:
        endpoint = f"v1/core/code-interpreters/{code_interpreter_id}"
        method = "PUT"
        pass
    
    def get_code_interpreter(self, code_interpreter_id: str) -> Dict[Any, Any]:
        endpoint = f"v1/core/code-interpreters/{code_interpreter_id}"
        method = "GET"
        pass

    def delete_code_interpreter(self, code_interpreter_id: str) -> Dict[Any, Any]:
        endpoint = f"v1/core/code-interpreters/{code_interpreter_id}"
        method = "DELETE"
        pass


class DataToolsHttpClient(BaseHTTPClient):
    def __init__(self, region_name: str, endpoint_url: str):
        super().__init__(RequestConfig(base_url=endpoint_url))
        self.region_name = region_name
    
    def start_session(self, code_interpreter_name: str, api_key: str, request_params: Dict) -> Dict[Any, Any]:

        endpoint = f"v1/code-interpreters/{code_interpreter_name}/sessions-start"
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        return self._request("POST", endpoint, headers=headers, data=request_params)

    def stop_session(self, code_interpreter_name: str, session_id: str, api_key: str) -> Dict[Any, Any]:
        endpoint = f"v1/code-interpreters/{code_interpreter_name}/sessions-stop"
        headers = {
            "x-HW-Agentarts-Code-Interpreter-Session-Id": session_id,
            "Authorization": f"Bearer {api_key}"
        }
        return self._request("POST", endpoint, headers=headers)

    def get_session(self, code_interpreter_name: str, session_id: str, api_key: str) -> Dict[Any, Any]:
        endpoint = f"v1/code-interpreters/{code_interpreter_name}/sessions-get"
        headers = {
            "x-HW-Agentarts-Code-Interpreter-Session-Id": session_id,
            "Authorization": f"Bearer {api_key}"
        }
        return self._request("GET", endpoint, headers=headers)
    
    def invoke(
            self,
            code_interpreter_name: str,
            session_id: str,
            api_key: str,
            arguments: Optional[Dict] = None,
    ) -> Dict[Any, Any]:
        endpoint = f"v1/code-interpreters/{code_interpreter_name}/invoke"
        headers = {
            "x-HW-Agentarts-Code-Interpreter-Session-Id": session_id,
            "Authorization": f"Bearer {api_key}"
        }
        return self._request("POST", endpoint, headers=headers, data=arguments)  

