from unittest.mock import MagicMock, patch

import pytest

from agentarts.sdk.identity.types import OAuth2Vendor
from agentarts.sdk.service.identity.identity_client import IdentityClient

# We expect these to be available in huaweicloudsdkagentidentity.v1
from huaweicloudsdkagentidentity.v1 import (
    AgentIdentityClient,
    ApiKeyCredentialProvider,
    CreateApiKeyCredentialProviderResponse,
    CreateOauth2CredentialProviderResponse,
    Oauth2CredentialProvider,
    Tag,
)


@pytest.fixture
def mock_sdk_client() -> MagicMock:
    return MagicMock(spec=AgentIdentityClient)


@pytest.fixture
def identity_client(mock_sdk_client: MagicMock) -> IdentityClient:
    with patch.dict(
        "os.environ",
        {
            "HUAWEICLOUD_SDK_AK": "test-ak",
            "HUAWEICLOUD_SDK_SK": "test-sk",
            "HUAWEICLOUD_SDK_PROJECT_ID": "test-project",
            "HUAWEICLOUD_SDK_REGION": "ap-southeast-4",
            "HUAWEICLOUD_SDK_DOMAIN_ID": "test-domain",
        },
    ):
        return IdentityClient(region="ap-southeast-4", client=mock_sdk_client)


def test_create_api_key_credential_provider_success(
    identity_client: IdentityClient, mock_sdk_client: MagicMock
) -> None:
    # GIVEN
    mock_provider = MagicMock(spec=ApiKeyCredentialProvider)
    mock_response = MagicMock(spec=CreateApiKeyCredentialProviderResponse)
    mock_response.credential_provider = mock_provider
    mock_sdk_client.create_api_key_credential_provider.return_value = mock_response

    name = "test-provider"
    api_key = "test-api-key"

    # WHEN
    result = identity_client.create_api_key_credential_provider(
        name=name, api_key=api_key
    )

    # THEN
    assert result == mock_provider
    mock_sdk_client.create_api_key_credential_provider.assert_called_once()
    request = mock_sdk_client.create_api_key_credential_provider.call_args.kwargs[
        "request"
    ]
    assert request.body.name == name
    assert request.body.api_key == api_key


def test_create_oauth2_credential_provider_google_success(
    identity_client: IdentityClient, mock_sdk_client: MagicMock
) -> None:
    # GIVEN
    mock_provider = MagicMock(spec=Oauth2CredentialProvider)
    mock_response = MagicMock(spec=CreateOauth2CredentialProviderResponse)
    mock_response.credential_provider = mock_provider
    mock_sdk_client.create_oauth2_credential_provider.return_value = mock_response

    name = "google-provider"
    vendor = OAuth2Vendor.GOOGLEOAUTH2
    client_id = "test-client-id"
    client_secret = "test-client-secret"

    # WHEN
    result = identity_client.create_oauth2_credential_provider(
        name=name,
        vendor=vendor,
        client_id=client_id,
        client_secret=client_secret,
    )

    # THEN
    assert result == mock_provider
    mock_sdk_client.create_oauth2_credential_provider.assert_called_once()
    request = mock_sdk_client.create_oauth2_credential_provider.call_args.kwargs[
        "request"
    ]
    assert request.body.name == name
    assert request.body.credential_provider_vendor == vendor
    assert (
        request.body.oauth2_provider_config_input.google_oauth2_provider_config.client_id
        == client_id
    )
    assert (
        request.body.oauth2_provider_config_input.google_oauth2_provider_config.client_secret
        == client_secret
    )


