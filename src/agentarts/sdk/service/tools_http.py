"""AgentArts Tools HTTP Client"""

import base64
import os
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
    def __init__(self, region_name: str, endpoint_url: str, verify_ssl: bool | str = True):
        request_config = RequestConfig(base_url=endpoint_url, verify_ssl=verify_ssl)
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
    def __init__(
        self,
        region_name: str,
        endpoint_url: str,
        auth_type: str = "API_KEY",
        verify_ssl: bool | str = True,
    ):
        """Initialize the data tools HTTP client.

        Args:
            region_name (str): The region name
            endpoint_url (str): The endpoint URL for data plane API
            auth_type (str, optional): Authentication type, supports "API_KEY" or "IAM". Defaults to "API_KEY"
            verify_ssl (bool | str, optional): SSL verification setting. Defaults to True
            - True: Verify SSL certificates using system CA bundle (default)
            - False: Skip SSL verification
            - str: Path to custom CA certificate file
        """
        if auth_type == "IAM":
            super().__init__(
                RequestConfig(base_url=endpoint_url, verify_ssl=verify_ssl),
                open_ak_sk=True,
                sign_mode=SignMode.V11_HMAC_SHA256,
                region_id=region_name,
            )
        else:
            super().__init__(RequestConfig(base_url=endpoint_url, verify_ssl=verify_ssl))
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


