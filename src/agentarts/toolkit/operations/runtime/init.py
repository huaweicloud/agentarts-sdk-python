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
from agentarts.toolkit.utils.runtime.config import detect_arch
from agentarts.toolkit.utils.swr_org import generate_swr_org_name
from agentarts.toolkit.utils.templates.manager import template_manager

console = Console()

TEMPLATES = {
    "basic": "basic",
    "langchain": "langchain",
    "langgraph": "langgraph",
    "google-adk": "google-adk",
    "java-basic": "java-basic",
    "java-agentscope": "java-agentscope",
}

# Templates that generate a Java (Maven/JDK17) project instead of a Python one.
JAVA_TEMPLATES = {"java-basic", "java-agentscope"}


def is_java_template(template: str) -> bool:
    """Return True if the template generates a Java project."""
    return template in JAVA_TEMPLATES


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

    # Unknown architecture: default to linux/arm64 (the backend is
    # predominantly arm).
    return "linux/arm64"


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

    java_project = is_java_template(template)

    create_agent_file(project_path, template, name)
    if java_project:
        create_pom_file(project_path, template, name)
    else:
        create_requirements_file(project_path, template)
    create_config_file(project_path, name, template, region, swr_org, swr_repo)
    create_dockerfile(project_path, template, name, region)

    echo_success(f"Project '{name}' created successfully!")

    if java_project:
        echo_info(
            "Project structure",
            f"[cyan]{name}/[/cyan]\n"
            f"  ├── [green].agentarts_config.yaml[/green]  # Configuration\n"
            f"  ├── [green]pom.xml[/green]                # Maven build file\n"
            f"  ├── [green]Dockerfile[/green]             # Docker build file\n"
            f"  └── [green]src/main/java/com/example/Agent.java[/green]  # Agent implementation"
        )
    else:
        echo_info(
            "Project structure",
            f"[cyan]{name}/[/cyan]\n"
            f"  ├── [green].agentarts_config.yaml[/green] # Configuration\n"
            f"  ├── [green]agent.py[/green]              # Agent implementation\n"
            f"  ├── [green]Dockerfile[/green]            # Docker build file\n"
            f"  └── [green]requirements.txt[/green]      # Dependencies"
        )

    console.print()
    console.print("[bold green]Next Steps - How to Deploy Agent[/bold green]")
    console.print()

    if java_project:
        echo_step(1, "Navigate to project directory")
        console.print(f"    [cyan]cd {name}[/cyan]")

        echo_step(2, "Build and run locally (requires JDK 17 + Maven)")
        console.print("    [cyan]agentarts dev[/cyan]")

        echo_step(3, "Edit src/main/java/com/example/Agent.java to implement your agent logic")

        echo_step(4, "Edit .agentarts_config.yaml and run config command (optional)")
        console.print("    [dim]Modify configuration as needed, then:[/dim]")
        console.print("    [cyan]agentarts config[/cyan]")

        echo_step(5, "Deploy to Huawei Cloud")
        console.print("    [cyan]agentarts deploy[/cyan]")
    else:
        echo_step(1, "Navigate to project directory")
        console.print(f"    [cyan]cd {name}[/cyan]")

        echo_step(2, "Install dependencies")
        console.print("    [cyan]pip install -r requirements.txt[/cyan]")

        echo_step(3, "Edit agent.py to implement your agent logic")

        echo_step(4, "Edit .agentarts_config.yaml and run config command (optional)")
        console.print("    [dim]Modify configuration as needed, then:[/dim]")
        console.print("    [cyan]agentarts config[/cyan]")

        echo_step(5, "Deploy to Huawei Cloud")
        console.print("    [cyan]agentarts deploy[/cyan]")

    return True


