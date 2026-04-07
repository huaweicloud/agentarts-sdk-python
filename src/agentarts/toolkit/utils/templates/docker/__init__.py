"""Docker templates for AgentArts"""

from pathlib import Path
from typing import Optional

TEMPLATES_DIR = Path(__file__).parent


def get_dockerfile_template() -> str:
    """Get the Dockerfile template content."""
    template_path = TEMPLATES_DIR / "Dockerfile.j2"
    return template_path.read_text(encoding="utf-8")


def render_dockerfile(
    base_image: str = "python:3.10-slim",
    dependency_file: Optional[str] = None,
    entrypoint: Optional[str] = None,
    port: int = 8080,
) -> str:
    """
    Render Dockerfile from template.

    Args:
        base_image: Base Docker image
        dependency_file: Path to dependency file (e.g., requirements.txt)
        entrypoint: Entrypoint in format "module:function" (e.g., "app:main")
        port: Port to expose

    Returns:
        Rendered Dockerfile content
    """
    template = get_dockerfile_template()

    if dependency_file:
        dependency_section = f"""COPY {dependency_file} .
RUN pip install --no-cache-dir -r {dependency_file}"""
    else:
        dependency_section = "# No dependency file specified"

    if entrypoint and ":" in entrypoint:
        module, func = entrypoint.split(":")
        cmd_section = f'CMD ["python", "-c", "from {module} import {func}; {func}()"]'
    else:
        cmd_section = 'CMD ["python", "-m", "agentarts.server", "--config", "agentarts.yaml"]'

    content = template.format(
        base_image=base_image,
        dependency_section=dependency_section,
        port=port,
        cmd_section=cmd_section,
    )

    lines = content.split("\n")
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        if line.strip() == "":
            if not prev_empty:
                cleaned_lines.append(line)
            prev_empty = True
        else:
            cleaned_lines.append(line)
            prev_empty = False

    return "\n".join(cleaned_lines)
