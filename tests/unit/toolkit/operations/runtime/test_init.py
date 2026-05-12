"""Unit tests for init.py module"""

from unittest.mock import patch

from agentarts.toolkit.operations.runtime.init import (
    TEMPLATES,
    create_agent_file,
    create_config_file,
    create_dockerfile,
    create_requirements_file,
    detect_platform,
    get_template_env_vars,
    init_project,
)


class TestDetectPlatform:
    """Tests for detect_platform() function."""

    def test_returns_valid_platform_format(self):
        """Returns a valid platform string format."""
        result = detect_platform()
        assert result in ("linux/amd64", "linux/arm64")

    @patch("platform.machine", return_value="x86_64")
    @patch("platform.system", return_value="Linux")
    def test_linux_amd64(self, mock_system, mock_machine):
        """Returns linux/amd64 for x86_64 Linux."""
        result = detect_platform()
        assert result == "linux/amd64"

    @patch("platform.machine", return_value="aarch64")
    @patch("platform.system", return_value="Linux")
    def test_linux_arm64(self, mock_system, mock_machine):
        """Returns linux/arm64 for aarch64 Linux."""
        result = detect_platform()
        assert result == "linux/arm64"

    @patch("platform.machine", return_value="amd64")
    @patch("platform.system", return_value="Windows")
    def test_windows_amd64(self, mock_system, mock_machine):
        """Returns linux/amd64 for amd64 Windows."""
        result = detect_platform()
        assert result == "linux/amd64"


class TestGetTemplateEnvVars:
    """Tests for get_template_env_vars() function."""

    def test_basic_template_has_no_env_vars(self):
        """Basic template has no required environment variables."""
        result = get_template_env_vars("basic")
        assert result == []

    def test_langgraph_template_has_env_vars(self):
        """LangGraph template has required environment variables."""
        result = get_template_env_vars("langgraph")
        assert len(result) == 3
        keys = [var["key"] for var in result]
        assert "OPENAI_API_KEY" in keys
        assert "OPENAI_MODEL_NAME" in keys
        assert "OPENAI_BASE_URL" in keys

    def test_langchain_template_has_env_vars(self):
        """LangChain template has required environment variables."""
        result = get_template_env_vars("langchain")
        assert len(result) == 3

    def test_google_adk_template_has_env_vars(self):
        """Google ADK template has required environment variables."""
        result = get_template_env_vars("google-adk")
        assert len(result) == 2
        keys = [var["key"] for var in result]
        assert "GOOGLE_API_KEY" in keys
        assert "GOOGLE_MODEL_NAME" in keys

    def test_unknown_template_returns_empty(self):
        """Unknown template returns empty list."""
        result = get_template_env_vars("unknown")
        assert result == []


class TestCreateDockerfile:
    """Tests for create_dockerfile() function."""

    def test_creates_dockerfile_with_region(self, tmp_path):
        """Creates Dockerfile with region environment variable."""
        create_dockerfile(tmp_path, "basic", region="cn-north-4")

        dockerfile_path = tmp_path / "Dockerfile"
        assert dockerfile_path.exists()

        content = dockerfile_path.read_text()
        assert "HUAWEICLOUD_SDK_REGION=cn-north-4" in content

    def test_creates_dockerfile_with_default_region(self, tmp_path):
        """Creates Dockerfile with default region when not specified."""
        create_dockerfile(tmp_path, "basic")

        dockerfile_path = tmp_path / "Dockerfile"
        content = dockerfile_path.read_text()
        assert "HUAWEICLOUD_SDK_REGION=cn-southwest-2" in content

    def test_dockerfile_contains_required_sections(self, tmp_path):
        """Dockerfile contains all required sections."""
        create_dockerfile(tmp_path, "basic", region="cn-north-4")

        content = (tmp_path / "Dockerfile").read_text()
        assert "FROM python:3.10-slim" in content
        assert "WORKDIR /app" in content
        assert "EXPOSE 8080" in content
        assert "agent" in content


