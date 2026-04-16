"""Init operation implementation"""

import platform as platform_module
from pathlib import Path

from rich.console import Console

from agentarts.toolkit.utils.common import (
    echo_info,
    echo_key_value,
    echo_step,
    echo_success,
)
from agentarts.toolkit.utils.templates.manager import template_manager

console = Console()

TEMPLATES = {
    "basic": "basic",
    "langchain": "langchain",
    "langgraph": "langgraph",
    "google-adk": "google-adk",
}


def detect_platform() -> str:
    """
    Detect the current platform architecture.

    Returns:
        str: Platform string (e.g., 'linux/amd64', 'linux/arm64')
    """
    machine = platform_module.machine().lower()
    system = platform_module.system().lower()

    if system in {"linux", "darwin"}:
        if machine in ("aarch64", "arm64"):
            return "linux/arm64"
        if machine in ("x86_64", "amd64"):
            return "linux/amd64"
    elif system == "windows":
        if machine in ("amd64", "x86_64"):
            return "linux/amd64"
        if machine in ("arm64", "aarch64"):
            return "linux/arm64"

    return "linux/amd64"


def init_project(
    template: str,
    name: str,
    path: str,
    region: str | None = None,
    swr_org: str | None = None,
    swr_repo: str | None = None,
) -> bool:
    """
    Initialize a new project.

    Args:
        template: Template type
        name: Project name
        path: Project path
        region: Huawei Cloud region
        swr_org: SWR organization
        swr_repo: SWR repository

    Returns:
        bool: True if successful, False otherwise
    """
    project_path = Path(path) / name

    if project_path.exists():
        console.print(f"[red]Error: Directory '{name}' already exists[/red]")
        return False

    try:
        project_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        console.print(f"[red]Error creating directory: {e}[/red]")
        return False

    create_agent_file(project_path, template, name)
    create_requirements_file(project_path, template)
    create_config_file(project_path, name, template, region, swr_org, swr_repo)
    create_dockerfile(project_path, template, region)

    echo_success(f"Project '{name}' created successfully!")

    echo_info(
        "Project structure",
        f"[cyan]{name}/[/cyan]\n"
        f"  ├── [green]agent.py[/green]              # Agent implementation\n"
        f"  ├── [green]requirements.txt[/green]      # Dependencies\n"
        f"  ├── [green].agentarts_config.yaml[/green] # Configuration\n"
        f"  └── [green]Dockerfile[/green]            # Docker build file"
    )

    console.print()
    echo_step(1, "Navigate to project directory")
    console.print(f"    [cyan]cd {name}[/cyan]")

    echo_step(2, "Install dependencies")
    console.print("    [cyan]pip install -r requirements.txt[/cyan]")

    echo_step(3, "Edit agent.py to implement your agent logic")

    echo_step(4, "Deploy to Huawei Cloud")
    console.print("    [cyan]agentarts deploy[/cyan]")

    return True


def create_agent_file(project_path: Path, template: str, name: str) -> None:
    """Create agent file based on template."""
    try:
        agent_content = template_manager.render_agent_template(template, name)
    except FileNotFoundError:
        console.print(f"[yellow]Warning: Template '{template}' not found, using basic template[/yellow]")
        agent_content = template_manager.render_agent_template("basic", name)

    agent_path = project_path / "agent.py"
    agent_path.write_text(agent_content, encoding="utf-8")
    echo_key_value("Created", "agent.py")


def create_requirements_file(project_path: Path, template: str) -> None:
    """Create requirements file based on template."""
    try:
        requirements = template_manager.render_requirements_template(template)
    except FileNotFoundError:
        console.print(f"[yellow]Warning: Template '{template}' not found, using basic template[/yellow]")
        requirements = template_manager.render_requirements_template("basic")

    requirements_path = project_path / "requirements.txt"
    requirements_path.write_text(requirements, encoding="utf-8")
    echo_key_value("Created", "requirements.txt")


