"""
Unit tests for IAM client
"""

from unittest.mock import Mock, patch

import pytest


class TestIAMClient:
    """Test IAM client"""

    def test_create_agency(self):
        """Test create_agency method"""
        from agentarts.sdk.service.iam_client import IAMClient

        trust_policy = '{"Version": "5.0", "Statement": [{"Action": ["sts:agencies:assume"], "Effect": "Allow", "Principal": {"Service": ["service.WorkloadSandboxMetadata"]}}]}'

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

    def test_list_policies(self):
        """Test list_policies method"""
        from agentarts.sdk.service.iam_client import IAMClient

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_response = Mock()
            mock_response.policies = []
            mock_instance = Mock()
            mock_instance.list_policies_v5.return_value = mock_response
            mock_get_client.return_value = mock_instance

            client = IAMClient()
            result = client.list_policies(policy_type="system")

            assert result is not None
            mock_instance.list_policies_v5.assert_called_once()

    def test_list_agencies(self):
        """Test list_agencies method"""
        from agentarts.sdk.service.iam_client import IAMClient

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_response = Mock()
            mock_response.agencies = []
            mock_instance = Mock()
            mock_instance.list_agencies_v5.return_value = mock_response
            mock_get_client.return_value = mock_instance

            client = IAMClient()
            result = client.list_agencies(name="TestAgency")

            assert result is not None
            mock_instance.list_agencies_v5.assert_called_once()

    def test_attach_agency_policy(self):
        """Test attach_agency_policy method"""
        from agentarts.sdk.service.iam_client import IAMClient

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_response = Mock()
            mock_instance = Mock()
            mock_instance.attach_agency_policy_v5.return_value = mock_response
            mock_get_client.return_value = mock_instance

            client = IAMClient()
            result = client.attach_agency_policy(
                agency_id="test-agency-id",
                policy_id="test-policy-id"
            )

            assert result is not None
            mock_instance.attach_agency_policy_v5.assert_called_once()

    def test_create_agency_with_policy(self):
        """Test create_agency_with_policy method"""
        from agentarts.sdk.service.iam_client import IAMClient

        trust_policy = '{"Version": "5.0", "Statement": [{"Action": ["sts:agencies:assume"], "Effect": "Allow", "Principal": {"Service": ["service.WorkloadSandboxMetadata"]}}]}'

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_create_response = Mock()
            mock_create_response.agency_id = "test-agency-id"

            mock_policy = Mock()
            mock_policy.policy_name = "AgentArtsCoreGatewayIdentityAgencyPolicy"
            mock_policy.policy_id = "test-policy-id"

            mock_page_info = Mock()
            mock_page_info.next_marker = None

            mock_list_response = Mock()
            mock_list_response.policies = [mock_policy]
            mock_list_response.page_info = mock_page_info

            mock_instance = Mock()
            mock_instance.create_agency_v5.return_value = mock_create_response
            mock_instance.list_policies_v5.return_value = mock_list_response
            mock_instance.attach_agency_policy_v5.return_value = Mock()
            mock_get_client.return_value = mock_instance

            client = IAMClient()
            result = client.create_agency_with_policy(
                agency_name="TestAgency",
                trust_policy=trust_policy,
                policy_name="AgentArtsCoreGatewayIdentityAgencyPolicy"
            )

            assert result is not None
            assert result.agency_id == "test-agency-id"
            mock_instance.create_agency_v5.assert_called_once()
            mock_instance.list_policies_v5.assert_called_once()
            mock_instance.attach_agency_policy_v5.assert_called_once()

    def test_create_agency_with_policy_pagination(self):
        """Test create_agency_with_policy method with pagination"""
        from agentarts.sdk.service.iam_client import IAMClient

        trust_policy = '{"Version": "5.0", "Statement": [{"Action": ["sts:agencies:assume"], "Effect": "Allow", "Principal": {"Service": ["service.WorkloadSandboxMetadata"]}}]}'

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_create_response = Mock()
            mock_create_response.agency_id = "test-agency-id"

            mock_policy = Mock()
            mock_policy.policy_name = "AgentArtsCoreGatewayIdentityAgencyPolicy"
            mock_policy.policy_id = "test-policy-id"

            mock_page_info_1 = Mock()
            mock_page_info_1.next_marker = "marker-1"

            mock_page_info_2 = Mock()
            mock_page_info_2.next_marker = None

            mock_list_response_1 = Mock()
            mock_list_response_1.policies = []
            mock_list_response_1.page_info = mock_page_info_1

            mock_list_response_2 = Mock()
            mock_list_response_2.policies = [mock_policy]
            mock_list_response_2.page_info = mock_page_info_2

            mock_instance = Mock()
            mock_instance.create_agency_v5.return_value = mock_create_response
            mock_instance.list_policies_v5.side_effect = [mock_list_response_1, mock_list_response_2]
            mock_instance.attach_agency_policy_v5.return_value = Mock()
            mock_get_client.return_value = mock_instance

            client = IAMClient()
            result = client.create_agency_with_policy(
                agency_name="TestAgency",
                trust_policy=trust_policy,
                policy_name="AgentArtsCoreGatewayIdentityAgencyPolicy"
            )

            assert result is not None
            assert result.agency_id == "test-agency-id"
            mock_instance.create_agency_v5.assert_called_once()
            assert mock_instance.list_policies_v5.call_count == 2
            mock_instance.attach_agency_policy_v5.assert_called_once()

    def test_create_agency_with_policy_already_exists(self):
        """Test create_agency_with_policy when agency already exists (409)"""
        from agentarts.sdk.service.iam_client import IAMClient

        trust_policy = '{"Version": "5.0", "Statement": [{"Action": ["sts:agencies:assume"], "Effect": "Allow", "Principal": {"Service": ["service.WorkloadSandboxMetadata"]}}]}'

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_409_error = Exception("409 Conflict: Agency already exists")

            mock_agency = Mock()
            mock_agency.agency_name = "TestAgency"
            mock_agency.agency_id = "existing-agency-id"

            mock_policy = Mock()
            mock_policy.policy_name = "AgentArtsCoreGatewayIdentityAgencyPolicy"
            mock_policy.policy_id = "test-policy-id"

            mock_page_info = Mock()
            mock_page_info.next_marker = None

            mock_list_agencies_response = Mock()
            mock_list_agencies_response.agencies = [mock_agency]

            mock_list_policies_response = Mock()
            mock_list_policies_response.policies = [mock_policy]
            mock_list_policies_response.page_info = mock_page_info

            mock_instance = Mock()
            mock_instance.create_agency_v5.side_effect = mock_409_error
            mock_instance.list_agencies_v5.return_value = mock_list_agencies_response
            mock_instance.list_policies_v5.return_value = mock_list_policies_response
            mock_instance.attach_agency_policy_v5.return_value = Mock()
            mock_get_client.return_value = mock_instance

            client = IAMClient()
            result = client.create_agency_with_policy(
                agency_name="TestAgency",
                trust_policy=trust_policy,
                policy_name="AgentArtsCoreGatewayIdentityAgencyPolicy"
            )

            # Should return None when agency already exists
            assert result is None
            mock_instance.create_agency_v5.assert_called_once()
            mock_instance.list_agencies_v5.assert_called_once()
            mock_instance.list_policies_v5.assert_called_once()
            mock_instance.attach_agency_policy_v5.assert_called_once()

    def test_create_agency_with_policy_already_attached(self):
        """Test create_agency_with_policy when policy already attached (409)"""
        from agentarts.sdk.service.iam_client import IAMClient

        trust_policy = '{"Version": "5.0", "Statement": [{"Action": ["sts:agencies:assume"], "Effect": "Allow", "Principal": {"Service": ["service.WorkloadSandboxMetadata"]}}]}'

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_create_response = Mock()
            mock_create_response.agency_id = "test-agency-id"

            mock_policy = Mock()
            mock_policy.policy_name = "AgentArtsCoreGatewayIdentityAgencyPolicy"
            mock_policy.policy_id = "test-policy-id"

            mock_page_info = Mock()
            mock_page_info.next_marker = None

            mock_list_response = Mock()
            mock_list_response.policies = [mock_policy]
            mock_list_response.page_info = mock_page_info

            mock_409_error = Exception("409 Conflict: Policy already attached")

            mock_instance = Mock()
            mock_instance.create_agency_v5.return_value = mock_create_response
            mock_instance.list_policies_v5.return_value = mock_list_response
            mock_instance.attach_agency_policy_v5.side_effect = mock_409_error
            mock_get_client.return_value = mock_instance

            client = IAMClient()
            result = client.create_agency_with_policy(
                agency_name="TestAgency",
                trust_policy=trust_policy,
                policy_name="AgentArtsCoreGatewayIdentityAgencyPolicy"
            )

            # Should return create_response even when policy already attached
            assert result is not None
            assert result.agency_id == "test-agency-id"
            mock_instance.create_agency_v5.assert_called_once()
            mock_instance.list_policies_v5.assert_called_once()
            mock_instance.attach_agency_policy_v5.assert_called_once()

    def test_create_agency_with_policy_not_found(self):
        """Test create_agency_with_policy method when policy not found"""
        from agentarts.sdk.service.iam_client import IAMClient

        trust_policy = '{"Version": "5.0", "Statement": [{"Action": ["sts:agencies:assume"], "Effect": "Allow", "Principal": {"Service": ["service.WorkloadSandboxMetadata"]}}]}'

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_create_response = Mock()
            mock_create_response.agency_id = "test-agency-id"

            mock_page_info = Mock()
            mock_page_info.next_marker = None

            mock_list_response = Mock()
            mock_list_response.policies = []
            mock_list_response.page_info = mock_page_info

            mock_instance = Mock()
            mock_instance.create_agency_v5.return_value = mock_create_response
            mock_instance.list_policies_v5.return_value = mock_list_response
            mock_get_client.return_value = mock_instance

            client = IAMClient()

            with pytest.raises(ValueError, match="not found"):
                client.create_agency_with_policy(
                    agency_name="TestAgency",
                    trust_policy=trust_policy,
                    policy_name="NonExistentPolicy"
                )

    def test_init_with_custom_ca_cert(self):
        """Test IAMClient initialization with custom CA certificate path"""
        from agentarts.sdk.service.iam_client import IAMClient

        custom_ca_path = "/path/to/custom/ca.crt"

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_instance = Mock()
            mock_get_client.return_value = mock_instance

            client = IAMClient(verify_ssl=custom_ca_path)
            assert client._verify_ssl == custom_ca_path

    def test_list_policies_with_all_params(self):
        """Test list_policies method with all optional parameters"""
        from agentarts.sdk.service.iam_client import IAMClient

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_response = Mock()
            mock_response.policies = []
            mock_instance = Mock()
            mock_instance.list_policies_v5.return_value = mock_response
            mock_get_client.return_value = mock_instance

            client = IAMClient()
            result = client.list_policies(
                policy_type="custom",
                limit=50,
                marker="test-marker",
                path_prefix="/test/",
                only_attached=True
            )

            assert result is not None
            mock_instance.list_policies_v5.assert_called_once()
            call_args = mock_instance.list_policies_v5.call_args
            request = call_args[0][0]
            assert request.policy_type == "custom"
            assert request.limit == 50
            assert request.marker == "test-marker"
            assert request.path_prefix == "/test/"
            assert request.only_attached is True

    def test_list_agencies_with_all_params(self):
        """Test list_agencies method with all optional parameters"""
        from agentarts.sdk.service.iam_client import IAMClient

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_response = Mock()
            mock_response.agencies = []
            mock_instance = Mock()
            mock_instance.list_agencies_v5.return_value = mock_response
            mock_get_client.return_value = mock_instance

            client = IAMClient()
            result = client.list_agencies(
                name="TestAgency",
                limit=50,
                marker="test-marker",
                path_prefix="/test/",
                only_attached=True
            )

            assert result is not None
            mock_instance.list_agencies_v5.assert_called_once()
            call_args = mock_instance.list_agencies_v5.call_args
            request = call_args[0][0]
            assert request.name == "TestAgency"
            assert request.limit == 50
            assert request.marker == "test-marker"
            assert request.path_prefix == "/test/"
            assert request.only_attached is True

    def test_create_agency_with_policy_non_409_error(self):
        """Test create_agency_with_policy when create_agency fails with non-409 error"""
        from agentarts.sdk.service.iam_client import IAMClient

        trust_policy = '{"Version": "5.0", "Statement": [{"Action": ["sts:agencies:assume"], "Effect": "Allow", "Principal": {"Service": ["service.WorkloadSandboxMetadata"]}}]}'

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_500_error = Exception("500 Internal Server Error")

            mock_instance = Mock()
            mock_instance.create_agency_v5.side_effect = mock_500_error
            mock_get_client.return_value = mock_instance

            client = IAMClient()

            with pytest.raises(Exception, match="500"):
                client.create_agency_with_policy(
                    agency_name="TestAgency",
                    trust_policy=trust_policy,
                    policy_name="TestPolicy"
                )

    def test_create_agency_with_policy_agency_not_in_list(self):
        """Test create_agency_with_policy when agency exists but not found in list"""
        from agentarts.sdk.service.iam_client import IAMClient

        trust_policy = '{"Version": "5.0", "Statement": [{"Action": ["sts:agencies:assume"], "Effect": "Allow", "Principal": {"Service": ["service.WorkloadSandboxMetadata"]}}]}'

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_409_error = Exception("409 Conflict: Agency already exists")

            mock_list_agencies_response = Mock()
            mock_list_agencies_response.agencies = []

            mock_instance = Mock()
            mock_instance.create_agency_v5.side_effect = mock_409_error
            mock_instance.list_agencies_v5.return_value = mock_list_agencies_response
            mock_get_client.return_value = mock_instance

            client = IAMClient()

            with pytest.raises(ValueError, match="already exists but cannot be found"):
                client.create_agency_with_policy(
                    agency_name="TestAgency",
                    trust_policy=trust_policy,
                    policy_name="TestPolicy"
                )

    def test_attach_agency_policy_non_409_error(self):
        """Test create_agency_with_policy when attach_agency_policy fails with non-409 error"""
        from agentarts.sdk.service.iam_client import IAMClient

        trust_policy = '{"Version": "5.0", "Statement": [{"Action": ["sts:agencies:assume"], "Effect": "Allow", "Principal": {"Service": ["service.WorkloadSandboxMetadata"]}}]}'

        with patch("agentarts.sdk.service.iam_client.IAMClient._get_iam_client") as mock_get_client:
            mock_create_response = Mock()
            mock_create_response.agency_id = "test-agency-id"

            mock_policy = Mock()
            mock_policy.policy_name = "TestPolicy"
            mock_policy.policy_id = "test-policy-id"

            mock_page_info = Mock()
            mock_page_info.next_marker = None

            mock_list_response = Mock()
            mock_list_response.policies = [mock_policy]
            mock_list_response.page_info = mock_page_info

            mock_500_error = Exception("500 Internal Server Error")

            mock_instance = Mock()
            mock_instance.create_agency_v5.return_value = mock_create_response
            mock_instance.list_policies_v5.return_value = mock_list_response
            mock_instance.attach_agency_policy_v5.side_effect = mock_500_error
            mock_get_client.return_value = mock_instance

            client = IAMClient()

            with pytest.raises(Exception, match="500"):
                client.create_agency_with_policy(
                    agency_name="TestAgency",
                    trust_policy=trust_policy,
                    policy_name="TestPolicy"
                )

    def test_get_iam_client_with_custom_ca(self):
        """Test _get_iam_client with custom CA certificate"""

        from agentarts.sdk.service.iam_client import IAMClient

        custom_ca_path = "/path/to/custom/ca.crt"

        with patch("agentarts.sdk.utils.constant.get_region") as mock_region:
            with patch("agentarts.sdk.utils.constant.get_iam_endpoint") as mock_endpoint:
                with patch("agentarts.sdk.utils.metadata.create_credential") as mock_cred:
                    mock_region.return_value = "cn-north-4"
                    mock_endpoint.return_value = "https://iam.cn-north-4.myhuaweicloud.com"
                    mock_cred.return_value = Mock()

                    with patch("huaweicloudsdkiam.v5.IamClient.new_builder") as mock_builder:
                        mock_builder_instance = Mock()
                        mock_builder.return_value = mock_builder_instance
                        mock_builder_instance.with_credentials.return_value = mock_builder_instance
                        mock_builder_instance.with_region.return_value = mock_builder_instance
                        mock_builder_instance.with_http_config.return_value = mock_builder_instance
                        mock_builder_instance.build.return_value = Mock()

                        client = IAMClient(verify_ssl=custom_ca_path)
                        iam_client = client._get_iam_client()

                        assert iam_client is not None
                        mock_builder_instance.with_http_config.assert_called_once()
                        http_config_arg = mock_builder_instance.with_http_config.call_args[0][0]
                        assert http_config_arg.ssl_ca_cert == custom_ca_path

    def test_get_iam_client_without_ssl_verification(self):
        """Test _get_iam_client with SSL verification disabled"""
        from agentarts.sdk.service.iam_client import IAMClient

        with patch("agentarts.sdk.utils.constant.get_region") as mock_region:
            with patch("agentarts.sdk.utils.constant.get_iam_endpoint") as mock_endpoint:
                with patch("agentarts.sdk.utils.metadata.create_credential") as mock_cred:
                    mock_region.return_value = "cn-north-4"
                    mock_endpoint.return_value = "https://iam.cn-north-4.myhuaweicloud.com"
                    mock_cred.return_value = Mock()

                    with patch("huaweicloudsdkiam.v5.IamClient.new_builder") as mock_builder:
                        mock_builder_instance = Mock()
                        mock_builder.return_value = mock_builder_instance
                        mock_builder_instance.with_credentials.return_value = mock_builder_instance
                        mock_builder_instance.with_region.return_value = mock_builder_instance
                        mock_builder_instance.with_http_config.return_value = mock_builder_instance
                        mock_builder_instance.build.return_value = Mock()

                        client = IAMClient(verify_ssl=False)
                        iam_client = client._get_iam_client()

                        assert iam_client is not None
                        mock_builder_instance.with_http_config.assert_called_once()
                        http_config_arg = mock_builder_instance.with_http_config.call_args[0][0]
                        assert http_config_arg.ignore_ssl_verification is True