class TestCreateConfigFile:
    """Tests for create_config_file() function."""

    def test_creates_config_file(self, tmp_path):
        """Creates config file with correct content."""
        create_config_file(
            project_path=tmp_path,
            name="test-agent",
            template="basic",
            region="cn-north-4",
            swr_org="test-org",
            swr_repo="test-repo",
        )

        config_path = tmp_path / ".agentarts_config.yaml"
        assert config_path.exists()

        content = config_path.read_text()
        assert "test-agent" in content
        assert "cn-north-4" in content
        assert "test-org" in content
        assert "test-repo" in content

    def test_config_uses_default_swr_repo(self, tmp_path):
        """Config uses agent_{name} as default SWR repo."""
        create_config_file(
            project_path=tmp_path,
            name="myagent",
            template="basic",
        )

        content = (tmp_path / ".agentarts_config.yaml").read_text()
        assert "agent_myagent" in content

    def test_config_includes_region(self, tmp_path):
        """Config includes specified region."""
        create_config_file(
            project_path=tmp_path,
            name="test-agent",
            template="basic",
            region="cn-east-3",
        )

        content = (tmp_path / ".agentarts_config.yaml").read_text()
        assert "cn-east-3" in content


class TestCreateAgentFile:
    """Tests for create_agent_file() function."""

    def test_creates_agent_file(self, tmp_path):
        """Creates agent.py file."""
        create_agent_file(tmp_path, "basic", "test-agent")

        agent_path = tmp_path / "agent.py"
        assert agent_path.exists()

    def test_fallback_to_basic_template(self, tmp_path):
        """Falls back to basic template for unknown template."""
        create_agent_file(tmp_path, "unknown-template", "test-agent")

        agent_path = tmp_path / "agent.py"
        assert agent_path.exists()


class TestCreateRequirementsFile:
    """Tests for create_requirements_file() function."""

    def test_creates_requirements_file(self, tmp_path):
        """Creates requirements.txt file."""
        create_requirements_file(tmp_path, "basic")

        req_path = tmp_path / "requirements.txt"
        assert req_path.exists()

    def test_requirements_contains_sdk(self, tmp_path):
        """Requirements contains agentarts-sdk."""
        create_requirements_file(tmp_path, "basic")

        content = (tmp_path / "requirements.txt").read_text()
        assert "agentarts-sdk" in content


class TestInitProject:
    """Tests for init_project() function."""

    def test_init_fails_when_directory_exists(self, tmp_path):
        """Init fails when target directory already exists."""
        existing_dir = tmp_path / "existing-project"
        existing_dir.mkdir()

        result = init_project(
            template="basic",
            name="existing-project",
            path=str(tmp_path),
        )

        assert result is False

    def test_init_creates_project_structure(self, tmp_path):
        """Init creates complete project structure."""
        result = init_project(
            template="basic",
            name="test-project",
            path=str(tmp_path),
            region="cn-north-4",
        )

        assert result is True

        project_path = tmp_path / "test-project"
        assert project_path.exists()
        assert (project_path / "agent.py").exists()
        assert (project_path / "requirements.txt").exists()
        assert (project_path / ".agentarts_config.yaml").exists()
        assert (project_path / "Dockerfile").exists()

    def test_init_with_custom_swr_settings(self, tmp_path):
        """Init with custom SWR organization and repository."""
        result = init_project(
            template="basic",
            name="test-project",
            path=str(tmp_path),
            swr_org="custom-org",
            swr_repo="custom-repo",
        )

        assert result is True

        config_content = (tmp_path / "test-project" / ".agentarts_config.yaml").read_text()
        assert "custom-org" in config_content
        assert "custom-repo" in config_content


class TestTemplates:
    """Tests for template constants."""

    def test_templates_dict_contains_expected_templates(self):
        """TEMPLATES dict contains expected template types."""
        assert "basic" in TEMPLATES
        assert "langchain" in TEMPLATES
        assert "langgraph" in TEMPLATES
        assert "google-adk" in TEMPLATES
