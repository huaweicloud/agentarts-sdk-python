"""Unit tests for config.py module"""

from unittest.mock import patch

from agentarts.toolkit.operations.runtime.config import (
    CONFIG_FILE_NAME,
    add_agent,
    detect_arch,
    detect_dependency_file,
    detect_platform,
    get_agent,
    get_config_file_path,
    get_config_value,
    list_agents,
    load_config,
    remove_agent,
    save_config,
    set_config_value,
    set_default_agent,
)
from agentarts.toolkit.utils.runtime.config import (
    AgentArtsConfig,
    AgentArtsConfigList,
    ArchType,
    AuthConfig,
    BaseConfig,
    CustomJWTAuthConfig,
    InboundIdentityConfig,
    SfsTurboConfig,
    StorageConfig,
)


class TestDetectPlatform:
    """Tests for detect_platform() function."""

    def test_returns_valid_platform_format(self):
        """Returns a valid platform string format."""
        result = detect_platform()
        assert result in ("linux/amd64", "linux/arm64")


class TestDetectArch:
    """Tests for detect_arch() function."""

    def test_returns_valid_arch_type(self):
        """Returns a valid ArchType value."""
        result = detect_arch()
        assert result in (ArchType.X86_64, ArchType.ARM64)

    @patch("platform.machine", return_value="arm64")
    def test_detects_arm64_for_arm64_machine(self, mock_machine):
        """Returns ARM64 when platform.machine() is arm64."""
        result = detect_arch()
        assert result == ArchType.ARM64

    @patch("platform.machine", return_value="aarch64")
    def test_detects_arm64_for_aarch64_machine(self, mock_machine):
        """Returns ARM64 when platform.machine() is aarch64."""
        result = detect_arch()
        assert result == ArchType.ARM64

    @patch("platform.machine", return_value="x86_64")
    def test_detects_x86_64_for_x86_64_machine(self, mock_machine):
        """Returns X86_64 when platform.machine() is x86_64."""
        result = detect_arch()
        assert result == ArchType.X86_64

    @patch("platform.machine", return_value="AMD64")
    def test_detects_x86_64_for_uppercase_amd64(self, mock_machine):
        """Returns X86_64 for non-arm machine strings (case-insensitive)."""
        result = detect_arch()
        assert result == ArchType.X86_64


class TestDetectDependencyFile:
    """Tests for detect_dependency_file() function."""

    def test_detects_requirements_txt(self, tmp_path, monkeypatch):
        """Detects requirements.txt when it exists."""
        (tmp_path / "requirements.txt").write_text("fastapi")
        monkeypatch.chdir(tmp_path)

        result = detect_dependency_file()
        assert result == "requirements.txt"

    def test_detects_pyproject_toml(self, tmp_path, monkeypatch):
        """Detects pyproject.toml when requirements.txt doesn't exist."""
        (tmp_path / "pyproject.toml").write_text("[project]")
        monkeypatch.chdir(tmp_path)

        result = detect_dependency_file()
        assert result == "pyproject.toml"

    def test_defaults_to_requirements_txt(self, tmp_path, monkeypatch):
        """Defaults to requirements.txt when neither exists."""
        monkeypatch.chdir(tmp_path)

        result = detect_dependency_file()
        assert result == "requirements.txt"


class TestGetConfigFilePath:
    """Tests for get_config_file_path() function."""

    def test_returns_correct_path(self, tmp_path, monkeypatch):
        """Returns correct config file path."""
        monkeypatch.chdir(tmp_path)

        result = get_config_file_path()

        assert result == tmp_path / CONFIG_FILE_NAME


class TestLoadConfig:
    """Tests for load_config() function."""

    def test_loads_existing_config(self, tmp_path, monkeypatch):
        """Loads existing configuration file."""
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
"""
        (tmp_path / CONFIG_FILE_NAME).write_text(config_content)
        monkeypatch.chdir(tmp_path)

        config = load_config()

        assert config.default_agent == "test-agent"
        assert "test-agent" in config.agents

    def test_returns_empty_config_when_file_not_exists(self, tmp_path, monkeypatch):
        """Returns empty config when file doesn't exist."""
        monkeypatch.chdir(tmp_path)

        config = load_config()

        assert config.default_agent is None
        assert config.agents == {}


