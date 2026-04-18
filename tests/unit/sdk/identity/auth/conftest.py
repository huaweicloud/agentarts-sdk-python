from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentarts.sdk.identity import auth


@pytest.fixture
def mock_identity_client():
    """Fixture to mock IdentityClient and its instance."""
    with patch.object(auth, "IdentityClient") as MockClass:
        mock_instance = MockClass.return_value
        # Pre-configure common async methods
        mock_instance.get_resource_oauth2_token = AsyncMock()
        yield mock_instance


@pytest.fixture
def mock_identity_client_class():
    """Fixture to mock IdentityClient class for verifying constructor calls."""
    with patch.object(auth, "IdentityClient") as MockClass:
        mock_instance = MockClass.return_value
        mock_instance.get_resource_oauth2_token = AsyncMock()
        mock_instance.get_resource_api_key = MagicMock(return_value="mock-api-key")
        mock_instance.get_resource_sts_token = MagicMock(return_value={})
        mock_instance.create_workload_identity = MagicMock()
        mock_instance.create_workload_access_token = MagicMock(return_value="mock-workload-token")
        yield MockClass


@pytest.fixture
def mock_context_token():
    """Fixture to mock AgentIdentityContext.get_workload_access_token."""
    with patch.object(
        auth.AgentArtsRuntimeContext, "get_workload_access_token"
    ) as mock:
        yield mock


@pytest.fixture
def mock_config():
    """Fixture to mock Config class and its load method."""
    with patch.object(auth, "Config") as MockClass:
        yield MockClass