def create_config_file(
    project_path: Path,
    name: str,
    template: str,
    region: str | None = None,
    swr_org: str | None = None,
    swr_repo: str | None = None,
) -> None:
    """Create .agentarts_config.yaml configuration file."""
    actual_region = region or "cn-southwest-2"
    actual_swr_org = swr_org or "agentarts-org"
    actual_swr_repo = swr_repo or f"agent_{name}"
    detected_platform = detect_platform()

    artifact_url = f"swr.{actual_region}.myhuaweicloud.com/{actual_swr_org}/{actual_swr_repo}:latest"

    env_vars = get_template_env_vars(template)

    env_vars_yaml = ""
    for var in env_vars:
        env_vars_yaml += f'\n        - key: {var["key"]}\n          value: null  # {var["description"]}'

    config_content = f"""# AgentArts Configuration
# Generated by 'agentarts init' command

default_agent: {name}

agents:
  {name}:
    base:
      name: {name}
      entrypoint: agent:app
      dependency_file: requirements.txt
      platform: {detected_platform}
      language: python3
      base_image: python:3.10-slim
      region: {actual_region}

    swr_config:
      organization: {actual_swr_org}
      repository: {actual_swr_repo}
      organization_auto_create: true
      repository_auto_create: true

    runtime:
      invoke_config:
        protocol: HTTP
        port: 8080

      network_config:
        network_mode: PUBLIC
        vpc_config:
          vpc_id: null
          subnet_id: null
          security_group_id: []

      identity_configuration:
        authorizer_type: IAM
        authorizer_configuration:
          custom_jwt:
            discovery_url: null
            allowed_audience: []
            allowed_clients: []
            allowed_scopes: []
          key_auth:
            api_keys: []

      observability:
        tracing:
          enabled: false
        metrics:
          enabled: false
        logs:
          enabled: false

      artifact_source:
        url: {artifact_url}
        commands: []

      environment_variables:{env_vars_yaml}

      tags: []
"""

    config_path = project_path / ".agentarts_config.yaml"
    config_path.write_text(config_content, encoding="utf-8")
    echo_key_value("Created", ".agentarts_config.yaml")


def get_template_env_vars(template: str) -> list[dict[str, str]]:
    """Get required environment variables for a template."""
    template_env_vars = {
        "basic": [],
        "langgraph": [
            {
                "key": "OPENAI_API_KEY",
                "description": "OpenAI API key for LLM access",
            },
            {
                "key": "OPENAI_MODEL_NAME",
                "description": "Model name (default: gpt-4o-mini, e.g., gpt-4o, gpt-4-turbo)",
            },
            {
                "key": "OPENAI_BASE_URL",
                "description": "Custom API endpoint URL (optional, for OpenAI-compatible APIs)",
            },
        ],
        "langchain": [
            {
                "key": "OPENAI_API_KEY",
                "description": "OpenAI API key for LLM access",
            },
            {
                "key": "OPENAI_MODEL_NAME",
                "description": "Model name (default: gpt-4o-mini, e.g., gpt-4o, gpt-4-turbo)",
            },
            {
                "key": "OPENAI_BASE_URL",
                "description": "Custom API endpoint URL (optional, for OpenAI-compatible APIs)",
            },
        ],
        "google-adk": [
            {
                "key": "GOOGLE_API_KEY",
                "description": "Google API key for Gemini access",
            },
            {
                "key": "GOOGLE_MODEL_NAME",
                "description": "Model name (default: gemini-2.0-flash, e.g., gemini-1.5-pro)",
            },
        ],
    }
    return template_env_vars.get(template, [])


def create_dockerfile(project_path: Path, template: str, region: str | None = None) -> None:
    """Create Dockerfile for the project."""
    from agentarts.toolkit.utils.templates.docker import render_dockerfile

    actual_region = region or "cn-southwest-2"
    dockerfile_content = render_dockerfile(
        base_image="python:3.10-slim",
        dependency_file="requirements.txt",
        entrypoint="agent:app",
        port=8080,
        region=actual_region,
    )

    dockerfile_path = project_path / "Dockerfile"
    dockerfile_path.write_text(dockerfile_content, encoding="utf-8")
    echo_key_value("Created", "Dockerfile")
