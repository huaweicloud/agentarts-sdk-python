import pytest
from unittest.mock import MagicMock, patch

from huaweicloudsdkagentidentity.v1 import (
    AgentIdentityClient,
    UpdateWorkloadIdentityResponse,
    WorkloadIdentity,
)

from agentarts.sdk.service.identity.identity_client import IdentityClient


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


def test_update_workload_identity_success(
    identity_client: IdentityClient, mock_sdk_client: MagicMock
) -> None:
    # GIVEN
    mock_workload = MagicMock(spec=WorkloadIdentity)
    mock_response = MagicMock(spec=UpdateWorkloadIdentityResponse)
    mock_response.workload_identity = mock_workload
    mock_sdk_client.update_workload_identity.return_value = mock_response

    name = "test-workload"
    urls = ["https://example.com/callback"]

    # WHEN
    result = identity_client.update_workload_identity(
        name=name, allowed_resource_oauth2_return_urls=urls
    )

    # THEN
    assert result == mock_workload
    mock_sdk_client.update_workload_identity.assert_called_once()
    request = mock_sdk_client.update_workload_identity.call_args.kwargs["request"]
    assert request.workload_identity_name == name
    assert request.body.allowed_resource_oauth2_return_urls == urls


def test_update_workload_identity_no_urls(
    identity_client: IdentityClient, mock_sdk_client: MagicMock
) -> None:
    # GIVEN
    mock_workload = MagicMock(spec=WorkloadIdentity)
    mock_response = MagicMock(spec=UpdateWorkloadIdentityResponse)
    mock_response.workload_identity = mock_workload
    mock_sdk_client.update_workload_identity.return_value = mock_response

    name = "test-workload"

    # WHEN
    result = identity_client.update_workload_identity(name=name)

    # THEN
    assert result == mock_workload
    mock_sdk_client.update_workload_identity.assert_called_once()
    request = mock_sdk_client.update_workload_identity.call_args.kwargs["request"]
    assert request.workload_identity_name == name
    assert request.body.allowed_resource_oauth2_return_urls is None


def test_update_workload_identity_error(
    identity_client: IdentityClient, mock_sdk_client: MagicMock
) -> None:
    # GIVEN
    mock_sdk_client.update_workload_identity.side_effect = Exception("SDK Error")

    # WHEN / THEN
    with pytest.raises(Exception, match="SDK Error"):
        identity_client.update_workload_identity(name="test-workload")
