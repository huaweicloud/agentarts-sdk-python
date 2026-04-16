import unittest
from unittest.mock import patch

from agentarts.sdk.service.http_client import RequestResult
from agentarts.sdk.service.tools_http import ControlToolsHttpClient, DataToolsHttpClient


class TestToolsHttpClient(unittest.TestCase):
    @patch("agentarts.sdk.utils.constant.ENV_HUAWEICLOUD_SDK_AK")
    @patch("agentarts.sdk.utils.constant.ENV_HUAWEICLOUD_SDK_SK")
    def setUp(self, mock_ak, mock_sk):
        self.control_client = ControlToolsHttpClient(region_name="test-region", endpoint_url="https://test.com")
        self.data_client = DataToolsHttpClient(region_name="test-region", endpoint_url="https://test.com")

    @patch.object(ControlToolsHttpClient, "post")
    def test_create_code_interpreter(self, mock_post):
        """测试create_code_interpreter方法"""
        # Arrange
        mock_post.return_value = RequestResult(
            success=True,
            status_code=200,
            data={
                "name": "test-code-interpreter-name",
                "description": "test-code-interpreter-description",
                "auth_type": "API_KEY",
                "api_key_name": "test-api-key-name",
                "execution_agency_name": "my_agency",
                "observability": {},
                "network_config": {},
                "agent_gateway_id": "a1b2c3d4-e5f6-7890-abcd-ef12334567890",
                "tags": []
            },
            headers={},
            streaming=True,
            _raw_response=None,
        )

        # Act
        result = self.control_client.create_code_interpreter(
            {
                "name": "test-code-interpreter-name",
                "description": "test-code-interpreter-description",
                "auth_type": "API_KEY",
                "api_key_name": "test-api-key-name",
                "execution_agency_name": "my_agency",
                "observability": {},
                "network_config": {},
                "agent_gateway_id": "a1b2c3d4-e5f6-7890-abcd-ef12334567890",
                "tags": []
            }
        )

        # Assert
        assert result == mock_post.return_value.data
        mock_post.assert_called_once_with(
            url="/v1/core/code-interpreters",
            json={
                "name": "test-code-interpreter-name",
                "description": "test-code-interpreter-description",
                "auth_type": "API_KEY",
                "api_key_name": "test-api-key-name",
                "execution_agency_name": "my_agency",
                "observability": {},
                "network_config": {},
                "agent_gateway_id": "a1b2c3d4-e5f6-7890-abcd-ef12334567890",
                "tags": []
            }
        )

    @patch.object(ControlToolsHttpClient, "get")
    def test_list_code_interpreters(self, mock_get):
        """测试list_code_interpreters方法"""
        # Arrange
        mock_get.return_value = RequestResult(
            success=True,
            status_code=200,
            data={
                "total": 1,
                "items": [
                    {
                        "id": "00000000-0000-0000-0000-000000000000",
                        "name": "string",
                        "description": "string",
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-01T00:00:00Z",
                        "execution_agency_name": "my_agency",
                        "agent_gateway_id": "",
                        "workload_identity": {
                            "urn": "agentArts:cn-north-7:123456789:coreCodeInterpreter:123321"
                        },
                        "access_endpoint": "",
                        "observability": {},
                        "tags": []
                    }
                ]
            },
            headers={},
            streaming=True,
            _raw_response=None,
        )

        # Act
        result = self.control_client.list_code_interpreters(
            {
                "offset": 0,
                "limit": 10
            }
        )

        # Assert
        assert result == mock_get.return_value.data
        mock_get.assert_called_once_with(
            url="/v1/core/code-interpreters",
            json={
                "offset": 0,
                "limit": 10
            }
        )

    @patch.object(ControlToolsHttpClient, "put")
    def test_update_code_interpreter(self, mock_put):
        """测试update_code_interpreter方法"""
        # Arrange
        code_interpreter_id = "test-code-interpreter-id"
        mock_put.return_value = RequestResult(
            success=True,
            status_code=200,
            data={
                "observability": {},
                "tags": [
                    {
                        "key": "test-tag",
                        "value": "test-tag-value"
                    }
                ]
            },
            headers={},
            streaming=True,
            _raw_response=None,
        )

        # Act
        result = self.control_client.update_code_interpreter(
            code_interpreter_id=code_interpreter_id,
            request_params={
                "observability": {},
                "tags": [
                    {
                        "key": "test-tag",
                        "value": "test-tag-value"
                    }
                ]
            }
        )

        # Assert
        assert result == mock_put.return_value.data
        mock_put.assert_called_once_with(
            url=f"/v1/core/code-interpreters/{code_interpreter_id}",
            json={
                "observability": {},
                "tags": [
                    {
                        "key": "test-tag",
                        "value": "test-tag-value"
                    }
                ]
            }
        )

    @patch.object(ControlToolsHttpClient, "get")
    def test_get_code_interpreter(self, mock_get):
        """测试get_code_interpreter方法"""
        # Arrange
        code_interpreter_id = "test-code-interpreter-id"
        mock_get.return_value = RequestResult(
            success=True,
            status_code=200,
            data={
                "id": "00000000-0000-0000-0000-000000000000",
                "name": "string",
                "description": "string",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "execution_agency_name": "my_agency",
                "agent_gateway_id": "",
                "workload_identity": {
                    "urn": "agentArts:cn-north-7:123456789:coreCodeInterpreter:123321"
                },
                "access_endpoint": "",
                "observability": {},
                "tags": [],
                "auth_type": "API_KEY",
                "api_key_name": "test-api-key-name",
                "network_config": {}
            },
            headers={},
            streaming=True,
            _raw_response=None,
        )

        # Act
        result = self.control_client.get_code_interpreter(
            code_interpreter_id=code_interpreter_id
        )

        # Assert
        assert result == mock_get.return_value.data
        mock_get.assert_called_once_with(
            url=f"/v1/core/code-interpreters/{code_interpreter_id}"
        )

    @patch.object(ControlToolsHttpClient, "delete")
    def test_delete_code_interpreter(self, mock_delete):
        """测试delete_code_interpreter方法"""
        # Arrange
        code_interpreter_id = "test-code-interpreter-id"
        mock_delete.return_value = RequestResult(
            success=True,
            status_code=200,
            data=None,
            headers={},
            streaming=True,
            _raw_response=None,
        )

        # Act
        result = self.control_client.delete_code_interpreter(
            code_interpreter_id=code_interpreter_id
        )

        # Assert
        assert result == mock_delete.return_value.data
        mock_delete.assert_called_once_with(
            url=f"/v1/core/code-interpreters/{code_interpreter_id}"
        )

    @patch.object(DataToolsHttpClient, "put")
    def test_start_session(self, mock_post):
        """测试start_session方法"""
        # Arrange
        mock_post.return_value = RequestResult(
            success=True,
            status_code=200,
            data={
                "code_interpreter_id": "test-code-interpreter-id",
                "created_at": "2026-01-01T00:00:00Z",
                "name": "test-session-name",
                "session_id": "test-session-id",
                "session_timeout": 600
            },
            headers={},
            streaming=True,
            _raw_response=None,
        )
        code_interpreter_name = "test-code-interpreter-name"
        api_key = "test-api-key"
        request_params = {
            "name": "test-session-name",
            "session_timeout": 600
        }

        # Act
        result = self.data_client.start_session(
            code_interpreter_name=code_interpreter_name,
            api_key=api_key,
            request_params=request_params
        )

        # Assert
        assert result == mock_post.return_value.data
        mock_post.assert_called_once_with(
            url=f"/v1/code-interpreters/{code_interpreter_name}/sessions-start",
            json=request_params,
            headers = {"Authorization": f"Bearer {api_key}"}
        )

    @patch.object(DataToolsHttpClient, "get")
    def test_get_session(self, mock_get):
        """测试get_session方法"""
        # Arrange
        mock_get.return_value = RequestResult(
            success=True,
            status_code=200,
            data={
                "code_interpreter_id": "test-code-interpreter-id",
                "created_at": "2026-01-01T00:00:00Z",
                "name": "test-session-name",
                "session_id": "test-session-id",
                "session_timeout": 600
            },
            headers={},
            streaming=True,
            _raw_response=None,
        )
        code_interpreter_name = "test-code-interpreter-name"
        api_key = "test-api-key"
        session_id = "test-session-id"

        # Act
        result = self.data_client.get_session(
            code_interpreter_name=code_interpreter_name,
            session_id=session_id,
            api_key=api_key
        )

        # Assert
        assert result == mock_get.return_value.data
        mock_get.assert_called_once_with(
            url=f"/v1/code-interpreters/{code_interpreter_name}/sessions-get",
            headers={
                "x-HW-Agentarts-Code-Interpreter-Session-Id": session_id,
                "Authorization": f"Bearer {api_key}"
            }
        )

    @patch.object(DataToolsHttpClient, "put")
    def test_stop_session(self, mock_put):
        """测试stop_session方法"""
        # Arrange
        code_interpreter_name = "test-code-interpreter-name"
        api_key = "test-api-key"
        session_id = "test-session-id"

        # Act
        self.data_client.stop_session(
            code_interpreter_name=code_interpreter_name,
            session_id=session_id,
            api_key=api_key
        )

        # Assert
        mock_put.assert_called_once_with(
            url=f"/v1/code-interpreters/{code_interpreter_name}/sessions-stop",
            headers={
                "x-HW-Agentarts-Code-Interpreter-Session-Id": session_id,
                "Authorization": f"Bearer {api_key}"
            }
        )

    @patch.object(DataToolsHttpClient, "post")
    def test_invoke(self, mock_post):
        """测试invoke方法"""
        # Arrange
        mock_post.return_value = RequestResult(
            success=True,
            status_code=200,
            data={
                "result": {
                    "content": [
                        {
                            "type": "string",
                            "data": "",
                            "description": "string",
                            "mime_type": "string",
                            "name": "string",
                            "size": 1,
                            "text": "string",
                            "url": "string",
                            "resource": {
                                "type": "string",
                                "blob": "",
                                "mime_type": "string",
                                "text": "string",
                                "uri": "string"
                            }
                        }
                    ],
                    "is_error": False,
                    "structured_content": {
                        "execution_time": 100,
                        "exit_code": 0,
                        "stderr": "string",
                        "stdout": "string"
                    }
                },
            },
            headers={},
            streaming=True,
            _raw_response=None,
        )
        code_interpreter_name = "test-code-interpreter-name"
        api_key = "test-api-key"
        session_id = "test-session-id"
        params = {
            "operate_type": "execute_code",
            "arguments": {
                "clear_context": False,
                "code": "print('hello world')",
                "language": "python"
            }
        }

        # Act
        result = self.data_client.invoke(
            code_interpreter_name=code_interpreter_name,
            session_id=session_id,
            api_key=api_key,
            arguments=params
        )

        # Assert
        assert result == mock_post.return_value.data
        mock_post.assert_called_once_with(
            url=f"/v1/code-interpreters/{code_interpreter_name}/invoke",
            headers={
                "x-HW-Agentarts-Code-Interpreter-Session-Id": session_id,
                "Authorization": f"Bearer {api_key}"
            },
            json=params
        )
