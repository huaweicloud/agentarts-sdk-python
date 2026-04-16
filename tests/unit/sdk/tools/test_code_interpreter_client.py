"""
测试CodeInterpreterClient
"""

import base64
import os
import unittest
from unittest.mock import patch

import pytest

from agentarts.sdk.service.tools_http import ControlToolsHttpClient, DataToolsHttpClient
from agentarts.sdk.tools.code_interpreter import CodeInterpreter


class TestCodeInterpreterClient(unittest.TestCase):
    @patch("agentarts.sdk.utils.constant.ENV_HUAWEICLOUD_SDK_AK")
    @patch("agentarts.sdk.utils.constant.ENV_HUAWEICLOUD_SDK_SK")
    @patch("agentarts.sdk.utils.constant.get_control_plane_endpoint")
    @patch("agentarts.sdk.utils.constant.get_code_interpreter_data_plane_endpoint")
    def setUp(self, mock_get_data_plane_endpoint, mock_get_control_plane_endpoint, mock_sk, mock_ak):
        """在每个测试方法前调用"""
        mock_get_control_plane_endpoint.return_value = "https://control-plane.example.com"
        mock_get_data_plane_endpoint.return_value = "https://data-plane.example.com"
        mock_ak.return_value = "test_ak"
        mock_sk.return_value = "test-sk"
        self.code_interpreter_client = CodeInterpreter(region="test-region")

    @patch.object(ControlToolsHttpClient, "create_code_interpreter")
    def test_create_code_interpreter_with_required_params(self, mock_create_code_interpreter):
        """测试create_code_interpreter方法，提供所有必填参数的情况"""
        # Arrange
        mock_create_code_interpreter.return_value = {
            "name": "test-code-interpreter-name",
            "api_key_name": "test-api-key-name",
            "description": "test-code-interpreter-description",
            "auth_type": "API_KEY",
            "execution_agency_name": "test-execution-agency-name",
            "observability": {},
            "network_config": {},
            "agent_gateway_id": "test-agent-gateway-id",
            "tags": []
        }

        # Act
        result = self.code_interpreter_client.create_code_interpreter(
            name="test-code-interpreter-name",
            api_key_name="test-api-key-name"
        )

        # Assert
        assert result == mock_create_code_interpreter.return_value
        mock_create_code_interpreter.assert_called_once_with(
            request_params={
                "name": "test-code-interpreter-name",
                "api_key_name": "test-api-key-name"
            }
        )

    @patch.object(ControlToolsHttpClient, "create_code_interpreter")
    def test_create_code_interpreter_with_all_params(self, mock_create_code_interpreter):
        """测试create_code_interpreter方法，提供所有参数的情况"""
        # Arrange
        mock_create_code_interpreter.return_value = {
            "name": "test-code-interpreter-name",
            "api_key_name": "test-api-key-name",
            "description": "test-code-interpreter-description",
            "auth_type": "API_KEY",
            "execution_agency_name": "test-execution-agency-name",
            "observability": {
                "logs": {
                    "enable": True,
                    "group_id": "test-group-id",
                    "stream_id": "test-stream-id"
                },
                "metrics": {
                    "enable": True,
                    "instance_id": "test-instance-id"
                },
                "tracing": {
                    "enable": True,
                    "service_group": "test-service-group"
                }
            },
            "network_config": {
                "network_config": "PUBLIC"
            },
            "agent_gateway_id": "test-agent-gateway-id",
            "tags": [
                {
                    "key": "test-tag",
                    "value": "test-tag-value"
                }
            ]
        }

        # Act
        result = self.code_interpreter_client.create_code_interpreter(
            name="test-code-interpreter-name",
            api_key_name="test-api-key-name",
            description="test-code-interpreter-description",
            auth_type="API_KEY",
            execution_agency_name="test-execution-agency-name",
            observability={
                "logs": {
                    "enable": True,
                    "group_id": "test-group-id",
                    "stream_id": "test-stream-id"
                },
                "metrics": {
                    "enable": True,
                    "instance_id": "test-instance-id"
                },
                "tracing": {
                    "enable": True,
                    "service_group": "test-service-group"
                }
            },
            network_config={
                "network_config": "PUBLIC"
            },
            agent_gateway_id="test-agent-gateway-id",
            tags=[
                {
                    "key": "test-tag",
                    "value": "test-tag-value"
                }
            ]
        )

        # Assert
        assert result == mock_create_code_interpreter.return_value
        mock_create_code_interpreter.assert_called_once_with(
            request_params={
                "name": "test-code-interpreter-name",
                "api_key_name": "test-api-key-name",
                "description": "test-code-interpreter-description",
                "auth_type": "API_KEY",
                "execution_agency_name": "test-execution-agency-name",
                "observability": {
                    "logs": {
                        "enable": True,
                        "group_id": "test-group-id",
                        "stream_id": "test-stream-id"
                    },
                    "metrics": {
                        "enable": True,
                        "instance_id": "test-instance-id"
                    },
                    "tracing": {
                        "enable": True,
                        "service_group": "test-service-group"
                    }
                },
                "network_config": {
                    "network_config": "PUBLIC"
                },
                "agent_gateway_id": "test-agent-gateway-id",
                "tags": [
                    {
                        "key": "test-tag",
                        "value": "test-tag-value"
                    }
                ]
            }
        )

    @patch.object(ControlToolsHttpClient, "list_code_interpreters")
    def test_list_code_interpreters_with_default_params(self, mock_list_code_interpreters):
        """测试list_code_interpreters方法，提供默认参数的情况"""
        # Arrange
        mock_list_code_interpreters.return_value = {
            "total_count": 1,
            "items": [
                {
                    "name": "test-code-interpreter-name",
                    "api_key_name": "test-api-key-name"
                }
            ]
        }

        # Act
        result = self.code_interpreter_client.list_code_interpreters()

        # Assert
        assert result == mock_list_code_interpreters.return_value
        mock_list_code_interpreters.assert_called_once_with(
            request_params={
                "limit": 10,
                "offset": 0,
            }
        )

    @patch.object(ControlToolsHttpClient, "list_code_interpreters")
    def test_list_code_interpreters_with_all_params(self, mock_list_code_interpreters):
        """测试list_code_interpreters方法，提供所有参数的情况"""
        # Arrange
        mock_list_code_interpreters.return_value = {
            "total_count": 1,
            "items": [
                {
                    "name": "test-code-interpreter-name",
                    "api_key_name": "test-api-key-name"
                }
            ]
        }

        # Act
        result = self.code_interpreter_client.list_code_interpreters(
            name="test-name",
            limit=20,
            offset=10,
            sort_key="created_at",
            sort_dir="asc"
        )

        # Assert
        assert result == mock_list_code_interpreters.return_value
        mock_list_code_interpreters.assert_called_once_with(
            request_params={
                "name": "test-name",
                "limit": 20,
                "offset": 10,
                "sort_key": "created_at",
                "sort_dir": "asc"
            }
        )

    @patch.object(ControlToolsHttpClient, "update_code_interpreter")
    def test_update_code_interpreter(self, mock_update_code_interpreter):
        """测试update_code_interpreter方法"""
        # Arrange
        mock_update_code_interpreter.return_value = {
            "id": "test-code-interpreter-id",
            "name": "test-code-interpreter-name",
            "description": "test-code-interpreter-description",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "execution_agency_name": "test-execution-agency-name",
            "agent_gateway_id": "test-agent-gateway-id",
            "workload_identity": {
                "urn": "test-workload-urn"
            },
            "access_endpoint": "test-access-endpoint-url",
            "observability": {
                "logs": {
                    "enable": True,
                    "group_id": "test-group-id",
                    "stream_id": "test-stream-id"
                },
                "metrics": {
                    "enable": True,
                    "instance_id": "test-instance-id"
                },
                "tracing": {
                    "enable": True,
                    "service_group": "test-service-group"
                }
            },
            "tags": [
                {
                    "key": "test-tag",
                    "value": "test-tag-value"
                }
            ]
        }

        # Act
        result = self.code_interpreter_client.update_code_interpreter(
            code_interpreter_id="test-code-interpreter-id",
            observability={
                "logs": {
                    "enable": True,
                    "group_id": "test-group-id",
                    "stream_id": "test-stream-id"
                },
                "metrics": {
                    "enable": True,
                    "instance_id": "test-instance-id"
                },
                "tracing": {
                    "enable": True,
                    "service_group": "test-service-group"
                }
            },
            tags=[
                {
                    "key": "test-tag",
                    "value": "test-tag-value"
                }
            ]
        )
        # Assert
        assert result == mock_update_code_interpreter.return_value
        mock_update_code_interpreter.assert_called_once_with(
            code_interpreter_id="test-code-interpreter-id",
            request_params={
                "observability": {
                    "logs": {
                        "enable": True,
                        "group_id": "test-group-id",
                        "stream_id": "test-stream-id"
                    },
                    "metrics": {
                        "enable": True,
                        "instance_id": "test-instance-id"
                    },
                    "tracing": {
                        "enable": True,
                        "service_group": "test-service-group"
                    }
                },
                "tags": [
                    {
                        "key": "test-tag",
                        "value": "test-tag-value"
                    }
                ]
            }
        )

    @patch.object(ControlToolsHttpClient, "get_code_interpreter")
    def test_get_code_interpreter(self, mock_get_code_interpreter):
        """测试get_code_interpreter方法"""
        # Arrange
        mock_get_code_interpreter.return_value = {
            "id": "test-code-interpreter-id",
            "name": "test-code-interpreter-name",
            "description": "test-code-interpreter-description",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "execution_agency_name": "test-execution-agency-name",
            "observability": {
                "logs": {
                    "enable": True,
                    "group_id": "test-group-id",
                    "stream_id": "test-stream-id"
                },
                "metrics": {
                    "enable": True,
                    "instance_id": "test-instance-id"
                },
                "tracing": {
                    "enable": True,
                    "service_group": "test-service-group"
                }
            },
            "workload_identity": {
                "urn": "test-workload-urn"
            },
            "access_endpoint": "test-access-endpoint-url",
            "agent_gateway_id": "test-agent-gateway-id",
            "tags": [
                {
                    "key": "test-tag",
                    "value": "test-tag-value"
                }
            ],
            "auth_type": "API_KEY",
            "api_key_name": "test-api-key-name",
            "network_config": {
                "vpc_id": "test-vpc-id",
                "subnet_id": "test-subnet-id",
                "security_group_id": [
                    "test-security-group-id"
                ]
            }
        }
        code_interpreter_id = "test-code-interpreter-id"

        # Act
        result = self.code_interpreter_client.get_code_interpreter(
            code_interpreter_id=code_interpreter_id
        )

        # Assert
        assert result == mock_get_code_interpreter.return_value
        mock_get_code_interpreter.assert_called_once_with(
            code_interpreter_id=code_interpreter_id
        )

    @patch.object(ControlToolsHttpClient, "delete_code_interpreter")
    def test_delete_code_interpreter(self, mock_delete_code_interpreter):
        """测试delete_code_interpreter方法"""
        # Arrange & Act
        code_interpreter_id = "test-code-interpreter-id"
        self.code_interpreter_client.delete_code_interpreter(
            code_interpreter_id=code_interpreter_id
        )

        # Assert
        mock_delete_code_interpreter.assert_called_once_with(
            code_interpreter_id=code_interpreter_id
        )

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "start_session")
    def test_start_session_with_default_params(self, mock_start_session, mock_getenv):
        """测试start_session方法，提供默认参数的情况"""
        # Arrange
        test_session_id = "test-session-id"
        test_code_interpreter_name = "test-code-interpreter-name"
        test_session_name = "test-session-name"
        mock_start_session.return_value = {"session_id": test_session_id}
        mock_getenv.return_value = "test-api-key"

        # Act
        result = self.code_interpreter_client.start_session(
            code_interpreter_name=test_code_interpreter_name,
            session_name=test_session_name
        )

        # Assert
        assert result == test_session_id
        assert self.code_interpreter_client.session_id == test_session_id
        assert self.code_interpreter_client.code_interpreter_name == test_code_interpreter_name
        mock_start_session.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            api_key="test-api-key",
            request_params={
                "name": test_session_name,
                "session_timeout": 900  # 默认值
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "start_session")
    def test_start_session_with_custom_params(self, mock_start_session, mock_getenv):
        """测试start_session方法，提供自定义参数的情况"""
        test_session_id = "test-session-id"
        test_code_interpreter_name = "test-code-interpreter-name"
        test_session_name = "test-session-name"
        test_api_key = "custom-api-key"
        test_session_timeout = 3600  # 1小时
        mock_start_session.return_value = {"session_id": test_session_id}

        # Act
        result = self.code_interpreter_client.start_session(
            code_interpreter_name=test_code_interpreter_name,
            session_name=test_session_name,
            api_key=test_api_key,
            session_timeout=test_session_timeout
        )

        # Assert
        assert result == test_session_id
        assert self.code_interpreter_client.session_id == test_session_id
        assert self.code_interpreter_client.code_interpreter_name == test_code_interpreter_name
        mock_start_session.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            api_key=test_api_key,
            request_params={
                "name": test_session_name,
                "session_timeout": test_session_timeout
            }
        )
        mock_getenv.assert_not_called()  # 因为我们提供了api_key，所以不应该调用getenv


    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "get_session")
    def test_get_session_with_custom_params(self, mock_get_session, mock_getenv):
        """测试get_session方法，提供自定义参数的情况"""
        # Arrange
        session_id = "test-session-id"
        code_interpreter_name = "test-code-interpreter-name"
        mock_get_session.return_value = {
            "code_interpreter_name": code_interpreter_name,
            "session_id": session_id,
            "created_at": "2023-01-01T00:00:00Z",
            "name": "test-session-name",
            "session_timeout": 900
        }
        mock_getenv.return_value = "test-api-key"

        # Act
        response = self.code_interpreter_client.get_session(
            code_interpreter_name=code_interpreter_name,
            session_id=session_id
        )

        # Assert
        assert response == mock_get_session.return_value
        mock_get_session.assert_called_once_with(
            code_interpreter_name=code_interpreter_name,
            session_id=session_id,
            api_key="test-api-key"
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    def test_get_session_with_no_params(self):
        """测试get_session方法，不提供参数的情况"""
        # Arrange
        error_message = "code_interpreter_name and session_id are required"
        code_interpreter_name = "test-code-interpreter-name"

        # Act & Assert
        with pytest.raises(ValueError, match=error_message):
            self.code_interpreter_client.get_session(
                code_interpreter_name=code_interpreter_name
            )

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "stop_session")
    def test_stop_session_with_session_exists(self, mock_stop_session, mock_getenv):
        """测试stop_session方法，会话已存在的情况"""
        # Arrange
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"

        # Act
        self.code_interpreter_client.stop_session()

        # Assert
        mock_stop_session.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key"
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    def test_stop_session_with_no_activate(self):
        """测试stop_session方法，无激活会话的情况"""
        # Arrange & Act
        self.code_interpreter_client.stop_session()

        # Assert
        assert self.code_interpreter_client.session_id is None
        assert self.code_interpreter_client.code_interpreter_name is None


    def test_invoke_with_no_existing_session(self):
        """测试invoke方法，无激活会话的情况"""
        # Arrange
        error_message = "No Code Interpreter exists, use create_code_interpreter method first"

        # Act & Assert
        with pytest.raises(ValueError, match=error_message):
            self.code_interpreter_client.invoke(
                operate_type="test-method",
                arguments={}
            )

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_invoke_with_existing_session(self, mock_invoke, mock_getenv):
        """测试invoke方法，会话已存在的情况"""
        # Arrange
        mock_invoke.return_value = {"result": "success"}
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"

        # Act
        self.code_interpreter_client.invoke(
            operate_type="test-method",
            arguments={}
        )

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "test-method",
                "arguments": {}
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_execute_code_with_python(self, mock_invoke, mock_getenv):
        """测试execute_code方法，提供Python代码的情况"""
        # Arrange
        code = "print('Hello, World!')"
        mock_invoke.return_value = {"result": "success"}
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"

        # Act
        self.code_interpreter_client.execute_code(
            code=code,
        )

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "execute_code",
                "arguments": {
                    "code": code,
                    "language": "python",
                    "clear_context": False
                }
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_execute_code_with_clear_context(self, mock_invoke, mock_getenv):
        """测试execute_code方法，提供清除上下文的情况"""
        # Arrange
        code = "print('Hello, World!')"
        mock_invoke.return_value = {"result": "success"}
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"

        # Act
        self.code_interpreter_client.execute_code(
            code=code,
            clear_context=True
        )

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "execute_code",
                "arguments": {
                    "code": code,
                    "language": "python",
                    "clear_context": True
                }
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    def test_execute_code_with_invalid_language(self):
        """测试execute_code方法，提供无效的语言的情况"""
        # Arrange
        code = "console.log('Hello, World!')"
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        language = "javascript"
        error_message = f"Invalid language. Supported languages are: {', '.join(['python'])}"

        # Act & Assert
        with pytest.raises(ValueError, match=error_message):
            self.code_interpreter_client.execute_code(
                code=code,
                language=language
            )

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_execute_command_with_valid_command(self, mock_invoke, mock_getenv):
        """测试execute_command方法，提供有效命令的情况"""
        # Arrange
        command = "ls -la"
        mock_invoke.return_value = {"result": "success"}
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"

        # Act
        self.code_interpreter_client.execute_command(
            command=command
        )

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "execute_command",
                "arguments": {
                    "command": command
                }
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    @patch.object(os, "getenv")
    def test_execute_command_with_invalid_command(self, mock_getenv):
        """测试execute_command方法，提供无效命令的情况"""
        # Arrange
        command = "^ls -la"
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"
        error_message = "Invalid command format"

        # Act & Assert
        with pytest.raises(ValueError, match=error_message):
            self.code_interpreter_client.execute_command(
                command=command
            )

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_upload_file_with_text_content(self, mock_invoke, mock_getenv):
        """测试upload_file方法，提供文本内容的情况"""
        # Arrange
        mock_invoke.return_value = {"result": "success"}
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"
        path = "/home/user/test.txt"
        text_content = "Hello, World!"
        description = "test file"
        self.code_interpreter_client.upload_file(
            path=path,
            content=text_content,
            description=description
        )

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "write_files",
                "arguments": {
                    "write_contents": [
                        {
                            "path": path,
                            "text": text_content
                        }
                    ]
                }
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_upload_file_with_binary_content(self, mock_invoke, mock_getenv):
        """测试upload_file方法，提供二进制内容的情况"""
        # Arrange
        mock_invoke.return_value = {"result": "success"}
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"
        path = "/home/user/image.jpg"
        binary_content = b"\x89PNG\r\n\x1a\n"
        encoded_content = base64.b64encode(binary_content).decode("utf-8")
        description = "test file"
        self.code_interpreter_client.upload_file(
            path=path,
            content=binary_content,
            description=description
        )

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "write_files",
                "arguments": {
                    "write_contents": [
                        {
                            "path": path,
                            "blob": encoded_content
                        }
                    ]
                }
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_upload_file_with_relative_path(self, mock_invoke, mock_getenv):
        """测试upload_file方法，提供相对路径的情况"""
        # Arrange
        mock_invoke.return_value = {"result": "success"}
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"
        path = "test.txt"
        text_content = "Hello, World!"
        description = "test file"

        # Act
        self.code_interpreter_client.upload_file(
            path=path,
            content=text_content,
            description=description
        )

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "write_files",
                "arguments": {
                    "write_contents": [
                        {
                            "path": os.path.join("/home/user", path),
                            "text": text_content
                        }
                    ]
                }
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")


    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_upload_files_with_mixed_content(self, mock_invoke, mock_getenv):
        """测试upload_files方法，提供混合内容的情况"""
        # Arrange
        mock_invoke.return_value = {"result": "success"}
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"
        binary_content = b"\x89PNG\r\n\x1a\n"
        encoded_content = base64.b64encode(binary_content).decode("utf-8")
        files = [
            {
                "path": "/home/user/test.txt",
                "content": "Hello, World!",
            },
            {
                "path": "/home/user/image.jpg",
                "content": binary_content,
            },
        ]

        # Act
        self.code_interpreter_client.upload_files(files=files)

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "write_files",
                "arguments": {
                    "write_contents": [
                        {
                            "path": "/home/user/test.txt",
                            "text": "Hello, World!",
                        },
                        {
                            "path": "/home/user/image.jpg",
                            "blob": encoded_content,
                        },
                    ]
                }
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")


    def test_upload_files_with_invalid_path(self):
        """测试upload_files方法，提供无效路径的情况"""
        # Arrange
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        error_message= "Invalid path. Path must start with /home/user"
        files = [
            {
                "path": "/invalid/user/test.txt",
                "content": "Hello, World!",
            },
            {
                "path": "/home/user/image.jpg",
                "content": b"\x89PNG\r\n\x1a\n",
            },
        ]

        # Act & Assert
        with pytest.raises(ValueError, match=error_message):
            self.code_interpreter_client.upload_files(files=files)


    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_download_file_with_text_content(self, mock_invoke, mock_getenv):
        """测试download_file方法，提供文本内容的情况"""
        # Arrange
        text_content = "col1, col2\n1, 2\n3, 4"
        mock_invoke.return_value = {
            "stream" : [
                {
                    "result": {
                        "contents": [
                            {
                                "type": "resource",
                                "resource": {
                                    "uri": "/home/user/data.csv",
                                    "text": text_content
                                }
                            }
                        ]
                    }
                }
            ]
        }
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        path = "/home/user/data.csv"
        mock_getenv.return_value = "test-api-key"

        # Act
        response = self.code_interpreter_client.download_file(path)

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "read_files",
                "arguments": {
                    "paths": [
                        path
                    ]
                }
            }
        )
        assert response == text_content
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_download_file_with_binary_content(self, mock_invoke, mock_getenv):
        """测试download_file方法，提供二进制内容的情况"""
        # Arrange
        binary_content = b"\x89PNG\r\n\x1a\n"
        encode_content = base64.b64encode(binary_content).decode("utf-8")
        mock_invoke.return_value = {
            "stream" : [
                {
                    "result": {
                        "contents": [
                            {
                                "type": "resource",
                                "resource": {
                                    "uri": "/home/user/image.png",
                                    "blob": encode_content
                                }
                            }
                        ]
                    }
                }
            ]
        }
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        path = "/home/user/image.png"
        mock_getenv.return_value = "test-api-key"

        # Act
        response = self.code_interpreter_client.download_file(path)

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "read_files",
                "arguments": {
                    "paths": [
                        path
                    ]
                }
            }
        )
        assert response == binary_content
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    @patch.object(DataToolsHttpClient, "invoke")
    def test_download_file_with_no_found_file(self, mock_invoke):
        """测试download_file方法，提供不存在的文件的情况"""
        # Arrange
        mock_invoke.return_value = {
            "stream" : []
        }
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        path = "/home/user/non-existent.csv"
        error_message = f"Could not read file: {path}"

        # Act & Assert
        with pytest.raises(FileNotFoundError, match=error_message):
            self.code_interpreter_client.download_file(path)

    def test_download_file_with_invalid_path(self):
        """测试download_file方法，提供无效路径的情况"""
        # Arrange
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        path = "/var/invalid.csv"
        error_message = "Invalid path. Path must start with /home/user"

        # Act & Assert
        with pytest.raises(ValueError, match=error_message):
            self.code_interpreter_client.download_file(path)

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_download_files_with_text_files(self, mock_invoke, mock_getenv):
        """测试download_files方法，提供文本文件的情况"""
        # Arrange
        mock_invoke.return_value = {
            "stream" : [
                {
                    "result": {
                        "content": [
                            {
                                "type": "resource",
                                "resource": {
                                    "uri": "/home/user/data.csv",
                                    "text": "col1, col2\n1, 2\n3, 4"
                                }
                            },
                            {
                                "type": "resource",
                                "resource": {
                                    "uri": "/home/user/config.json",
                                    "text": '{"key": "value"}'
                                }
                            }
                        ]
                    }
                }
            ]
        }
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        paths = ["/home/user/data.csv", "/home/user/config.json"]
        mock_getenv.return_value = "test-api-key"

        # Act
        self.code_interpreter_client.download_files(paths)

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "read_files",
                "arguments": {
                    "paths": paths
                }
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_download_files_with_binary_files(self, mock_invoke, mock_getenv):
        """测试download_files方法，提供二进制文件的情况"""
        # Arrange
        binary_content = b"\x89PNG\r\n\x1a\n"
        encode_binary = base64.b64encode(binary_content).decode("utf-8")
        mock_invoke.return_value = {
            "stream" : [
                {
                    "result": {
                        "content": [
                            {
                                "type": "resource",
                                "resource": {
                                    "uri": "/home/user/iamge-1.png",
                                    "blob": encode_binary
                                }
                            },
                            {
                                "type": "resource",
                                "resource": {
                                    "uri": "/home/user/image-2.png",
                                    "blob": encode_binary
                                }
                            }
                        ]
                    }
                }
            ]
        }
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        paths = ["/home/user/iamge-1.png", "/home/user/image-2.png"]
        mock_getenv.return_value = "test-api-key"

        # Act
        self.code_interpreter_client.download_files(paths)

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "read_files",
                "arguments": {
                    "paths": paths
                }
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    def test_download_files_with_invalid_path(self):
        """测试download_files方法，提供无效路径的情况"""
        # Arrange
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        paths = ["/var/user/data.csv", "/var/user/config.json"]
        error_message = "Invalid path. Path must start with /home/user"

        # Act & Assert
        with pytest.raises(ValueError, match=error_message):
            self.code_interpreter_client.download_files(paths)


    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_install_packages(self, mock_invoke, mock_getenv):
        """测试install_packages方法"""
        # Arrange
        packages = ["pandas"]
        mock_invoke.return_value = {"result": "success"}
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"

        # Act
        self.code_interpreter_client.install_packages(packages)

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "execute_command",
                "arguments": {
                    "command": f"pip install {' '.join(packages)} "
                }
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_install_packages_with_version(self, mock_invoke, mock_getenv):
        """测试install_packages方法，提供版本号的情况"""
        # Arrange
        packages = ["pandas>=2.0"]
        mock_invoke.return_value = {"result": "success"}
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"

        # Act
        self.code_interpreter_client.install_packages(packages)

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "execute_command",
                "arguments": {
                    "command": f"pip install {' '.join(packages)} "
                }
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_install_packages_with_upgrade(self, mock_invoke, mock_getenv):
        """测试install_packages方法，提供升级选项"""
        # Arrange
        packages = ["pandas"]
        mock_invoke.return_value = {"result": "success"}
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"

        # Act
        self.code_interpreter_client.install_packages(
            packages=packages,
            upgrade=True
        )

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "execute_command",
                "arguments": {
                    "command": f"pip install {' '.join(packages)} --upgrade"
                }
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

    def test_install_packages_with_invalid_package(self):
        """测试install_packages方法，提供无效的包的情况"""
        # Arrange
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        invalid_package = ["pandas&&"]
        error_message = f"Invalid package name: {invalid_package[0]}"

        # Act & Assert
        with pytest.raises(ValueError, match=error_message):
            self.code_interpreter_client.install_packages(invalid_package)



    @patch.object(os, "getenv")
    @patch.object(DataToolsHttpClient, "invoke")
    def test_clear_context(self, mock_invoke, mock_getenv):
        """测试clear_context方法"""
        # Arrange
        mock_invoke.return_value = {"result": "success"}
        self.code_interpreter_client.code_interpreter_name = "test-code-interpreter-name"
        self.code_interpreter_client.session_id = "test-session-id"
        mock_getenv.return_value = "test-api-key"

        # Act
        self.code_interpreter_client.clear_context()

        # Assert
        mock_invoke.assert_called_once_with(
            code_interpreter_name="test-code-interpreter-name",
            session_id="test-session-id",
            api_key="test-api-key",
            arguments={
                "operate_type": "execute_code",
                "arguments": {
                    "code": "# Context cleared",
                    "language": "python",
                    "clear_context": True
                }
            }
        )
        mock_getenv.assert_called_once_with("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")
