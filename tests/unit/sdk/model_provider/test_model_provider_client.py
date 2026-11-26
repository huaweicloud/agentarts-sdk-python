"""
Unit tests for ModelProvider client
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from agentarts.sdk.custom_model_provider.custom_model_provider_client import CustomModelProviderClient

# Fake credentials so the AK/SK signing path resolves locally during unit
# tests. These are dummy values only — never real secrets.
_FAKE_ENV = {
    "HUAWEICLOUD_SDK_AK": "test-ak",
    "HUAWEICLOUD_SDK_SK": "test-sk",
    "HUAWEICLOUD_SDK_REGION": "cn-southwest-2",
    "AGENTARTS_CONTROL_ENDPOINT": "https://test.endpoint.com",
}

_BASE_URL = "https://test.endpoint.com/v1/core"

_CREDENTIAL_CONFIGURATION = {
    "provider_configuration": {
        "credential_provider_type": "api_key",
        "credential_provider": {
            "api_key_credential_provider": {
                "provider_name": "aa-it-key",
                "credential_location": "header",
            }
        },
    }
}


def _mock_response(status_code=200, json_data=None):
    """Build a mock requests response object."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.ok = 200 <= status_code < 300
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.content = b""
    if json_data is not None:
        mock_resp.json.return_value = json_data
    else:
        mock_resp.json.side_effect = ValueError("Not JSON")
    mock_resp.text = ""
    return mock_resp


