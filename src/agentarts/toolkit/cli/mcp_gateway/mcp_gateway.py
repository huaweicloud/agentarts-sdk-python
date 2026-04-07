"""
AgentArts MCP Gateway CLI Commands

Provides CLI commands for MCP (Model Context Protocol) gateway operations.
"""

import json
from typing import Annotated, Any, Dict, List, Optional

import typer

from agentarts.toolkit.utils.common import echo_error, echo_success, echo_warning

mcp_gateway = typer.Typer(help="MCP Gateway management commands")


def _parse_json(s: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse JSON string to dictionary"""
    if not s:
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format")


def _get_mcp_gateway_client():
    """Get MCP Gateway client"""
    from agentarts.sdk.mcpgateway import MCPGatewayClient

    return MCPGatewayClient()


def _format_output(data) -> str:
    """Format data as JSON with indentation, or as string if JSON serialization fails"""
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(data)


def _handle_error(operation: str, result):
    """Handle error response from API call"""
    if isinstance(result.data, dict) and "error_msg" in result.data and "error_code" in result.data:
        echo_error(f"Error {operation} (Code: {result.data['error_code']}): {result.data['error_msg']}")
    else:
        echo_error(f"Error {operation}: {_format_output(result.data) if result.data else result.error}")


# Gateway commands


@mcp_gateway.command("create-mcp-gateway")
def create_mcp_gateway(
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Gateway name")] = None,
    description: Annotated[Optional[str], typer.Option("--description", "-d", help="Gateway description")] = None,
    protocol_type: Annotated[str, typer.Option("--protocol-type", help="Protocol type (default: mcp)")] = "mcp",
    authorizer_type: Annotated[str, typer.Option("--authorizer-type", help="Authorizer type (default: iam)")] = "iam",
    agency_name: Annotated[Optional[str], typer.Option("--agency-name", help="Agency name")] = None,
    authorizer_configuration: Annotated[Optional[str], typer.Option("--authorizer-configuration", help="Authorizer configuration (JSON format)")] = None,
    log_delivery_configuration: Annotated[Optional[str], typer.Option("--log-delivery-configuration", help="Log delivery configuration (JSON format)")] = None,
    outbound_network_configuration: Annotated[Optional[str], typer.Option("--outbound-network-configuration", help="Outbound network configuration (JSON format)")] = None,
    tags: Annotated[List[str], typer.Option("--tags", help="Gateway tags")] = None,
):
    """
    Create a new MCP gateway

    Examples:
        agentarts mcp create-mcp-gateway --name my-gateway --description "My MCP Gateway"
    """
    try:
        authorizer_config = _parse_json(authorizer_configuration)
        log_delivery_config = _parse_json(log_delivery_configuration)
        outbound_network_config = _parse_json(outbound_network_configuration)

        client = _get_mcp_gateway_client()
        result = client.create_mcp_gateway(
            name=name,
            description=description,
            protocol_type=protocol_type,
            authorizer_type=authorizer_type,
            agency_name=agency_name,
            authorizer_configuration=authorizer_config,
            log_delivery_configuration=log_delivery_config,
            outbound_network_configuration=outbound_network_config,
            tags=list(tags) if tags else [],
        )

        if result.success:
            echo_success("Gateway created successfully:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("creating gateway", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@mcp_gateway.command("update-mcp-gateway")
def update_mcp_gateway(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    description: Annotated[Optional[str], typer.Option("--description", "-d", help="Gateway description")] = None,
    authorizer_configuration: Annotated[Optional[str], typer.Option("--authorizer-configuration", help="Authorizer configuration (JSON format)")] = None,
    log_delivery_configuration: Annotated[Optional[str], typer.Option("--log-delivery-configuration", help="Log delivery configuration (JSON format)")] = None,
    outbound_network_configuration: Annotated[Optional[str], typer.Option("--outbound-network-configuration", help="Outbound network configuration (JSON format)")] = None,
    tags: Annotated[List[str], typer.Option("--tags", help="Gateway tags")] = None,
):
    """
    Update an existing MCP gateway

    Examples:
        agentarts mcp update-mcp-gateway 123 --description "Updated description"
    """
    try:
        authorizer_config = _parse_json(authorizer_configuration)
        log_delivery_config = _parse_json(log_delivery_configuration)
        outbound_network_config = _parse_json(outbound_network_configuration)

        client = _get_mcp_gateway_client()
        result = client.update_mcp_gateway(
            gateway_id=gateway_id,
            description=description,
            authorizer_configuration=authorizer_config,
            log_delivery_configuration=log_delivery_config,
            outbound_network_configuration=outbound_network_config,
            tags=list(tags) if tags else [],
        )

        if result.success:
            echo_success("Gateway updated successfully:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("updating gateway", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@mcp_gateway.command("delete-mcp-gateway")
def delete_mcp_gateway(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
):
    """
    Delete an MCP gateway

    Examples:
        agentarts mcp delete-mcp-gateway 123
    """
    try:
        warning_message = f"Are you sure you want to delete gateway {gateway_id}? This action cannot be undone."
        if not typer.confirm(warning_message):
            echo_warning("Deletion cancelled")
            return

        client = _get_mcp_gateway_client()
        result = client.delete_mcp_gateway(gateway_id=gateway_id)

        if result.success:
            echo_success("Gateway deleted successfully")
        else:
            _handle_error("deleting gateway", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@mcp_gateway.command("get-mcp-gateway")
def get_mcp_gateway(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
):
    """
    Get details of an MCP gateway

    Examples:
        agentarts mcp get-mcp-gateway 123
    """
    try:
        client = _get_mcp_gateway_client()
        result = client.get_mcp_gateway(gateway_id=gateway_id)

        if result.success:
            echo_success("Gateway details:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("getting gateway", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@mcp_gateway.command("list-mcp-gateways")
def list_mcp_gateways(
    name: Annotated[Optional[str], typer.Option("--name", help="Gateway name")] = None,
    status: Annotated[Optional[str], typer.Option("--status", help="Gateway status")] = None,
    gateway_id: Annotated[Optional[str], typer.Option("--gateway-id", help="Gateway ID")] = None,
    tags: Annotated[Optional[str], typer.Option("--tags", help="Gateway tags")] = None,
    limit: Annotated[Optional[int], typer.Option("--limit", help="Limit for pagination (default: 50, min: 1, max: 50)")] = None,
    offset: Annotated[Optional[int], typer.Option("--offset", help="Offset for pagination (default: 0, min: 0, max: 1000000)")] = None,
):
    """
    List MCP gateways

    Examples:
        agentarts mcp list-mcp-gateways --limit 10
    """
    try:
        if offset is None:
            offset = 0
        elif offset < 0:
            raise ValueError("Offset must be greater than or equal to 0")
        elif offset > 1000000:
            raise ValueError("Offset must be less than or equal to 1000000")

        if limit is None:
            limit = 50
        elif limit < 1:
            raise ValueError("Limit must be greater than 0")
        elif limit > 50:
            raise ValueError("Limit must be less than or equal to 50")

        client = _get_mcp_gateway_client()
        result = client.list_mcp_gateways(
            name=name,
            status=status,
            gateway_id=gateway_id,
            tags=tags,
            limit=limit,
            offset=offset,
        )

        if result.success:
            echo_success(f"Total gateways: {result.data.get('total', 0)}")
            echo_success("Gateways:")
            echo_success(_format_output(result.data.get('gateways', [])))
        else:
            _handle_error("listing gateways", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


# Target commands


@mcp_gateway.command("create-mcp-gateway-target")
def create_mcp_gateway_target(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Target name")] = None,
    description: Annotated[Optional[str], typer.Option("--description", "-d", help="Target description")] = None,
    target_configuration: Annotated[Optional[str], typer.Option("--target-configuration", help="Target configuration (JSON format)")] = None,
    credential_configuration: Annotated[Optional[str], typer.Option("--credential-configuration", help="Credential configuration (JSON format)")] = None,
):
    """
    Create a new MCP gateway target

    Examples:
        agentarts mcp create-mcp-gateway-target 123 --name my-target
    """
    try:
        target_config = _parse_json(target_configuration)
        credential_config = _parse_json(credential_configuration)

        client = _get_mcp_gateway_client()
        result = client.create_mcp_gateway_target(
            gateway_id=gateway_id,
            name=name,
            description=description,
            target_configuration=target_config,
            credential_configuration=credential_config,
        )

        if result.success:
            echo_success("Target created successfully:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("creating target", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@mcp_gateway.command("update-mcp-gateway-target")
def update_mcp_gateway_target(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    target_id: Annotated[str, typer.Argument(help="Target ID")],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Target name")] = None,
    description: Annotated[Optional[str], typer.Option("--description", "-d", help="Target description")] = None,
    target_configuration: Annotated[Optional[str], typer.Option("--target-configuration", help="Target configuration (JSON format)")] = None,
    credential_configuration: Annotated[Optional[str], typer.Option("--credential-configuration", help="Credential configuration (JSON format)")] = None,
):
    """
    Update an existing MCP gateway target

    Examples:
        agentarts mcp update-mcp-gateway-target 123 456 --name updated-target
    """
    try:
        target_config = _parse_json(target_configuration)
        credential_config = _parse_json(credential_configuration)

        client = _get_mcp_gateway_client()
        result = client.update_mcp_gateway_target(
            gateway_id=gateway_id,
            target_id=target_id,
            name=name,
            description=description,
            target_configuration=target_config,
            credential_configuration=credential_config,
        )

        if result.success:
            echo_success("Target updated successfully:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("updating target", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@mcp_gateway.command("delete-mcp-gateway-target")
def delete_mcp_gateway_target(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    target_id: Annotated[str, typer.Argument(help="Target ID")],
):
    """
    Delete an MCP gateway target

    Examples:
        agentarts mcp delete-mcp-gateway-target 123 456
    """
    try:
        warning_message = f"Are you sure you want to delete target {target_id} from gateway {gateway_id}? This action cannot be undone."
        if not typer.confirm(warning_message):
            echo_warning("Deletion cancelled")
            return

        client = _get_mcp_gateway_client()
        result = client.delete_mcp_gateway_target(
            gateway_id=gateway_id,
            target_id=target_id,
        )

        if result.success:
            echo_success("Target deleted successfully")
        else:
            _handle_error("deleting target", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@mcp_gateway.command("get-mcp-gateway-target")
def get_mcp_gateway_target(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    target_id: Annotated[str, typer.Argument(help="Target ID")],
):
    """
    Get details of an MCP gateway target

    Examples:
        agentarts mcp get-mcp-gateway-target 123 456
    """
    try:
        client = _get_mcp_gateway_client()
        result = client.get_mcp_gateway_target(
            gateway_id=gateway_id,
            target_id=target_id,
        )

        if result.success:
            echo_success("Target details:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("getting target", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@mcp_gateway.command("list-mcp-gateway-targets")
def list_mcp_gateway_targets(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    limit: Annotated[Optional[int], typer.Option("--limit", help="Limit for pagination (default: 50, min: 1, max: 50)")] = None,
    offset: Annotated[Optional[int], typer.Option("--offset", help="Offset for pagination (default: 0, min: 0, max: 1000000)")] = None,
):
    """
    List MCP gateway targets

    Examples:
        agentarts mcp list-mcp-gateway-targets 123 --limit 10
    """
    try:
        if offset is None:
            offset = 0
        elif offset < 0:
            raise ValueError("Offset must be greater than or equal to 0")
        elif offset > 1000000:
            raise ValueError("Offset must be less than or equal to 1000000")

        if limit is None:
            limit = 50
        elif limit < 1:
            raise ValueError("Limit must be greater than 0")
        elif limit > 50:
            raise ValueError("Limit must be less than or equal to 50")

        client = _get_mcp_gateway_client()
        result = client.list_mcp_gateway_targets(
            gateway_id=gateway_id,
            limit=limit,
            offset=offset,
        )

        if result.success:
            echo_success(f"Total targets: {result.data.get('total', 0)}")
            echo_success("Targets:")
            echo_success(_format_output(result.data.get('targets', [])))
        else:
            _handle_error("listing targets", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")