class TestSaveConfig:
    """Tests for save_config() function."""

    def test_saves_config_to_file(self, tmp_path, monkeypatch):
        """Saves configuration to file."""
        monkeypatch.chdir(tmp_path)

        config = AgentArtsConfigList(
            default_agent="test-agent",
            agents={
                "test-agent": AgentArtsConfig(
                    base=BaseConfig(name="test-agent"),
                )
            }
        )

        result = save_config(config)

        assert result is True
        assert (tmp_path / CONFIG_FILE_NAME).exists()

    def test_creates_config_file_if_not_exists(self, tmp_path, monkeypatch):
        """Creates config file if it doesn't exist."""
        monkeypatch.chdir(tmp_path)

        config = AgentArtsConfigList()
        save_config(config)

        assert (tmp_path / CONFIG_FILE_NAME).exists()


class TestAddAgent:
    """Tests for add_agent() function."""

    def test_adds_new_agent(self, tmp_path, monkeypatch):
        """Adds a new agent configuration."""
        monkeypatch.chdir(tmp_path)

        result = add_agent(
            name="new-agent",
            entrypoint="agent:app",
            region="cn-north-4",
        )

        assert result is True

        config = load_config()
        assert "new-agent" in config.agents

    def test_adds_agent_with_swr_config(self, tmp_path, monkeypatch):
        """Adds agent with SWR configuration."""
        monkeypatch.chdir(tmp_path)

        result = add_agent(
            name="test-agent",
            entrypoint="agent:app",
            swr_organization="test-org",
            swr_repository="test-repo",
        )

        assert result is True

        config = load_config()
        agent = config.get_agent("test-agent")
        assert agent.swr_config.organization == "test-org"
        assert agent.swr_config.repository == "test-repo"

    def test_adds_agent_includes_storage_config_block(self, tmp_path, monkeypatch):
        """Config-generated YAML includes the storage_config / sfs_turbo block."""
        monkeypatch.chdir(tmp_path)

        result = add_agent(name="test-agent", entrypoint="agent:app", region="cn-north-4")
        assert result is True

        content = (tmp_path / CONFIG_FILE_NAME).read_text()
        assert "storage_config:" in content
        assert "sfs_turbo:" in content
        assert "sfs_turbo_id:" in content
        assert "mount_path:" in content

    def test_uses_default_swr_repo_as_agent_prefix(self, tmp_path, monkeypatch):
        """Uses agent_{name} as default SWR repository."""
        monkeypatch.chdir(tmp_path)

        add_agent(
            name="myagent",
            entrypoint="agent:app",
        )

        config = load_config()
        agent = config.get_agent("myagent")
        assert agent.swr_config.repository is None

    def test_sets_as_default_when_first_agent(self, tmp_path, monkeypatch):
        """Sets as default when it's the first agent."""
        monkeypatch.chdir(tmp_path)

        add_agent(name="first-agent", entrypoint="agent:app")

        config = load_config()
        assert config.default_agent == "first-agent"

    def test_updates_existing_agent(self, tmp_path, monkeypatch):
        """Updates existing agent configuration."""
        monkeypatch.chdir(tmp_path)

        add_agent(
            name="test-agent",
            entrypoint="agent:app",
            region="cn-north-4",
        )

        add_agent(
            name="test-agent",
            entrypoint="agent:new_app",
            region="cn-southwest-2",
        )

        config = load_config()
        agent = config.get_agent("test-agent")
        assert agent.base.entrypoint == "agent:new_app"

    @patch("platform.machine", return_value="arm64")
    def test_sets_arch_from_detected_environment_arm64(self, mock_machine, tmp_path, monkeypatch):
        """Sets arch to arm64 when running on an arm64 machine."""
        monkeypatch.chdir(tmp_path)

        add_agent(name="test-agent", entrypoint="agent:app")

        config = load_config()
        agent = config.get_agent("test-agent")
        assert agent.base.arch == ArchType.ARM64

    @patch("platform.machine", return_value="x86_64")
    def test_sets_arch_from_detected_environment_x86_64(self, mock_machine, tmp_path, monkeypatch):
        """Sets arch to x86_64 when running on an x86_64 machine."""
        monkeypatch.chdir(tmp_path)

        add_agent(name="test-agent", entrypoint="agent:app")

        config = load_config()
        agent = config.get_agent("test-agent")
        assert agent.base.arch == ArchType.X86_64


