"""Init operation implementation"""

from pathlib import Path

from rich.console import Console

console = Console()

TEMPLATES = {
    "basic": "basic_agent",
    "langchain": "langchain_agent",
    "langgraph": "langgraph_agent",
    "autogen": "autogen_agent",
    "crewai": "crewai_agent",
}


def init_project(template: str, name: str, path: str) -> bool:
    """
    Initialize a new project.

    Args:
        template: Template type
        name: Project name
        path: Project path

    Returns:
        True if successful, False otherwise
    """
    project_path = Path(path) / name

    if project_path.exists():
        console.print(f"[red]Error: Directory '{name}' already exists[/red]")
        return False

    project_path.mkdir(parents=True, exist_ok=True)

    create_config_file(project_path, name)
    create_agent_file(project_path, template)
    create_requirements_file(project_path, template)

    console.print(f"\n[green]Success:[/green] Project '{name}' created successfully!")
    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  cd {name}")
    console.print("  pip install -e .")
    console.print("  agentarts dev")

    return True


def create_config_file(project_path: Path, name: str) -> None:
    """Create configuration file."""
    config_content = f"""# agentarts.yaml
project:
  name: {name}
  version: 1.0.0
  description: AgentArts Agent Project

runtime:
  region: cn-north-4
  environment: development

memory:
  short_term:
    enabled: true
    max_size: 100
  long_term:
    enabled: true
    vector_store: huaweicloud_vector_db

tools:
  code_interpreter:
    enabled: true
    timeout: 30

server:
  host: 0.0.0.0
  port: 8000

logging:
  level: INFO
"""

    config_path = project_path / "agentarts.yaml"
    config_path.write_text(config_content, encoding="utf-8")


def create_agent_file(project_path: Path, template: str) -> None:
    """Create agent file."""
    agent_content = '''"""Agent implementation"""

from agentarts import AgentRuntime, Context


class MyAgent:
    """Custom Agent implementation"""

    async def run(self, context: Context):
        """Run the agent"""
        query = context.get("query", "")

        # TODO: Implement your agent logic here

        return {
            "response": f"Processed: {query}",
            "status": "success"
        }


def create_agent():
    """Create agent instance"""
    return MyAgent()


def create_runtime(config: dict):
    """Create runtime instance"""
    return AgentRuntime(config=config)
'''

    agent_path = project_path / "agent.py"
    agent_path.write_text(agent_content, encoding="utf-8")


def create_requirements_file(project_path: Path, template: str) -> None:
    """Create requirements file."""
    requirements = """huaweicloud-agentarts-sdk

# Add your additional dependencies here
"""

    req_path = project_path / "requirements.txt"
    req_path.write_text(requirements, encoding="utf-8")