def test_create_oauth2_credential_provider_with_tags(
    identity_client: IdentityClient, mock_sdk_client: MagicMock
) -> None:
    # GIVEN
    mock_provider = MagicMock(spec=Oauth2CredentialProvider)
    mock_response = MagicMock(spec=CreateOauth2CredentialProviderResponse)
    mock_response.credential_provider = mock_provider
    mock_sdk_client.create_oauth2_credential_provider.return_value = mock_response

    name = "google-provider-with-tags"
    vendor = OAuth2Vendor.GOOGLEOAUTH2
    client_id = "test-client-id"
    client_secret = "test-client-secret"
    tags = [Tag(key="env", value="production"), Tag(key="team", value="platform")]

    # WHEN
    result = identity_client.create_oauth2_credential_provider(
        name=name,
        vendor=vendor,
        client_id=client_id,
        client_secret=client_secret,
        tags=tags,
    )

    # THEN
    assert result == mock_provider
    mock_sdk_client.create_oauth2_credential_provider.assert_called_once()
    request = mock_sdk_client.create_oauth2_credential_provider.call_args.kwargs[
        "request"
    ]
    assert request.body.name == name
    assert request.body.credential_provider_vendor == vendor
    assert request.body.tags == tags


def test_create_oauth2_credential_provider_microsoft_success(
    identity_client: IdentityClient, mock_sdk_client: MagicMock
) -> None:
    # GIVEN
    mock_provider = MagicMock(spec=Oauth2CredentialProvider)
    mock_response = MagicMock(spec=CreateOauth2CredentialProviderResponse)
    mock_response.credential_provider = mock_provider
    mock_sdk_client.create_oauth2_credential_provider.return_value = mock_response

    name = "ms-provider"
    vendor = OAuth2Vendor.MICROSOFTOAUTH2
    client_id = "test-client-id"
    client_secret = "test-client-secret"
    tenant_id = "test-tenant-id"

    # WHEN
    result = identity_client.create_oauth2_credential_provider(
        name=name,
        vendor=vendor,
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
    )

    # THEN
    assert result == mock_provider
    mock_sdk_client.create_oauth2_credential_provider.assert_called_once()
    request = mock_sdk_client.create_oauth2_credential_provider.call_args.kwargs[
        "request"
    ]
    assert request.body.name == name
    assert request.body.credential_provider_vendor == vendor
    assert (
        request.body.oauth2_provider_config_input.microsoft_oauth2_provider_config.tenant_id
        == tenant_id
    )
    assert (
        request.body.oauth2_provider_config_input.microsoft_oauth2_provider_config.client_id
        == client_id
    )
    assert (
        request.body.oauth2_provider_config_input.microsoft_oauth2_provider_config.client_secret
        == client_secret
    )


def test_create_oauth2_credential_provider_custom_success(
    identity_client: IdentityClient, mock_sdk_client: MagicMock
) -> None:
    # GIVEN
    from huaweicloudsdkagentidentity.v1 import Oauth2Discovery

    mock_provider = MagicMock(spec=Oauth2CredentialProvider)
    mock_response = MagicMock(spec=CreateOauth2CredentialProviderResponse)
    mock_response.credential_provider = mock_provider
    mock_sdk_client.create_oauth2_credential_provider.return_value = mock_response

    name = "custom-provider"
    vendor = OAuth2Vendor.CUSTOMOAUTH2
    client_id = "test-client-id"
    client_secret = "test-client-secret"
    discovery = Oauth2Discovery(
        discovery_url="https://example.com/.well-known/openid-configuration"
    )

    # WHEN
    result = identity_client.create_oauth2_credential_provider(
        name=name,
        vendor=vendor,
        client_id=client_id,
        client_secret=client_secret,
        oauth_discovery=discovery,
    )

    # THEN
    assert result == mock_provider
    mock_sdk_client.create_oauth2_credential_provider.assert_called_once()
    request = mock_sdk_client.create_oauth2_credential_provider.call_args.kwargs[
        "request"
    ]
    assert request.body.name == name
    assert request.body.credential_provider_vendor == vendor
    assert (
        request.body.oauth2_provider_config_input.custom_oauth2_provider_config.oauth2_discovery
        == discovery
    )
    assert (
        request.body.oauth2_provider_config_input.custom_oauth2_provider_config.client_id
        == client_id
    )
