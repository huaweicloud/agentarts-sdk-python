"""
Unit tests for IAM client
"""

import pytest
from unittest.mock import Mock, patch
from agentarts.sdk.service.iam_client import IAMClient
from agentarts.sdk.service.http_client import RequestConfig, RequestResult


class TestIAMClient:
    """Test IAM client"""
    
    def setup_method(self):
        """Setup test method"""
        self.client = IAMClient()
    
    def test_create_agency(self):
        """Test create_agency method"""
        # Test that create_agency works correctly when huaweicloudsdkiam is installed
        trust_policy = '{"Version": "5.0", "Statement": [{"Action": ["agentIdentity::getWorkloadAccessToken"], "Effect": "Allow", "Principal": {}}]}'
        
        # Mock the IamClient to avoid actual API calls
        with patch('huaweicloudsdkiam.v5.IamClient') as mock_iam_client:
            # Set up mock response
            mock_response = Mock()
            
            # Set up mock client
            mock_instance = Mock()
            mock_instance.create_agency_v5.return_value = mock_response
            mock_iam_client.new_builder.return_value.with_credentials.return_value.with_endpoint.return_value.build.return_value = mock_instance
            
            # Call create_agency
            result = self.client.create_agency(
                agency_name="AgentArtsCoreGateway",
                trust_policy=trust_policy
            )
            
            # Verify the result
            assert result is not None
