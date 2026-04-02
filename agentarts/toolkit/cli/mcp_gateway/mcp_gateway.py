"""
AgentArts MCP Gateway CLI Commands

Provides CLI commands for MCP (Model Context Protocol) gateway operations.
"""

import click
import json
from typing import Optional, List, Dict, Any
from agentarts.wrapper.mcpgateway import MCPGatewayClient
from agentarts.wrapper.service.http_client import RequestConfig

from agentarts.toolkit.utils.common import echo_error, echo_success, echo_warning


def _parse_json(s: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse JSON string to dictionary"""
    if not s:
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format")


def _get_mcp_gateway_client() -> MCPGatewayClient:
    """Get MCP Gateway client"""
    return MCPGatewayClient()


def _format_output(data) -> str:
    """Format data as JSON with indentation, or as string if JSON serialization fails"""
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(data)


def _handle_error(operation: str, result):
    """Handle error response from API call"""
    # Check if result.data is a dictionary with error_msg and error_code
    if isinstance(result.data, dict) and "error_msg" in result.data and "error_code" in result.data:
        echo_error(f"Error {operation} (Code: {result.data['error_code']}): {result.data['error_msg']}")
    else:
        echo_error(f"Error {operation}: {_format_output(result.data) if result.data else result.error}")


# Gateway commands

@click.command('create-mcp-gateway')
@click.option(
    '--name', '-n',
    help='Gateway name'
)
@click.option(
    '--description', '-d',
    help='Gateway description'
)
@click.option(
    '--protocol-type',
    default='mcp',
    help='Protocol type (default: mcp)'
)
@click.option(
    '--authorizer-type',
    default='iam',
    help='Authorizer type (default: iam)'
)
@click.option(
    '--agency-name',
    help='Agency name'
)
@click.option(
    '--authorizer-configuration',
    help='Authorizer configuration (JSON format)'
)
@click.option(
    '--log-delivery-configuration',
    help='Log delivery configuration (JSON format)'
)
@click.option(
    '--outbound-network-configuration',
    help='Outbound network configuration (JSON format)'
)
@click.option(
    '--tags',
    multiple=True,
    help='Gateway tags'
)
def create_mcp_gateway(name: Optional[str], description: Optional[str], protocol_type: str, 
           authorizer_type: str, agency_name: Optional[str], 
           authorizer_configuration: Optional[str], log_delivery_configuration: Optional[str], 
           outbound_network_configuration: Optional[str], tags: List[str]):
    """
    Create a new MCP gateway
    
    Examples:
        agentarts mcp-gateway create-mcp-gateway --name my-gateway --description "My MCP Gateway"
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
            tags=list(tags)
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


@click.command('update-mcp-gateway')
@click.argument('gateway_id')
@click.option(
    '--description', '-d',
    help='Gateway description'
)
@click.option(
    '--authorizer-configuration',
    help='Authorizer configuration (JSON format)'
)
@click.option(
    '--log-delivery-configuration',
    help='Log delivery configuration (JSON format)'
)
@click.option(
    '--outbound-network-configuration',
    help='Outbound network configuration (JSON format)'
)
@click.option(
    '--tags',
    multiple=True,
    help='Gateway tags'
)
def update_mcp_gateway(gateway_id: str, description: Optional[str], 
           authorizer_configuration: Optional[str], log_delivery_configuration: Optional[str], 
           outbound_network_configuration: Optional[str], tags: List[str]):
    """
    Update an existing MCP gateway
    
    Examples:
        agentarts mcp-gateway update-mcp-gateway 123 --description "Updated description"
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
            tags=list(tags)
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


@click.command('delete-mcp-gateway')
@click.argument('gateway_id')
def delete_mcp_gateway(gateway_id: str):
    """
    Delete an MCP gateway
    
    Examples:
        agentarts mcp-gateway delete-mcp-gateway 123
    """
    try:
        # Ask for confirmation
        warning_message = f"Are you sure you want to delete gateway {gateway_id}? This action cannot be undone."
        if not click.confirm(click.style(warning_message, fg="yellow")):
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


@click.command('get-mcp-gateway')
@click.argument('gateway_id')
def get_mcp_gateway(gateway_id: str):
    """
    Get details of an MCP gateway
    
    Examples:
        agentarts mcp-gateway get-mcp-gateway 123
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


@click.command('list-mcp-gateways')
@click.option(
    '--name',
    help='Gateway name'
)
@click.option(
    '--status',
    help='Gateway status'
)
@click.option(
    '--gateway-id',
    help='Gateway ID'
)
@click.option(
    '--tags',
    help='Gateway tags'
)
@click.option(
    '--limit',
    type=int,
    help='Limit for pagination (default: 50, min: 1, max: 50)'
)
@click.option(
    '--offset',
    type=int,
    help='Offset for pagination (default: 0, min: 0, max: 1000000)'
)
def list_mcp_gateways(name: Optional[str], status: Optional[str], gateway_id: Optional[str], 
           tags: Optional[str], limit: Optional[int], offset: Optional[int]):
    """
    List MCP gateways
    
    Examples:
        agentarts mcp-gateway list-mcp-gateways --limit 10
    """
    try:
        # Validate and set default values
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
            offset=offset
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

@click.command('create-mcp-gateway-target')
@click.argument('gateway_id')
@click.option(
    '--name', '-n',
    help='Target name'
)
@click.option(
    '--description', '-d',
    help='Target description'
)
@click.option(
    '--target-configuration',
    help='Target configuration (JSON format)'
)
@click.option(
    '--credential-configuration',
    help='Credential configuration (JSON format)'
)
def create_mcp_gateway_target(gateway_id: str, name: Optional[str], description: Optional[str], 
           target_configuration: Optional[str], credential_configuration: Optional[str]):
    """
    Create a new MCP gateway target
    
    Examples:
        agentarts mcp-gateway create-mcp-gateway-target 123 --name my-target
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
            credential_configuration=credential_config
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


@click.command('update-mcp-gateway-target')
@click.argument('gateway_id')
@click.argument('target_id')
@click.option(
    '--name', '-n',
    help='Target name'
)
@click.option(
    '--description', '-d',
    help='Target description'
)
@click.option(
    '--target-configuration',
    help='Target configuration (JSON format)'
)
@click.option(
    '--credential-configuration',
    help='Credential configuration (JSON format)'
)
def update_mcp_gateway_target(gateway_id: str, target_id: str, name: Optional[str], description: Optional[str], 
           target_configuration: Optional[str], credential_configuration: Optional[str]):
    """
    Update an existing MCP gateway target
    
    Examples:
        agentarts mcp-gateway update-mcp-gateway-target 123 456 --name updated-target
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
            credential_configuration=credential_config
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


@click.command('delete-mcp-gateway-target')
@click.argument('gateway_id')
@click.argument('target_id')
def delete_mcp_gateway_target(gateway_id: str, target_id: str):
    """
    Delete an MCP gateway target
    
    Examples:
        agentarts mcp-gateway delete-mcp-gateway-target 123 456
    """
    try:
        # Ask for confirmation
        warning_message = f"Are you sure you want to delete target {target_id} from gateway {gateway_id}? This action cannot be undone."
        if not click.confirm(click.style(warning_message, fg="yellow")):
            echo_warning("Deletion cancelled")
            return
        
        client = _get_mcp_gateway_client()
        result = client.delete_mcp_gateway_target(
            gateway_id=gateway_id,
            target_id=target_id
        )
        
        if result.success:
            echo_success("Target deleted successfully")
        else:
            _handle_error("deleting target", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@click.command('get-mcp-gateway-target')
@click.argument('gateway_id')
@click.argument('target_id')
def get_mcp_gateway_target(gateway_id: str, target_id: str):
    """
    Get details of an MCP gateway target
    
    Examples:
        agentarts mcp-gateway get-mcp-gateway-target 123 456
    """
    try:
        client = _get_mcp_gateway_client()
        result = client.get_mcp_gateway_target(
            gateway_id=gateway_id,
            target_id=target_id
        )
        
        if result.success:
            echo_success("Target details:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("getting target", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@click.command('list-mcp-gateway-targets')
@click.argument('gateway_id')
@click.option(
    '--limit',
    type=int,
    help='Limit for pagination (default: 50, min: 1, max: 50)'
)
@click.option(
    '--offset',
    type=int,
    help='Offset for pagination (default: 0, min: 0, max: 1000000)'
)
def list_mcp_gateway_targets(gateway_id: str, limit: Optional[int], offset: Optional[int]):
    """
    List MCP gateway targets
    
    Examples:
        agentarts mcp-gateway list-mcp-gateway-targets 123 --limit 10
    """
    try:
        # Validate and set default values
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
            offset=offset
        )
        
        if result.success:
            echo_success(f"Total targets: {result.data.get('total', 0)}")
            echo_success("Targets:")
            echo_success(_format_output(result.data.get('targets', [])))
        else:
            _handle_error("listing targets", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


# Create command group
@click.group()
def mcp_gateway():
    """
    MCP Gateway management commands
    
    Examples:
        agentarts mcp-gateway create-mcp-gateway --name my-gateway --description "My MCP Gateway"
        agentarts mcp-gateway list-mcp-gateways
        agentarts mcp-gateway create-mcp-gateway-target --gateway-id 123 --name my-target
    """
    pass


# Register all commands to the group
mcp_gateway.add_command(create_mcp_gateway)
mcp_gateway.add_command(update_mcp_gateway)
mcp_gateway.add_command(delete_mcp_gateway)
mcp_gateway.add_command(get_mcp_gateway)
mcp_gateway.add_command(list_mcp_gateways)
mcp_gateway.add_command(create_mcp_gateway_target)
mcp_gateway.add_command(update_mcp_gateway_target)
mcp_gateway.add_command(delete_mcp_gateway_target)
mcp_gateway.add_command(get_mcp_gateway_target)
mcp_gateway.add_command(list_mcp_gateway_targets)
