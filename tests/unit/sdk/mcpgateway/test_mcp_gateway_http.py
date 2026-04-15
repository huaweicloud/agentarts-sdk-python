"""
Unit tests for MCP Gateway HTTP client
"""

import pytest
from unittest.mock import Mock, patch
from agentarts.sdk.mcpgateway.mcp_gateway_client import MCPGatewayClient
from agentarts.sdk.service.http_client import RequestConfig, RequestResult


class TestMCPGatewayClient:
    """Test MCP Gateway HTTP client"""
    
    def setup_method(self):
        """Setup test method"""
        self.client = MCPGatewayClient(RequestConfig(base_url="http://test.example.com"))
    
    @patch('agentarts.sdk.mcpgateway.mcp_gateway_client.MCPGatewayClient.post')
    def test_create_mcp_gateway(self, mock_post):
        """Test create_mcp_gateway method"""
        # Mock response
        mock_post.return_value = RequestResult(
            success=True,
            status_code=201,
            data={"id": "123", "name": "TestGateway-1234"}
        )
        
        # Test with all parameters
        result = self.client.create_mcp_gateway(
            name="TestGateway",
            description="Test gateway",
            protocol_type="mcp",
            authorizer_type="iam",
            agency_name="TestAgency"
        )
        
        assert result.success
        assert result.data["id"] == "123"
        mock_post.assert_called_once()
    
    @patch('agentarts.sdk.mcpgateway.mcp_gateway_client.MCPGatewayClient.put')
    def test_update_mcp_gateway(self, mock_put):
        """Test update_mcp_gateway method"""
        # Mock response
        mock_put.return_value = RequestResult(
            success=True,
            status_code=200,
            data={"id": "123", "description": "Updated gateway"}
        )
        
        # Test with valid parameters
        result = self.client.update_mcp_gateway(
            gateway_id="123",
            description="Updated gateway"
        )
        
        assert result.success
        mock_put.assert_called_once()
    
    @pytest.mark.parametrize("description, authorizer_config, log_config", [
        (None, None, None),
    ])
    def test_update_mcp_gateway_no_params(self, description, authorizer_config, log_config):
        """Test update_mcp_gateway with no parameters"""
        with pytest.raises(ValueError):
            self.client.update_mcp_gateway(
                gateway_id="123",
                description=description,
                authorizer_configuration=authorizer_config,
                log_delivery_configuration=log_config
            )
    
    @patch('agentarts.sdk.mcpgateway.mcp_gateway_client.MCPGatewayClient.delete')
    def test_delete_mcp_gateway(self, mock_delete):
        """Test delete_mcp_gateway method"""
        # Mock response
        mock_delete.return_value = RequestResult(
            success=True,
            status_code=204
        )
        
        result = self.client.delete_mcp_gateway(gateway_id="123")
        
        assert result.success
        mock_delete.assert_called_once_with("/gateways/123")
    
    @patch('agentarts.sdk.mcpgateway.mcp_gateway_client.MCPGatewayClient.get')
    def test_get_mcp_gateway(self, mock_get):
        """Test get_mcp_gateway method"""
        # Mock response
        mock_get.return_value = RequestResult(
            success=True,
            status_code=200,
            data={"id": "123", "name": "TestGateway"}
        )
        
        result = self.client.get_mcp_gateway(gateway_id="123")
        
        assert result.success
        assert result.data["id"] == "123"
        mock_get.assert_called_once_with("/gateways/123")
    
    @patch('agentarts.sdk.mcpgateway.mcp_gateway_client.MCPGatewayClient.get')
    def test_list_mcp_gateways(self, mock_get):
        """Test list_mcp_gateways method"""
        # Mock response
        mock_get.return_value = RequestResult(
            success=True,
            status_code=200,
            data={"gateways": [{"id": "123", "name": "TestGateway"}], "total": 1}
        )
        
        result = self.client.list_mcp_gateways(
            name="Test",
            limit=10,
            offset=0
        )
        
        assert result.success
        assert len(result.data["gateways"]) == 1
        mock_get.assert_called_once()
