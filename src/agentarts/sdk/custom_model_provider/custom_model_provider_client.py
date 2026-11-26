"""
Model Provider HTTP Client Module

Provides HTTP client implementation for model provider, model service and
model proxy operations on the AgentArts model gateway.
"""

import json
from typing import Any

from agentarts.sdk.service.http_client import BaseHTTPClient, RequestConfig, RequestResult
from agentarts.sdk.service.iam_client import IAMClient
from agentarts.sdk.utils.common import generate_random_string
from agentarts.sdk.utils.constant import get_control_plane_endpoint


class CustomModelProviderClient(BaseHTTPClient):
    """
    Custom model provider client for making API calls to the model gateway.

    Inherits from BaseHTTPClient to provide service-specific API methods for
    model providers, model services, model proxies and model management quotas.
    """

    def __init__(self, verify_ssl: bool = True):
        config = RequestConfig()
        config.base_url = f"{get_control_plane_endpoint()}/v1/core"
        config.verify_ssl = verify_ssl
        self.verify_ssl = verify_ssl
        super().__init__(config, open_ak_sk=True)

    # ------------------------------------------------------------------ #
    # Model provider management
    # ------------------------------------------------------------------ #
    def create_model_provider(
        self,
        name: str,
        base_url: str,
        credential_configuration: dict[str, Any],
        network_configuration: dict[str, Any] | None = None,
        description: str | None = None,
        tags: list[dict[str, str]] | None = None
    ) -> RequestResult:
        """
        Create a new custom model provider.

        Args:
            name: Model provider name, unique per account (case-insensitive)
            base_url: Default API base URL of the model provider
            credential_configuration: Credential information of the model provider
            network_configuration: Outbound network configuration,
                default is {"network_mode": "public"}
            description: Model provider description
            tags: Resource tags list

        Returns:
            RequestResult: Result of the API call
        """
        # Set default network configuration if not provided
        if network_configuration is None:
            network_configuration = {"network_mode": "public"}

        payload = {
            "name": name,
            "base_url": base_url,
            "credential_configuration": credential_configuration,
            "network_configuration": network_configuration,
            "description": description,
            "tags": tags
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        return self.post("/custom-model-providers", json=payload)

    def update_model_provider(
        self,
        model_provider_id: str,
        name: str | None = None,
        base_url: str | None = None,
        credential_configuration: dict[str, Any] | None = None,
        network_configuration: dict[str, Any] | None = None,
        description: str | None = None,
        tags: list[dict[str, str]] | None = None
    ) -> RequestResult:
        """
        Update an existing custom model provider.

        Args:
            model_provider_id: Model provider ID
            name: Model provider name
            base_url: Default API base URL of the model provider
            credential_configuration: Credential information of the model provider
            network_configuration: Outbound network configuration
            description: Model provider description
            tags: Resource tags list

        Returns:
            RequestResult: Result of the API call

        Raises:
            ValueError: If all optional parameters are None
        """
        # Validate that not all optional parameters are None
        if all(param is None for param in [
            name,
            base_url,
            credential_configuration,
            network_configuration,
            description,
            tags
        ]):
            updateable_fields = [
                "name",
                "base_url",
                "credential_configuration",
                "network_configuration",
                "description",
                "tags"
            ]
            msg = f"At least one parameter must be provided for update. Available fields: {', '.join(updateable_fields)}"
            raise ValueError(msg)

        payload = {
            "name": name,
            "base_url": base_url,
            "credential_configuration": credential_configuration,
            "network_configuration": network_configuration,
            "description": description,
            "tags": tags
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        return self.put(f"/custom-model-providers/{model_provider_id}", json=payload)

    def delete_model_provider(self, model_provider_id: str) -> RequestResult:
        """
        Delete a custom model provider.

        Args:
            model_provider_id: Model provider ID

        Returns:
            RequestResult: Result of the API call
        """
        return self.delete(f"/custom-model-providers/{model_provider_id}")

    def get_model_provider(self, model_provider_id: str) -> RequestResult:
        """
        Get details of a custom model provider.

        Args:
            model_provider_id: Model provider ID

        Returns:
            RequestResult: Result of the API call
        """
        return self.get(f"/custom-model-providers/{model_provider_id}")

    def list_model_providers(
        self,
        name: str | None = None,
        model_provider_id: str | None = None,
        tag_key_exists: list[str] | None = None,
        tag_key_matches: list[str] | None = None,
        tag_value_matches: list[str] | None = None,
        tag_match_policy: str | None = None,
        limit: int | None = None,
        offset: int | None = None
    ) -> RequestResult:
        """
        List custom model providers with optional filters.

        Args:
            name: Model provider name filter
            model_provider_id: Model provider ID filter
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
            "id": model_provider_id,
            "tag_key_exists": tag_key_exists,
            "tag_key_matches": tag_key_matches,
            "tag_value_matches": tag_value_matches,
            "tag_match_policy": tag_match_policy,
            "limit": limit,
            "offset": offset
        }

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        return self.get("/custom-model-providers", params=params)

    # ------------------------------------------------------------------ #
    # Model service management
    # ------------------------------------------------------------------ #
    def create_model(
        self,
        model_provider_id: str,
        model: str,
        model_service_name: str,
        type_: list[str],
        protocol: str,
        description: str | None = None
    ) -> RequestResult:
        """
        Create a new model under a custom model provider.

        Args:
            model_provider_id: Model provider ID
            model: Model name, e.g. "qwen2.5-72b"
            model_service_name: Display name of the model service
            type_: Model type list, e.g. ["completions"]
            protocol: API protocol, "openai", "anthropic" or "maas_v1"
            description: Model description

        Returns:
            RequestResult: Result of the API call
        """
        payload = {
            "model": model,
            "model_service_name": model_service_name,
            "type": type_,
            "protocol": protocol,
            "description": description
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        return self.post(f"/custom-model-providers/{model_provider_id}/models", json=payload)

    def update_model(
        self,
        model_provider_id: str,
        model_id: str,
        model: str | None = None,
        model_service_name: str | None = None,
        type_: list[str] | None = None,
        protocol: str | None = None,
        description: str | None = None
    ) -> RequestResult:
        """
        Update an existing model under a custom model provider.

        Args:
            model_provider_id: Model provider ID
            model_id: Model ID
            model: Model name, e.g. "qwen2.5-72b"
            model_service_name: Display name of the model service
            type_: Model type list, e.g. ["completions"]
            protocol: API protocol, "openai", "anthropic" or "maas_v1"
            description: Model description

        Returns:
            RequestResult: Result of the API call

        Raises:
            ValueError: If all optional parameters are None
        """
        # Validate that not all optional parameters are None
        if all(param is None for param in [
            model,
            model_service_name,
            type_,
            protocol,
            description
        ]):
            updateable_fields = [
                "model",
                "model_service_name",
                "type_",
                "protocol",
                "description"
            ]
            msg = f"At least one parameter must be provided for update. Available fields: {', '.join(updateable_fields)}"
            raise ValueError(msg)

        payload = {
            "model": model,
            "model_service_name": model_service_name,
            "type": type_,
            "protocol": protocol,
            "description": description
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        return self.put(
            f"/custom-model-providers/{model_provider_id}/models/{model_id}",
            json=payload
        )

    def delete_model(self, model_provider_id: str, model_id: str) -> RequestResult:
        """
        Delete a model under a custom model provider.

        Args:
            model_provider_id: Model provider ID
            model_id: Model ID

        Returns:
            RequestResult: Result of the API call
        """
        return self.delete(f"/custom-model-providers/{model_provider_id}/models/{model_id}")

    def get_model(self, model_provider_id: str, model_id: str) -> RequestResult:
        """
        Get details of a model under a custom model provider.

        Args:
            model_provider_id: Model provider ID
            model_id: Model ID

        Returns:
            RequestResult: Result of the API call
        """
        return self.get(f"/custom-model-providers/{model_provider_id}/models/{model_id}")

    def list_models(
        self,
        model_provider_id: str,
        model_service_name: str | None = None,
        model_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None
    ) -> RequestResult:
        """
        List models under a custom model provider with optional filters.

        Args:
            model_provider_id: Model provider ID
            model_service_name: Model service display name filter
            model_id: Model ID filter
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            RequestResult: Result of the API call
        """
        params = {
            "model_service_name": model_service_name,
            "id": model_id,
            "limit": limit,
            "offset": offset
        }

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        return self.get(f"/custom-model-providers/{model_provider_id}/models", params=params)

    # ------------------------------------------------------------------ #
    # Model proxy management
    # ------------------------------------------------------------------ #
    def create_model_proxy(
        self,
        custom_model_provider_id: str,
        name: str | None = None,
        description: str | None = None,
        inbound_authorizer_type: str | None = "iam",
        agency_name: str | None = None,
        inbound_authorizer_configuration: dict[str, Any] | None = None,
        agent_gateway_id: str | None = None,
        tags: list[dict[str, str]] | None = None
    ) -> RequestResult:
        """
        Create a new model proxy bound to a custom model provider.

        Args:
            custom_model_provider_id: Model provider ID
            name: Model proxy name, default is model-proxy-<random-string>
            description: Model proxy description
            inbound_authorizer_type: Inbound authorizer type, "iam" or "api_key",
                default is "iam"
            agency_name: Agency name. If not provided, an agency named
                AgentArtsCoreGateway is created automatically
            inbound_authorizer_configuration: Inbound authorizer configuration
            agent_gateway_id: Inbound network configuration ID of the
                underlying AgentGateway instance
            tags: Resource tags list

        Returns:
            RequestResult: Result of the API call

        Raises:
            ValueError: If agency creation fails and no agency_name is provided
        """
        # Set default name if not provided
        if name is None:
            name = f"model-proxy-{generate_random_string(8)}"

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

        payload = {
            "custom_model_provider_id": custom_model_provider_id,
            "name": name,
            "description": description,
            "inbound_authorizer_type": inbound_authorizer_type,
            "agency_name": agency_name,
            "inbound_authorizer_configuration": inbound_authorizer_configuration,
            "agent_gateway_id": agent_gateway_id,
            "tags": tags
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        return self.post("/model-proxy", json=payload)

    def update_model_proxy(
        self,
        gateway_id: str,
        tags: list[dict[str, str]] | None = None
    ) -> RequestResult:
        """
        Update an existing model proxy.

        Args:
            gateway_id: Model proxy gateway ID
            tags: Resource tags list

        Returns:
            RequestResult: Result of the API call

        Raises:
            ValueError: If all optional parameters are None
        """
        # Validate that not all optional parameters are None
        if all(param is None for param in [tags]):
            updateable_fields = ["tags"]
            msg = f"At least one parameter must be provided for update. Available fields: {', '.join(updateable_fields)}"
            raise ValueError(msg)

        payload = {
            "tags": tags
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        return self.put(f"/model-proxy/{gateway_id}", json=payload)

    def batch_disassociate_model_proxies(
        self,
        unbindings: list[dict[str, str]]
    ) -> RequestResult:
        """
        Batch disassociate model proxies from model providers.

        A model proxy is deleted automatically when it is no longer
        associated with any model provider.

        Args:
            unbindings: Unbinding list, each item is a dict of
                {"custom_model_provider_id": "...", "gateway_id": "..."}

        Returns:
            RequestResult: Result of the API call
        """
        payload = {
            "unbindings": unbindings
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        return self.post("/model-proxy-batch-disassociate", json=payload)

    # ------------------------------------------------------------------ #
    # Model management quotas
    # ------------------------------------------------------------------ #
    def list_model_management_quotas(
        self,
        custom_model_provider_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None
    ) -> RequestResult:
        """
        List model management quotas of the current authenticated account.

        Args:
            custom_model_provider_id: Model provider ID. When specified, only
                per-provider quotas are returned
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            RequestResult: Result of the API call
        """
        params = {
            "custom_model_provider_id": custom_model_provider_id,
            "limit": limit,
            "offset": offset
        }

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        return self.get("/model-management-quotas", params=params)
