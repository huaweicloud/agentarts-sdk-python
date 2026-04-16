"""Unit tests for deploy.py module"""

from unittest.mock import MagicMock, patch

from agentarts.toolkit.operations.runtime.deploy import (
    DeployMode,
    create_agentarts_runtime,
    deploy_project,
)


class TestDeployMode:
    """Tests for DeployMode enum."""

    def test_has_local_mode(self):
        """Has LOCAL mode."""
        assert DeployMode.LOCAL.value == "local"

    def test_has_cloud_mode(self):
        """Has CLOUD mode."""
        assert DeployMode.CLOUD.value == "cloud"


class TestCreateAgentartsRuntime:
    """Tests for create_agentarts_runtime() function."""

    @patch("agentarts.toolkit.operations.runtime.deploy.RuntimeClient")
    def test_creates_runtime_with_default_description(self, mock_client, tmp_path, monkeypatch):
        """Creates runtime with default description."""
        monkeypatch.chdir(tmp_path)

        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.create_or_update_agent.return_value = {
            "id": "agent-123",
            "latest_version": "v1",
        }

        result = create_agentarts_runtime(
            agent_name="test-agent",
            swr_image="swr.cn-north-4.myhuaweicloud.com/org/repo:latest",
            region="cn-north-4",
        )

        assert result is not None
        assert result["id"] == "agent-123"

    @patch("agentarts.toolkit.operations.runtime.deploy.RuntimeClient")
    def test_description_includes_toolkit_info(self, mock_client, tmp_path, monkeypatch):
        """Description includes AgentArts SDK Toolkit info."""
        monkeypatch.chdir(tmp_path)

        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.create_or_update_agent.return_value = {
            "id": "agent-123",
            "latest_version": "v1",
        }

        create_agentarts_runtime(
            agent_name="test-agent",
            swr_image="swr.cn-north-4.myhuaweicloud.com/org/repo:latest",
            region="cn-north-4",
        )

        call_args = mock_client_instance.create_or_update_agent.call_args
        assert "AgentArts SDK Toolkit" in call_args.kwargs["description"]

    @patch("agentarts.toolkit.operations.runtime.deploy.RuntimeClient")
    def test_uses_custom_description(self, mock_client, tmp_path, monkeypatch):
        """Uses custom description when provided."""
        monkeypatch.chdir(tmp_path)

        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.create_or_update_agent.return_value = {
            "id": "agent-123",
            "latest_version": "v1",
        }

        create_agentarts_runtime(
            agent_name="test-agent",
            swr_image="swr.cn-north-4.myhuaweicloud.com/org/repo:latest",
            region="cn-north-4",
            description="My custom description",
        )

        call_args = mock_client_instance.create_or_update_agent.call_args
        assert call_args.kwargs["description"] == "My custom description"


class TestDeployProject:
    """Tests for deploy_project() function."""

    @patch("agentarts.toolkit.operations.runtime.deploy.check_docker_available")
    @patch("agentarts.toolkit.operations.runtime.deploy.check_dockerfile_exists")
    def test_returns_false_when_no_config(self, mock_docker, mock_dockerfile, tmp_path, monkeypatch):
        """Returns False when no configuration file exists."""
        monkeypatch.chdir(tmp_path)

        result = deploy_project()

        assert result is False

    @patch("agentarts.toolkit.operations.runtime.deploy.check_docker_available")
    def test_returns_false_when_docker_not_available(self, mock_docker, tmp_path, monkeypatch):
        """Returns False when Docker is not available."""
        mock_docker.return_value = False

        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
      entrypoint: agent:app
      region: cn-north-4
    swr_config:
      organization: test-org
      repository: test-repo
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        monkeypatch.chdir(tmp_path)

        result = deploy_project()

        assert result is False

    @patch("agentarts.toolkit.operations.runtime.deploy.check_docker_available")
    @patch("agentarts.toolkit.operations.runtime.deploy.check_dockerfile_exists")
    @patch("agentarts.toolkit.operations.runtime.deploy.build_docker_image")
    @patch("agentarts.toolkit.operations.runtime.deploy.run_container")
    def test_local_mode_runs_container(self, mock_build, mock_run, mock_docker, mock_dockerfile, tmp_path, monkeypatch):
        """Local mode runs container directly."""
        mock_build.return_value = True
        mock_run.return_value = True
        mock_docker.return_value = True
        mock_dockerfile.return_value = True

        config_content = """
default_agent: test-agent
agents:
  test-agent:
    base:
      name: test-agent
      entrypoint: agent:app
      region: cn-north-4
    swr_config:
      organization: test-org
      repository: test-repo
    runtime:
      invoke_config:
        port: 8080
"""
        (tmp_path / ".agentarts_config.yaml").write_text(config_content)
        (tmp_path / "Dockerfile").write_text("FROM python:3.10-slim")
        monkeypatch.chdir(tmp_path)

        result = deploy_project(mode=DeployMode.LOCAL)

        assert result is True
