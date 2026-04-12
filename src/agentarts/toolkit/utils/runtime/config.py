"""
AgentArts Configuration Models

This module defines configuration models for the AgentArts toolkit.
All models use Pydantic for validation and serialization.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NetworkProtocol(str, Enum):
    """Network protocol."""

    HTTP = "HTTP"
    MCP = "MCP"
    WEBSOCKET = "WEBSOCKET"


class AuthType(str, Enum):
    """Authentication type."""

    IAM = "IAM"
    API_KEY = "API_KEY"
    CUSTOM_JWT = "CUSTOM_JWT"


class BaseConfig(BaseModel):
    """Base configuration with region and environment."""

    name: Optional[str] = Field(
        default=None,
        description="Name of the AgentArts runtime",
    )
    entrypoint: Optional[str] = Field(
        default=None,
        description="Entrypoint of the AgentArts runtime",
    )
    dependency_file: Optional[str] = Field(
        default=None,
        description="Path to dependency file (e.g., requirements.txt, pyproject.toml)",
    )
    region: Optional[str] = Field(
        default=None,
        description="Huawei Cloud region",
    )
    platform: str = Field(
        default="linux/amd64",
        description="Platform of the AgentArts runtime",
    )
    language: str = Field(
        default="python3",
        description="Language of the AgentArts runtime",
    )
    container_runtime: str = Field(
        default="docker",
        description="Container runtime of the AgentArts runtime",
    )
    base_image: str = Field(
        default="python:3.10-slim",
        description="Base image of the AgentArts runtime",
    )

    model_config = {
        "use_enum_values": True,
        "extra": "allow",
    }


class SWRConfig(BaseModel):
    """Huawei Cloud SWR (SoftWare Repository) configuration."""

    organization_auto_create: bool = Field(
        default=False,
        description="Whether to automatically create the SWR organization if it doesn't exist",
    )
    organization: Optional[str] = Field(
        default=None,
        description="SWR organization name",
    )
    repository_auto_create: bool = Field(
        default=False,
        description="Whether to automatically create the SWR repository if it doesn't exist",
    )
    repository: Optional[str] = Field(
        default=None,
        description="SWR repository name",
    )

    model_config = {
        "extra": "allow",
    }


class InvokeConfig(BaseModel):
    """Invoke configuration."""

    protocol: NetworkProtocol = Field(
        default=NetworkProtocol.HTTP,
        description="Server protocol for deployment, either HTTP, MCP or WEBSOCKET",
    )
    port: int = Field(
        default=8080,
        ge=1,
        le=65535,
        description="Port number of the server",
    )

    model_config = {
        "use_enum_values": True,
        "extra": "allow",
    }


class VpcConfig(BaseModel):
    """VPC configuration."""

    vpc_id: Optional[str] = Field(
        default=None,
        description="VPC ID",
    )
    subnet_id: Optional[str] = Field(
        default=None,
        description="Subnet ID",
    )
    security_group_id: Optional[List[str]] = Field(
        default_factory=list,
        description="Security group IDs",
    )

    model_config = {
        "extra": "allow",
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(mode="json", exclude_none=True)


class NetworkConfig(BaseModel):
    """Network endpoint configuration."""

    network_mode: str = Field(
        default="PUBLIC",
        description="Network mode, e.g., 'VPC' or 'PUBLIC'",
    )
    vpc_config: Optional[VpcConfig] = Field(
        default_factory=VpcConfig,
        description="VPC configuration details",
    )

    model_config = {
        "extra": "allow",
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(mode="json", exclude_none=True)


class APIKeyPair(BaseModel):
    """API key pair configuration."""

    api_key: Optional[str] = Field(
        default=None,
        description="API key",
    )
    api_key_name: Optional[str] = Field(
        default=None,
        description="API key name",
    )

    model_config = {
        "extra": "allow",
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(mode="json", exclude_none=True)


class APIKeyAuthConfig(BaseModel):
    """API key authentication configuration."""

    api_keys: Optional[List[APIKeyPair]] = Field(
        default_factory=list,
        description="API keys for authentication",
    )

    model_config = {
        "extra": "allow",
    }


class CustomJWTAuthConfig(BaseModel):
    """Custom JWT authentication configuration."""

    discovery_url: Optional[str] = Field(
        default=None,
        description="Discovery URL for JWT authentication",
    )
    allowed_audience: Optional[List[str]] = Field(
        default_factory=list,
        description="Allowed audiences for JWT authentication",
    )
    allowed_clients: Optional[List[str]] = Field(
        default_factory=list,
        description="Allowed clients for JWT authentication",
    )
    allowed_scopes: Optional[List[str]] = Field(
        default_factory=list,
        description="Allowed scopes for JWT authentication",
    )

    model_config = {
        "extra": "allow",
    }


class AuthConfig(BaseModel):
    """Authentication configuration."""

    custom_jwt: Optional[CustomJWTAuthConfig] = Field(
        default_factory=CustomJWTAuthConfig,
        description="Custom JWT authentication configuration",
    )
    key_auth: Optional[APIKeyAuthConfig] = Field(
        default_factory=APIKeyAuthConfig,
        description="API key authentication configuration",
    )

    model_config = {
        "extra": "allow",
    }


class InboundIdentityConfig(BaseModel):
    """Inbound identity configuration."""

    authorizer_type: AuthType = Field(
        default=AuthType.IAM,
        description="Authentication type",
    )
    authorizer_configuration: Optional[AuthConfig] = Field(
        default=None,
        description="Authorizer configuration",
    )

    model_config = {
        "use_enum_values": True,
        "extra": "allow",
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(mode="json", exclude_none=True)


class ArtifactSourceConfig(BaseModel):
    """Artifact source configuration."""

    url: Optional[str] = Field(
        default=None,
        description="URL of the artifact source",
    )
    commands: Optional[List[str]] = Field(
        default_factory=list,
        description="Commands to run when the artifact is deployed",
    )

    model_config = {
        "extra": "allow",
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(mode="json", exclude_none=True)


class KeyValuePair(BaseModel):
    """Key-value pair configuration."""

    key: str = Field(
        description="Key",
    )
    value: Optional[str] = Field(
        default=None,
        description="Value",
    )

    model_config = {
        "extra": "allow",
    }


class TracingConfig(BaseModel):
    """Tracing configuration for observability."""

    enabled: bool = Field(
        default=False,
        description="Whether tracing is enabled",
    )

    model_config = {
        "extra": "allow",
    }


class MetricsConfig(BaseModel):
    """Metrics configuration for observability."""

    enabled: bool = Field(
        default=False,
        description="Whether metrics collection is enabled",
    )

    model_config = {
        "extra": "allow",
    }


class LoggingConfig(BaseModel):
    """Logging configuration for observability."""

    enabled: bool = Field(
        default=False,
        description="Whether logging is enabled",
    )

    model_config = {
        "extra": "allow",
    }


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    tracing: TracingConfig = Field(
        default_factory=TracingConfig,
        description="Tracing configuration",
    )
    metrics: MetricsConfig = Field(
        default_factory=MetricsConfig,
        description="Metrics configuration",
    )
    logs: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration",
    )

    model_config = {
        "extra": "allow",
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(mode="json", exclude_none=True)


class AgentArtsRuntimeConfig(BaseModel):
    """Runtime configuration for AgentArts."""

    agent_id: Optional[str] = Field(
        default=None,
        description="Agent ID",
    )
    agent_gateway_id: Optional[str] = Field(
        default=None,
        description="Agent gateway ID",
    )
    execution_agency_name: Optional[str] = Field(
        default=None,
        description="Execution agency name",
    )
    identity_configuration: Optional[InboundIdentityConfig] = Field(
        default_factory=InboundIdentityConfig,
        description="Identity configuration",
    )
    network_config: Optional[NetworkConfig] = Field(
        default_factory=NetworkConfig,
        description="Network configuration",
    )
    invoke_config: Optional[InvokeConfig] = Field(
        default_factory=InvokeConfig,
        description="Invoke configuration",
    )
    observability: Optional[ObservabilityConfig] = Field(
        default_factory=ObservabilityConfig,
        description="Observability configuration",
    )
    artifact_source: Optional[ArtifactSourceConfig] = Field(
        default_factory=ArtifactSourceConfig,
        description="Artifact source configuration",
    )
    environment_variables: Optional[List[KeyValuePair]] = Field(
        default_factory=list,
        description="Environment variables configuration",
    )
    tags: Optional[List[KeyValuePair]] = Field(
        default_factory=list,
        description="Tags configuration",
    )

    model_config = {
        "extra": "allow",
    }


class AgentArtsConfig(BaseModel):
    """
    Main configuration for AgentArts toolkit.

    This is the top-level configuration that aggregates all sub-configurations.
    """

    base: BaseConfig = Field(
        default_factory=BaseConfig,
        description="Base configuration",
    )
    swr_config: SWRConfig = Field(
        default_factory=SWRConfig,
        description="SWR configuration",
    )
    runtime: AgentArtsRuntimeConfig = Field(
        default_factory=AgentArtsRuntimeConfig,
        description="Runtime configuration",
    )

    model_config = {
        "extra": "allow",
    }

    @classmethod
    def from_yaml(cls, path: str) -> "AgentArtsConfig":
        """Load configuration from YAML file."""
        import yaml

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.model_validate(data)

    def to_yaml(self, path: str) -> None:
        """Save configuration to YAML file with ordered fields."""
        import yaml
        
        def order_dict(d: Dict[str, Any], key_order: List[str]) -> Dict[str, Any]:
            """Reorder dictionary keys with specified order."""
            ordered = {}
            for key in key_order:
                if key in d:
                    ordered[key] = d[key]
            for key in d:
                if key not in ordered:
                    ordered[key] = d[key]
            return ordered
        
        data = self.model_dump(mode="json")
        
        ordered_data = order_dict(data, ["default_agent", "agents"])
        
        if "agents" in ordered_data:
            ordered_agents = {}
            for agent_name, agent_config in ordered_data["agents"].items():
                ordered_agents[agent_name] = order_dict(
                    agent_config, ["base", "swr_config", "runtime"]
                )
                if "base" in ordered_agents[agent_name]:
                    ordered_agents[agent_name]["base"] = order_dict(
                        ordered_agents[agent_name]["base"],
                        ["name", "entrypoint", "dependency_file", "region", "platform", "language", "base_image"]
                    )
                if "runtime" in ordered_agents[agent_name]:
                    ordered_agents[agent_name]["runtime"] = order_dict(
                        ordered_agents[agent_name]["runtime"],
                        ["agent_id", "agent_gateway_id", "execution_agency_name", "invoke_config", "network_config", "identity_configuration", "observability", "artifact_source", "environment_variables", "tags"]
                    )
            ordered_data["agents"] = ordered_agents
        
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(ordered_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentArtsConfig":
        """Create configuration from dictionary."""
        return cls.model_validate(data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(mode="json")


class AgentArtsConfigList(BaseModel):
    """
    Configuration list for multiple AgentArts runtimes.

    This is used to manage multiple agent configurations in a single file.
    """

    default_agent: Optional[str] = Field(
        default=None,
        description="Default AgentArts runtime name for toolkit operations",
    )
    agents: Dict[str, AgentArtsConfig] = Field(
        default_factory=dict,
        description="Dictionary of AgentArts runtime configurations",
    )

    model_config = {
        "extra": "allow",
    }

    @classmethod
    def from_yaml(cls, path: str) -> "AgentArtsConfigList":
        """Load configuration from YAML file."""
        import yaml

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.model_validate(data)

    def to_yaml(self, path: str) -> None:
        """Save configuration to YAML file with ordered fields."""
        import yaml
        
        def order_dict(d: Dict[str, Any], key_order: List[str]) -> Dict[str, Any]:
            """Reorder dictionary keys with specified order."""
            ordered = {}
            for key in key_order:
                if key in d:
                    ordered[key] = d[key]
            for key in d:
                if key not in ordered:
                    ordered[key] = d[key]
            return ordered
        
        data = self.model_dump(mode="json")
        
        ordered_data = order_dict(data, ["default_agent", "agents"])
        
        if "agents" in ordered_data:
            ordered_agents = {}
            for agent_name, agent_config in ordered_data["agents"].items():
                ordered_agents[agent_name] = order_dict(
                    agent_config, ["base", "swr_config", "runtime"]
                )
                if "base" in ordered_agents[agent_name]:
                    ordered_agents[agent_name]["base"] = order_dict(
                        ordered_agents[agent_name]["base"],
                        ["name", "entrypoint", "dependency_file", "region", "platform", "language", "base_image"]
                    )
                if "runtime" in ordered_agents[agent_name]:
                    ordered_agents[agent_name]["runtime"] = order_dict(
                        ordered_agents[agent_name]["runtime"],
                        ["invoke_config", "network_config", "identity_configuration", "observability", "artifact_source", "environment_variables", "tags"]
                    )
            ordered_data["agents"] = ordered_agents
        
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(ordered_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentArtsConfigList":
        """Create configuration from dictionary."""
        return cls.model_validate(data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(mode="json")

    def get_agent(self, name: Optional[str] = None) -> Optional[AgentArtsConfig]:
        """
        Get agent configuration by name.

        Args:
            name: Agent name. If None, returns the default agent.

        Returns:
            AgentArtsConfig if found, None otherwise.
        """
        if name is None:
            name = self.default_agent
        if name is None:
            return None
        return self.agents.get(name)

    def add_agent(self, name: str, config: AgentArtsConfig) -> None:
        """
        Add an agent configuration.

        Args:
            name: Agent name.
            config: Agent configuration.
        """
        self.agents[name] = config
        if self.default_agent is None:
            self.default_agent = name

    def remove_agent(self, name: str) -> bool:
        """
        Remove an agent configuration.

        Args:
            name: Agent name.

        Returns:
            True if removed, False if not found.
        """
        if name in self.agents:
            del self.agents[name]
            if self.default_agent == name:
                self.default_agent = next(iter(self.agents), None)
            return True
        return False

    def list_agents(self) -> List[str]:
        """
        List all agent names.

        Returns:
            List of agent names.
        """
        return list(self.agents.keys())
