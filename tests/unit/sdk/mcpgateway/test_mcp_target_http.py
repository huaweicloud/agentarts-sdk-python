"""
Unit tests for MCP Gateway Target HTTP client
"""

import pytest
from unittest.mock import Mock, patch
from agentarts.sdk.mcpgateway.mcp_gateway_client import MCPGatewayClient
from agentarts.sdk.service.http_client import RequestConfig, RequestResult


class TestMCPGatewayClient:
    """Test MCP Gateway client"""
    
    def setup_method(self):
        """Setup test method"""
        self.client = MCPGatewayClient(RequestConfig(base_url="http://test.example.com"))
    
    @patch('agentarts.sdk.mcpgateway.mcp_gateway_client.MCPGatewayClient.post')
    def test_create_mcp_gateway_target(self, mock_post):
        """Test create_mcp_gateway_target method"""
        # Mock response
        mock_post.return_value = RequestResult(
            success=True,
            status_code=201,
            data={"id": "456", "name": "TestGatewayTarget-1234"}
        )
        
        # Test with parameters
        result = self.client.create_mcp_gateway_target(
            gateway_id="123",
            name="TestTarget",
            description="Test target"
        )
        
        assert result.success
        assert result.data["id"] == "456"
        mock_post.assert_called_once()
    
    @patch('agentarts.sdk.mcpgateway.mcp_gateway_client.MCPGatewayClient.put')
    def test_update_mcp_gateway_target(self, mock_put):
        """Test update_mcp_gateway_target method"""
        # Mock response
        mock_put.return_value = RequestResult(
            success=True,
            status_code=200,
            data={"id": "456", "name": "UpdatedTarget"}
        )
        
        # Test with valid parameters
        result = self.client.update_mcp_gateway_target(
            gateway_id="123",
            target_id="456",
            name="UpdatedTarget"
        )
        
        assert result.success
        mock_put.assert_called_once()
    
    @pytest.mark.parametrize("name, description, target_config, credential_config", [
        (None, None, None, None),
    ])
    def test_update_mcp_gateway_target_no_params(self, name, description, target_config, credential_config):
        """Test update_mcp_gateway_target with no parameters"""
        with pytest.raises(ValueError):
            self.client.update_mcp_gateway_target(
                gateway_id="123",
                target_id="456",
                name=name,
                description=description,
                target_configuration=target_config,
                credential_configuration=credential_config
            )
    
    @patch('agentarts.sdk.mcpgateway.mcp_gateway_client.MCPGatewayClient.delete')
    def test_delete_mcp_gateway_target(self, mock_delete):
        """Test delete_mcp_gateway_target method"""
        # Mock response
        mock_delete.return_value = RequestResult(
            success=True,
            status_code=204
        )
        
        result = self.client.delete_mcp_gateway_target(gateway_id="123", target_id="456")
        
        assert result.success
        mock_delete.assert_called_once_with("/gateways/123/target/456")
    
    @patch('agentarts.sdk.mcpgateway.mcp_gateway_client.MCPGatewayClient.get')
    def test_get_mcp_gateway_target(self, mock_get):
        """Test get_mcp_gateway_target method"""
        # Mock response
        mock_get.return_value = RequestResult(
            success=True,
            status_code=200,
            data={"id": "456", "name": "TestTarget"}
        )
        
        result = self.client.get_mcp_gateway_target(gateway_id="123", target_id="456")
        
        assert result.success
        assert result.data["id"] == "456"
        mock_get.assert_called_once_with("/gateways/123/target/456")
    
    @patch('agentarts.sdk.mcpgateway.mcp_gateway_client.MCPGatewayClient.get')
    def test_list_mcp_gateway_targets(self, mock_get):
        """Test list_mcp_gateway_targets method"""
        # Mock response
        mock_get.return_value = RequestResult(
            success=True,
            status_code=200,
            data={"targets": [{"id": "456", "name": "TestTarget"}], "total": 1}
        )
        
        result = self.client.list_mcp_gateway_targets(
            gateway_id="123",
            limit=10,
            offset=0
        )
        
        assert result.success
        assert len(result.data["targets"]) == 1
        mock_get.assert_called_once()
