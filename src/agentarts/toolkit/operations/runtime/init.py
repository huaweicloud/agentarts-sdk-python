"""Init operation implementation"""

from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()

TEMPLATES = {
    "basic": "basic_agent",
    "langchain": "langchain_agent",
    "langgraph": "langgraph_agent",
    "google-adk": "google_adk_agent",
}


def init_project(
    template: str,
    name: str,
    path: str,
    region: Optional[str] = None,
    swr_org: Optional[str] = None,
    swr_repo: Optional[str] = None,
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
        True if successful, False otherwise
    """
    project_path = Path(path) / name

    if project_path.exists():
        console.print(f"[red]Error: Directory '{name}' already exists[/red]")
        return False

    project_path.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold]Creating project:[/bold] [cyan]{name}[/cyan]")
    console.print(f"[dim]Template: {template}[/dim]")

    create_agent_file(project_path, template, name)
    create_requirements_file(project_path, template)
    create_config_file(project_path, name, region, swr_org, swr_repo)
    create_dockerfile(project_path, template)

    console.print(f"\n[green]Success:[/green] Project '{name}' created successfully!")
    console.print("\n[bold]Project structure:[/bold]")
    console.print(f"  {name}/")
    console.print(f"  ├── agent.py              # Agent implementation")
    console.print(f"  ├── requirements.txt      # Dependencies")
    console.print(f"  ├── .agentarts_config.yaml # Configuration")
    console.print(f"  └── Dockerfile            # Docker build file")

    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  [cyan]cd {name}[/cyan]")
    console.print(f"  [cyan]pip install -r requirements.txt[/cyan]")
    console.print(f"  [cyan]# Edit agent.py to implement your agent logic[/cyan]")
    console.print(f"  [cyan]agentarts deploy[/cyan]  # Deploy to Huawei Cloud")

    return True


def create_agent_file(project_path: Path, template: str, name: str) -> None:
    """Create agent file based on template."""
    templates = {
        "basic": get_basic_agent_template(name),
        "langchain": get_langchain_agent_template(name),
        "langgraph": get_langgraph_agent_template(name),
        "google-adk": get_google_adk_agent_template(name),
    }

    agent_content = templates.get(template, templates["basic"])

    agent_path = project_path / "agent.py"
    agent_path.write_text(agent_content, encoding="utf-8")
    console.print(f"  [green]Created:[/green] agent.py")


def get_basic_agent_template(name: str) -> str:
    return f'''"""
{name} - Basic Agent Implementation

A simple agent that processes user queries.
"""

from typing import Dict, Any


class Agent:
    """Basic Agent implementation."""

    def __init__(self):
        self.name = "{name}"

    async def run(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Process a query and return a response.

        Args:
            query: User input query
            **kwargs: Additional parameters

        Returns:
            Response dictionary
        """
        # TODO: Implement your agent logic here

        return {{
            "response": f"Processed: {{query}}",
            "status": "success",
            "agent": self.name,
        }}


def create_agent():
    """Create agent instance for runtime."""
    return Agent()


if __name__ == "__main__":
    import asyncio

    agent = create_agent()
    result = asyncio.run(agent.run("Hello, World!"))
    print(result)
'''


def get_langchain_agent_template(name: str) -> str:
    return f'''"""
{name} - LangChain Agent Implementation

An agent built using LangChain framework.
"""

from typing import Dict, Any, Optional


class Agent:
    """LangChain-based Agent implementation."""

    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.name = "{name}"
        self.model_name = model_name
        self._llm = None

    def _get_llm(self):
        """Initialize LLM lazily."""
        if self._llm is None:
            try:
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(model=self.model_name)
            except ImportError:
                raise ImportError(
                    "langchain-openai is required. Install it with: pip install langchain-openai"
                )
        return self._llm

    async def run(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Process a query using LangChain.

        Args:
            query: User input query
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Returns:
            Response dictionary
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = self._get_llm()

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=query))

        response = await llm.ainvoke(messages)

        return {{
            "response": response.content,
            "status": "success",
            "agent": self.name,
            "model": self.model_name,
        }}


def create_agent():
    """Create agent instance for runtime."""
    return Agent()


if __name__ == "__main__":
    import asyncio

    agent = create_agent()
    result = asyncio.run(agent.run("Hello, World!"))
    print(result)
'''


def get_langgraph_agent_template(name: str) -> str:
    return f'''"""
{name} - LangGraph Agent Implementation

An agent built using LangGraph for stateful workflows.
"""

from typing import Dict, Any, TypedDict, Annotated
from operator import add


class State(TypedDict):
    """Agent state definition."""
    messages: Annotated[list, add]
    query: str
    response: str
    status: str


class Agent:
    """LangGraph-based Agent implementation."""

    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.name = "{name}"
        self.model_name = model_name
        self._graph = None

    def _build_graph(self):
        """Build the LangGraph workflow."""
        try:
            from langgraph.graph import StateGraph, END
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, AIMessage
        except ImportError as e:
            raise ImportError(
                f"Required packages not installed: {{e}}. "
                "Install with: pip install langgraph langchain-openai"
            )

        llm = ChatOpenAI(model=self.model_name)

        async def process_node(state: State) -> Dict[str, Any]:
            """Process the query using LLM."""
            query = state.get("query", "")
            messages = state.get("messages", [])

            if not messages:
                messages = [HumanMessage(content=query)]

            response = await llm.ainvoke(messages)

            return {{
                "messages": [AIMessage(content=response.content)],
                "response": response.content,
                "status": "completed",
            }}

        workflow = StateGraph(State)
        workflow.add_node("process", process_node)
        workflow.set_entry_point("process")
        workflow.add_edge("process", END)

        return workflow.compile()

    def _get_graph(self):
        """Get or create the graph."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    async def run(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Process a query using LangGraph workflow.

        Args:
            query: User input query
            **kwargs: Additional parameters

        Returns:
            Response dictionary
        """
        graph = self._get_graph()

        initial_state: State = {{
            "messages": [],
            "query": query,
            "response": "",
            "status": "pending",
        }}

        result = await graph.ainvoke(initial_state)

        return {{
            "response": result.get("response", ""),
            "status": result.get("status", "success"),
            "agent": self.name,
            "model": self.model_name,
        }}


