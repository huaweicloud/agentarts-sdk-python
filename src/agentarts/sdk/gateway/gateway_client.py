"""
Gateway HTTP Client Module

Provides HTTP client implementation for MCP (Model Context Protocol) gateway operations.
"""

import json
from typing import Any

from agentarts.sdk.service.http_client import BaseHTTPClient, RequestConfig, RequestResult
from agentarts.sdk.service.iam_client import IAMClient
from agentarts.sdk.utils.common import generate_random_string
from agentarts.sdk.utils.constant import get_control_plane_endpoint


class GatewayClient(BaseHTTPClient):
    """
    Gateway client for making API calls to Gateway service.

    Inherits from BaseHTTPClient to provide service-specific API methods.
    """

    def __init__(self, verify_ssl: bool = True):
        config = RequestConfig()
        config.base_url = f"{get_control_plane_endpoint()}/v1/core"
        config.verify_ssl = verify_ssl
        self.verify_ssl = verify_ssl
        super().__init__(config, open_ak_sk=True)

    def create_gateway(
        self,
        name: str | None = None,
        description: str | None = None,
        protocol_type: str | None = "mcp",
        authorizer_type: str | None = "iam",
        agency_name: str | None = None,
        authorizer_configuration: dict[str, Any] | None = None,
        protocol_configuration: dict[str, Any] | None = None,
        log_delivery_configuration: dict[str, Any] | None = None,
        outbound_network_configuration: dict[str, Any] | None = None,
        tags: list[dict[str, str]] | None = None
    ) -> RequestResult:
        """
        Create a new gateway.

        Args:
            name: Gateway name, default is gateway-<random-string>
            description: Gateway description
            protocol_type: Protocol type, default is "mcp"
            authorizer_type: Authorizer type, can be "custom_jwt", "iam", or "api_key", default is "iam"
            agency_name: Agency name
            authorizer_configuration: Authorizer configuration
            protocol_configuration: Protocol configuration, e.g. {"mcp": {"search_configuration": {...}}}
            log_delivery_configuration: Log delivery configuration
            outbound_network_configuration: Outbound network configuration
            tags: Resource tags list

        Returns:
            RequestResult: Result of the API call

        Raises:
            ValueError: If agency creation fails and no agency_name is provided
        """
        # Set default name if not provided
        if name is None:
            name = f"gateway-{generate_random_string(8)}"

        # Handle agency_name if not provided
        if agency_name is None:
            # Create IAM client
            iam_client = IAMClient(verify_ssl=self.verify_ssl)

            # Agency configuration
            agency_name = "AgentArtsCoreGateway"
            # Set service principal to service.WorkloadSandboxMetadata
            service_principal = "service.WorkloadSandboxMetadata"
            trust_policy = {
                "Version": "5.0",
                "Statement": [
                    {
                        "Action": ["sts:agencies:assume"],
                        "Effect": "Allow",
                        "Principal": {
                            "Service": [service_principal]
                        }
                    }
                ]
            }

            # Convert trust_policy to JSON string
            trust_policy_str = json.dumps(trust_policy)

            try:
                # Try to create the agency with policy
                iam_client.create_agency_with_policy(
                    agency_name=agency_name,
                    trust_policy=trust_policy_str,
                    policy_name="AgentArtsCoreGatewayIdentityAgencyPolicy"
                )
            except Exception as e:
                # Check if the error is a 409 Conflict (agency already exists)
                if "409" not in str(e):
                    msg = (
                        f"Failed to create agency with policy. Please provide a valid agency_name parameter. "
                        f"Error: {e!s}"
                    )
                    raise ValueError(
                        msg
                    )
                # If agency already exists (409), assume it has the correct policy and continue

        if log_delivery_configuration is None:
            log_delivery_configuration = { "enabled": False }

        if outbound_network_configuration is None:
            outbound_network_configuration = {"network_mode": "public"}

        payload = {
            "name": name,
            "description": description,
            "protocol_type": protocol_type,
            "authorizer_type": authorizer_type,
            "agency_name": agency_name,
            "authorizer_configuration": authorizer_configuration,
            "protocol_configuration": protocol_configuration,
            "log_delivery_configuration": log_delivery_configuration,
            "outbound_network_configuration": outbound_network_configuration,
            "tags": tags
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        return self.post("/gateways", json=payload)

    def update_gateway(
        self,
        gateway_id: str,
        description: str | None = None,
        protocol_configuration: dict[str, Any] | None = None,
        log_delivery_configuration: dict[str, Any] | None = None,
        tags: list[dict[str, str]] | None = None
    ) -> RequestResult:
        """
        Update an existing gateway.

        Args:
            gateway_id: Gateway ID
            description: Gateway description
            protocol_configuration: Protocol configuration
            log_delivery_configuration: Log delivery configuration
            tags: Resource tags list

        Returns:
            RequestResult: Result of the API call

        Raises:
            ValueError: If all optional parameters are None
        """

        # Validate that not all optional parameters are None
        if all(param is None for param in [
            description,
            protocol_configuration,
            log_delivery_configuration,
            tags
        ]):
            updateable_fields = [
                "description",
                "protocol_configuration",
                "log_delivery_configuration",
                "tags"
            ]
            msg = f"At least one parameter must be provided for update. Available fields: {', '.join(updateable_fields)}"
            raise ValueError(msg)

        payload = {
            "description": description,
            "protocol_configuration": protocol_configuration,
            "log_delivery_configuration": log_delivery_configuration,
            "tags": tags
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        return self.put(f"/gateways/{gateway_id}", json=payload)

    def delete_gateway(self, gateway_id: str) -> RequestResult:
        """
        Delete a gateway.

        Args:
            gateway_id: Gateway ID

        Returns:
            RequestResult: Result of the API call
        """
        return self.delete(f"/gateways/{gateway_id}")

    def get_gateway(self, gateway_id: str) -> RequestResult:
        """
        Get details of a gateway.

        Args:
            gateway_id: Gateway ID

        Returns:
            RequestResult: Result of the API call
        """
        return self.get(f"/gateways/{gateway_id}")

    def list_gateways(
        self,
        name: str | None = None,
        status: str | None = None,
        gateway_id: str | None = None,
        tag_key_exists: list[str] | None = None,
        tag_key_matches: list[str] | None = None,
        tag_value_matches: list[str] | None = None,
        tag_match_policy: str | None = None,
        limit: int | None = None,
        offset: int | None = None
    ) -> RequestResult:
        """
        List gateways with optional filters.

        Args:
            name: Gateway name filter
            status: Gateway status filter
            gateway_id: Gateway ID filter
            tag_key_exists: Filter by tag key existence
            tag_key_matches: Filter by tag key-value pairs (keys)
            tag_value_matches: Filter by tag key-value pairs (values)
            tag_match_policy: Tag match policy, "ALL" or "ANY"
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            RequestResult: Result of the API call
        """
        params = {
            "name": name,
            "status": status,
            "gateway_id": gateway_id,
            "tag_key_exists": tag_key_exists,
            "tag_key_matches": tag_key_matches,
            "tag_value_matches": tag_value_matches,
            "tag_match_policy": tag_match_policy,
            "limit": limit,
            "offset": offset
        }

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        return self.get("/gateways", params=params)

    def create_gateway_target(
        self,
        gateway_id: str,
        name: str | None = None,
        description: str | None = None,
        target_configuration: dict[str, Any] | None = None,
        credential_provider_configuration: dict[str, Any] | None = None
    ) -> RequestResult:
        """
        Create a new gateway target.

        Args:
            gateway_id: Gateway ID
            name: Target name, default is target-<random-string>
            description: Target description
            target_configuration: Target configuration
            credential_provider_configuration: Credential provider configuration

        Returns:
            RequestResult: Result of the API call
        """
        # Set default name if not provided
        if name is None:
            name = f"target-{generate_random_string(8)}"

        # Set default credential provider configuration if not provided
        if credential_provider_configuration is None:
            credential_provider_configuration = {"credential_provider_type": "none"}

        payload = {
            "name": name,
            "description": description,
            "target_configuration": target_configuration,
            "credential_provider_configuration": credential_provider_configuration
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        return self.post(f"/gateways/{gateway_id}/targets", json=payload)

    def update_gateway_target(
        self,
        gateway_id: str,
        target_id: str,
        name: str | None = None,
        description: str | None = None,
        target_configuration: dict[str, Any] | None = None,
        credential_provider_configuration: dict[str, Any] | None = None
    ) -> RequestResult:
        """
        Update an existing gateway target.

        Args:
            gateway_id: Gateway ID
            target_id: Target ID
            name: Target name
            description: Target description
            target_configuration: Target configuration
            credential_provider_configuration: Credential provider configuration

        Returns:
            RequestResult: Result of the API call

        Raises:
            ValueError: If all optional parameters are None
        """
        # Validate that not all optional parameters are None
        if all(param is None for param in [
            name,
            description,
            target_configuration,
            credential_provider_configuration
        ]):
            updateable_fields = [
                "name",
                "description",
                "target_configuration",
                "credential_provider_configuration"
            ]
            msg = f"At least one parameter must be provided for update. Available fields: {', '.join(updateable_fields)}"
            raise ValueError(msg)

        payload = {
            "name": name,
            "description": description,
            "target_configuration": target_configuration,
            "credential_provider_configuration": credential_provider_configuration
        }
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        return self.put(f"/gateways/{gateway_id}/targets/{target_id}", json=payload)

    def delete_gateway_target(self, gateway_id: str, target_id: str) -> RequestResult:
        """
        Delete a gateway target.

        Args:
            gateway_id: Gateway ID
            target_id: Target ID

        Returns:
            RequestResult: Result of the API call
        """
        return self.delete(f"/gateways/{gateway_id}/targets/{target_id}")

    def get_gateway_target(self, gateway_id: str, target_id: str) -> RequestResult:
        """
        Get details of a gateway target.

        Args:
            gateway_id: Gateway ID
            target_id: Target ID

        Returns:
            RequestResult: Result of the API call
        """
        return self.get(f"/gateways/{gateway_id}/targets/{target_id}")

    def list_gateway_targets(
        self,
        gateway_id: str,
        limit: int | None = None,
        offset: int | None = None
    ) -> RequestResult:
        """
        List gateway targets with pagination.

        Args:
            gateway_id: Gateway ID
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            RequestResult: Result of the API call
        """
        params = {
            "limit": limit,
            "offset": offset
        }

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        return self.get(f"/gateways/{gateway_id}/targets", params=params)
