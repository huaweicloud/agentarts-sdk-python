"""
Unit tests for Model Provider CLI commands
"""

import importlib
from unittest.mock import Mock, patch

import pytest

model_provider_module = importlib.import_module("agentarts.toolkit.cli.custom_model_provider.custom_model_provider")

from agentarts.toolkit.cli.custom_model_provider.custom_model_provider import (
    _format_output,
    _parse_json,
    _split_csv,
    _validate_pagination,
)


class TestCustomModelProviderCLI:
    """Test Custom Model Provider CLI commands"""

    # ------------------------------------------------------------------ #
    # Helper functions
    # ------------------------------------------------------------------ #
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

    def test_validate_pagination_defaults(self):
        """Test _validate_pagination applies default values"""
        limit, offset = _validate_pagination(None, None)
        assert limit == 50
        assert offset == 0

    def test_validate_pagination_invalid_offset(self):
        """Test _validate_pagination rejects invalid offset"""
        with pytest.raises(ValueError, match="Offset must be greater than or equal to 0"):
            _validate_pagination(None, -1)
        with pytest.raises(ValueError, match="Offset must be less than or equal to 100000"):
            _validate_pagination(None, 100001)

    def test_validate_pagination_invalid_limit(self):
        """Test _validate_pagination rejects invalid limit"""
        with pytest.raises(ValueError, match="Limit must be greater than 0"):
            _validate_pagination(0, 0)
        with pytest.raises(ValueError, match="Limit must be less than or equal to 100"):
            _validate_pagination(101, 0)

    def test_split_csv(self):
        """Test _split_csv splits comma-separated values"""
        assert _split_csv("a,b,c") == ["a", "b", "c"]
        assert _split_csv("a") == ["a"]
        assert _split_csv("") is None
        assert _split_csv(None) is None

    def test_handle_error_with_error_fields(self):
        """Test _handle_error with error_code and error_msg fields"""
        mock_result = Mock()
        mock_result.data = {"error_code": "400", "error_msg": "Bad request"}
        mock_result.error = None

        with patch.object(model_provider_module, "echo_error") as mock_echo_error:
            model_provider_module._handle_error("test operation", mock_result)

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

        with patch.object(model_provider_module, "echo_error") as mock_echo_error:
            model_provider_module._handle_error("test operation", mock_result)

            mock_echo_error.assert_called()
            call_args = mock_echo_error.call_args[0][0]
            assert "Error test operation" in call_args

    # ------------------------------------------------------------------ #
    # Model provider commands
    # ------------------------------------------------------------------ #
    def test_create_provider_command(self):
        """Test create-provider CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"id": "test-provider-id", "name": "test-provider"}
            mock_instance.create_model_provider.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "create-provider",
                "test-provider",
                "https://example.com/v1",
                "--credential-configuration", '{"provider_configuration": {}}',
            ])

            assert result.exit_code == 0
            mock_instance.create_model_provider.assert_called_once()
            call_args = mock_instance.create_model_provider.call_args
            assert call_args[1]["name"] == "test-provider"
            assert call_args[1]["base_url"] == "https://example.com/v1"
            assert call_args[1]["credential_configuration"] == {"provider_configuration": {}}

    def test_create_provider_command_invalid_json(self):
        """Test create-provider CLI command with invalid JSON"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(model_provider_module.custom_model_provider, [
            "create-provider",
            "test-provider",
            "https://example.com/v1",
            "--credential-configuration", '{"invalid json',
        ])

        assert result.exit_code == 0
        assert "Invalid JSON format" in result.output

    def test_update_provider_command(self):
        """Test update-provider CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"id": "test-provider-id"}
            mock_instance.update_model_provider.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "update-provider",
                "test-provider-id",
                "--description", "Updated description",
            ])

            assert result.exit_code == 0
            mock_instance.update_model_provider.assert_called_once()
            call_args = mock_instance.update_model_provider.call_args
            assert call_args[1]["model_provider_id"] == "test-provider-id"
            assert call_args[1]["description"] == "Updated description"

    def test_delete_provider_command_cancelled(self):
        """Test delete-provider CLI command when cancelled"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(model_provider_module.custom_model_provider, [
            "delete-provider", "test-provider-id"
        ], input="n")

        assert result.exit_code == 0
        assert "Deletion cancelled" in result.output

    def test_delete_provider_command_confirmed(self):
        """Test delete-provider CLI command when confirmed"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_instance.delete_model_provider.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "delete-provider", "test-provider-id"
            ], input="y")

            assert result.exit_code == 0
            mock_instance.delete_model_provider.assert_called_once()

    def test_get_provider_command(self):
        """Test get-provider CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"id": "test-provider-id", "name": "test-provider"}
            mock_instance.get_model_provider.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "get-provider", "test-provider-id"
            ])

            assert result.exit_code == 0
            mock_instance.get_model_provider.assert_called_once()

    def test_list_providers_command(self):
        """Test list-providers CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"total": 0, "model_providers": []}
            mock_instance.list_model_providers.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, ["list-providers"])

            assert result.exit_code == 0
            mock_instance.list_model_providers.assert_called_once()

    def test_list_providers_command_with_filters(self):
        """Test list-providers CLI command with filters"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"total": 1, "model_providers": [{"name": "test"}]}
            mock_instance.list_model_providers.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "list-providers",
                "--name", "test",
                "--model-provider-id", "test-provider-id",
                "--limit", "10",
                "--offset", "0",
                "--tag-key-exists", "key1,key2",
            ])

            assert result.exit_code == 0
            call_args = mock_instance.list_model_providers.call_args
            assert call_args[1]["name"] == "test"
            assert call_args[1]["model_provider_id"] == "test-provider-id"
            assert call_args[1]["limit"] == 10
            assert call_args[1]["offset"] == 0
            assert call_args[1]["tag_key_exists"] == ["key1", "key2"]

    def test_list_providers_command_invalid_limit(self):
        """Test list-providers CLI command with invalid limit"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(model_provider_module.custom_model_provider, [
            "list-providers", "--limit", "0"
        ])

        assert result.exit_code == 0
        assert "Limit must be greater than 0" in result.output

    # ------------------------------------------------------------------ #
    # Model service commands
    # ------------------------------------------------------------------ #
    def test_create_model_command(self):
        """Test create-model CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"id": "test-model-id"}
            mock_instance.create_model.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "create-model",
                "test-provider-id",
                "--model", "qwen2.5-72b",
                "--model-service-name", "my-model",
                "--type", "completions,embeddings",
                "--protocol", "openai",
                "--description", "Test model",
            ])

            assert result.exit_code == 0
            mock_instance.create_model.assert_called_once()
            call_args = mock_instance.create_model.call_args
            assert call_args[1]["model_provider_id"] == "test-provider-id"
            assert call_args[1]["model"] == "qwen2.5-72b"
            assert call_args[1]["model_service_name"] == "my-model"
            assert call_args[1]["type_"] == ["completions", "embeddings"]
            assert call_args[1]["protocol"] == "openai"
            assert call_args[1]["description"] == "Test model"

    def test_list_models_command(self):
        """Test list-models CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"total": 0, "models": []}
            mock_instance.list_models.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "list-models", "test-provider-id"
            ])

            assert result.exit_code == 0
            mock_instance.list_models.assert_called_once()
            call_args = mock_instance.list_models.call_args
            assert call_args[1]["model_provider_id"] == "test-provider-id"
            assert call_args[1]["limit"] == 50
            assert call_args[1]["offset"] == 0

    # ------------------------------------------------------------------ #
    # Model proxy commands
    # ------------------------------------------------------------------ #
    def test_create_proxy_command(self):
        """Test create-proxy CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"gateway_id": "test-gateway-id"}
            mock_instance.create_model_proxy.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "create-proxy",
                "--custom-model-provider-id", "test-provider-id",
                "--name", "test-proxy",
                "--description", "Test proxy",
                "--inbound-authorizer-type", "iam",
                "--agency-name", "TestAgency",
            ])

            assert result.exit_code == 0
            mock_instance.create_model_proxy.assert_called_once()
            call_args = mock_instance.create_model_proxy.call_args
            assert call_args[1]["custom_model_provider_id"] == "test-provider-id"
            assert call_args[1]["name"] == "test-proxy"
            assert call_args[1]["description"] == "Test proxy"
            assert call_args[1]["inbound_authorizer_type"] == "iam"
            assert call_args[1]["agency_name"] == "TestAgency"

    def test_update_proxy_command(self):
        """Test update-proxy CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"gateway_id": "test-gateway-id"}
            mock_instance.update_model_proxy.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "update-proxy",
                "test-gateway-id",
                "--tags", '[{"key": "Environment", "value": "test"}]',
            ])

            assert result.exit_code == 0
            mock_instance.update_model_proxy.assert_called_once()
            call_args = mock_instance.update_model_proxy.call_args
            assert call_args[1]["gateway_id"] == "test-gateway-id"
            assert call_args[1]["tags"] == [{"key": "Environment", "value": "test"}]

    def test_disassociate_proxies_command(self):
        """Test disassociate-proxies CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"success_details": []}
            mock_instance.batch_disassociate_model_proxies.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "disassociate-proxies",
                "--unbindings",
                '[{"custom_model_provider_id": "test-provider-id", "gateway_id": "test-gateway-id"}]',
            ])

            assert result.exit_code == 0
            mock_instance.batch_disassociate_model_proxies.assert_called_once()
            call_args = mock_instance.batch_disassociate_model_proxies.call_args
            assert call_args[1]["unbindings"] == [
                {"custom_model_provider_id": "test-provider-id", "gateway_id": "test-gateway-id"}
            ]

    # ------------------------------------------------------------------ #
    # Quota commands
    # ------------------------------------------------------------------ #
    def test_list_quotas_command(self):
        """Test list-quotas CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"total": 0, "quotas": []}
            mock_instance.list_model_management_quotas.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "list-quotas",
                "--custom-model-provider-id", "test-provider-id",
                "--limit", "10",
                "--offset", "0",
            ])

            assert result.exit_code == 0
            mock_instance.list_model_management_quotas.assert_called_once()
            call_args = mock_instance.list_model_management_quotas.call_args
            assert call_args[1]["custom_model_provider_id"] == "test-provider-id"
            assert call_args[1]["limit"] == 10
            assert call_args[1]["offset"] == 0

    # ------------------------------------------------------------------ #
    # Client helper
    # ------------------------------------------------------------------ #
    def test_get_model_provider_client(self):
        """Test _get_model_provider_client returns the SDK client"""
        import agentarts.sdk.custom_model_provider as sdk_module

        with patch.object(sdk_module, "CustomModelProviderClient") as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance

            result = model_provider_module._get_model_provider_client(verify_ssl=True)

            assert result == mock_instance
            mock_client_class.assert_called_once_with(verify_ssl=True)

    def test_get_model_provider_client_skip_ssl(self):
        """Test _get_model_provider_client with SSL verification skipped"""
        import agentarts.sdk.custom_model_provider as sdk_module

        with patch.object(sdk_module, "CustomModelProviderClient") as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance

            result = model_provider_module._get_model_provider_client(verify_ssl=False)

            assert result == mock_instance
            mock_client_class.assert_called_once_with(verify_ssl=False)

    # ------------------------------------------------------------------ #
    # Error paths: model provider commands
    # ------------------------------------------------------------------ #
    def test_create_provider_command_error_response(self):
        """Test create-provider CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "400", "error_msg": "Bad request"}
            mock_result.error = None
            mock_instance.create_model_provider.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "create-provider", "test-provider", "https://example.com/v1",
                "--credential-configuration", '{"provider_configuration": {}}',
            ])

            assert result.exit_code == 0
            assert "Error creating model provider (Code: 400)" in result.output

    def test_create_provider_command_unexpected_error(self):
        """Test create-provider CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.create_model_provider.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "create-provider", "test-provider", "https://example.com/v1",
                "--credential-configuration", '{"provider_configuration": {}}',
            ])

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output

    def test_update_provider_command_invalid_json(self):
        """Test update-provider CLI command with invalid JSON"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(model_provider_module.custom_model_provider, [
            "update-provider", "test-provider-id",
            "--tags", '{"invalid json',
        ])

        assert result.exit_code == 0
        assert "Invalid JSON format" in result.output

    def test_update_provider_command_error_response(self):
        """Test update-provider CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "400", "error_msg": "Bad request"}
            mock_result.error = None
            mock_instance.update_model_provider.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "update-provider", "test-provider-id", "--description", "Updated",
            ])

            assert result.exit_code == 0
            assert "Error updating model provider (Code: 400)" in result.output

    def test_update_provider_command_unexpected_error(self):
        """Test update-provider CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.update_model_provider.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "update-provider", "test-provider-id", "--description", "Updated",
            ])

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output

    def test_delete_provider_command_error_response(self):
        """Test delete-provider CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "400", "error_msg": "Bad request"}
            mock_result.error = None
            mock_instance.delete_model_provider.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "delete-provider", "test-provider-id",
            ], input="y")

            assert result.exit_code == 0
            assert "Error deleting model provider (Code: 400)" in result.output

    def test_delete_provider_command_unexpected_error(self):
        """Test delete-provider CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.delete_model_provider.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "delete-provider", "test-provider-id",
            ], input="y")

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output

    def test_get_provider_command_error_response(self):
        """Test get-provider CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "404", "error_msg": "Not found"}
            mock_result.error = None
            mock_instance.get_model_provider.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "get-provider", "test-provider-id",
            ])

            assert result.exit_code == 0
            assert "Error getting model provider (Code: 404)" in result.output

    def test_get_provider_command_unexpected_error(self):
        """Test get-provider CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.get_model_provider.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "get-provider", "test-provider-id",
            ])

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output

    def test_list_providers_command_error_response(self):
        """Test list-providers CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "500", "error_msg": "Server error"}
            mock_result.error = None
            mock_instance.list_model_providers.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "list-providers",
            ])

            assert result.exit_code == 0
            assert "Error listing model providers (Code: 500)" in result.output

    def test_list_providers_command_unexpected_error(self):
        """Test list-providers CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.list_model_providers.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "list-providers",
            ])

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output

    # ------------------------------------------------------------------ #
    # Error paths: model service commands
    # ------------------------------------------------------------------ #
    def test_create_model_command_error_response(self):
        """Test create-model CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "400", "error_msg": "Bad request"}
            mock_result.error = None
            mock_instance.create_model.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "create-model", "test-provider-id",
                "--model", "qwen2.5-72b",
            ])

            assert result.exit_code == 0
            assert "Error creating model (Code: 400)" in result.output

    def test_create_model_command_value_error(self):
        """Test create-model CLI command with ValueError"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.create_model.side_effect = ValueError("bad parameter")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "create-model", "test-provider-id",
                "--model", "qwen2.5-72b",
            ])

            assert result.exit_code == 0
            assert "bad parameter" in result.output

    def test_create_model_command_unexpected_error(self):
        """Test create-model CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.create_model.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "create-model", "test-provider-id",
                "--model", "qwen2.5-72b",
            ])

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output

    def test_update_model_command(self):
        """Test update-model CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"id": "test-model-id"}
            mock_instance.update_model.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "update-model", "test-provider-id", "test-model-id",
                "--description", "Updated description",
                "--type", "completions,embeddings",
            ])

            assert result.exit_code == 0
            mock_instance.update_model.assert_called_once()
            call_args = mock_instance.update_model.call_args
            assert call_args[1]["model_provider_id"] == "test-provider-id"
            assert call_args[1]["model_id"] == "test-model-id"
            assert call_args[1]["description"] == "Updated description"
            assert call_args[1]["type_"] == ["completions", "embeddings"]

    def test_update_model_command_error_response(self):
        """Test update-model CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "400", "error_msg": "Bad request"}
            mock_result.error = None
            mock_instance.update_model.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "update-model", "test-provider-id", "test-model-id",
                "--description", "Updated description",
            ])

            assert result.exit_code == 0
            assert "Error updating model (Code: 400)" in result.output

    def test_update_model_command_value_error(self):
        """Test update-model CLI command with ValueError"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.update_model.side_effect = ValueError("bad parameter")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "update-model", "test-provider-id", "test-model-id",
                "--description", "Updated description",
            ])

            assert result.exit_code == 0
            assert "bad parameter" in result.output

    def test_update_model_command_unexpected_error(self):
        """Test update-model CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.update_model.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "update-model", "test-provider-id", "test-model-id",
                "--description", "Updated description",
            ])

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output

    def test_delete_model_command_cancelled(self):
        """Test delete-model CLI command when cancelled"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(model_provider_module.custom_model_provider, [
            "delete-model", "test-provider-id", "test-model-id",
        ], input="n")

        assert result.exit_code == 0
        assert "Deletion cancelled" in result.output

    def test_delete_model_command_confirmed(self):
        """Test delete-model CLI command when confirmed"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_instance.delete_model.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "delete-model", "test-provider-id", "test-model-id",
            ], input="y")

            assert result.exit_code == 0
            mock_instance.delete_model.assert_called_once()

    def test_delete_model_command_error_response(self):
        """Test delete-model CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "400", "error_msg": "Bad request"}
            mock_result.error = None
            mock_instance.delete_model.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "delete-model", "test-provider-id", "test-model-id",
            ], input="y")

            assert result.exit_code == 0
            assert "Error deleting model (Code: 400)" in result.output

    def test_delete_model_command_unexpected_error(self):
        """Test delete-model CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.delete_model.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "delete-model", "test-provider-id", "test-model-id",
            ], input="y")

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output

    def test_get_model_command(self):
        """Test get-model CLI command"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = True
            mock_result.data = {"id": "test-model-id"}
            mock_instance.get_model.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "get-model", "test-provider-id", "test-model-id", "--skip-ssl-verification",
            ])

            assert result.exit_code == 0
            mock_instance.get_model.assert_called_once()
            mock_client.assert_called_once_with(verify_ssl=False)

    def test_get_model_command_error_response(self):
        """Test get-model CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "404", "error_msg": "Not found"}
            mock_result.error = None
            mock_instance.get_model.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "get-model", "test-provider-id", "test-model-id",
            ])

            assert result.exit_code == 0
            assert "Error getting model (Code: 404)" in result.output

    def test_get_model_command_unexpected_error(self):
        """Test get-model CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.get_model.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "get-model", "test-provider-id", "test-model-id",
            ])

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output

    def test_list_models_command_error_response(self):
        """Test list-models CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "500", "error_msg": "Server error"}
            mock_result.error = None
            mock_instance.list_models.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "list-models", "test-provider-id",
            ])

            assert result.exit_code == 0
            assert "Error listing models (Code: 500)" in result.output

    def test_list_models_command_invalid_offset(self):
        """Test list-models CLI command with invalid offset"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(model_provider_module.custom_model_provider, [
            "list-models", "test-provider-id", "--offset", "-1",
        ])

        assert result.exit_code == 0
        assert "Offset must be greater than or equal to 0" in result.output

    def test_list_models_command_unexpected_error(self):
        """Test list-models CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.list_models.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "list-models", "test-provider-id",
            ])

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output

    # ------------------------------------------------------------------ #
    # Error paths: model proxy commands
    # ------------------------------------------------------------------ #
    def test_create_proxy_command_invalid_json(self):
        """Test create-proxy CLI command with invalid JSON"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(model_provider_module.custom_model_provider, [
            "create-proxy",
            "--custom-model-provider-id", "test-provider-id",
            "--inbound-authorizer-configuration", '{"invalid json',
        ])

        assert result.exit_code == 0
        assert "Invalid JSON format" in result.output

    def test_create_proxy_command_error_response(self):
        """Test create-proxy CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "400", "error_msg": "Bad request"}
            mock_result.error = None
            mock_instance.create_model_proxy.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "create-proxy",
                "--custom-model-provider-id", "test-provider-id",
            ])

            assert result.exit_code == 0
            assert "Error creating model proxy (Code: 400)" in result.output

    def test_create_proxy_command_unexpected_error(self):
        """Test create-proxy CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.create_model_proxy.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "create-proxy",
                "--custom-model-provider-id", "test-provider-id",
            ])

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output

    def test_update_proxy_command_invalid_json(self):
        """Test update-proxy CLI command with invalid JSON"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(model_provider_module.custom_model_provider, [
            "update-proxy", "test-gateway-id",
            "--tags", '{"invalid json',
        ])

        assert result.exit_code == 0
        assert "Invalid JSON format" in result.output

    def test_update_proxy_command_no_tags(self):
        """Test update-proxy CLI command without tags (SDK ValueError)"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.update_model_proxy.side_effect = ValueError(
                "At least one parameter must be provided for update. Available fields: tags"
            )

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "update-proxy", "test-gateway-id",
            ])

            assert result.exit_code == 0
            assert "At least one parameter must be provided" in result.output

    def test_update_proxy_command_error_response(self):
        """Test update-proxy CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "400", "error_msg": "Bad request"}
            mock_result.error = None
            mock_instance.update_model_proxy.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "update-proxy", "test-gateway-id",
                "--tags", '[{"key": "Environment", "value": "test"}]',
            ])

            assert result.exit_code == 0
            assert "Error updating model proxy (Code: 400)" in result.output

    def test_update_proxy_command_unexpected_error(self):
        """Test update-proxy CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.update_model_proxy.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "update-proxy", "test-gateway-id",
                "--tags", '[{"key": "Environment", "value": "test"}]',
            ])

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output

    def test_disassociate_proxies_command_invalid_json(self):
        """Test disassociate-proxies CLI command with invalid JSON"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(model_provider_module.custom_model_provider, [
            "disassociate-proxies",
            "--unbindings", '{"invalid json',
        ])

        assert result.exit_code == 0
        assert "Invalid JSON format" in result.output

    def test_disassociate_proxies_command_error_response(self):
        """Test disassociate-proxies CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "400", "error_msg": "Bad request"}
            mock_result.error = None
            mock_instance.batch_disassociate_model_proxies.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "disassociate-proxies",
                "--unbindings", '[{"custom_model_provider_id": "1", "gateway_id": "2"}]',
            ])

            assert result.exit_code == 0
            assert "Error disassociating model proxies (Code: 400)" in result.output

    def test_disassociate_proxies_command_unexpected_error(self):
        """Test disassociate-proxies CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.batch_disassociate_model_proxies.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "disassociate-proxies",
                "--unbindings", '[{"custom_model_provider_id": "1", "gateway_id": "2"}]',
            ])

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output

    # ------------------------------------------------------------------ #
    # Error paths: quota commands
    # ------------------------------------------------------------------ #
    def test_list_quotas_command_invalid_limit(self):
        """Test list-quotas CLI command with invalid limit"""
        from typer.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(model_provider_module.custom_model_provider, [
            "list-quotas", "--limit", "0",
        ])

        assert result.exit_code == 0
        assert "Limit must be greater than 0" in result.output

    def test_list_quotas_command_error_response(self):
        """Test list-quotas CLI command with error response"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_result = Mock()
            mock_result.success = False
            mock_result.data = {"error_code": "500", "error_msg": "Server error"}
            mock_result.error = None
            mock_instance.list_model_management_quotas.return_value = mock_result

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "list-quotas",
            ])

            assert result.exit_code == 0
            assert "Error listing quotas (Code: 500)" in result.output

    def test_list_quotas_command_unexpected_error(self):
        """Test list-quotas CLI command with unexpected error"""
        from typer.testing import CliRunner

        runner = CliRunner()

        with patch.object(model_provider_module, "_get_model_provider_client") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            mock_instance.list_model_management_quotas.side_effect = Exception("boom")

            result = runner.invoke(model_provider_module.custom_model_provider, [
                "list-quotas",
            ])

            assert result.exit_code == 0
            assert "Unexpected error: boom" in result.output
