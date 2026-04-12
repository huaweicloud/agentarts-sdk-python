"""Template manager for AgentArts projects."""

from pathlib import Path
from typing import Dict, Any, Optional

TEMPLATES_DIR = Path(__file__).parent


class TemplateManager:
    """Manager for project templates."""

    def __init__(self):
        self.templates_dir = TEMPLATES_DIR

    def get_template_path(self, template_type: str, filename: str) -> Path:
        """
        Get the path to a template file.

        Args:
            template_type: Template type (basic, langchain, langgraph, google-adk)
            filename: Template filename (e.g., agent.py.j2)

        Returns:
            Path to the template file
        """
        return self.templates_dir / template_type / filename

    def load_template(self, template_type: str, filename: str) -> str:
        """
        Load a template file content.

        Args:
            template_type: Template type
            filename: Template filename

        Returns:
            Template content
        """
        template_path = self.get_template_path(template_type, filename)

        if not template_path.exists():
            raise FileNotFoundError(
                f"Template file not found: {template_path}"
            )

        return template_path.read_text(encoding="utf-8")

    def render_template(
        self,
        template_type: str,
        filename: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Render a template with context variables.

        Args:
            template_type: Template type
            filename: Template filename
            context: Dictionary of variables to substitute

        Returns:
            Rendered template content
        """
        content = self.load_template(template_type, filename)

        if context:
            for key, value in context.items():
                placeholder = "{{ " + key + " }}"
                content = content.replace(placeholder, str(value))

        return content

    def render_agent_template(
        self,
        template_type: str,
        agent_name: str,
    ) -> str:
        """
        Render agent.py template.

        Args:
            template_type: Template type
            agent_name: Agent name

        Returns:
            Rendered agent.py content
        """
        return self.render_template(
            template_type,
            "agent.py.j2",
            context={"name": agent_name},
        )

    def render_requirements_template(
        self,
        template_type: str,
    ) -> str:
        """
        Render requirements.txt template.

        Args:
            template_type: Template type

        Returns:
            Rendered requirements.txt content
        """
        return self.render_template(template_type, "requirements.txt.j2")

    def list_templates(self) -> list:
        """
        List available template types.

        Returns:
            List of template type names
        """
        templates = []
        for item in self.templates_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                if item.name != "docker":
                    templates.append(item.name)
        return sorted(templates)


template_manager = TemplateManager()
