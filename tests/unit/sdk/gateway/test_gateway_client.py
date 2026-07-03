"""
Unit tests for Gateway client
"""

from unittest.mock import Mock, patch

import pytest


class TestGatewayClient:
    """Test Gateway client"""

    def test_create_gateway(self):
        """Test create_gateway method"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch("agentarts.sdk.gateway.gateway_client.IAMClient") as mock_iam_client:
                mock_iam_instance = Mock()
                mock_iam_client.return_value = mock_iam_instance
                mock_iam_instance.create_agency_with_policy.return_value = Mock()

                with patch.object(GatewayClient, "post") as mock_post:
                    mock_post.return_value = Mock(status_code=200)

                    client = GatewayClient()
                    result = client.create_gateway(
                        name="test-gateway",
                        description="Test gateway",
                        agency_name="TestAgency"
                    )

                    assert result is not None
                    mock_post.assert_called_once()

    def test_create_gateway_with_default_agency(self):
        """Test create_gateway with default agency creation"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch("agentarts.sdk.gateway.gateway_client.IAMClient") as mock_iam_client:
                mock_iam_instance = Mock()
                mock_iam_client.return_value = mock_iam_instance
                mock_iam_instance.create_agency_with_policy.return_value = Mock()

                with patch.object(GatewayClient, "post") as mock_post:
                    mock_post.return_value = Mock(status_code=200)

                    client = GatewayClient()
                    result = client.create_gateway(
                        name="test-gateway",
                        description="Test gateway"
                    )

                    assert result is not None
                    mock_iam_instance.create_agency_with_policy.assert_called_once()
                    mock_post.assert_called_once()

    def test_create_gateway_with_agency_409_error(self):
        """Test create_gateway when agency already exists (409)"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch("agentarts.sdk.gateway.gateway_client.IAMClient") as mock_iam_client:
                mock_iam_instance = Mock()
                mock_iam_client.return_value = mock_iam_instance

                mock_409_error = Exception("409 Conflict: Agency already exists")
                mock_iam_instance.create_agency_with_policy.side_effect = mock_409_error

                with patch.object(GatewayClient, "post") as mock_post:
                    mock_post.return_value = Mock(status_code=200)

                    client = GatewayClient()
                    result = client.create_gateway(
                        name="test-gateway",
                        description="Test gateway"
                    )

                    assert result is not None
                    mock_post.assert_called_once()

    def test_create_gateway_with_agency_non_409_error(self):
        """Test create_gateway when agency creation fails with non-409 error"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch("agentarts.sdk.gateway.gateway_client.IAMClient") as mock_iam_client:
                mock_iam_instance = Mock()
                mock_iam_client.return_value = mock_iam_instance

                mock_500_error = Exception("500 Internal Server Error")
                mock_iam_instance.create_agency_with_policy.side_effect = mock_500_error

                client = GatewayClient()

                with pytest.raises(ValueError, match="Failed to create agency"):
                    client.create_gateway(
                        name="test-gateway",
                        description="Test gateway"
                    )

    def test_update_gateway(self):
        """Test update_gateway method"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch.object(GatewayClient, "put") as mock_put:
                mock_put.return_value = Mock(status_code=200)

                client = GatewayClient()
                result = client.update_gateway(
                    gateway_id="test-gateway-id",
                    description="Updated description"
                )

                assert result is not None
                mock_put.assert_called_once()

    def test_update_gateway_no_params(self):
        """Test update_gateway with no parameters"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            client = GatewayClient()

            with pytest.raises(ValueError, match="At least one parameter"):
                client.update_gateway(gateway_id="test-gateway-id")

    def test_delete_gateway(self):
        """Test delete_gateway method"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch.object(GatewayClient, "delete") as mock_delete:
                mock_delete.return_value = Mock(status_code=200)

                client = GatewayClient()
                result = client.delete_gateway(gateway_id="test-gateway-id")

                assert result is not None
                mock_delete.assert_called_once()

    def test_get_gateway(self):
        """Test get_gateway method"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch.object(GatewayClient, "get") as mock_get:
                mock_get.return_value = Mock(status_code=200)

                client = GatewayClient()
                result = client.get_gateway(gateway_id="test-gateway-id")

                assert result is not None
                mock_get.assert_called_once()

    def test_list_gateways(self):
        """Test list_gateways method"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch.object(GatewayClient, "get") as mock_get:
                mock_get.return_value = Mock(status_code=200)

                client = GatewayClient()
                result = client.list_gateways(name="test-gateway")

                assert result is not None
                mock_get.assert_called_once()

    def test_create_gateway_target(self):
        """Test create_gateway_target method"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch.object(GatewayClient, "post") as mock_post:
                mock_post.return_value = Mock(status_code=200)

                client = GatewayClient()
                result = client.create_gateway_target(
                    gateway_id="test-gateway-id",
                    name="test-target",
                    description="Test target"
                )

                assert result is not None
                mock_post.assert_called_once()

    def test_update_gateway_target(self):
        """Test update_gateway_target method"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch.object(GatewayClient, "put") as mock_put:
                mock_put.return_value = Mock(status_code=200)

                client = GatewayClient()
                result = client.update_gateway_target(
                    gateway_id="test-gateway-id",
                    target_id="test-target-id",
                    name="updated-target"
                )

                assert result is not None
                mock_put.assert_called_once()

    def test_update_gateway_target_no_params(self):
        """Test update_gateway_target with no parameters"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            client = GatewayClient()

            with pytest.raises(ValueError, match="At least one parameter"):
                client.update_gateway_target(
                    gateway_id="test-gateway-id",
                    target_id="test-target-id"
                )

    def test_delete_gateway_target(self):
        """Test delete_gateway_target method"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch.object(GatewayClient, "delete") as mock_delete:
                mock_delete.return_value = Mock(status_code=200)

                client = GatewayClient()
                result = client.delete_gateway_target(
                    gateway_id="test-gateway-id",
                    target_id="test-target-id"
                )

                assert result is not None
                mock_delete.assert_called_once()

    def test_get_gateway_target(self):
        """Test get_gateway_target method"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch.object(GatewayClient, "get") as mock_get:
                mock_get.return_value = Mock(status_code=200)

                client = GatewayClient()
                result = client.get_gateway_target(
                    gateway_id="test-gateway-id",
                    target_id="test-target-id"
                )

                assert result is not None
                mock_get.assert_called_once()

    def test_list_gateway_targets(self):
        """Test list_gateway_targets method"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch.object(GatewayClient, "get") as mock_get:
                mock_get.return_value = Mock(status_code=200)

                client = GatewayClient()
                result = client.list_gateway_targets(gateway_id="test-gateway-id")

                assert result is not None
                mock_get.assert_called_once()

    def test_create_gateway_with_default_name(self):
        """Test create_gateway with default name generation"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            with patch("agentarts.sdk.gateway.gateway_client.generate_random_string") as mock_random:
                mock_endpoint.return_value = "https://test.endpoint.com"
                mock_random.return_value = "abcdefgh"

                with patch("agentarts.sdk.gateway.gateway_client.IAMClient") as mock_iam_client:
                    mock_iam_instance = Mock()
                    mock_iam_client.return_value = mock_iam_instance
                    mock_iam_instance.create_agency_with_policy.return_value = Mock()

                    with patch.object(GatewayClient, "post") as mock_post:
                        mock_post.return_value = Mock(status_code=200)

                        client = GatewayClient()
                        result = client.create_gateway(
                            description="Test gateway"
                        )

                        assert result is not None
                        call_args = mock_post.call_args
                        json_payload = call_args[1]["json"]
                        assert json_payload["name"] == "gateway-abcdefgh"

    def test_create_gateway_with_default_configurations(self):
        """Test create_gateway with default configurations"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            mock_endpoint.return_value = "https://test.endpoint.com"

            with patch("agentarts.sdk.gateway.gateway_client.IAMClient") as mock_iam_client:
                mock_iam_instance = Mock()
                mock_iam_client.return_value = mock_iam_instance
                mock_iam_instance.create_agency_with_policy.return_value = Mock()

                with patch.object(GatewayClient, "post") as mock_post:
                    mock_post.return_value = Mock(status_code=200)

                    client = GatewayClient()
                    result = client.create_gateway(
                        name="test-gateway",
                        agency_name="TestAgency"
                    )

                    assert result is not None
                    call_args = mock_post.call_args
                    json_payload = call_args[1]["json"]
                    assert json_payload["log_delivery_configuration"] == {"enabled": False}
                    assert json_payload["outbound_network_configuration"] == {"network_mode": "public"}

    def test_create_gateway_target_with_default_name(self):
        """Test create_gateway_target with default name generation"""
        from agentarts.sdk.gateway.gateway_client import GatewayClient

        with patch("agentarts.sdk.gateway.gateway_client.get_control_plane_endpoint") as mock_endpoint:
            with patch("agentarts.sdk.gateway.gateway_client.generate_random_string") as mock_random:
                mock_endpoint.return_value = "https://test.endpoint.com"
                mock_random.return_value = "abcdefgh"

                with patch.object(GatewayClient, "post") as mock_post:
                    mock_post.return_value = Mock(status_code=200)

                    client = GatewayClient()
                    result = client.create_gateway_target(
                        gateway_id="test-gateway-id",
                        description="Test target"
                    )

                    assert result is not None
                    call_args = mock_post.call_args
                    json_payload = call_args[1]["json"]
                    assert json_payload["name"] == "target-abcdefgh"
                    assert json_payload["credential_provider_configuration"] == {"credential_provider_type": "none"}
