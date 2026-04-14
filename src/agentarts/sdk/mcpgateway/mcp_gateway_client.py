"""
MCP Gateway HTTP Client Module

Provides HTTP client implementation for MCP (Model Context Protocol) gateway operations.
"""

import json
from typing import Any, Dict, List, Optional
from agentarts.sdk.service.http_client import BaseHTTPClient, RequestConfig, RequestResult
from agentarts.sdk.service.iam_client import IAMClient
from agentarts.sdk.utils.common import generate_random_string
from agentarts.sdk.utils.constant import get_control_plane_endpoint



class MCPGatewayClient(BaseHTTPClient):
    """
    MCP Gateway client for making API calls to MCP Gateway service.
    
    Inherits from BaseHTTPClient to provide service-specific API methods.
    """
    
    def __init__(self, config: Optional[RequestConfig] = None):
        # If config is None or base_url is not set, use control plane endpoint
        if config is None or (config.base_url is None or config.base_url == ""):
            from agentarts.sdk.service.http_client import RequestConfig
            if config is None:
                config = RequestConfig()
            config.base_url = f"{get_control_plane_endpoint()}/v1/core"
            config.verify_ssl = False
        super().__init__(config, open_ak_sk=True)
    
    def create_mcp_gateway(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        protocol_type: Optional[str] = "mcp",
        authorizer_type: Optional[str] = "iam",
        agency_name: Optional[str] = None,
        authorizer_configuration: Optional[Dict[str, Any]] = None,
        log_delivery_configuration: Optional[Dict[str, Any]] = None,
        outbound_network_configuration: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> RequestResult:
        """
        Create a new MCP gateway.
        
        Args:
            name: Gateway name, default is gateway-<random-string>
            description: Gateway description
            protocol_type: Protocol type, default is "mcp"
            authorizer_type: Authorizer type, can be "custom_jwt", "iam", or "api_key", default is "iam"
            agency_name: Agency name
            authorizer_configuration: Authorizer configuration
            log_delivery_configuration: Log delivery configuration
            outbound_network_configuration: Outbound network configuration
            tags: Gateway tags
        
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
            iam_client = IAMClient()
            
            # Agency configuration
            agency_name = "AgentArtsCoreGateway"
            trust_policy = {
                "Version": "5.0",
                "Statement": [
                    {
                        "Action": [
                            "agentIdentity::getWorkloadAccessToken",
                            "agentIdentity::getWorkloadAccessToken",
                            "agentIdentity::getWorkloadAccessToken",
                            "agentIdentity::getWorkloadAccessToken",
                            "agentIdentity::getWorkloadAccessToken",
                            "csms:secret:getVersion"
                        ],
                        "Effect": "Allow",
                        "Principal": {}
                    }
                ]
            }
            
            # Convert trust_policy to JSON string
            trust_policy_str = json.dumps(trust_policy)
            
            try:
                # Try to create the agency
                iam_client.create_agency(
                    agency_name=agency_name,
                    trust_policy=trust_policy_str
                )
            except Exception as e:
                # Check if the error is a 409 Conflict (agency already exists)
                if "409" not in str(e):
                    raise ValueError(
                        f"Failed to create agency. Please provide a valid agency_name parameter. "
                        f"Error: {str(e)}"
                    )
        
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
            "log_delivery_configuration": log_delivery_configuration,
            "outbound_network_configuration": outbound_network_configuration,
            "tags": tags
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        return self.post("/gateways", json=payload)
    
    def update_mcp_gateway(
        self,
        gateway_id: str,
        description: Optional[str] = None,
        authorizer_configuration: Optional[Dict[str, Any]] = None,
        log_delivery_configuration: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> RequestResult:
        """
        Update an existing MCP gateway.
        
        Args:
            gateway_id: Gateway ID
            description: Gateway description
            authorizer_configuration: Authorizer configuration
            log_delivery_configuration: Log delivery configuration
            tags: Gateway tags
            
        Returns:
            RequestResult: Result of the API call
            
        Raises:
            ValueError: If all optional parameters are None
        """
        
        # Validate that not all optional parameters are None
        if all(param is None for param in [
            description,
            authorizer_configuration,
            log_delivery_configuration,
            tags
        ]):
            updateable_fields = [
                "description",
                "authorizer_configuration",
                "log_delivery_configuration",
                "tags"
            ]
            raise ValueError(f"At least one parameter must be provided for update. Available fields: {', '.join(updateable_fields)}")
        
        payload = {
            "description": description,
            "authorizer_configuration": authorizer_configuration,
            "log_delivery_configuration": log_delivery_configuration,
            "tags": tags
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        return self.put(f"/gateways/{gateway_id}", json=payload)
    
    def delete_mcp_gateway(self, gateway_id: str) -> RequestResult:
        """
        Delete an MCP gateway.
        
        Args:
            gateway_id: Gateway ID
            
        Returns:
            RequestResult: Result of the API call
        """
        return self.delete(f"/gateways/{gateway_id}")
    
    def get_mcp_gateway(self, gateway_id: str) -> RequestResult:
        """
        Get details of an MCP gateway.
        
        Args:
            gateway_id: Gateway ID
            
        Returns:
            RequestResult: Result of the API call
        """
        return self.get(f"/gateways/{gateway_id}")
    
    def list_mcp_gateways(
        self,
        name: Optional[str] = None,
        status: Optional[str] = None,
        gateway_id: Optional[str] = None,
        tags: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> RequestResult:
        """
        List MCP gateways with optional filters.
        
        Args:
            name: Gateway name filter
            status: Gateway status filter
            gateway_id: Gateway ID filter
            tags: Gateway tags filter
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            RequestResult: Result of the API call
        """
        params = {
            "name": name,
            "status": status,
            "gateway_id": gateway_id,
            "tags": tags,
            "limit": limit,
            "offset": offset
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        return self.get("/gateways", params=params)
    
    def create_mcp_gateway_target(
        self,
        gateway_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        target_configuration: Optional[Dict[str, Any]] = None,
        credential_provider_configuration: Optional[Dict[str, Any]] = None
    ) -> RequestResult:
        """
        Create a new MCP gateway target.
        
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
    
    def update_mcp_gateway_target(
        self,
        gateway_id: str,
        target_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        target_configuration: Optional[Dict[str, Any]] = None,
        credential_provider_configuration: Optional[Dict[str, Any]] = None
    ) -> RequestResult:
        """
        Update an existing MCP gateway target.
        
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
            raise ValueError(f"At least one parameter must be provided for update. Available fields: {', '.join(updateable_fields)}")
        
        payload = {
            "name": name,
            "description": description,
            "target_configuration": target_configuration,
            "credential_provider_configuration": credential_provider_configuration
        }
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        return self.put(f"/gateways/{gateway_id}/targets/{target_id}", json=payload)
    
    def delete_mcp_gateway_target(self, gateway_id: str, target_id: str) -> RequestResult:
        """
        Delete an MCP gateway target.
        
        Args:
            gateway_id: Gateway ID
            target_id: Target ID
            
        Returns:
            RequestResult: Result of the API call
        """
        return self.delete(f"/gateways/{gateway_id}/targets/{target_id}")
    
    def get_mcp_gateway_target(self, gateway_id: str, target_id: str) -> RequestResult:
        """
        Get details of an MCP gateway target.
        
        Args:
            gateway_id: Gateway ID
            target_id: Target ID
            
        Returns:
            RequestResult: Result of the API call
        """
        return self.get(f"/gateways/{gateway_id}/targets/{target_id}")
    
    def list_mcp_gateway_targets(
        self,
        gateway_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> RequestResult:
        """
        List MCP gateway targets with pagination.
        
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
