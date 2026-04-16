import pytest

from agentarts.sdk.identity.auth import require_api_key


@pytest.mark.asyncio
async def test_require_api_key_injects_into_async_function(
    mock_identity_client, mock_context_token
):
    """Test that the decorator correctly injects an API key into an async function."""
    # GIVEN: A mock identity service and a valid workload token in context
    mock_identity_client.get_resource_api_key.return_value = "mock-api-key-123"
    mock_context_token.return_value = "workload-token"

    @require_api_key(provider_name="test-provider")
    async def decorated_func(api_key=None):
        return api_key

    # WHEN: The decorated async function is called
    result = await decorated_func()

    # THEN: The injected key should match the mock
    assert result == "mock-api-key-123"
    mock_identity_client.get_resource_api_key.assert_called_once()


def test_require_api_key_injects_into_sync_function(
    mock_identity_client, mock_context_token
):
    """Test that the decorator correctly injects an API key into a sync function."""
    mock_identity_client.get_resource_api_key.return_value = "sync-api-key"
    mock_context_token.return_value = "workload-token"

    @require_api_key(provider_name="test-provider")
    def decorated_func(api_key=None):
        return api_key

    result = decorated_func()

    assert result == "sync-api-key"


def test_require_api_key_custom_parameter_name(
    mock_identity_client, mock_context_token
):
    """Test that the 'into' parameter correctly changes the injected argument name."""
    mock_identity_client.get_resource_api_key.return_value = "custom-key"
    mock_context_token.return_value = "workload-token"

    @require_api_key(provider_name="test", into="my_key")
    def decorated_func(my_key=None):
        return my_key

    result = decorated_func()

    assert result == "custom-key"


def test_require_api_key_calls_identity_client_correctly(
    mock_identity_client, mock_context_token
):
    """Test that the decorator passes correct arguments to the identity client."""
    mock_identity_client.get_resource_api_key.return_value = "key"
    mock_context_token.return_value = "workload-token"

    @require_api_key(provider_name="specific-provider")
    def decorated_func(api_key=None):
        pass

    decorated_func()

    mock_identity_client.get_resource_api_key.assert_called_once_with(
        provider_name="specific-provider", workload_access_token="workload-token"
    )
