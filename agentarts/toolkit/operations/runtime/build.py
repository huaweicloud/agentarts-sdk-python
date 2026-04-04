"""Build operation implementation"""

from pathlib import Path

from rich.console import Console

console = Console()


def build_project(output: str, platform: str) -> bool:
    """
    Build project.

    Args:
        output: Output directory
        platform: Target platform

    Returns:
        True if successful, False otherwise
    """
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold cyan]Building project for platform: {platform}[/bold cyan]")
    console.print(f"Output directory: [yellow]{output_path}[/yellow]")

    if platform == "docker":
        build_docker(output_path)
    elif platform == "kubernetes":
        build_kubernetes(output_path)
    elif platform == "serverless":
        build_serverless(output_path)

    console.print("\n[bold green]Build completed successfully![/bold green]")
    return True


def build_docker(output_path: Path) -> None:
    """Build Docker image."""
    console.print("Building Docker image...")

    dockerfile_content = """FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "agentarts.server", "--config", "agentarts.yaml"]
"""

    dockerfile_path = output_path / "Dockerfile"
    dockerfile_path.write_text(dockerfile_content, encoding="utf-8")

    console.print("  [green]Done:[/green] Created Dockerfile")


def build_kubernetes(output_path: Path) -> None:
    """Build Kubernetes manifests."""
    console.print("Building Kubernetes manifests...")

    deployment_content = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentarts-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agentarts-agent
  template:
    metadata:
      labels:
        app: agentarts-agent
    spec:
      containers:
      - name: agent
        image: agentarts-agent:latest
        ports:
        - containerPort: 8000
"""

    deployment_path = output_path / "deployment.yaml"
    deployment_path.write_text(deployment_content, encoding="utf-8")

    console.print("  [green]Done:[/green] Created deployment.yaml")


def build_serverless(output_path: Path) -> None:
    """Build Serverless configuration."""
    console.print("Building Serverless configuration...")

    serverless_content = """service: agentarts-agent

provider:
  name: huawei
  runtime: python3.10
  region: cn-north-4

functions:
  agent:
    handler: agent.handler
    events:
      - http:
          path: /invoke
          method: post
"""

    serverless_path = output_path / "serverless.yaml"
    serverless_path.write_text(serverless_content, encoding="utf-8")

    console.print("  [green]Done:[/green] Created serverless.yaml")