class TestRemoveAgent:
    """Tests for remove_agent() function."""

    def test_removes_existing_agent(self, tmp_path, monkeypatch):
        """Removes an existing agent."""
        monkeypatch.chdir(tmp_path)

        add_agent(name="to-remove", entrypoint="agent:app")

        result = remove_agent("to-remove")

        assert result is True
        config = load_config()
        assert "to-remove" not in config.agents

    def test_returns_false_for_nonexistent_agent(self, tmp_path, monkeypatch):
        """Returns False for non-existent agent."""
        monkeypatch.chdir(tmp_path)

        result = remove_agent("nonexistent")

        assert result is False


class TestSetDefaultAgent:
    """Tests for set_default_agent() function."""

    def test_sets_default_agent(self, tmp_path, monkeypatch):
        """Sets default agent."""
        monkeypatch.chdir(tmp_path)

        add_agent(name="agent1", entrypoint="agent:app")
        add_agent(name="agent2", entrypoint="agent:app")

        result = set_default_agent("agent2")

        assert result is True
        config = load_config()
        assert config.default_agent == "agent2"

    def test_returns_false_for_nonexistent_agent(self, tmp_path, monkeypatch):
        """Returns False for non-existent agent."""
        monkeypatch.chdir(tmp_path)

        result = set_default_agent("nonexistent")

        assert result is False


class TestGetAgent:
    """Tests for get_agent() function."""

    def test_gets_agent_by_name(self, tmp_path, monkeypatch):
        """Gets agent by name."""
        monkeypatch.chdir(tmp_path)

        add_agent(name="test-agent", entrypoint="agent:app")

        agent = get_agent("test-agent")

        assert agent is not None
        assert agent.base.name == "test-agent"

    def test_gets_default_agent_when_name_is_none(self, tmp_path, monkeypatch):
        """Gets default agent when name is None."""
        monkeypatch.chdir(tmp_path)

        add_agent(name="default-agent", entrypoint="agent:app")
        set_default_agent("default-agent")

        agent = get_agent()

        assert agent is not None
        assert agent.base.name == "default-agent"


class TestSetConfigValue:
    """Tests for set_config_value() function."""

    def test_sets_base_region(self, tmp_path, monkeypatch):
        """Sets base.region configuration."""
        monkeypatch.chdir(tmp_path)

        add_agent(name="test-agent", entrypoint="agent:app")

        result = set_config_value("base.region", "cn-east-3", "test-agent")

        assert result is True
        agent = get_agent("test-agent")
        assert agent.base.region == "cn-east-3"

    def test_sets_swr_config(self, tmp_path, monkeypatch):
        """Sets swr_config.organization configuration."""
        monkeypatch.chdir(tmp_path)

        add_agent(name="test-agent", entrypoint="agent:app")

        result = set_config_value("swr_config.organization", "new-org", "test-agent")

        assert result is True
        agent = get_agent("test-agent")
        assert agent.swr_config.organization == "new-org"

    def test_renames_agent_via_base_name(self, tmp_path, monkeypatch):
        """Renames agent when setting base.name to a different value."""
        monkeypatch.chdir(tmp_path)

        add_agent(name="old-name", entrypoint="agent:app")
        set_default_agent("old-name")

        result = set_config_value("base.name", "new-name", "old-name")

        assert result is True
        config = load_config()
        assert "new-name" in config.agents
        assert "old-name" not in config.agents
        assert config.default_agent == "new-name"


class TestGetConfigValue:
    """Tests for get_config_value() function."""

    def test_gets_base_region(self, tmp_path, monkeypatch):
        """Gets base.region configuration."""
        monkeypatch.chdir(tmp_path)

        add_agent(name="test-agent", entrypoint="agent:app", region="cn-north-4")

        result = get_config_value("base.region", "test-agent")

        assert result is True

    def test_returns_false_for_nonexistent_key(self, tmp_path, monkeypatch):
        """Returns False for non-existent key."""
        monkeypatch.chdir(tmp_path)

        add_agent(name="test-agent", entrypoint="agent:app")

        result = get_config_value("nonexistent.key", "test-agent")

        assert result is False


class TestListAgents:
    """Tests for list_agents() function."""

    def test_lists_all_agents(self, tmp_path, monkeypatch):
        """Lists all configured agents."""
        monkeypatch.chdir(tmp_path)

        add_agent(name="agent1", entrypoint="agent:app")
        add_agent(name="agent2", entrypoint="agent:app")

        agents = list_agents()

        assert "agent1" in agents
        assert "agent2" in agents