def create_agent():
    """Create agent instance for runtime."""
    return Agent()


if __name__ == "__main__":
    import asyncio

    agent = create_agent()
    result = asyncio.run(agent.run("Hello, World!"))
    print(result)
'''


def get_google_adk_agent_template(name: str) -> str:
    return f'''"""
{name} - Google ADK Agent Implementation

An agent built using Google Agent Development Kit (ADK).
"""

from typing import Dict, Any, Optional


class Agent:
    """Google ADK-based Agent implementation."""

    def __init__(self, model: str = "gemini-2.0-flash"):
        self.name = "{name}"
        self.model = model
        self._agent = None

    def _setup_agent(self):
        """Setup Google ADK agent."""
        try:
            from google.adk.agents import Agent
            from google.genai import types
        except ImportError:
            raise ImportError(
                "google-adk is required. Install it with: pip install google-adk"
            )

        agent = Agent(
            name=self.name,
            model=self.model,
            description="A helpful AI assistant.",
            instruction="You are a helpful AI assistant. "
                        "Provide clear and accurate responses to user queries.",
        )

        return agent

    def _get_agent(self):
        """Get or create the agent."""
        if self._agent is None:
            self._agent = self._setup_agent()
        return self._agent

    async def run(
        self,
        query: str,
        system_instruction: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Process a query using Google ADK.

        Args:
            query: User input query
            system_instruction: Optional system instruction
            **kwargs: Additional parameters

        Returns:
            Response dictionary
        """
        try:
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai import types
        except ImportError:
            raise ImportError(
                "google-adk is required. Install it with: pip install google-adk"
            )

        agent = self._get_agent()

        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            app_name=self.name,
            session_service=session_service,
        )

        session = session_service.create_session(
            app_name=self.name,
            user_id="default_user",
        )

        content = types.Content(
            role="user",
            parts=[types.Part(text=query)],
        )

        events = runner.run(
            user_id="default_user",
            session_id=session.id,
            new_message=content,
        )

        response_text = ""
        for event in events:
            if event.is_final_response():
                if event.content and event.content.parts:
                    response_text = event.content.parts[0].text
                break

        return {{
            "response": response_text,
            "status": "success",
            "agent": self.name,
            "model": self.model,
        }}


def create_agent():
    """Create agent instance for runtime."""
    return Agent()


if __name__ == "__main__":
    import asyncio

    agent = create_agent()
    result = asyncio.run(agent.run("Hello, World!"))
    print(result)
'''


def create_requirements_file(project_path: Path, template: str) -> None:
    """Create requirements file based on template."""
    base_requirements = """huaweicloud-agentarts-sdk
"""

    template_requirements = {
        "basic": "",
        "langchain": """
langchain>=0.1.0
langchain-openai>=0.1.0
langchain-core>=0.1.0
""",
        "langgraph": """
langgraph>=0.0.20
langchain>=0.1.0
langchain-openai>=0.1.0
langchain-core>=0.1.0
""",
        "google-adk": """
google-adk>=0.1.0
google-genai>=0.3.0
""",
    }

    requirements = base_requirements + template_requirements.get(template, "")

    req_path = project_path / "requirements.txt"
    req_path.write_text(requirements.strip() + "\n", encoding="utf-8")
    console.print(f"  [green]Created:[/green] requirements.txt")


def create_config_file(
    project_path: Path,
    name: str,
    region: Optional[str] = None,
    swr_org: Optional[str] = None,
    swr_repo: Optional[str] = None,
) -> None:
    """Create .agentarts_config.yaml configuration file."""
    actual_region = region or "cn-north-4"
    actual_swr_org = swr_org or f"{name}-org"
    actual_swr_repo = swr_repo or name

    config_content = f"""# AgentArts Configuration
# Generated by 'agentarts init' command

default_agent: {name}

agents:
  {name}:
    base:
      name: {name}
      entrypoint: agent:create_agent
      dependency_file: requirements.txt
      platform: linux/amd64
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
"""

    config_path = project_path / ".agentarts_config.yaml"
    config_path.write_text(config_content, encoding="utf-8")
    console.print(f"  [green]Created:[/green] .agentarts_config.yaml")


def create_dockerfile(project_path: Path, template: str) -> None:
    """Create Dockerfile for the project."""
    from agentarts.toolkit.utils.templates.docker import render_dockerfile

    dockerfile_content = render_dockerfile(
        base_image="python:3.10-slim",
        dependency_file="requirements.txt",
        entrypoint="agent:create_agent",
        port=8080,
    )

    dockerfile_path = project_path / "Dockerfile"
    dockerfile_path.write_text(dockerfile_content, encoding="utf-8")
    console.print(f"  [green]Created:[/green] Dockerfile")