class TestCustomModelProviderClient:
    """Test CustomModelProvider client"""

    @pytest.fixture(autouse=True)
    def _fake_credentials(self):
        with patch.dict(os.environ, _FAKE_ENV):
            yield

    # ------------------------------------------------------------------ #
    # Model provider management
    # ------------------------------------------------------------------ #
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_create_model_provider(self, mock_request):
        """Test create_model_provider method"""
        mock_request.return_value = _mock_response(201, {"id": "test-provider-id"})

        client = CustomModelProviderClient()
        result = client.create_model_provider(
            name="test-provider",
            base_url="https://example.com/v1",
            credential_configuration=_CREDENTIAL_CONFIGURATION,
        )

        assert result.success is True
        assert result.status_code == 201
        mock_request.assert_called_once()

        # HTTP method and URL
        assert mock_request.call_args[0][0] == "POST"
        assert mock_request.call_args[0][1] == f"{_BASE_URL}/custom-model-providers"

        # Body: None values removed, default network configuration injected
        payload = mock_request.call_args[1]["json"]
        assert payload["name"] == "test-provider"
        assert payload["base_url"] == "https://example.com/v1"
        assert payload["credential_configuration"] == _CREDENTIAL_CONFIGURATION
        assert payload["network_configuration"] == {"network_mode": "public"}
        assert "description" not in payload
        assert "tags" not in payload

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_create_model_provider_with_explicit_configuration(self, mock_request):
        """Test create_model_provider with explicit network configuration and tags"""
        mock_request.return_value = _mock_response(201, {"id": "test-provider-id"})
        network_configuration = {"network_mode": "vpc", "vpc_config": {"vpc_id": "vpc-1"}}
        tags = [{"key": "Environment", "value": "test"}]

        client = CustomModelProviderClient()
        result = client.create_model_provider(
            name="test-provider",
            base_url="https://example.com/v1",
            credential_configuration=_CREDENTIAL_CONFIGURATION,
            network_configuration=network_configuration,
            description="Test provider",
            tags=tags,
        )

        assert result.success is True
        payload = mock_request.call_args[1]["json"]
        assert payload["network_configuration"] == network_configuration
        assert payload["description"] == "Test provider"
        assert payload["tags"] == tags

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_update_model_provider(self, mock_request):
        """Test update_model_provider method"""
        mock_request.return_value = _mock_response(200, {"id": "test-provider-id"})

        client = CustomModelProviderClient()
        result = client.update_model_provider(
            model_provider_id="test-provider-id",
            description="Updated description",
        )

        assert result.success is True
        mock_request.assert_called_once()

        # HTTP method and URL
        assert mock_request.call_args[0][0] == "PUT"
        assert mock_request.call_args[0][1] == f"{_BASE_URL}/custom-model-providers/test-provider-id"

        # Body: None values removed
        payload = mock_request.call_args[1]["json"]
        assert payload == {"description": "Updated description"}

    def test_update_model_provider_no_params(self):
        """Test update_model_provider with no parameters"""
        client = CustomModelProviderClient()

        with pytest.raises(ValueError, match="At least one parameter"):
            client.update_model_provider(model_provider_id="test-provider-id")

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_delete_model_provider(self, mock_request):
        """Test delete_model_provider method"""
        mock_request.return_value = _mock_response(204)

        client = CustomModelProviderClient()
        result = client.delete_model_provider(model_provider_id="test-provider-id")

        assert result.success is True
        mock_request.assert_called_once()

        # HTTP method and URL
        assert mock_request.call_args[0][0] == "DELETE"
        assert mock_request.call_args[0][1] == f"{_BASE_URL}/custom-model-providers/test-provider-id"

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_get_model_provider(self, mock_request):
        """Test get_model_provider method"""
        mock_request.return_value = _mock_response(200, {"id": "test-provider-id"})

        client = CustomModelProviderClient()
        result = client.get_model_provider(model_provider_id="test-provider-id")

        assert result.success is True
        assert result.data == {"id": "test-provider-id"}
        mock_request.assert_called_once()

        # HTTP method and URL
        assert mock_request.call_args[0][0] == "GET"
        assert mock_request.call_args[0][1] == f"{_BASE_URL}/custom-model-providers/test-provider-id"

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_list_model_providers(self, mock_request):
        """Test list_model_providers method"""
        mock_request.return_value = _mock_response(200, {"model_providers": [], "total": 0})

        client = CustomModelProviderClient()
        result = client.list_model_providers(
            name="test-provider",
            model_provider_id="test-provider-id",
            tag_key_exists=["key1"],
            tag_key_matches=["key1"],
            tag_value_matches=["value1"],
            tag_match_policy="ALL",
            limit=10,
            offset=0,
        )

        assert result.success is True
        mock_request.assert_called_once()

        # HTTP method, URL and query parameters
        assert mock_request.call_args[0][0] == "GET"
        assert mock_request.call_args[0][1] == f"{_BASE_URL}/custom-model-providers"
        params = mock_request.call_args[1]["params"]
        assert params["name"] == "test-provider"
        assert params["id"] == "test-provider-id"
        assert params["tag_key_exists"] == ["key1"]
        assert params["tag_key_matches"] == ["key1"]
        assert params["tag_value_matches"] == ["value1"]
        assert params["tag_match_policy"] == "ALL"
        assert params["limit"] == 10
        assert params["offset"] == 0

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_list_model_providers_strips_none(self, mock_request):
        """Test list_model_providers removes None query values"""
        mock_request.return_value = _mock_response(200, {"model_providers": [], "total": 0})

        client = CustomModelProviderClient()
        result = client.list_model_providers()

        assert result.success is True
        # All query values were None → no params forwarded to the request
        assert "params" not in mock_request.call_args[1]

    # ------------------------------------------------------------------ #
    # Model service management
    # ------------------------------------------------------------------ #
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_create_model(self, mock_request):
        """Test create_model method"""
        mock_request.return_value = _mock_response(201, {"id": "test-model-id"})

        client = CustomModelProviderClient()
        result = client.create_model(
            model_provider_id="test-provider-id",
            model="qwen2.5-72b",
            model_service_name="my-model",
            type_=["completions"],
            protocol="openai",
            description="Test model",
        )

        assert result.success is True
        mock_request.assert_called_once()

        # HTTP method and URL
        assert mock_request.call_args[0][0] == "POST"
        assert mock_request.call_args[0][1] == f"{_BASE_URL}/custom-model-providers/test-provider-id/models"

        # Body: type_ mapped to "type", None values removed
        payload = mock_request.call_args[1]["json"]
        assert payload == {
            "model": "qwen2.5-72b",
            "model_service_name": "my-model",
            "type": ["completions"],
            "protocol": "openai",
            "description": "Test model",
        }

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_create_model_without_description(self, mock_request):
        """Test create_model without optional description"""
        mock_request.return_value = _mock_response(201, {"id": "test-model-id"})

        client = CustomModelProviderClient()
        client.create_model(
            model_provider_id="test-provider-id",
            model="qwen2.5-72b",
            model_service_name="my-model",
            type_=["completions"],
            protocol="openai",
        )

        payload = mock_request.call_args[1]["json"]
        assert "description" not in payload

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_update_model(self, mock_request):
        """Test update_model method"""
        mock_request.return_value = _mock_response(200, {"id": "test-model-id"})

        client = CustomModelProviderClient()
        result = client.update_model(
            model_provider_id="test-provider-id",
            model_id="test-model-id",
            description="Updated description",
        )

        assert result.success is True
        mock_request.assert_called_once()

        # HTTP method and URL
        assert mock_request.call_args[0][0] == "PUT"
        assert mock_request.call_args[0][1] == (
            f"{_BASE_URL}/custom-model-providers/test-provider-id/models/test-model-id"
        )

        # Body: None values removed
        payload = mock_request.call_args[1]["json"]
        assert payload == {"description": "Updated description"}

    def test_update_model_no_params(self):
        """Test update_model with no parameters"""
        client = CustomModelProviderClient()

        with pytest.raises(ValueError, match="At least one parameter"):
            client.update_model(
                model_provider_id="test-provider-id",
                model_id="test-model-id",
            )

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_delete_model(self, mock_request):
        """Test delete_model method"""
        mock_request.return_value = _mock_response(204)

        client = CustomModelProviderClient()
        result = client.delete_model(
            model_provider_id="test-provider-id",
            model_id="test-model-id",
        )

        assert result.success is True
        mock_request.assert_called_once()

        # HTTP method and URL
        assert mock_request.call_args[0][0] == "DELETE"
        assert mock_request.call_args[0][1] == (
            f"{_BASE_URL}/custom-model-providers/test-provider-id/models/test-model-id"
        )

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_get_model(self, mock_request):
        """Test get_model method"""
        mock_request.return_value = _mock_response(200, {"id": "test-model-id"})

        client = CustomModelProviderClient()
        result = client.get_model(
            model_provider_id="test-provider-id",
            model_id="test-model-id",
        )

        assert result.success is True
        assert result.data == {"id": "test-model-id"}
        mock_request.assert_called_once()

        # HTTP method and URL
        assert mock_request.call_args[0][0] == "GET"
        assert mock_request.call_args[0][1] == (
            f"{_BASE_URL}/custom-model-providers/test-provider-id/models/test-model-id"
        )

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_list_models(self, mock_request):
        """Test list_models method"""
        mock_request.return_value = _mock_response(200, {"models": [], "total": 0})

        client = CustomModelProviderClient()
        result = client.list_models(
            model_provider_id="test-provider-id",
            model_service_name="my-model",
            model_id="test-model-id",
            limit=10,
            offset=0,
        )

        assert result.success is True
        mock_request.assert_called_once()

        # HTTP method, URL and query parameters
        assert mock_request.call_args[0][0] == "GET"
        assert mock_request.call_args[0][1] == f"{_BASE_URL}/custom-model-providers/test-provider-id/models"
        params = mock_request.call_args[1]["params"]
        assert params["model_service_name"] == "my-model"
        assert params["id"] == "test-model-id"
        assert params["limit"] == 10
        assert params["offset"] == 0

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_list_models_strips_none(self, mock_request):
        """Test list_models removes None query values"""
        mock_request.return_value = _mock_response(200, {"models": [], "total": 0})

        client = CustomModelProviderClient()
        client.list_models(model_provider_id="test-provider-id")

        # All query values were None → no params forwarded to the request
        assert "params" not in mock_request.call_args[1]

    # ------------------------------------------------------------------ #
    # Model proxy management
    # ------------------------------------------------------------------ #
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_create_model_proxy(self, mock_request):
        """Test create_model_proxy method with explicit name and agency"""
        mock_request.return_value = _mock_response(201, {"gateway_id": "test-gateway-id"})

        client = CustomModelProviderClient()
        result = client.create_model_proxy(
            custom_model_provider_id="test-provider-id",
            name="test-proxy",
            agency_name="TestAgency",
        )

        assert result.success is True
        mock_request.assert_called_once()

        # HTTP method and URL
        assert mock_request.call_args[0][0] == "POST"
        assert mock_request.call_args[0][1] == f"{_BASE_URL}/model-proxy"

        # Body: None values removed
        payload = mock_request.call_args[1]["json"]
        assert payload == {
            "custom_model_provider_id": "test-provider-id",
            "name": "test-proxy",
            "inbound_authorizer_type": "iam",
            "agency_name": "TestAgency",
        }

    @patch("agentarts.sdk.custom_model_provider.custom_model_provider_client.IAMClient")
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_create_model_proxy_with_default_agency(self, mock_request, mock_iam_client):
        """Test create_model_proxy with default agency creation"""
        mock_request.return_value = _mock_response(201, {"gateway_id": "test-gateway-id"})
        mock_iam_instance = MagicMock()
        mock_iam_client.return_value = mock_iam_instance
        mock_iam_instance.create_agency_with_policy.return_value = MagicMock()

        with patch(
            "agentarts.sdk.custom_model_provider.custom_model_provider_client.generate_random_string"
        ) as mock_random:
            mock_random.return_value = "abcdefgh"

            client = CustomModelProviderClient()
            result = client.create_model_proxy(
                custom_model_provider_id="test-provider-id",
            )

        assert result.success is True
        mock_iam_instance.create_agency_with_policy.assert_called_once()
        mock_request.assert_called_once()

        # Default name and agency injected into the body
        payload = mock_request.call_args[1]["json"]
        assert payload["name"] == "model-proxy-abcdefgh"
        assert payload["agency_name"] == "AgentArtsCoreGateway"
        assert payload["custom_model_provider_id"] == "test-provider-id"
        assert payload["inbound_authorizer_type"] == "iam"

    @patch("agentarts.sdk.custom_model_provider.custom_model_provider_client.IAMClient")
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_create_model_proxy_with_agency_409_error(self, mock_request, mock_iam_client):
        """Test create_model_proxy when agency already exists (409)"""
        mock_request.return_value = _mock_response(201, {"gateway_id": "test-gateway-id"})
        mock_iam_instance = MagicMock()
        mock_iam_client.return_value = mock_iam_instance
        mock_iam_instance.create_agency_with_policy.side_effect = Exception(
            "409 Conflict: Agency already exists"
        )

        client = CustomModelProviderClient()
        result = client.create_model_proxy(custom_model_provider_id="test-provider-id")

        assert result.success is True
        mock_request.assert_called_once()

    @patch("agentarts.sdk.custom_model_provider.custom_model_provider_client.IAMClient")
    def test_create_model_proxy_with_agency_non_409_error(self, mock_iam_client):
        """Test create_model_proxy when agency creation fails with non-409 error"""
        mock_iam_instance = MagicMock()
        mock_iam_client.return_value = mock_iam_instance
        mock_iam_instance.create_agency_with_policy.side_effect = Exception(
            "500 Internal Server Error"
        )

        client = CustomModelProviderClient()

        with pytest.raises(ValueError, match="Failed to create agency"):
            client.create_model_proxy(custom_model_provider_id="test-provider-id")

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_update_model_proxy(self, mock_request):
        """Test update_model_proxy method"""
        mock_request.return_value = _mock_response(200, {"gateway_id": "test-gateway-id"})
        tags = [{"key": "Environment", "value": "test"}]

        client = CustomModelProviderClient()
        result = client.update_model_proxy(gateway_id="test-gateway-id", tags=tags)

        assert result.success is True
        mock_request.assert_called_once()

        # HTTP method and URL
        assert mock_request.call_args[0][0] == "PUT"
        assert mock_request.call_args[0][1] == f"{_BASE_URL}/model-proxy/test-gateway-id"

        # Body
        payload = mock_request.call_args[1]["json"]
        assert payload == {"tags": tags}

    def test_update_model_proxy_no_params(self):
        """Test update_model_proxy with no parameters"""
        client = CustomModelProviderClient()

        with pytest.raises(ValueError, match="At least one parameter"):
            client.update_model_proxy(gateway_id="test-gateway-id")

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_batch_disassociate_model_proxies(self, mock_request):
        """Test batch_disassociate_model_proxies method"""
        mock_request.return_value = _mock_response(201, {"success_details": []})
        unbindings = [
            {"custom_model_provider_id": "test-provider-id", "gateway_id": "test-gateway-id"}
        ]

        client = CustomModelProviderClient()
        result = client.batch_disassociate_model_proxies(unbindings=unbindings)

        assert result.success is True
        mock_request.assert_called_once()

        # HTTP method, URL and body
        assert mock_request.call_args[0][0] == "POST"
        assert mock_request.call_args[0][1] == f"{_BASE_URL}/model-proxy-batch-disassociate"
        payload = mock_request.call_args[1]["json"]
        assert payload == {"unbindings": unbindings}

    # ------------------------------------------------------------------ #
    # Model management quotas
    # ------------------------------------------------------------------ #
    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_list_model_management_quotas(self, mock_request):
        """Test list_model_management_quotas method"""
        mock_request.return_value = _mock_response(200, {"quotas": [], "total": 0})

        client = CustomModelProviderClient()
        result = client.list_model_management_quotas(
            custom_model_provider_id="test-provider-id",
            limit=10,
            offset=0,
        )

        assert result.success is True
        mock_request.assert_called_once()

        # HTTP method, URL and query parameters
        assert mock_request.call_args[0][0] == "GET"
        assert mock_request.call_args[0][1] == f"{_BASE_URL}/model-management-quotas"
        params = mock_request.call_args[1]["params"]
        assert params == {
            "custom_model_provider_id": "test-provider-id",
            "limit": 10,
            "offset": 0,
        }

    @patch("agentarts.sdk.service.http_client.requests.Session.request")
    def test_list_model_management_quotas_strips_none(self, mock_request):
        """Test list_model_management_quotas removes None query values"""
        mock_request.return_value = _mock_response(200, {"quotas": [], "total": 0})

        client = CustomModelProviderClient()
        client.list_model_management_quotas()

        # All query values were None → no params forwarded to the request
        assert "params" not in mock_request.call_args[1]
