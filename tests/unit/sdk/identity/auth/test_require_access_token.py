from typing import TYPE_CHECKING

import pytest

from agentarts.sdk.identity.auth import require_access_token

if TYPE_CHECKING:
    from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_require_access_token_injects_token_into_async_function(
    mock_identity_client, mock_context_token
):
    """Test that the decorator correctly injects a token into an async function."""
    # GIVEN: A mock identity service and a valid workload token in context
    mock_identity_client.get_resource_oauth2_token.return_value = "mock-token-123"
    mock_context_token.return_value = "workload-token"

    @require_access_token(
        provider_name="test-provider", scopes=["read"], auth_flow="M2M"
    )
    async def decorated_func(access_token=None):
        return access_token

    # WHEN: The decorated async function is called
    result = await decorated_func()

    # THEN: The injected token should match the mock, and the client should be called correctly
    assert result == "mock-token-123"
    mock_identity_client.get_resource_oauth2_token.assert_called_once()

    # Verify arguments passed to IdentityClient
    args = mock_identity_client.get_resource_oauth2_token.call_args.kwargs
    assert args["provider_name"] == "test-provider"
    assert args["scopes"] == ["read"]


def test_require_access_token_injects_token_into_sync_function(
    mock_identity_client, mock_context_token
):
    """Test that the decorator correctly injects a token into a sync function."""
    # GIVEN: A mock identity service and a valid workload token in context
    mock_identity_client.get_resource_oauth2_token.return_value = "sync-mock-token"
    mock_context_token.return_value = "workload-token"

    @require_access_token(
        provider_name="test-provider", scopes=["read"], auth_flow="M2M"
    )
    def decorated_func(access_token=None):
        return access_token

    # WHEN: The decorated sync function is called
    result = decorated_func()

    # THEN: The injected token should match the mock
    assert result == "sync-mock-token"


@pytest.mark.asyncio
async def test_require_access_token_injects_into_custom_parameter_name(
    mock_identity_client, mock_context_token
):
    """Test that the 'into' parameter correctly changes the injected argument name."""
    # GIVEN: A custom parameter name 'my_special_token' for injection
    mock_identity_client.get_resource_oauth2_token.return_value = "custom-token"
    mock_context_token.return_value = "workload-token"

    @require_access_token(
        provider_name="test", scopes=["read"], auth_flow="M2M", into="my_special_token"
    )
    async def decorated_func(my_special_token=None):
        return my_special_token

    # WHEN: The decorated function is called
    result = await decorated_func()

    # THEN: The token should be injected into the specified parameter name
    assert result == "custom-token"


@pytest.mark.asyncio
async def test_require_access_token_falls_back_to_local_auth_when_context_is_empty(
    mock_identity_client, mock_context_token, mock_config
):
    """Test the fallback to local auth when no workload token is in context."""
    # GIVEN: No workload token in context and no existing local config
    from unittest.mock import MagicMock

    mock_workload = MagicMock()
    mock_workload.name = "new-workload"
    mock_identity_client.create_workload_identity.return_value = mock_workload
    mock_identity_client.create_workload_access_token.return_value = (
        "local-workload-token"
    )
    mock_identity_client.get_resource_oauth2_token.return_value = "final-resource-token"

    mock_context_token.return_value = None

    mock_cfg_instance = mock_config.load.return_value
    mock_cfg_instance.workload_identity_name = None
    mock_cfg_instance.user_id = None

    @require_access_token(provider_name="test", scopes=["read"], auth_flow="M2M")
    async def decorated_func(access_token=None):
        return access_token

    # WHEN: The decorated function is called
    result = await decorated_func()

    # THEN: It should fallback to local identity creation and save the config
    assert result == "final-resource-token"
    mock_identity_client.create_workload_identity.assert_called_once()
    mock_cfg_instance.save.assert_called()


@pytest.mark.asyncio
async def test_require_access_token_uses_user_id_from_context_in_local_fallback(
    mock_identity_client, mock_context_token, mock_config
):
    """Test that local fallback uses user id from context if available."""
    # GIVEN: No workload token, but a user id in context
    from agentarts.sdk.runtime.context import AgentArtsRuntimeContext

    mock_context_token.return_value = None
    AgentArtsRuntimeContext.set_user_id("context-user-id")

    mock_cfg_instance = mock_config.load.return_value
    mock_cfg_instance.workload_identity_name = "test-workload"

    mock_identity_client.create_workload_access_token.return_value = (
        "local-workload-token"
    )
    mock_identity_client.get_resource_oauth2_token.return_value = "final-token"

    @require_access_token(provider_name="test", scopes=["read"], auth_flow="M2M")
    async def decorated_func(access_token=None):
        return access_token

    try:
        # WHEN: Calling the decorated function
        result = await decorated_func()

        # THEN: It should use the user id from context
        assert result == "final-token"
        mock_identity_client.create_workload_access_token.assert_called_once_with(
            "test-workload", user_id="context-user-id"
        )
    finally:
        AgentArtsRuntimeContext.set_user_id(None)


def test_require_access_token_passes_ignore_ssl_verification(
    mock_identity_client, mock_context_token, monkeypatch
):
    """Test that ignore_ssl_verification is passed to IdentityClient."""
    from agentarts.sdk.identity.auth import IdentityClient

    # Explicitly set the region env variable so the test is deterministic
    monkeypatch.setenv("HUAWEICLOUD_SDK_REGION", "ap-southeast-4")

    mock_context_token.return_value = "workload-token"

    @require_access_token(
        provider_name="test",
        scopes=["read"],
        auth_flow="M2M",
        ignore_ssl_verification=True,
    )
    def decorated_func(access_token=None):
        return access_token

    # The IdentityClient is initialized when the decorator is applied
    # So we check the mock call args on the class (which is IdentityClient in auth.py)
    # We need to get the mock class from the fixture
    # In conftest.py, it's: with patch.object(auth, "IdentityClient") as MockClass:
    # So IdentityClient in auth.py is now that MockClass.

    # We need to find where the MockClass is. Since we imported it from auth, it is the MockClass.
    from typing import cast

    mock_client_class = cast("MagicMock", IdentityClient)
    mock_client_class.assert_called_with(
        region="ap-southeast-4", ignore_ssl_verification=True
    )
