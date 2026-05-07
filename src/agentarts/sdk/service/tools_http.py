"""AgentArts Tools HTTP Client"""

from typing import Any

from .http_client import BaseHTTPClient, RequestConfig, SignMode


class ToolsAPIError(BaseException):

    def __init__(self, status_code: int, error_msg: str):
        """
        Initialize ToolsAPIError exception.

        Args:
            status_code (int): HTTP status code
            error_msg (str): Error message
        """
        self.status_code = status_code
        self.error_msg = error_msg
        super().__init__(f"Tools API Error: {error_msg}")


class ControlToolsHttpClient(BaseHTTPClient):
    def __init__(self, region_name: str, endpoint_url: str):
        request_config = RequestConfig(base_url=endpoint_url, verify_ssl=False)
        super().__init__(request_config, open_ak_sk=True)
        self.region_name = region_name

    def create_code_interpreter(self, request_params: dict) -> dict[Any, Any]:
        """POST v1/core/code-interpreters/

        Create a code interpreter.
        """
        endpoint = "/v1/core/code-interpreters"
        response = self.post(url=endpoint, json=request_params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def list_code_interpreters(self, request_params: dict) -> dict[Any, Any]:
        """GET v1/core/code-interpreters/

        List all code interpreters.
        """
        endpoint = "/v1/core/code-interpreters"
        response = self.get(url=endpoint, params=request_params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def update_code_interpreter(
        self, code_interpreter_id: str, request_params: dict
    ) -> dict[Any, Any]:
        """PUT v1/core/code-interpreters/{code_interpreter_id}

        Update a code interpreter.
        """
        endpoint = f"/v1/core/code-interpreters/{code_interpreter_id}"
        response = self.put(url=endpoint, json=request_params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def get_code_interpreter(self, code_interpreter_id: str) -> dict[Any, Any]:
        """GET v1/core/code-interpreters/{code_interpreter_id}

        Get code interpreter details.
        """
        endpoint = f"/v1/core/code-interpreters/{code_interpreter_id}"
        response = self.get(url=endpoint)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def delete_code_interpreter(self, code_interpreter_id: str):
        """DELETE v1/core/code-interpreters/{code_interpreter_id}

        Delete a code interpreter.
        """
        endpoint = f"/v1/core/code-interpreters/{code_interpreter_id}"
        response = self.delete(url=endpoint)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)


class DataToolsHttpClient(BaseHTTPClient):
    def __init__(self, region_name: str, endpoint_url: str, auth_type: str = "API_KEY"):
        """Initialize the data tools HTTP client.

        Args:
            region_name (str): The region name
            endpoint_url (str): The endpoint URL for data plane API
            auth_type (str, optional): Authentication type, supports "API_KEY" or "IAM". Defaults to "API_KEY"
        """
        if auth_type == "IAM":
            super().__init__(
                RequestConfig(base_url=endpoint_url, verify_ssl=False),
                open_ak_sk=True,
                sign_mode=SignMode.V11_HMAC_SHA256,
                region_id=region_name,
            )
        else:
            super().__init__(RequestConfig(base_url=endpoint_url, verify_ssl=False))
        self.region_name = region_name

    @property
    def open_ak_sk(self) -> bool:
        return self._open_ak_sk

    @open_ak_sk.setter
    def open_ak_sk(self, open_ak_sk: bool):
        self._open_ak_sk = open_ak_sk

    def start_session(
        self, code_interpreter_name: str, request_params: dict, api_key: str | None = None
    ) -> dict[Any, Any]:
        """PUT v1/code-interpreters/{code_interpreter_name}/sessions-start

        Start a code interpreter session.
        """
        endpoint = f"/v1/code-interpreters/{code_interpreter_name}/sessions-start"
        headers = {}
        if api_key is not None:
            headers = {"Authorization": f"Bearer {api_key}"}
        response = self.put(url=endpoint, json=request_params, headers=headers)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def stop_session(
        self, code_interpreter_name: str, session_id: str, api_key: str | None = None
    ) -> dict[Any, Any]:
        """PUT v1/code-interpreters/{code_interpreter_name}/sessions-stop

        Stop a code interpreter session.
        """
        endpoint = f"/v1/code-interpreters/{code_interpreter_name}/sessions-stop"
        headers = {"x-HW-Agentarts-Code-Interpreter-Session-Id": session_id}
        if api_key is not None:
            headers["Authorization"] = f"Bearer {api_key}"
        response = self.put(url=endpoint, headers=headers)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def get_session(
        self, code_interpreter_name: str, session_id: str, api_key: str | None = None
    ) -> dict[Any, Any]:
        """GET v1/code-interpreters/{code_interpreter_name}/sessions-get

        Get code interpreter session details.
        """
        endpoint = f"/v1/code-interpreters/{code_interpreter_name}/sessions-get"
        headers = {
            "x-HW-Agentarts-Code-Interpreter-Session-Id": session_id,
        }
        if api_key is not None:
            headers["Authorization"] = f"Bearer {api_key}"
        response = self.get(url=endpoint, headers=headers)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def invoke(
        self,
        code_interpreter_name: str,
        session_id: str,
        arguments: dict | None = None,
        api_key: str | None = None,
    ) -> dict[Any, Any]:
        """POST v1/code-interpreters/{code_interpreter_name}/invoke

        Invoke a code interpreter session.
        """
        endpoint = f"/v1/code-interpreters/{code_interpreter_name}/invoke"
        headers = {
            "x-HW-Agentarts-Code-Interpreter-Session-Id": session_id,
        }
        if api_key is not None:
            headers["Authorization"] = f"Bearer {api_key}"
        response = self.post(url=endpoint, headers=headers, json=arguments)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data
