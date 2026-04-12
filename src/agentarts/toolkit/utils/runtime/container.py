"""
Container operations for Docker.

Provides functions for building, tagging, pushing, and running Docker images.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

console = Console()


def check_docker_available() -> bool:
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def check_dockerfile_exists() -> bool:
    """Check if Dockerfile exists in current directory."""
    return Path.cwd().joinpath("Dockerfile").exists()


def build_docker_image(
    image_name: str,
    image_tag: str = "latest",
    dockerfile_path: str = "Dockerfile",
    build_context: str = ".",
) -> bool:
    """
    Build Docker image with real-time output.

    Args:
        image_name: Image name
        image_tag: Image tag
        dockerfile_path: Path to Dockerfile
        build_context: Build context path

    Returns:
        True if successful, False otherwise
    """
    full_image_name = f"{image_name}:{image_tag}"

    console.print(f"\n[bold]Building Docker image:[/bold] [cyan]{full_image_name}[/cyan]")
    console.print(f"[dim]Dockerfile: {dockerfile_path}[/dim]")
    console.print(f"[dim]Build context: {build_context}[/dim]")
    console.print()

    current_step = ""
    step_pattern = re.compile(r"^Step\s+(\d+)/(\d+)\s*:\s*(.+)$")
    
    try:
        cmd = [
            "docker",
            "build",
            "-t", full_image_name,
            "-f", dockerfile_path,
            build_context,
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        output_lines = []
        
        for line in iter(process.stdout.readline, ""):
            if not line:
                break
            
            line = line.rstrip()
            output_lines.append(line)
            
            match = step_pattern.match(line)
            if match:
                step_num = match.group(1)
                total_steps = match.group(2)
                step_desc = match.group(3)
                current_step = f"Step {step_num}/{total_steps}: {step_desc}"
                
                console.print(f"\n[bold yellow]▶[/bold yellow] [cyan]Step {step_num}/{total_steps}[/cyan]: [white]{step_desc}[/white]")
            elif line.startswith(" ---> "):
                console.print(f"  [dim]{line}[/dim]")
            elif "Running in" in line:
                console.print(f"  [green]✓[/green] {line.strip()}")
            elif "Successfully built" in line:
                console.print(f"  [green]✓[/green] [bold]{line.strip()}[/bold]")
            elif "Successfully tagged" in line:
                console.print(f"  [green]✓[/green] [bold cyan]{line.strip()}[/bold]")
            elif line.strip():
                if "error" in line.lower() or "error:" in line.lower():
                    console.print(f"  [red]{line}[/red]")
                elif "warning" in line.lower():
                    console.print(f"  [yellow]{line}[/yellow]")
                else:
                    console.print(f"  [dim]{line}[/dim]")

        process.wait()

        if process.returncode != 0:
            console.print(f"\n[red]Error building image:[/red]")
            for line in output_lines[-20:]:
                console.print(f"  [red]{line}[/red]")
            return False

        console.print(f"\n[green]✓ Done:[/green] Image [cyan]{full_image_name}[/cyan] built successfully")
        return True

    except subprocess.TimeoutExpired:
        console.print("[red]Error: Docker build timed out[/red]")
        return False
    except subprocess.SubprocessError as e:
        console.print(f"[red]Error: Failed to build Docker image: {e}[/red]")
        return False


def tag_image(
    source_image: str,
    target_image: str,
) -> bool:
    """
    Tag Docker image.

    Args:
        source_image: Source image name
        target_image: Target image name

    Returns:
        True if successful, False otherwise
    """
    console.print(f"\n[bold]Tagging image:[/bold] [cyan]{source_image}[/cyan] -> [cyan]{target_image}[/cyan]")

    try:
        result = subprocess.run(
            ["docker", "tag", source_image, target_image],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            console.print(f"[red]Error tagging image:[/red]")
            console.print(result.stderr)
            return False

        console.print(f"[green]✓ Done:[/green] Image tagged successfully")
        return True

    except subprocess.SubprocessError as e:
        console.print(f"[red]Error: Failed to tag image: {e}[/red]")
        return False


def push_image(image: str) -> bool:
    """
    Push Docker image to registry with real-time output.

    Args:
        image: Image name to push

    Returns:
        True if successful, False otherwise
    """
    console.print(f"\n[bold]Pushing image:[/bold] [cyan]{image}[/cyan]")
    console.print()

    try:
        process = subprocess.Popen(
            ["docker", "push", image],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        output_lines = []
        digest_pattern = re.compile(r"digest:\s*(sha256:[a-f0-9]+)")

        for line in iter(process.stdout.readline, ""):
            if not line:
                break
            
            line = line.rstrip()
            output_lines.append(line)
            
            if "Pushed" in line or "Layer already exists" in line:
                console.print(f"  [green]✓[/green] {line}")
            elif digest_pattern.search(line):
                match = digest_pattern.search(line)
                console.print(f"  [green]✓[/green] Digest: [cyan]{match.group(1)}[/cyan]")
            elif line.strip():
                console.print(f"  [dim]{line}[/dim]")

        process.wait()

        if process.returncode != 0:
            console.print(f"\n[red]Error pushing image:[/red]")
            for line in output_lines[-10:]:
                console.print(f"  [red]{line}[/red]")
            return False

        console.print(f"\n[green]✓ Done:[/green] Image pushed successfully")
        return True

    except subprocess.TimeoutExpired:
        console.print("[red]Error: Docker push timed out[/red]")
        return False
    except subprocess.SubprocessError as e:
        console.print(f"[red]Error: Failed to push image: {e}[/red]")
        return False


def login_to_registry(
    registry: str,
    username: str,
    password: str,
) -> bool:
    """
    Login to Docker registry.

    Args:
        registry: Registry URL
        username: Username
        password: Password

    Returns:
        True if successful, False otherwise
    """
    console.print(f"\n[bold]Logging in to registry:[/bold] [cyan]{registry}[/cyan]")

    try:
        result = subprocess.run(
            [
                "docker", "login",
                "-u", username,
                "-p", password,
                registry,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            console.print(f"[red]Error logging in:[/red]")
            console.print(result.stderr)
            return False

        console.print(f"[green]✓ Done:[/green] Logged in to registry successfully")
        return True

    except subprocess.SubprocessError as e:
        console.print(f"[red]Error: Failed to login: {e}[/red]")
        return False


def run_container(
    image_name: str,
    image_tag: str = "latest",
    port: int = 8080,
    container_name: Optional[str] = None,
    detach: bool = True,
) -> bool:
    """
    Run Docker container locally.

    Args:
        image_name: Image name
        image_tag: Image tag
        port: Port to expose
        container_name: Container name
        detach: Run in detached mode

    Returns:
        True if successful, False otherwise
    """
    full_image_name = f"{image_name}:{image_tag}"

    if container_name is None:
        container_name = image_name.replace("/", "-").replace(":", "-")

    console.print(f"\n[bold]Running container:[/bold] [cyan]{container_name}[/cyan]")

    try:
        cmd = [
            "docker",
            "run",
            "-p", f"{port}:{port}",
            "--name", container_name,
        ]

        if detach:
            cmd.append("-d")

        cmd.append(full_image_name)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            console.print(f"[red]Error running container:[/red]")
            console.print(result.stderr)
            return False

        container_id = result.stdout.strip()
        console.print(f"[green]✓ Done:[/green] Container [cyan]{container_name}[/cyan] started")
        console.print(f"[dim]Container ID: {container_id[:12]}[/dim]")
        console.print(f"\n[bold]Access your agent at:[/bold] [link]http://localhost:{port}[/link]")
        return True

    except subprocess.SubprocessError as e:
        console.print(f"[red]Error: Failed to run container: {e}[/red]")
        return False


def generate_dockerfile(
    base_image: str = "python:3.10-slim",
    dependency_file: Optional[str] = None,
    entrypoint: Optional[str] = None,
    port: int = 8080,
    output_path: str = "Dockerfile",
) -> bool:
    """
    Generate Dockerfile from template.

    Args:
        base_image: Base Docker image
        dependency_file: Path to dependency file (e.g., requirements.txt)
        entrypoint: Entrypoint in format "module:function" (e.g., "app:main")
        port: Port to expose
        output_path: Output path for Dockerfile

    Returns:
        True if successful, False otherwise
    """
    from agentarts.toolkit.utils.templates.docker import render_dockerfile

    console.print(f"\n[bold]Generating Dockerfile:[/bold] [cyan]{output_path}[/cyan]")

    content = render_dockerfile(
        base_image=base_image,
        dependency_file=dependency_file,
        entrypoint=entrypoint,
        port=port,
    )

    dockerfile_path = Path.cwd() / output_path

    try:
        dockerfile_path.write_text(content, encoding="utf-8")
        console.print(f"[green]✓ Done:[/green] Dockerfile generated at [cyan]{dockerfile_path}[/cyan]")
        return True
    except Exception as e:
        console.print(f"[red]Error: Failed to write Dockerfile: {e}[/red]")
        return False
