from unittest.mock import MagicMock, patch

import pytest
from huaweicloudsdkagentidentity.v1 import (
    AgentIdentityClient,
    CompleteResourceTokenAuthResponse,
    CreateStsCredentialProviderResponse,
    GetResourceStsTokenResponse,
    StsCredentialProvider,
    StsTag,
    Tag,
    UserIdentifier,
)
from huaweicloudsdkcore.exceptions.exceptions import (
    ConnectionException,
    ServiceResponseException,
)

from agentarts.sdk.service.identity.identity_client import IdentityClient


@pytest.fixture
def mock_sdk_client():
    return MagicMock(spec=AgentIdentityClient)


@pytest.fixture
def identity_client(mock_sdk_client):
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


def test_complete_resource_token_auth(identity_client, mock_sdk_client):
    # GIVEN
    mock_response = MagicMock(spec=CompleteResourceTokenAuthResponse)
    mock_sdk_client.complete_resource_token_auth.return_value = mock_response

    user_identifier = UserIdentifier(user_id="user-123", user_token="token-456")
    session_uri = "https://example.com/session"

    # WHEN
    result = identity_client.complete_resource_token_auth(
        session_uri=session_uri, user_identifier=user_identifier
    )

    # THEN
    assert result == mock_response
    mock_sdk_client.complete_resource_token_auth.assert_called_once()
    args = mock_sdk_client.complete_resource_token_auth.call_args.kwargs["request"]
    assert args.body.session_uri == session_uri
    assert args.body.user_identifier == user_identifier


def test_should_retry_logic(identity_client):
    """Test the _should_retry method with various scenarios."""
    # Scenario 1: No exception, no response
    assert identity_client._should_retry(None, None) is False

    # Scenario 2: ServiceResponseException with 429
    mock_error = MagicMock()
    mock_error.error_msg = "Throttled"
    mock_error.error_code = "Throttling"
    mock_error.request_id = "req-1"
    mock_error.encoded_auth_msg = None
    exc_429 = ServiceResponseException(429, mock_error)
    assert identity_client._should_retry(None, exc_429) is True

    # Scenario 3: ServiceResponseException with 500
    exc_500 = ServiceResponseException(500, mock_error)
    assert identity_client._should_retry(None, exc_500) is True

    # Scenario 4: ServiceResponseException with 400 (Should not retry)
    exc_400 = ServiceResponseException(400, mock_error)
    assert identity_client._should_retry(None, exc_400) is False

    # Scenario 5: ConnectionException (Should retry)
    exc_conn = ConnectionException("Connection error")
    assert identity_client._should_retry(None, exc_conn) is True

    # Scenario 6: Response with status_code 429
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    assert identity_client._should_retry(mock_resp_429, None) is True

    # Scenario 7: Response with status_code 200 (Should not retry)
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    assert identity_client._should_retry(mock_resp_200, None) is False


def test_get_resource_sts_token_with_all_params(identity_client, mock_sdk_client):
    # GIVEN
    mock_response = MagicMock(spec=GetResourceStsTokenResponse)
    mock_response.credentials = MagicMock()

    mock_invoker = MagicMock()
    mock_sdk_client.get_resource_sts_token_invoker.return_value = mock_invoker
    mock_invoker.with_retry.return_value = mock_invoker
    mock_invoker.invoke.return_value = mock_response

    provider_name = "test-provider"
    workload_access_token = "test-token"
    agency_session_name = "test-session"
    duration_seconds = 3600
    policy = '{"Version": "1.1", "Statement": []}'
    source_identity = "test-source-identity"
    tags = [StsTag(key="key1", value="value1")]
    transitive_tag_keys = ["key1"]

    # WHEN
    result = identity_client.get_resource_sts_token(
        provider_name=provider_name,
        workload_access_token=workload_access_token,
        agency_session_name=agency_session_name,
        duration_seconds=duration_seconds,
        policy=policy,
        source_identity=source_identity,
        tags=tags,
        transitive_tag_keys=transitive_tag_keys,
    )

    # THEN
    assert result == mock_response.credentials
    mock_sdk_client.get_resource_sts_token_invoker.assert_called_once()
    request = mock_sdk_client.get_resource_sts_token_invoker.call_args.kwargs["request"]
    body = request.body
    assert body.resource_credential_provider_name == provider_name
    assert body.workload_access_token == workload_access_token
    assert body.agency_session_name == agency_session_name
    assert body.duration_seconds == duration_seconds
    assert body.policy == policy
    assert body.source_identity == source_identity
    assert body.tags == tags
    assert body.transitive_tag_keys == transitive_tag_keys


def test_identity_client_ssl_verification_param(mock_sdk_client):
    """Test that the ignore_ssl_verification parameter is correctly passed to the SDK."""
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
        from agentarts.sdk.service.identity import identity_client

        with patch.object(identity_client, "HttpConfig") as mock_http_config_class:
            mock_http_config = mock_http_config_class.get_default_config.return_value

            with patch.object(identity_client, "AgentIdentityClient"):
                # WHEN - passing True
                IdentityClient(region="ap-southeast-4", ignore_ssl_verification=True)
                assert mock_http_config.ignore_ssl_verification is True

                # WHEN - passing False
                IdentityClient(region="ap-southeast-4", ignore_ssl_verification=False)
                assert mock_http_config.ignore_ssl_verification is False


def test_create_sts_credential_provider(identity_client, mock_sdk_client):
    # GIVEN
    mock_response = MagicMock(spec=CreateStsCredentialProviderResponse)
    mock_credential_provider = MagicMock(spec=StsCredentialProvider)
    mock_response.credential_provider = mock_credential_provider
    mock_sdk_client.create_sts_credential_provider.return_value = mock_response

    name = "test-sts-provider"
    agency_urn = "iam::123456789:agency:test-agency"
    tags = [Tag(key="env", value="test")]

    # WHEN
    result = identity_client.create_sts_credential_provider(
        name=name,
        agency_urn=agency_urn,
        tags=tags,
    )

    # THEN
    assert result == mock_credential_provider
    mock_sdk_client.create_sts_credential_provider.assert_called_once()
    args = mock_sdk_client.create_sts_credential_provider.call_args.kwargs["request"]
    assert args.body.name == name
    assert args.body.agency_urn == agency_urn
    assert args.body.tags == tags


def test_create_sts_credential_provider_no_tags(identity_client, mock_sdk_client):
    # GIVEN
    mock_response = MagicMock(spec=CreateStsCredentialProviderResponse)
    mock_credential_provider = MagicMock(spec=StsCredentialProvider)
    mock_response.credential_provider = mock_credential_provider
    mock_sdk_client.create_sts_credential_provider.return_value = mock_response

    name = "test-sts-provider"
    agency_urn = "iam::123456789:agency:test-agency"

    # WHEN
    result = identity_client.create_sts_credential_provider(
        name=name,
        agency_urn=agency_urn,
    )

    # THEN
    assert result == mock_credential_provider
    mock_sdk_client.create_sts_credential_provider.assert_called_once()
    args = mock_sdk_client.create_sts_credential_provider.call_args.kwargs["request"]
    assert args.body.name == name
    assert args.body.agency_urn == agency_urn
    assert args.body.tags is None
