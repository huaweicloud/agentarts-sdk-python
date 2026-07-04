"""
Unit tests for Gateway CLI commands
"""

import importlib
from unittest.mock import Mock, patch

import pytest

gateway_module = importlib.import_module("agentarts.toolkit.cli.gateway.gateway")

from agentarts.toolkit.cli.gateway.gateway import _format_output, _parse_json


class TestGatewayCLI:
    """Test Gateway CLI commands"""

    def test_parse_json_valid(self):
        """Test _parse_json with valid JSON"""
        json_str = '{"key": "value"}'
        result = _parse_json(json_str)
        assert result == {"key": "value"}

    def test_parse_json_invalid(self):
        """Test _parse_json with invalid JSON"""
        invalid_json = '{"key": "value"'
        with pytest.raises(ValueError, match="Invalid JSON format"):
            _parse_json(invalid_json)

    def test_parse_json_empty(self):
        """Test _parse_json with empty string"""
        result = _parse_json("")
        assert result is None

    def test_parse_json_none(self):
        """Test _parse_json with None"""
        result = _parse_json(None)
        assert result is None

    def test_format_output_json(self):
        """Test _format_output with JSON serializable data"""
        data = {"key": "value"}
        result = _format_output(data)
        assert isinstance(result, str)
        assert "key" in result
        assert "value" in result

    def test_format_output_non_json(self):
        """Test _format_output with non-JSON serializable data"""
        class NonSerializable:
            def __str__(self):
                return "NonSerializable object"

        data = NonSerializable()
        result = _format_output(data)
        assert isinstance(result, str)
        assert "NonSerializable object" in result

    def test_create_gateway_command(self):
        """Test create_gateway CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"gateway_id": "test-id", "name": "test-gateway"}
            mock_instance.create_gateway.return_value = mock_result

            result = runner.invoke(gateway_module.gateway, ["create", "--name", "test-gateway"])

            assert result.exit_code == 0
            mock_instance.create_gateway.assert_called_once()

    def test_create_gateway_command_with_json_configs(self):
        """Test create_gateway CLI command with JSON configuration"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"gateway_id": "test-id"}
            mock_instance.create_gateway.return_value = mock_result

            result = runner.invoke(gateway_module.gateway, [
                "create",
                "--name", "test-gateway",
                "--protocol-configuration", '{"mcp": {"search_configuration": {}}}'
            ])

            assert result.exit_code == 0
            call_args = mock_instance.create_gateway.call_args
            assert call_args[1]["protocol_configuration"] == {"mcp": {"search_configuration": {}}}

    def test_create_gateway_command_invalid_json(self):
        """Test create_gateway CLI command with invalid JSON"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(gateway_module.gateway, [
            "create",
            "--name", "test-gateway",
            "--protocol-configuration", '{"invalid json'
        ])

        assert result.exit_code == 0
        assert "Invalid JSON format" in result.output

    def test_create_gateway_command_error_response(self):
        """Test create_gateway CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "400", "error_msg": "Bad request"}
            mock_instance.create_gateway.return_value = mock_result

            result = runner.invoke(gateway_module.gateway, ["create", "--name", "test-gateway"])

            assert result.exit_code == 0
            assert "Error creating gateway" in result.output

    def test_update_gateway_command(self):
        """Test update_gateway CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"gateway_id": "test-id"}
            mock_instance.update_gateway.return_value = mock_result

            result = runner.invoke(gateway_module.gateway, ["update", "test-id", "--description", "Updated"])

            assert result.exit_code == 0
            mock_instance.update_gateway.assert_called_once()

    def test_delete_gateway_command_cancelled(self):
        """Test delete_gateway CLI command when cancelled"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(gateway_module.gateway, ["delete", "test-id"], input="n")

        assert result.exit_code == 0
        assert "Deletion cancelled" in result.output

    def test_delete_gateway_command_confirmed(self):
        """Test delete_gateway CLI command when confirmed"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_instance.delete_gateway.return_value = mock_result

            result = runner.invoke(gateway_module.gateway, ["delete", "test-id"], input="y")

            assert result.exit_code == 0
            mock_instance.delete_gateway.assert_called_once()

    def test_get_gateway_command(self):
        """Test get_gateway CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"gateway_id": "test-id", "name": "test-gateway"}
            mock_instance.get_gateway.return_value = mock_result

            result = runner.invoke(gateway_module.gateway, ["get", "test-id"])

            assert result.exit_code == 0
            mock_instance.get_gateway.assert_called_once()

    def test_list_gateways_command(self):
        """Test list_gateways CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"total": 0, "gateways": []}
            mock_instance.list_gateways.return_value = mock_result

            result = runner.invoke(gateway_module.gateway, ["list"])

            assert result.exit_code == 0
            mock_instance.list_gateways.assert_called_once()

    def test_list_gateways_command_with_filters(self):
        """Test list_gateways CLI command with filters"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"total": 1, "gateways": [{"name": "test"}]}
            mock_instance.list_gateways.return_value = mock_result

            result = runner.invoke(gateway_module.gateway, [
                "list",
                "--name", "test",
                "--limit", "10",
                "--offset", "0",
                "--tag-key-exists", "key1,key2"
            ])

            assert result.exit_code == 0
            call_args = mock_instance.list_gateways.call_args
            assert call_args[1]["name"] == "test"
            assert call_args[1]["limit"] == 10
            assert call_args[1]["offset"] == 0
            assert call_args[1]["tag_key_exists"] == ["key1", "key2"]

    def test_list_gateways_command_invalid_offset(self):
        """Test list_gateways CLI command with invalid offset"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(gateway_module.gateway, ["list", "--offset", "-1"])

        assert result.exit_code == 0
        assert "Offset must be greater than or equal to 0" in result.output

    def test_list_gateways_command_invalid_limit(self):
        """Test list_gateways CLI command with invalid limit"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(gateway_module.gateway, ["list", "--limit", "0"])

        assert result.exit_code == 0
        assert "Limit must be greater than 0" in result.output

    def test_create_target_command(self):
        """Test create_gateway_target CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"target_id": "test-target-id"}
            mock_instance.create_gateway_target.return_value = mock_result

            result = runner.invoke(gateway_module.gateway, [
                "create-target",
                "test-gateway-id",
                "--target-configuration", '{"type": "http"}'
            ])

            assert result.exit_code == 0
            mock_instance.create_gateway_target.assert_called_once()

    def test_update_target_command(self):
        """Test update_gateway_target CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"target_id": "test-target-id"}
            mock_instance.update_gateway_target.return_value = mock_result

            result = runner.invoke(gateway_module.gateway, [
                "update-target",
                "test-gateway-id",
                "test-target-id",
                "--name", "updated-target"
            ])

            assert result.exit_code == 0
            mock_instance.update_gateway_target.assert_called_once()

    def test_delete_target_command_cancelled(self):
        """Test delete_gateway_target CLI command when cancelled"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(gateway_module.gateway, ["delete-target", "test-gateway-id", "test-target-id"], input="n")

        assert result.exit_code == 0
        assert "Deletion cancelled" in result.output

    def test_delete_target_command_confirmed(self):
        """Test delete_gateway_target CLI command when confirmed"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_instance.delete_gateway_target.return_value = mock_result

            result = runner.invoke(gateway_module.gateway, ["delete-target", "test-gateway-id", "test-target-id"], input="y")

            assert result.exit_code == 0
            mock_instance.delete_gateway_target.assert_called_once()

    def test_get_target_command(self):
        """Test get_gateway_target CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"target_id": "test-target-id"}
            mock_instance.get_gateway_target.return_value = mock_result

            result = runner.invoke(gateway_module.gateway, ["get-target", "test-gateway-id", "test-target-id"])

            assert result.exit_code == 0
            mock_instance.get_gateway_target.assert_called_once()

    def test_list_targets_command(self):
        """Test list_gateway_targets CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"total": 0, "targets": []}
            mock_instance.list_gateway_targets.return_value = mock_result

            result = runner.invoke(gateway_module.gateway, ["list-targets", "test-gateway-id"])

            assert result.exit_code == 0
            mock_instance.list_gateway_targets.assert_called_once()

    def test_list_targets_command_invalid_offset(self):
        """Test list_gateway_targets CLI command with invalid offset"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(gateway_module.gateway, ["list-targets", "test-gateway-id", "--offset", "100001"])

        assert result.exit_code == 0
        assert "Offset must be less than or equal to 100000" in result.output

    def test_list_targets_command_invalid_limit(self):
        """Test list_gateway_targets CLI command with invalid limit"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(gateway_module.gateway, ["list-targets", "test-gateway-id", "--limit", "101"])

        assert result.exit_code == 0
        assert "Limit must be less than or equal to 100" in result.output

    def test_handle_error_with_error_fields(self):
        """Test _handle_error with error_code and error_msg fields"""
        mock_result = Mock()
        mock_result.data = {"error_code": "400", "error_msg": "Bad request"}
        mock_result.error = None

        with patch.object(gateway_module, "echo_error") as mock_echo_error:
            gateway_module._handle_error("test operation", mock_result)

            mock_echo_error.assert_called()
            call_args = mock_echo_error.call_args[0][0]
            assert "Error test operation" in call_args
            assert "400" in call_args
            assert "Bad request" in call_args

    def test_handle_error_without_error_fields(self):
        """Test _handle_error without error_code and error_msg fields"""
        mock_result = Mock()
        mock_result.data = {"message": "Unknown error"}
        mock_result.error = "Connection failed"

        with patch.object(gateway_module, "echo_error") as mock_echo_error:
            gateway_module._handle_error("test operation", mock_result)

            mock_echo_error.assert_called()
            call_args = mock_echo_error.call_args[0][0]
            assert "Error test operation" in call_args

    def test_get_gateway_client(self):
        """Test _get_gateway_client function"""
        import agentarts.sdk.gateway as gateway_sdk_module

        with patch.object(gateway_sdk_module, "GatewayClient") as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance

            result = gateway_module._get_gateway_client(verify_ssl=True)

            assert result == mock_instance
            mock_client_class.assert_called_once_with(verify_ssl=True)

    def test_get_gateway_client_skip_ssl(self):
        """Test _get_gateway_client with SSL verification skipped"""
        import agentarts.sdk.gateway as gateway_sdk_module

        with patch.object(gateway_sdk_module, "GatewayClient") as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance

            result = gateway_module._get_gateway_client(verify_ssl=False)

            assert result == mock_instance
            mock_client_class.assert_called_once_with(verify_ssl=False)

    def test_create_gateway_command_unexpected_error(self):
        """Test create_gateway CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.create_gateway.side_effect = Exception("Unexpected error")

            result = runner.invoke(gateway_module.gateway, ["create", "--name", "test-gateway"])

            assert result.exit_code == 0
            assert "Unexpected error" in result.output

    def test_update_gateway_command_unexpected_error(self):
        """Test update_gateway CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.update_gateway.side_effect = Exception("Unexpected error")

            result = runner.invoke(gateway_module.gateway, ["update", "test-id", "--description", "Updated"])

            assert result.exit_code == 0
            assert "Unexpected error" in result.output

    def test_update_gateway_command_value_error(self):
        """Test update_gateway CLI command with ValueError"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(gateway_module.gateway, [
            "update", "test-id",
            "--protocol-configuration", '{"invalid json'
        ])

        assert result.exit_code == 0
        assert "Invalid JSON format" in result.output

    def test_delete_gateway_command_unexpected_error(self):
        """Test delete_gateway CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.delete_gateway.side_effect = Exception("Unexpected error")

            result = runner.invoke(gateway_module.gateway, ["delete", "test-id"], input="y")

            assert result.exit_code == 0
            assert "Unexpected error" in result.output

    def test_get_gateway_command_unexpected_error(self):
        """Test get_gateway CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.get_gateway.side_effect = Exception("Unexpected error")

            result = runner.invoke(gateway_module.gateway, ["get", "test-id"])

            assert result.exit_code == 0
            assert "Unexpected error" in result.output

    def test_list_gateways_command_unexpected_error(self):
        """Test list_gateways CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.list_gateways.side_effect = Exception("Unexpected error")

            result = runner.invoke(gateway_module.gateway, ["list"])

            assert result.exit_code == 0
            assert "Unexpected error" in result.output

    def test_list_gateways_command_offset_greater_than_max(self):
        """Test list_gateways CLI command with offset > 100000"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(gateway_module.gateway, ["list", "--offset", "100001"])

        assert result.exit_code == 0
        assert "Offset must be less than or equal to 100000" in result.output

    def test_list_gateways_command_limit_greater_than_max(self):
        """Test list_gateways CLI command with limit > 100"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(gateway_module.gateway, ["list", "--limit", "101"])

        assert result.exit_code == 0
        assert "Limit must be less than or equal to 100" in result.output

    def test_create_target_command_unexpected_error(self):
        """Test create_gateway_target CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.create_gateway_target.side_effect = Exception("Unexpected error")

            result = runner.invoke(gateway_module.gateway, [
                "create-target", "test-gateway-id",
                "--target-configuration", '{"type": "http"}'
            ])

            assert result.exit_code == 0
            assert "Unexpected error" in result.output

    def test_create_target_command_value_error(self):
        """Test create_gateway_target CLI command with ValueError"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(gateway_module.gateway, [
            "create-target", "test-gateway-id",
            "--target-configuration", '{"invalid json'
        ])

        assert result.exit_code == 0
        assert "Invalid JSON format" in result.output

    def test_update_target_command_unexpected_error(self):
        """Test update_gateway_target CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.update_gateway_target.side_effect = Exception("Unexpected error")

            result = runner.invoke(gateway_module.gateway, [
                "update-target", "test-gateway-id", "test-target-id",
                "--name", "updated-target"
            ])

            assert result.exit_code == 0
            assert "Unexpected error" in result.output

    def test_update_target_command_value_error(self):
        """Test update_gateway_target CLI command with ValueError"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(gateway_module.gateway, [
            "update-target", "test-gateway-id", "test-target-id",
            "--target-configuration", '{"invalid json'
        ])

        assert result.exit_code == 0
        assert "Invalid JSON format" in result.output

    def test_delete_target_command_unexpected_error(self):
        """Test delete_gateway_target CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.delete_gateway_target.side_effect = Exception("Unexpected error")

            result = runner.invoke(gateway_module.gateway, ["delete-target", "test-gateway-id", "test-target-id"], input="y")

            assert result.exit_code == 0
            assert "Unexpected error" in result.output

    def test_get_target_command_unexpected_error(self):
        """Test get_gateway_target CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.get_gateway_target.side_effect = Exception("Unexpected error")

            result = runner.invoke(gateway_module.gateway, ["get-target", "test-gateway-id", "test-target-id"])

            assert result.exit_code == 0
            assert "Unexpected error" in result.output

    def test_list_targets_command_unexpected_error(self):
        """Test list_gateway_targets CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(gateway_module, "_get_gateway_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.list_gateway_targets.side_effect = Exception("Unexpected error")

            result = runner.invoke(gateway_module.gateway, ["list-targets", "test-gateway-id"])

            assert result.exit_code == 0
            assert "Unexpected error" in result.output
