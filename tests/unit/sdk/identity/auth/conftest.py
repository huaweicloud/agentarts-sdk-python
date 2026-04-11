import pytest
from unittest.mock import patch, AsyncMock
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