class ControlBrowserHttpClient(BaseHTTPClient):
    """Browser control plane HTTP client.

    Manages browser resources and browser profiles through the control plane API.
    Uses AK/SK signing for authentication.
    """

    def __init__(self, region_name: str, endpoint_url: str, verify_ssl: bool | str = True):
        request_config = RequestConfig(base_url=endpoint_url, verify_ssl=verify_ssl)
        super().__init__(request_config, open_ak_sk=True)
        self.region_name = region_name

    # ── Browser resource CRUD ──────────────────────────────────────────

    def create_browser(self, request_params: dict) -> dict[Any, Any]:
        """POST /v1/core/browsers

        Create a browser resource.
        """
        endpoint = "/v1/core/browsers"
        response = self.post(url=endpoint, json=request_params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def list_browsers(self, request_params: dict) -> dict[Any, Any]:
        """GET /v1/core/browsers

        List browser resources.
        """
        endpoint = "/v1/core/browsers"
        response = self.get(url=endpoint, params=request_params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def update_browser(
        self, browser_id: str, request_params: dict
    ) -> dict[Any, Any]:
        """PUT /v1/core/browsers/{browser_id}

        Update a browser resource.
        """
        endpoint = f"/v1/core/browsers/{browser_id}"
        response = self.put(url=endpoint, json=request_params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def get_browser(self, browser_id: str) -> dict[Any, Any]:
        """GET /v1/core/browsers/{browser_id}

        Get browser resource details.
        """
        endpoint = f"/v1/core/browsers/{browser_id}"
        response = self.get(url=endpoint)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def delete_browser(self, browser_id: str):
        """DELETE /v1/core/browsers/{browser_id}

        Delete a browser resource.
        """
        endpoint = f"/v1/core/browsers/{browser_id}"
        response = self.delete(url=endpoint)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)

    # ── Browser profile CRUD ───────────────────────────────────────────

    def create_browser_profile(self, request_params: dict) -> dict[Any, Any]:
        """POST /v1/core/browser-profiles

        Create a browser profile.
        """
        endpoint = "/v1/core/browser-profiles"
        response = self.post(url=endpoint, json=request_params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def list_browser_profiles(self, request_params: dict) -> dict[Any, Any]:
        """GET /v1/core/browser-profiles

        List browser profiles.
        """
        endpoint = "/v1/core/browser-profiles"
        response = self.get(url=endpoint, params=request_params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def get_browser_profile(self, profile_id: str) -> dict[Any, Any]:
        """GET /v1/core/browser-profiles/{profile_id}

        Get browser profile details.
        """
        endpoint = f"/v1/core/browser-profiles/{profile_id}"
        response = self.get(url=endpoint)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def delete_browser_profile(self, profile_id: str):
        """DELETE /v1/core/browser-profiles/{profile_id}

        Delete a browser profile.
        """
        endpoint = f"/v1/core/browser-profiles/{profile_id}"
        response = self.delete(url=endpoint)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)


class DataBrowserHttpClient(BaseHTTPClient):
    """Browser data plane HTTP client.

    Manages browser sessions and operation execution through the data plane API.
    Supports IAM (V11-HMAC-SHA256 signing) and API_KEY (Bearer token) authentication.
    """

    def __init__(
        self,
        region_name: str,
        endpoint_url: str,
        auth_type: str = "API_KEY",
        verify_ssl: bool | str = True,
    ):
        """Initialize the data browser HTTP client.

        Args:
            region_name: The region name.
            endpoint_url: The endpoint URL for data plane API.
            auth_type: Authentication type, "API_KEY" or "IAM". Defaults to "API_KEY".
            verify_ssl: SSL verification. True to verify, False to skip,
                or a string path to a CA bundle. Defaults to True.
        """
        if auth_type == "IAM":
            super().__init__(
                RequestConfig(base_url=endpoint_url, verify_ssl=verify_ssl),
                open_ak_sk=True,
                sign_mode=SignMode.V11_HMAC_SHA256,
                region_id=region_name,
            )
        else:
            super().__init__(RequestConfig(base_url=endpoint_url, verify_ssl=verify_ssl))
        self.region_name = region_name

    @property
    def open_ak_sk(self) -> bool:
        return self._open_ak_sk

    @open_ak_sk.setter
    def open_ak_sk(self, open_ak_sk: bool):
        self._open_ak_sk = open_ak_sk

    def start_session(
        self,
        browser_name: str,
        session_id: str,
        request_params: dict,
        api_key: str | None = None,
    ) -> dict[Any, Any]:
        """PUT /v1/browsers/{browser_name}/sessions-start

        Start a browser session.
        """
        endpoint = f"/v1/browsers/{browser_name}/sessions-start"
        headers = {"x-HW-Agentarts-Browser-Session-Id": session_id}
        if api_key is not None:
            headers["Authorization"] = f"Bearer {api_key}"
        response = self.put(url=endpoint, json=request_params, headers=headers)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def stop_session(
        self,
        browser_name: str,
        session_id: str,
        api_key: str | None = None,
    ) -> dict[Any, Any]:
        """PUT /v1/browsers/{browser_name}/sessions-stop

        Stop a browser session.
        """
        endpoint = f"/v1/browsers/{browser_name}/sessions-stop"
        headers = {"x-HW-Agentarts-Browser-Session-Id": session_id}
        if api_key is not None:
            headers["Authorization"] = f"Bearer {api_key}"
        response = self.put(url=endpoint, headers=headers)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def get_session(
        self,
        browser_name: str,
        session_id: str,
        api_key: str | None = None,
    ) -> dict[Any, Any]:
        """GET /v1/browsers/{browser_name}/sessions-get

        Get browser session details.
        """
        endpoint = f"/v1/browsers/{browser_name}/sessions-get"
        headers = {"x-HW-Agentarts-Browser-Session-Id": session_id}
        if api_key is not None:
            headers["Authorization"] = f"Bearer {api_key}"
        response = self.get(url=endpoint, headers=headers)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def invoke(
        self,
        browser_name: str,
        session_id: str,
        action: dict,
        api_key: str | None = None,
    ) -> dict[Any, Any]:
        """POST /v1/browsers/{browser_name}/invoke

        Invoke a browser session operation.
        """
        endpoint = f"/v1/browsers/{browser_name}/invoke"
        headers = {"x-HW-Agentarts-Browser-Session-Id": session_id}
        if api_key is not None:
            headers["Authorization"] = f"Bearer {api_key}"

        request_params = {"action": action}

        response = self.post(url=endpoint, headers=headers, json=request_params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def update_stream(
        self,
        browser_name: str,
        session_id: str,
        stream_status: str,
        client_token: str | None = None,
        api_key: str | None = None,
    ) -> dict[Any, Any]:
        """PUT /v1/browsers/{browser_name}/sessions-update

        Update a browser session stream (e.g. enable/disable human handoff).
        """
        endpoint = f"/v1/browsers/{browser_name}/sessions-update"
        headers = {"x-HW-Agentarts-Browser-Session-Id": session_id}
        if api_key is not None:
            headers["Authorization"] = f"Bearer {api_key}"

        request_params: dict[str, Any] = {
            "stream_update": {"automation_stream_update": {"stream_status": stream_status}},
        }
        if client_token is not None:
            request_params["client_token"] = client_token

        response = self.put(url=endpoint, headers=headers, json=request_params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def save_profile(
        self,
        browser_name: str,
        session_id: str,
        profile_id: str,
        api_key: str | None = None,
    ) -> dict[Any, Any]:
        """PUT /v1/browsers/{browser_name}/sessions-save-profile

        Save current browser session state to a profile.
        """
        endpoint = f"/v1/browsers/{browser_name}/sessions-save-profile"
        headers = {"x-HW-Agentarts-Browser-Session-Id": session_id}
        if api_key is not None:
            headers["Authorization"] = f"Bearer {api_key}"

        request_params = {"profile_id": profile_id}

        response = self.put(url=endpoint, headers=headers, json=request_params)
        if not response.success:
            raise ToolsAPIError(response.status_code, response.error)
        return response.data

    def build_ws_headers(
        self,
        session_id: str,
        ws_url: str,
        api_key: str | None = None,
    ) -> dict:
        """Build WebSocket connection headers with auth and session info.

        For IAM auth, converts the WebSocket URL to an HTTP URL and signs
        it using V11-HMAC-SHA256, then merges the signed headers.

        For API_KEY auth, adds ``Authorization: Bearer <api_key>``.

        Args:
            session_id: The browser session ID.
            ws_url: The WebSocket endpoint URL (e.g. ``wss://...``).
            api_key: API Key for API_KEY auth mode.

        Returns:
            Dict of WebSocket connection headers including session ID,
            auth, and WebSocket upgrade headers.
        """
        ws_key = base64.b64encode(os.urandom(16)).decode()

        headers = {
            "x-HW-Agentarts-Browser-Session-Id": session_id,
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Version": "13",
            "Sec-WebSocket-Key": ws_key,
        }

        if self.open_ak_sk:
            # IAM mode: convert ws(s):// → http(s):// and sign with V11
            http_url = ws_url.replace("wss://", "https://").replace("ws://", "http://")
            signed_result = self._sign_request_v11("GET", http_url)
            iam_headers = {
                k.lower(): v for k, v in signed_result.get("headers", {}).items()
            }
            headers.update(iam_headers)
        else:
            api_key = api_key or os.getenv("HUAWEICLOUD_SDK_BROWSER_API_KEY")
            if api_key is None:
                msg = "API Key is not provided and not found in environment variable."
                raise ValueError(msg)
            headers["Authorization"] = f"Bearer {api_key}"

        return headers