def create_agent_file(project_path: Path, template: str, name: str) -> None:
    """Create agent file based on template."""
    fallback = "java-basic" if is_java_template(template) else "basic"
    try:
        if is_java_template(template):
            agent_content = template_manager.render_template(template, "Agent.java.j2", context={"name": name})
        else:
            agent_content = template_manager.render_agent_template(template, name)
    except FileNotFoundError:
        console.print(f"[yellow]Warning: Template '{template}' not found, using {fallback} template[/yellow]")
        if is_java_template(template):
            agent_content = template_manager.render_template(fallback, "Agent.java.j2", context={"name": name})
        else:
            agent_content = template_manager.render_agent_template(fallback, name)

    if is_java_template(template):
        agent_path = project_path / "src" / "main" / "java" / "com" / "example" / "Agent.java"
        agent_path.parent.mkdir(parents=True, exist_ok=True)
        agent_path.write_text(agent_content, encoding="utf-8")
        echo_key_value("Created", "src/main/java/com/example/Agent.java")
    else:
        agent_path = project_path / "agent.py"
        agent_path.write_text(agent_content, encoding="utf-8")
        echo_key_value("Created", "agent.py")


def create_pom_file(project_path: Path, template: str, name: str) -> None:
    """Create Maven pom.xml for a Java project."""
    try:
        pom_content = template_manager.render_template(template, "pom.xml.j2", context={"name": name})
    except FileNotFoundError:
        console.print(f"[yellow]Warning: Template '{template}' not found, using java-basic template[/yellow]")
        pom_content = template_manager.render_template("java-basic", "pom.xml.j2", context={"name": name})

    pom_path = project_path / "pom.xml"
    pom_path.write_text(pom_content, encoding="utf-8")
    echo_key_value("Created", "pom.xml")


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
    actual_swr_org = swr_org or generate_swr_org_name(region=actual_region)
    actual_swr_repo = swr_repo or f"agent_{name}"
    detected_platform = detect_platform()
    detected_arch = detect_arch()

    env_vars = get_template_env_vars(template)

    env_vars_yaml = ""
    for var in env_vars:
        env_vars_yaml += f'\n        - key: {var["key"]}\n          value: null  # {var["description"]}'

    if is_java_template(template):
        entrypoint = "com.example.Agent"
        dependency_file = "pom.xml"
        language = "java17"
        base_image = "eclipse-temurin:17-jre"
    else:
        entrypoint = "agent:app"
        dependency_file = "requirements.txt"
        language = "python3"
        base_image = "python:3.10-slim"

    config_content = f"""# AgentArts Configuration
# Generated by 'agentarts init' command

default_agent: {name}

agents:
  {name}:
    base:
      name: {name}
      entrypoint: {entrypoint}
      dependency_file: {dependency_file}
      platform: {detected_platform}
      language: {language}
      base_image: {base_image}
      region: {actual_region}

    swr_config:
      organization: {actual_swr_org}
      repository: {actual_swr_repo}
      organization_auto_create: true
      repository_auto_create: true

    runtime:
      arch: {detected_arch.value}
      agent_gateway_id: null
      invoke_config:
        protocol: HTTP
        port: 8080
        file_transfer_config:
          enabled: false
        url_match_type: ACCURATE_MATCH

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
        url: null  # Auto-generated during deploy from swr_config
        swr_instance_id: null  # UUID format, optional
        commands: []

      storage_config:
        sfs_turbo:
          sfs_turbo_id: null  # UUID format, required when using SFS Turbo
          sfs_path: null
          mount_path: null    # required when using SFS Turbo
          read_only: false
        session_storage:
          mount_path: null  # Session storage mount path in the container

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
        "java-basic": [],
        "java-agentscope": [
            {
                "key": "OPENAI_API_KEY",
                "description": "OpenAI API key for LLM access",
            },
            {
                "key": "OPENAI_MODEL_NAME",
                "description": "Model name (default: gpt-4o, e.g., gpt-4-turbo)",
            },
            {
                "key": "OPENAI_BASE_URL",
                "description": "Custom API endpoint URL (optional, for OpenAI-compatible APIs)",
            },
        ],
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


def create_dockerfile(
    project_path: Path, template: str, name: str, region: str | None = None
) -> None:
    """Create Dockerfile for the project."""
    from agentarts.toolkit.utils.templates.docker import (
        render_dockerfile,
        render_java_dockerfile,
    )

    actual_region = region or "cn-southwest-2"

    if is_java_template(template):
        dockerfile_content = render_java_dockerfile(name=name, port=8080, region=actual_region)
    else:
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