class TestCustomJWTAuthConfigIsEmpty:
    """Tests for CustomJWTAuthConfig.is_empty() method."""

    def test_is_empty_when_all_fields_default(self):
        """Returns True when all fields have default values."""
        config = CustomJWTAuthConfig()
        assert config.is_empty() is True

    def test_is_not_empty_when_discovery_url_set(self):
        """Returns False when discovery_url is set."""
        config = CustomJWTAuthConfig(discovery_url="https://example.com")
        assert config.is_empty() is False

    def test_is_not_empty_when_allowed_audience_set(self):
        """Returns False when allowed_audience is set."""
        config = CustomJWTAuthConfig(allowed_audience=["audience1"])
        assert config.is_empty() is False


class TestAuthConfigIsEmpty:
    """Tests for AuthConfig.is_empty() method."""

    def test_is_empty_when_all_fields_default(self):
        """Returns True when all fields have default values."""
        config = AuthConfig()
        assert config.is_empty() is True

    def test_is_not_empty_when_custom_jwt_has_values(self):
        """Returns False when custom_jwt has values."""
        config = AuthConfig(
            custom_jwt=CustomJWTAuthConfig(discovery_url="https://example.com")
        )
        assert config.is_empty() is False


class TestInboundIdentityConfigToDict:
    """Tests for InboundIdentityConfig.to_dict() method."""

    def test_excludes_empty_authorizer_configuration(self):
        """Excludes authorizer_configuration when empty."""
        config = InboundIdentityConfig(
            authorizer_type="IAM",
            authorizer_configuration=AuthConfig(),
        )

        result = config.to_dict()

        assert result["authorizer_type"] == "IAM"
        assert "authorizer_configuration" not in result

    def test_includes_authorizer_configuration_when_not_empty(self):
        """Includes authorizer_configuration when not empty."""
        config = InboundIdentityConfig(
            authorizer_type="CUSTOM_JWT",
            authorizer_configuration=AuthConfig(
                custom_jwt=CustomJWTAuthConfig(discovery_url="https://example.com")
            ),
        )

        result = config.to_dict()

        assert "authorizer_configuration" in result


class TestStorageConfig:
    """Tests for StorageConfig / SfsTurboConfig models."""

    def test_sfs_turbo_to_dict_excludes_none(self):
        """to_dict excludes None fields but keeps read_only."""
        cfg = SfsTurboConfig(
            sfs_turbo_id="12345678-1234-1234-1234-123456789012",
            mount_path="/data",
        )
        result = cfg.to_dict()

        assert result == {
            "sfs_turbo_id": "12345678-1234-1234-1234-123456789012",
            "mount_path": "/data",
            "read_only": False,
        }

    def test_sfs_turbo_empty_to_dict_keeps_read_only(self):
        """An all-default SfsTurboConfig keeps read_only (mirrors NetworkConfig/network_mode)."""
        assert SfsTurboConfig().to_dict() == {"read_only": False}

    def test_storage_config_to_dict_nested(self):
        """StorageConfig serializes the nested sfs_turbo block."""
        cfg = StorageConfig(
            sfs_turbo=SfsTurboConfig(
                sfs_turbo_id="12345678-1234-1234-1234-123456789012",
                sfs_path="/share/sub",
                mount_path="/data",
                read_only=True,
            )
        )
        result = cfg.to_dict()

        assert result == {
            "sfs_turbo": {
                "sfs_turbo_id": "12345678-1234-1234-1234-123456789012",
                "sfs_path": "/share/sub",
                "mount_path": "/data",
                "read_only": True,
            }
        }

    def test_storage_config_default_to_dict_has_read_only(self):
        """A default StorageConfig (sfs_turbo=SfsTurboConfig()) keeps read_only."""
        assert StorageConfig().to_dict() == {"sfs_turbo": {"read_only": False}}

    def test_invalid_sfs_turbo_id_rejected(self):
        """A non-UUID sfs_turbo_id is rejected by validation."""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SfsTurboConfig(sfs_turbo_id="not-a-uuid", mount_path="/data")

    def test_runtime_config_has_storage_config_field(self):
        """AgentArtsRuntimeConfig exposes a storage_config field with a default
        nested SfsTurboConfig (mirrors network_config/vpc_config), so the block
        is present in config-generated YAML even when unset."""
        from agentarts.toolkit.utils.runtime.config import AgentArtsRuntimeConfig

        runtime = AgentArtsRuntimeConfig()
        assert runtime.storage_config is not None
        assert runtime.storage_config.sfs_turbo is not None
        assert runtime.storage_config.sfs_turbo.sfs_turbo_id is None
        assert runtime.storage_config.sfs_turbo.mount_path is None
        assert runtime.storage_config.sfs_turbo.read_only is False
