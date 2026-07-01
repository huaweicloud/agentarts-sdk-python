"""
AgentArts Gateway CLI Commands

Provides CLI commands for MCP (Model Context Protocol) gateway operations.
"""

import json
from typing import Annotated, Any

import typer

from agentarts.toolkit.utils.common import echo_error, echo_success, echo_warning

gateway = typer.Typer(help="Gateway management commands")


def _parse_json(s: str | None) -> dict[str, Any] | None:
    """Parse JSON string to dictionary"""
    if not s:
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        msg = "Invalid JSON format"
        raise ValueError(msg)


def _get_gateway_client(verify_ssl: bool = True):
    """Get Gateway client"""
    from agentarts.sdk.gateway import GatewayClient

    return GatewayClient(verify_ssl=verify_ssl)


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


@gateway.command("create")
def create_gateway(
    name: Annotated[str | None, typer.Option("--name", "-n", help="Gateway name")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="Gateway description")] = None,
    protocol_type: Annotated[str, typer.Option("--protocol-type", help="Protocol type (default: mcp)")] = "mcp",
    authorizer_type: Annotated[str, typer.Option("--authorizer-type", help="Authorizer type (default: iam)")] = "iam",
    agency_name: Annotated[str | None, typer.Option("--agency-name", help="Agency name")] = None,
    authorizer_configuration: Annotated[str | None, typer.Option("--authorizer-configuration", help="Authorizer configuration (JSON format)")] = None,
    protocol_configuration: Annotated[str | None, typer.Option("--protocol-configuration", help="Protocol configuration (JSON format)")] = None,
    log_delivery_configuration: Annotated[str | None, typer.Option("--log-delivery-configuration", help="Log delivery configuration (JSON format)")] = None,
    outbound_network_configuration: Annotated[str | None, typer.Option("--outbound-network-configuration", help="Outbound network configuration (JSON format)")] = None,
    tags: Annotated[str | None, typer.Option("--tags", help="Resource tags (JSON format)")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Create a new gateway

    Examples:
        agentarts gateway create --name my-gateway --description "My Gateway"
    """
    try:
        authorizer_config = _parse_json(authorizer_configuration)
        protocol_config = _parse_json(protocol_configuration)
        log_delivery_config = _parse_json(log_delivery_configuration)
        outbound_network_config = _parse_json(outbound_network_configuration)
        tags_config = _parse_json(tags)

        client = _get_gateway_client(verify_ssl=not skip_ssl_verification)
        result = client.create_gateway(
            name=name,
            description=description,
            protocol_type=protocol_type,
            authorizer_type=authorizer_type,
            agency_name=agency_name,
            authorizer_configuration=authorizer_config,
            protocol_configuration=protocol_config,
            log_delivery_configuration=log_delivery_config,
            outbound_network_configuration=outbound_network_config,
            tags=tags_config
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


@gateway.command("update")
def update_gateway(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    description: Annotated[str | None, typer.Option("--description", "-d", help="Gateway description")] = None,
    protocol_configuration: Annotated[str | None, typer.Option("--protocol-configuration", help="Protocol configuration (JSON format)")] = None,
    log_delivery_configuration: Annotated[str | None, typer.Option("--log-delivery-configuration", help="Log delivery configuration (JSON format)")] = None,
    tags: Annotated[str | None, typer.Option("--tags", help="Resource tags (JSON format)")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Update an existing gateway

    Examples:
        agentarts gateway update 123 --description "Updated description"
    """
    try:
        protocol_config = _parse_json(protocol_configuration)
        log_delivery_config = _parse_json(log_delivery_configuration)
        tags_config = _parse_json(tags)

        client = _get_gateway_client(verify_ssl=not skip_ssl_verification)
        result = client.update_gateway(
            gateway_id=gateway_id,
            description=description,
            protocol_configuration=protocol_config,
            log_delivery_configuration=log_delivery_config,
            tags=tags_config,
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


@gateway.command("delete")
def delete_gateway(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Delete a gateway

    Examples:
        agentarts gateway delete 123
    """
    try:
        echo_warning(f"Are you sure you want to delete gateway {gateway_id}? This action cannot be undone.")
        if not typer.confirm("Do you want to proceed?"):
            echo_success("Deletion cancelled")
            return

        client = _get_gateway_client(verify_ssl=not skip_ssl_verification)
        result = client.delete_gateway(gateway_id=gateway_id)

        if result.success:
            echo_success("Gateway deleted successfully")
        else:
            _handle_error("deleting gateway", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@gateway.command("get")
def get_gateway(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Get details of a gateway

    Examples:
        agentarts gateway get 123
    """
    try:
        client = _get_gateway_client(verify_ssl=not skip_ssl_verification)
        result = client.get_gateway(gateway_id=gateway_id)

        if result.success:
            echo_success("Gateway details:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("getting gateway", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@gateway.command("list")
def list_gateways(
    name: Annotated[str | None, typer.Option("--name", help="Gateway name")] = None,
    status: Annotated[str | None, typer.Option("--status", help="Gateway status")] = None,
    gateway_id: Annotated[str | None, typer.Option("--gateway-id", help="Gateway ID")] = None,
    tag_key_exists: Annotated[str | None, typer.Option("--tag-key-exists", help="Tag key exists filter (comma-separated)")] = None,
    tag_key_matches: Annotated[str | None, typer.Option("--tag-key-matches", help="Tag key matches filter (comma-separated)")] = None,
    tag_value_matches: Annotated[str | None, typer.Option("--tag-value-matches", help="Tag value matches filter (comma-separated)")] = None,
    tag_match_policy: Annotated[str | None, typer.Option("--tag-match-policy", help="Tag match policy (ALL/ANY)")] = None,
    limit: Annotated[int | None, typer.Option("--limit", help="Limit for pagination (default: 50, min: 1, max: 100)")] = None,
    offset: Annotated[int | None, typer.Option("--offset", help="Offset for pagination (default: 0, min: 0, max: 100000)")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    List gateways

    Examples:
        agentarts gateway list --limit 10
    """
    try:
        if offset is None:
            offset = 0
        elif offset < 0:
            msg = "Offset must be greater than or equal to 0"
            raise ValueError(msg)
        elif offset > 100000:
            msg = "Offset must be less than or equal to 100000"
            raise ValueError(msg)

        if limit is None:
            limit = 50
        elif limit < 1:
            msg = "Limit must be greater than 0"
            raise ValueError(msg)
        elif limit > 100:
            msg = "Limit must be less than or equal to 100"
            raise ValueError(msg)

        tag_key_exists_list = tag_key_exists.split(",") if tag_key_exists else None
        tag_key_matches_list = tag_key_matches.split(",") if tag_key_matches else None
        tag_value_matches_list = tag_value_matches.split(",") if tag_value_matches else None

        client = _get_gateway_client(verify_ssl=not skip_ssl_verification)
        result = client.list_gateways(
            name=name,
            status=status,
            gateway_id=gateway_id,
            tag_key_exists=tag_key_exists_list,
            tag_key_matches=tag_key_matches_list,
            tag_value_matches=tag_value_matches_list,
            tag_match_policy=tag_match_policy,
            limit=limit,
            offset=offset,
        )

        if result.success:
            echo_success(f"Total gateways: {result.data.get('total', 0)}")
            echo_success("Gateways:")
            echo_success(_format_output(result.data.get("gateways", [])))
        else:
            _handle_error("listing gateways", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


# Target commands
@gateway.command("create-target")
def create_gateway_target(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    target_configuration: Annotated[str, typer.Option("--target-configuration", help="Target configuration (JSON format)")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Target name")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="Target description")] = None,
    credential_provider_configuration: Annotated[str | None, typer.Option("--credential-provider-configuration", help="Credential provider configuration (JSON format)")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Create a new gateway target

    Examples:
        agentarts gateway create-target 123 --name my-target
    """
    try:
        target_config = _parse_json(target_configuration)
        credential_config = _parse_json(credential_provider_configuration)

        client = _get_gateway_client(verify_ssl=not skip_ssl_verification)
        result = client.create_gateway_target(
            gateway_id=gateway_id,
            name=name,
            description=description,
            target_configuration=target_config,
            credential_provider_configuration=credential_config,
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


@gateway.command("update-target")
def update_gateway_target(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    target_id: Annotated[str, typer.Argument(help="Target ID")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Target name")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="Target description")] = None,
    target_configuration: Annotated[str | None, typer.Option("--target-configuration", help="Target configuration (JSON format)")] = None,
    credential_provider_configuration: Annotated[str | None, typer.Option("--credential-provider-configuration", help="Credential provider configuration (JSON format)")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Update an existing gateway target

    Examples:
        agentarts gateway update-target 123 456 --name updated-target
    """
    try:
        target_config = _parse_json(target_configuration)
        credential_config = _parse_json(credential_provider_configuration)

        client = _get_gateway_client(verify_ssl=not skip_ssl_verification)
        result = client.update_gateway_target(
            gateway_id=gateway_id,
            target_id=target_id,
            name=name,
            description=description,
            target_configuration=target_config,
            credential_provider_configuration=credential_config,
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


@gateway.command("delete-target")
def delete_gateway_target(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    target_id: Annotated[str, typer.Argument(help="Target ID")],
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Delete a gateway target

    Examples:
        agentarts gateway delete-target 123 456
    """
    try:
        echo_warning(f"Are you sure you want to delete target {target_id} from gateway {gateway_id}? This action cannot be undone.")
        if not typer.confirm("Do you want to proceed?"):
            echo_success("Deletion cancelled")
            return

        client = _get_gateway_client(verify_ssl=not skip_ssl_verification)
        result = client.delete_gateway_target(
            gateway_id=gateway_id,
            target_id=target_id,
        )

        if result.success:
            echo_success("Target deleted successfully")
        else:
            _handle_error("deleting target", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@gateway.command("get-target")
def get_gateway_target(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    target_id: Annotated[str, typer.Argument(help="Target ID")],
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Get details of a gateway target

    Examples:
        agentarts gateway get-target 123 456
    """
    try:
        client = _get_gateway_client(verify_ssl=not skip_ssl_verification)
        result = client.get_gateway_target(
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


@gateway.command("list-targets")
def list_gateway_targets(
    gateway_id: Annotated[str, typer.Argument(help="Gateway ID")],
    limit: Annotated[int | None, typer.Option("--limit", help="Limit for pagination (default: 50, min: 1, max: 100)")] = None,
    offset: Annotated[int | None, typer.Option("--offset", help="Offset for pagination (default: 0, min: 0, max: 100000)")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    List gateway targets

    Examples:
        agentarts gateway list-targets 123 --limit 10
    """
    try:
        if offset is None:
            offset = 0
        elif offset < 0:
            msg = "Offset must be greater than or equal to 0"
            raise ValueError(msg)
        elif offset > 100000:
            msg = "Offset must be less than or equal to 100000"
            raise ValueError(msg)

        if limit is None:
            limit = 50
        elif limit < 1:
            msg = "Limit must be greater than 0"
            raise ValueError(msg)
        elif limit > 100:
            msg = "Limit must be less than or equal to 100"
            raise ValueError(msg)

        client = _get_gateway_client(verify_ssl=not skip_ssl_verification)
        result = client.list_gateway_targets(
            gateway_id=gateway_id,
            limit=limit,
            offset=offset,
        )

        if result.success:
            echo_success(f"Total targets: {result.data.get('total', 0)}")
            echo_success("Targets:")
            echo_success(_format_output(result.data.get("targets", [])))
        else:
            _handle_error("listing targets", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")
