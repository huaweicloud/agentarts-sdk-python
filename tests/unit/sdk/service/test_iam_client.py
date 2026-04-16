"""
Unit tests for IAM client
"""

from unittest.mock import Mock, patch


class TestIAMClient:
    """Test IAM client"""

    def test_create_agency(self):
        """Test create_agency method"""
        from agentarts.sdk.service.iam_client import IAMClient

        trust_policy = '{"Version": "5.0", "Statement": [{"Action": ["agentIdentity::getWorkloadAccessToken"], "Effect": "Allow", "Principal": {}}]}'

        with patch("agentarts.sdk.utils.metadata.create_credential") as mock_cred:
            mock_cred.return_value = Mock()

            with patch("huaweicloudsdkiam.v5.IamClient") as mock_iam_client:
                mock_response = Mock()
                mock_instance = Mock()
                mock_instance.create_agency_v5.return_value = mock_response
                mock_iam_client.new_builder.return_value.with_credentials.return_value.with_endpoint.return_value.build.return_value = mock_instance

                client = IAMClient()
                result = client.create_agency(
                    agency_name="AgentArtsCoreGateway",
                    trust_policy=trust_policy
                )

                assert result is not None
