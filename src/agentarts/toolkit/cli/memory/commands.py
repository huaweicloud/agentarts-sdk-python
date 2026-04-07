"""Memory CLI commands - Space CRUD operations."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentarts.toolkit.utils.common import echo_error, echo_success

from ...operations.memory import (
    create_space,
    delete_space,
    get_space,
    list_spaces,
    update_space,
)

console = Console()

# Create memory app
memory_app = typer.Typer(
    name="memory",
    help="Memory Space management commands",
    add_completion=False,
)


@memory_app.command("create")
def create_space_cmd(
        name: str = typer.Argument(..., help="Space name, required (1-128 characters)"),
        message_ttl_hours: int = typer.Option(168, "--ttl", "-t", help="Message TTL in hours"),
        description: Optional[str] = typer.Option(None, "--description", "-d", help="Space description"),
        memory_extract_idle_seconds: Optional[int] = typer.Option(None, "--extract-idle",
                                                                  help="Memory extraction idle time in seconds"),
        memory_extract_max_tokens: Optional[int] = typer.Option(None, "--extract-tokens",
                                                                help="Memory extraction max tokens"),
        memory_extract_max_messages: Optional[int] = typer.Option(None, "--extract-messages",
                                                                  help="Memory extraction max messages"),
        memory_strategies: Optional[str] = typer.Option(None, "--strategies", "-s",
                                                        help="Built-in memory strategies (comma-separated)"),
        tags: Optional[str] = typer.Option(None, "--tags", help="Tags in format 'key1=value1,key2=value2'"),
        enable_public: bool = typer.Option(True, "--public/--private", help="Enable/disable public access"),
        vpc_id: Optional[str] = typer.Option(None, "--vpc-id", help="Private VPC ID (requires subnet-id)"),
        subnet_id: Optional[str] = typer.Option(None, "--subnet-id", help="Private subnet ID (requires vpc-id)"),
        region: Optional[str] = typer.Option(None, "--region", "-r", help="Region name (default: cn-north-4)"),
        output: str = typer.Option("table", "--output", "-o", help="Output format: table, json"),
):
    """Create a Memory Space.

    Uses AK/SK authentication via environment variables:
    - HUAWEICLOUD_SDK_AK: Access Key
    - HUAWEICLOUD_SDK_SK: Secret Key
    """
    # Input validation
    if not name or not isinstance(name, str) or not name.strip():
        echo_error("Space name cannot be empty")

    if len(name.strip()) > 128:
        echo_error("Space name cannot exceed 128 characters")

    # Validate TTL values
    if message_ttl_hours <= 0 or message_ttl_hours > 8760:
        echo_error("Message TTL must be between 1 and 8760 hours")

    # Validate VPC and subnet combination
    if (vpc_id is None and subnet_id is not None) or (vpc_id is not None and subnet_id is None):
        echo_error("Both VPC ID and subnet ID must be provided for private access")

    if vpc_id and not vpc_id.strip():
        echo_error("VPC ID cannot be empty if provided")

    if subnet_id and not subnet_id.strip():
        echo_error("Subnet ID cannot be empty if provided")

    # Parse memory strategies
    memory_strategies_list = None
    if memory_strategies:
        try:
            memory_strategies_list = [s.strip() for s in memory_strategies.split(",")]
        except Exception:
            echo_error("Invalid memory strategies format, use comma-separated values")

    # Parse tags
    tags_list = None
    if tags:
        try:
            tags_list = []
            for tag_pair in tags.split(","):
                if "=" not in tag_pair:
                    echo_error("Invalid tag format, use 'key=value' pairs separated by commas")
                key, value = tag_pair.split("=", 1)
                tags_list.append({"key": key.strip(), "value": value.strip()})
        except Exception:
            echo_error("Invalid tags format, use 'key1=value1,key2=value2'")

    result = create_space(
        name=name,
        message_ttl_hours=message_ttl_hours,
        description=description,
        memory_extract_idle_seconds=memory_extract_idle_seconds,
        memory_extract_max_tokens=memory_extract_max_tokens,
        memory_extract_max_messages=memory_extract_max_messages,
        memory_strategies_builtin=memory_strategies_list,
        tags=tags_list,
        public_access_enable=enable_public,
        private_vpc_id=vpc_id.strip() if vpc_id else None,
        private_subnet_id=subnet_id.strip() if subnet_id else None,
        region=region,
    )

    if not result.success:
        echo_error(f"Failed to create space: {result.error}")

    if output == "json":
        try:
            serialized_data = json.dumps(result.space, indent=2, default=str)
            console.print_json(serialized_data)
        except (TypeError, ValueError) as e:
            echo_error(f"Failed to serialize space data to JSON: {e}")
    else:
        echo_success(f"Space created successfully!")
        console.print(f"  Space ID: [bold]{result.space_id}[/bold]")
        if result.space:
            console.print(f"  Status: {result.space.get('status', 'N/A')}")


@memory_app.command("get")
def get_space_cmd(
        space_id: str = typer.Argument(..., help="Space ID"),
        region: Optional[str] = typer.Option(None, "--region", "-r", help="Region name (default: cn-north-4)"),
        output: str = typer.Option("table", "--output", "-o", help="Output format: table, json"),
):
    """Get Space details.

    Uses AK/SK authentication via environment variables.
    """
    # Input validation
    if not space_id or not isinstance(space_id, str) or not space_id.strip():
        echo_error("Space ID cannot be empty")

    # Clean up the space_id for display
    display_space_id = space_id.strip()
    result = get_space(
        space_id=space_id,
        region=region,
    )

    if not result.success:
        echo_error(f"Failed to get space: {result.error}")

    if output == "json":
        try:
            serialized_data = json.dumps(result.space, indent=2, default=str)
            console.print_json(serialized_data)
        except (TypeError, ValueError) as e:
            echo_error(f"Failed to serialize space data to JSON: {e}")
    else:
        space = result.space or {}
        console.print(Panel(
            f"[bold]Space ID:[/bold] {space.get('id', display_space_id)}\n"
            f"[bold]Project ID:[/bold] {space.get('project_id', 'N/A')}\n"
            f"[bold]Status:[/bold] {space.get('status', 'N/A')}\n"
            f"[bold]Message TTL:[/bold] {space.get('message_ttl_hours', 'N/A')} hours\n"
            f"[bold]Created:[/bold] {space.get('created_at', 'N/A')}",
            title="Space Details",
            border_style="green",
        ))


@memory_app.command("list")
def list_spaces_cmd(
        limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of spaces"),
        offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
        region: Optional[str] = typer.Option(None, "--region", "-r", help="Region name (default: cn-north-4)"),
        output: str = typer.Option("table", "--output", "-o", help="Output format: table, json"),
):
    """List Spaces.

    Uses AK/SK authentication via environment variables.
    """
    # Validate pagination parameters
    if limit <= 0:
        echo_error("Limit must be greater than 0")

    if limit > 100:
        echo_error("Limit cannot exceed 100")

    if offset < 0:
        echo_error("Offset must be greater than or equal to 0")

    result = list_spaces(
        limit=limit,
        offset=offset,
        region=region,
    )

    if not result.success:
        echo_error(f"Failed to list spaces: {result.error}")

    if output == "json":
        try:
            output_data = {
                "spaces": result.spaces or [],
                "total": result.total or 0
            }
            serialized_data = json.dumps(output_data, indent=2, default=str)
            console.print_json(serialized_data)
        except (TypeError, ValueError) as e:
            echo_error(f"Failed to serialize spaces data to JSON: {e}")
    else:
        table = Table(title=f"Spaces (Total: {result.total})")
        table.add_column("Space ID", style="cyan")
        table.add_column("Project ID", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Message TTL", style="magenta")
        table.add_column("Created", style="dim")

        for space in result.spaces:
            table.add_row(
                space.get("id", "N/A"),
                space.get("project_id", "N/A"),
                space.get("status", "N/A"),
                str(space.get("message_ttl_hours", "N/A")),
                space.get("created_at", "N/A"),
            )

        console.print(table)


@memory_app.command("update")
def update_space_cmd(
        space_id: str = typer.Argument(..., help="Space ID"),
        message_ttl_hours: Optional[int] = typer.Option(None, "--ttl", "-t", help="Message TTL in hours"),
        description: Optional[str] = typer.Option(None, "--description", "-d", help="Space description"),
        memory_extract_idle_seconds: Optional[int] = typer.Option(None, "--extract-idle",
                                                                  help="Memory extraction idle time in seconds"),
        memory_extract_max_tokens: Optional[int] = typer.Option(None, "--extract-tokens",
                                                                help="Memory extraction max tokens"),
        memory_extract_max_messages: Optional[int] = typer.Option(None, "--extract-messages",
                                                                  help="Memory extraction max messages"),
        memory_strategies: Optional[str] = typer.Option(None, "--strategies", "-s",
                                                        help="Built-in memory strategies (comma-separated)"),
        tags: Optional[str] = typer.Option(None, "--tags", help="Tags in format 'key1=value1,key2=value2'"),
        enable_public: Optional[bool] = typer.Option(None, "--public/--private", help="Enable/disable public access"),
        vpc_id: Optional[str] = typer.Option(None, "--vpc-id", help="Private VPC ID (requires subnet-id)"),
        subnet_id: Optional[str] = typer.Option(None, "--subnet-id", help="Private subnet ID (requires vpc-id)"),
        region: Optional[str] = typer.Option(None, "--region", "-r", help="Region name (default: cn-north-4)"),
        output: str = typer.Option("table", "--output", "-o", help="Output format: table, json"),
):
    """Update a Space.

    Uses AK/SK authentication via environment variables.
    """
    # Input validation
    if not space_id or not isinstance(space_id, str) or not space_id.strip():
        echo_error("Space ID cannot be empty")

    # Clean up the space_id
    clean_space_id = space_id.strip()

    # Validate TTL if provided
    if message_ttl_hours is not None:
        if message_ttl_hours <= 0 or message_ttl_hours > 8760:
            echo_error("Message TTL must be between 1 and 8760 hours")

    # Validate VPC and subnet combination
    if (vpc_id is None and subnet_id is not None) or (vpc_id is not None and subnet_id is None):
        echo_error("Both VPC ID and subnet ID must be provided for private access")

    # Parse memory strategies
    memory_strategies_list = None
    if memory_strategies:
        try:
            memory_strategies_list = [s.strip() for s in memory_strategies.split(",")]
        except Exception:
            echo_error("Invalid memory strategies format, use comma-separated values")

    # Parse tags
    tags_list = None
    if tags:
        try:
            tags_list = []
            for tag_pair in tags.split(","):
                if "=" not in tag_pair:
                    echo_error("Invalid tag format, use 'key=value' pairs separated by commas")
                key, value = tag_pair.split("=", 1)
                tags_list.append({"key": key.strip(), "value": value.strip()})
        except Exception:
            echo_error("Invalid tags format, use 'key1=value1,key2=value2'")

    result = update_space(
        space_id=clean_space_id,
        message_ttl_hours=message_ttl_hours,
        description=description,
        memory_extract_idle_seconds=memory_extract_idle_seconds,
        memory_extract_max_tokens=memory_extract_max_tokens,
        memory_extract_max_messages=memory_extract_max_messages,
        memory_strategies_builtin=memory_strategies_list,
        tags=tags_list,
        public_access_enable=enable_public,
        private_vpc_id=vpc_id.strip() if vpc_id else None,
        private_subnet_id=subnet_id.strip() if subnet_id else None,
        region=region,
    )

    if not result.success:
        echo_error(f"Failed to update space: {result.error}")

    if output == "json":
        try:
            output_data = {
                "space_id": clean_space_id,
                "space": result.space or None
            }
            serialized_data = json.dumps(output_data, indent=2, default=str)
            console.print_json(serialized_data)
        except (TypeError, ValueError) as e:
            echo_error(f"Failed to serialize space data to JSON: {e}")
    else:
        echo_success(f"Space updated successfully!")
        console.print(f"  Space ID: [bold]{clean_space_id}[/bold]")

        # Show more details if available
        if result.space:
            status = result.space.get('status', 'N/A')
            project_id = result.space.get('project_id', 'N/A')
            message_ttl = result.space.get('message_ttl_hours', 'N/A')

            console.print(f"  Status: {status}")
            console.print(f"  Project ID: {project_id}")
            if message_ttl != 'N/A':
                console.print(f"  Message TTL: {message_ttl} hours")

            # Show updates that were made
            updates = []
            if message_ttl_hours is not None:
                updates.append(f"TTL set to {message_ttl} hours")
            if enable_public is not None:
                updates.append(f"Public access {'enabled' if enable_public else 'disabled'}")

            if updates:
                console.print(f"  Updates: {', '.join(updates)}")


@memory_app.command("delete")
def delete_space_cmd(
        space_id: str = typer.Argument(..., help="Space ID"),
        region: Optional[str] = typer.Option(None, "--region", "-r", help="Region name (default: cn-north-4)"),
        force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation"),
):
    """Delete a Space.

    Uses AK/SK authentication via environment variables.
    """
    # Validate space_id
    if not space_id or not isinstance(space_id, str) or not space_id.strip():
        echo_error("Space ID cannot be empty")

    # Clean up the space_id for display
    display_space_id = space_id.strip()

    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete space '{display_space_id}'?")
        if not confirm:
            console.print("[yellow]Deletion cancelled.[/yellow]")
            raise typer.Exit(0)

    result = delete_space(
        space_id=space_id,
        region=region,
    )

    if not result.success:
        echo_error(f"Failed to delete space: {result.error}")

    echo_success(f"Space deleted successfully!")
    console.print(f"  Space ID: [bold]{display_space_id}[/bold]")


@memory_app.command("status")
def space_status_cmd(
        space_id: str = typer.Argument(..., help="Space ID to check status"),
        region: Optional[str] = typer.Option(None, "--region", "-r", help="Region name (default: cn-north-4)"),
        output: str = typer.Option("table", "--output", "-o", help="Output format: table, json"),
):
    """Check the status of a Memory Space.
    
    This command provides a simplified view of space status showing
    only the essential information like available status and health.
    
    Uses AK/SK authentication via environment variables:
    - HUAWEICLOUD_SDK_AK: Access Key
    - HUAWEICLOUD_SDK_SK: Secret Key
    """
    # Input validation
    if not space_id or not isinstance(space_id, str) or not space_id.strip():
        echo_error("Space ID cannot be empty")

    # Clean up the space_id for display
    display_space_id = space_id.strip()

    result = get_space(
        space_id=space_id,
        region=region,
    )

    if not result.success:
        echo_error(f"Failed to get space status: {result.error}")

    # Format output based on user preference
    if output == "json":
        try:
            output_data = {
                "space_id": display_space_id,
                "status_available": None,
                "project_id": None,
                "created_at": None,
                "updated_at": None,
                "health_status": None
            }

            if result.space:
                # Extract essential status information
                output_data["status_available"] = {
                    "status": result.space.get("status", "unknown"),
                    "message_ttl_hours": result.space.get("message_ttl_hours"),
                    "enable_memory_extract": result.space.get("enable_memory_extract"),
                }
                output_data["project_id"] = result.space.get("project_id")
                output_data["created_at"] = result.space.get("created_at")
                output_data["updated_at"] = result.space.get("updated_at")

                # Determine health status based on various indicators
                status = result.space.get("status", "").upper()
                ttl = result.space.get("message_ttl_hours")
                memory_extract = result.space.get("enable_memory_extract")

                # Determine overall health status
                health = "healthy"
                if status in ["ERROR", "FAILED"]:
                    health = "error"
                elif status in ["STOPPED", "INACTIVE"]:
                    health = "warning"
                elif ttl is not None and ttl < 24:
                    health = "warning"
                elif memory_extract is False and result.space.get("status") == "ACTIVE":
                    health = "warning"

                output_data["health_status"] = health

            serialized_data = json.dumps(output_data, indent=2, default=str)
            console.print_json(serialized_data)
        except (TypeError, ValueError) as e:
            echo_error(f"Failed to serialize space status to JSON: {e}")
    else:
        # Table format - focus on status
        status_info = result.space.get("status", "unknown") if result.space else "unknown"

        # Determine color and health status based on space status
        health_status = "healthy"
        if status_info.upper() in ["ACTIVE", "RUNNING", "READY"]:
            status_color = "[green]"
            health_status = "healthy"
        elif status_info.upper() in ["STOPPED", "INACTIVE", "WARNING"]:
            status_color = "[yellow]"
            health_status = "warning"
        elif status_info.upper() in ["ERROR", "FAILED"]:
            status_color = "[red]"
            health_status = "error"
        else:
            status_color = "[dim]"
            health_status = "unknown"

        # Create a more comprehensive status panel
        status_content = (
            f"[bold]Space ID:[/bold] {display_space_id}\n"
            f"[bold]Status:[/bold] {status_color}{status_info}[/color]\n"
            f"[bold]Health:[/bold] {status_color}{health_status.title()}[/color]"
        )

        if result.space:
            status_content += f"\n[bold]Project:[/bold] {result.space.get('project_id', 'N/A')}"
            status_content += f"\n[bold]Created:[/bold] {result.space.get('created_at', 'N/A')}"
            status_content += f"\n[bold]TTL:[/bold] {result.space.get('message_ttl_hours', 'N/A')} hours"

            # Add memory extraction status
            memory_extract = result.space.get("enable_memory_extract")
            if memory_extract is not None:
                extract_status = "[green]Enabled[/green]" if memory_extract else "[red]Disabled[/red]"
                status_content += f"\n[bold]Memory Extract:[/bold] {extract_status}"

        console.print(Panel(
            status_content,
            title=f"Memory Space Status",
            border_style="cyan",
        ))

        # Show additional warnings or information if available
        if result.space:
            # Show warning if message TTL is about to expire
            ttl = result.space.get("message_ttl_hours")
            if ttl and ttl < 24:
                console.print(f"[yellow]⚠️  Warning: Message TTL is low ({ttl} hours)[/yellow]")

            # Show region information
            region_info = result.space.get("region")
            if region_info:
                console.print(f"  Region: [cyan]{region_info}[/cyan]")
