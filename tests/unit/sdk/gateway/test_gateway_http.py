"""
Unit tests for Gateway HTTP client
"""

from unittest.mock import patch

import pytest

from agentarts.sdk.gateway.gateway_client import GatewayClient
from agentarts.sdk.service.http_client import RequestResult


class TestGatewayClient:
    """Test Gateway HTTP client"""

    def setup_method(self):
        """Setup test method"""
        self.client = GatewayClient(verify_ssl=True)

    @patch("agentarts.sdk.gateway.gateway_client.GatewayClient.post")
    def test_create_gateway(self, mock_post):
        """Test create_gateway method"""
        # Mock response
        mock_post.return_value = RequestResult(
            success=True,
            status_code=201,
            data={"id": "123", "name": "TestGateway-1234"}
        )

        # Test with all parameters
        result = self.client.create_gateway(
            name="TestGateway",
            description="Test gateway",
            protocol_type="mcp",
            authorizer_type="iam",
            agency_name="TestAgency"
        )

        assert result.success
        assert result.data["id"] == "123"
        mock_post.assert_called_once()

    @patch("agentarts.sdk.gateway.gateway_client.GatewayClient.put")
    def test_update_gateway(self, mock_put):
        """Test update_gateway method"""
        # Mock response
        mock_put.return_value = RequestResult(
            success=True,
            status_code=200,
            data={"id": "123", "description": "Updated gateway"}
        )

        # Test with valid parameters
        result = self.client.update_gateway(
            gateway_id="123",
            description="Updated gateway"
        )

        assert result.success
        mock_put.assert_called_once()

    @pytest.mark.parametrize(("description", "log_config"), [
        (None, None),
    ])
    def test_update_gateway_no_params(self, description, log_config):
        """Test update_gateway with no parameters"""
        with pytest.raises(ValueError):
            self.client.update_gateway(
                gateway_id="123",
                description=description,
                log_delivery_configuration=log_config
            )

    @patch("agentarts.sdk.gateway.gateway_client.GatewayClient.delete")
    def test_delete_gateway(self, mock_delete):
        """Test delete_gateway method"""
        # Mock response
        mock_delete.return_value = RequestResult(
            success=True,
            status_code=204
        )

        result = self.client.delete_gateway(gateway_id="123")

        assert result.success
        mock_delete.assert_called_once_with("/gateways/123")

    @patch("agentarts.sdk.gateway.gateway_client.GatewayClient.get")
    def test_get_gateway(self, mock_get):
        """Test get_gateway method"""
        # Mock response
        mock_get.return_value = RequestResult(
            success=True,
            status_code=200,
            data={"id": "123", "name": "TestGateway"}
        )

        result = self.client.get_gateway(gateway_id="123")

        assert result.success
        assert result.data["id"] == "123"
        mock_get.assert_called_once_with("/gateways/123")

    @patch("agentarts.sdk.gateway.gateway_client.GatewayClient.get")
    def test_list_gateways(self, mock_get):
        """Test list_gateways method"""
        # Mock response
        mock_get.return_value = RequestResult(
            success=True,
            status_code=200,
            data={"gateways": [{"id": "123", "name": "TestGateway"}], "total": 1}
        )

        result = self.client.list_gateways(
            name="Test",
            limit=10,
            offset=0
        )

        assert result.success
        assert len(result.data["gateways"]) == 1
        mock_get.assert_called_once()
