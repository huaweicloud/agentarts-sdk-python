from unittest.mock import MagicMock, patch

from huaweicloudsdkagentidentity.v1 import (
    AgentIdentityClient,
    GetWorkloadIdentityResponse,
    ListWorkloadIdentitiesResponse,
    WorkloadIdentity,
    WorkloadIdentitySummary,
)

from agentarts.sdk.service.identity.identity_client import IdentityClient


def _build_identity_client(mock_sdk_client: MagicMock) -> IdentityClient:
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


def test_get_workload_identity_success() -> None:
    # GIVEN
    mock_sdk_client = MagicMock(spec=AgentIdentityClient)
    identity_client = _build_identity_client(mock_sdk_client)
    mock_workload = MagicMock(spec=WorkloadIdentity)
    mock_response = MagicMock(spec=GetWorkloadIdentityResponse)
    mock_response.workload_identity = mock_workload
    mock_sdk_client.get_workload_identity.return_value = mock_response

    name = "test-workload"

    # WHEN
    result = identity_client.get_workload_identity(name=name)

    # THEN
    assert result == mock_workload
    mock_sdk_client.get_workload_identity.assert_called_once()
    request = mock_sdk_client.get_workload_identity.call_args.kwargs["request"]
    assert request.workload_identity_name == name


def test_list_workload_identities_success() -> None:
    # GIVEN
    mock_sdk_client = MagicMock(spec=AgentIdentityClient)
    identity_client = _build_identity_client(mock_sdk_client)
    mock_workloads = [
        MagicMock(spec=WorkloadIdentitySummary),
        MagicMock(spec=WorkloadIdentitySummary),
    ]
    mock_response = MagicMock(spec=ListWorkloadIdentitiesResponse)
    mock_response.workload_identities = mock_workloads
    mock_sdk_client.list_workload_identities.return_value = mock_response

    # WHEN
    result = identity_client.list_workload_identities(limit=10, marker="next-page")

    # THEN
    assert result == mock_workloads
    mock_sdk_client.list_workload_identities.assert_called_once()
    request = mock_sdk_client.list_workload_identities.call_args.kwargs["request"]
    assert request.limit == 10
    assert request.marker == "next-page"


def test_list_workload_identities_returns_empty_list_when_response_is_empty() -> None:
    # GIVEN
    mock_sdk_client = MagicMock(spec=AgentIdentityClient)
    identity_client = _build_identity_client(mock_sdk_client)
    mock_response = MagicMock(spec=ListWorkloadIdentitiesResponse)
    mock_response.workload_identities = None
    mock_sdk_client.list_workload_identities.return_value = mock_response

    # WHEN
    result = identity_client.list_workload_identities()

    # THEN
    assert result == []
    mock_sdk_client.list_workload_identities.assert_called_once()
    request = mock_sdk_client.list_workload_identities.call_args.kwargs["request"]
    assert request.limit is None
    assert request.marker is None
