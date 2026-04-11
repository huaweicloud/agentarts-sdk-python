import pytest
from agentarts.sdk.identity.auth import require_sts_token


@pytest.mark.asyncio
async def test_require_sts_token_injects_into_async_function(
    mock_identity_client, mock_context_token
):
    """Test that the decorator correctly injects an STS token into an async function."""
    # GIVEN: A mock identity service and a valid workload token in context
    mock_credentials = {
        "access_key": "ak",
        "secret_key": "sk",
        "security_token": "token",
    }
    mock_identity_client.get_resource_sts_token.return_value = mock_credentials
    mock_context_token.return_value = "workload-token"

    @require_sts_token(
        provider_name="test-provider", agency_session_name="test-session"
    )
    async def decorated_func(sts_credentials=None):
        return sts_credentials

    # WHEN: The decorated async function is called
    result = await decorated_func()

    # THEN: The injected credentials should match the mock
    assert result == mock_credentials
    mock_identity_client.get_resource_sts_token.assert_called_once()


def test_require_sts_token_injects_into_sync_function(
    mock_identity_client, mock_context_token
):
    """Test that the decorator correctly injects an STS token into a sync function."""
    mock_credentials = {"access_key": "sync-ak", "secret_key": "sync-sk"}
    mock_identity_client.get_resource_sts_token.return_value = mock_credentials
    mock_context_token.return_value = "workload-token"

    @require_sts_token(
        provider_name="test-provider", agency_session_name="test-session"
    )
    def decorated_func(sts_credentials=None):
        return sts_credentials

    result = decorated_func()

    assert result == mock_credentials


def test_require_sts_token_custom_parameter_name(
    mock_identity_client, mock_context_token
):
    """Test that the 'into' parameter correctly changes the injected argument name."""
    mock_credentials = {"token": "custom"}
    mock_identity_client.get_resource_sts_token.return_value = mock_credentials
    mock_context_token.return_value = "workload-token"

    @require_sts_token(
        provider_name="test", agency_session_name="test-session", into="my_sts"
    )
    def decorated_func(my_sts=None):
        return my_sts

    result = decorated_func()

    assert result == mock_credentials


def test_require_sts_token_calls_identity_client_correctly(
    mock_identity_client, mock_context_token
):
    """Test that the decorator passes correct arguments to the identity client."""
    mock_identity_client.get_resource_sts_token.return_value = {}
    mock_context_token.return_value = "workload-token"

    @require_sts_token(
        provider_name="specific-provider",
        agency_session_name="test-session",
        duration_seconds=3600,
    )
    def decorated_func(sts_credentials=None):
        pass

    decorated_func()

    mock_identity_client.get_resource_sts_token.assert_called_once_with(
        provider_name="specific-provider",
        workload_access_token="workload-token",
        agency_session_name="test-session",
        duration_seconds=3600,
        policy=None,
        source_identity=None,
        tags=None,
        transitive_tag_keys=None,
    )


def test_require_sts_token_passes_all_parameters(
    mock_identity_client, mock_context_token
):
    """Test that the decorator passes all new optional parameters correctly."""
    from huaweicloudsdkagentidentity.v1 import StsTag

    mock_identity_client.get_resource_sts_token.return_value = {}
    mock_context_token.return_value = "workload-token"
    tags = [StsTag(key="test-key", value="test-value")]

    @require_sts_token(
        provider_name="p",
        agency_session_name="test-session",
        policy="pol",
        source_identity="src",
        tags=tags,
        transitive_tag_keys=["tk1"],
    )
    def decorated_func(sts_credentials=None):
        pass

    decorated_func()

    mock_identity_client.get_resource_sts_token.assert_called_once_with(
        provider_name="p",
        workload_access_token="workload-token",
        agency_session_name="test-session",
        duration_seconds=None,
        policy="pol",
        source_identity="src",
        tags=tags,
        transitive_tag_keys=["tk1"],
    )
