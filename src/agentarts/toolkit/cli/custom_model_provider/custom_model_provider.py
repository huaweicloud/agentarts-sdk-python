"""
AgentArts Model Provider CLI Commands

Provides CLI commands for model provider, model service and model proxy
operations on the AgentArts model gateway.
"""

import json
from typing import Annotated, Any

import typer

from agentarts.toolkit.utils.common import echo_error, echo_success, echo_warning

custom_model_provider = typer.Typer(help="Model provider management commands")


def _parse_json(s: str | None) -> dict[str, Any] | None:
    """Parse JSON string to dictionary"""
    if not s:
        return None
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        msg = "Invalid JSON format"
        raise ValueError(msg)


def _get_model_provider_client(verify_ssl: bool = True):
    """Get ModelProvider client"""
    from agentarts.sdk.custom_model_provider import CustomModelProviderClient

    return CustomModelProviderClient(verify_ssl=verify_ssl)


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


def _validate_pagination(limit: int | None, offset: int | None) -> tuple[int, int]:
    """Validate and normalize pagination parameters"""
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

    return limit, offset


def _split_csv(s: str | None) -> list[str] | None:
    """Split comma-separated string into a list"""
    if not s:
        return None
    return s.split(",")


# Model provider commands


@custom_model_provider.command("create-provider")
def create_provider(
    name: Annotated[str, typer.Argument(help="Model provider name")],
    base_url: Annotated[str, typer.Argument(help="Model provider API base URL")],
    credential_configuration: Annotated[str, typer.Option("--credential-configuration", help="Credential configuration (JSON format)")],
    network_configuration: Annotated[str | None, typer.Option("--network-configuration", help="Network configuration (JSON format)")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="Model provider description")] = None,
    tags: Annotated[str | None, typer.Option("--tags", help="Resource tags (JSON format)")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Create a new model provider

    Examples:
        agentarts custom-model-provider create-provider my-provider https://example.com/v1 --credential-configuration '{"provider_configuration": {}}'
    """
    try:
        credential_config = _parse_json(credential_configuration)
        network_config = _parse_json(network_configuration)
        tags_config = _parse_json(tags)

        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.create_model_provider(
            name=name,
            base_url=base_url,
            credential_configuration=credential_config,
            network_configuration=network_config,
            description=description,
            tags=tags_config,
        )

        if result.success:
            echo_success("Model provider created successfully:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("creating model provider", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@custom_model_provider.command("update-provider")
def update_provider(
    model_provider_id: Annotated[str, typer.Argument(help="Model provider ID")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Model provider name")] = None,
    base_url: Annotated[str | None, typer.Option("--base-url", help="Model provider API base URL")] = None,
    credential_configuration: Annotated[str | None, typer.Option("--credential-configuration", help="Credential configuration (JSON format)")] = None,
    network_configuration: Annotated[str | None, typer.Option("--network-configuration", help="Network configuration (JSON format)")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="Model provider description")] = None,
    tags: Annotated[str | None, typer.Option("--tags", help="Resource tags (JSON format)")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Update an existing model provider

    Examples:
        agentarts custom-model-provider update-provider 123 --description "Updated description"
    """
    try:
        credential_config = _parse_json(credential_configuration)
        network_config = _parse_json(network_configuration)
        tags_config = _parse_json(tags)

        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.update_model_provider(
            model_provider_id=model_provider_id,
            name=name,
            base_url=base_url,
            credential_configuration=credential_config,
            network_configuration=network_config,
            description=description,
            tags=tags_config,
        )

        if result.success:
            echo_success("Model provider updated successfully:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("updating model provider", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@custom_model_provider.command("delete-provider")
def delete_provider(
    model_provider_id: Annotated[str, typer.Argument(help="Model provider ID")],
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Delete a model provider

    Examples:
        agentarts custom-model-provider delete-provider 123
    """
    try:
        echo_warning(f"Are you sure you want to delete model provider {model_provider_id}? This action cannot be undone.")
        if not typer.confirm("Do you want to proceed?"):
            echo_success("Deletion cancelled")
            return

        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.delete_model_provider(model_provider_id=model_provider_id)

        if result.success:
            echo_success("Model provider deleted successfully")
        else:
            _handle_error("deleting model provider", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@custom_model_provider.command("get-provider")
def get_provider(
    model_provider_id: Annotated[str, typer.Argument(help="Model provider ID")],
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Get details of a model provider

    Examples:
        agentarts custom-model-provider get-provider 123
    """
    try:
        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.get_model_provider(model_provider_id=model_provider_id)

        if result.success:
            echo_success("Model provider details:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("getting model provider", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@custom_model_provider.command("list-providers")
def list_providers(
    name: Annotated[str | None, typer.Option("--name", help="Model provider name")] = None,
    model_provider_id: Annotated[str | None, typer.Option("--model-provider-id", help="Model provider ID")] = None,
    tag_key_exists: Annotated[str | None, typer.Option("--tag-key-exists", help="Tag key exists filter (comma-separated)")] = None,
    tag_key_matches: Annotated[str | None, typer.Option("--tag-key-matches", help="Tag key matches filter (comma-separated)")] = None,
    tag_value_matches: Annotated[str | None, typer.Option("--tag-value-matches", help="Tag value matches filter (comma-separated)")] = None,
    tag_match_policy: Annotated[str | None, typer.Option("--tag-match-policy", help="Tag match policy (ALL/ANY)")] = None,
    limit: Annotated[int | None, typer.Option("--limit", help="Limit for pagination (default: 50, min: 1, max: 100)")] = None,
    offset: Annotated[int | None, typer.Option("--offset", help="Offset for pagination (default: 0, min: 0, max: 100000)")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    List model providers

    Examples:
        agentarts custom-model-provider list-providers --limit 10
    """
    try:
        limit, offset = _validate_pagination(limit, offset)

        tag_key_exists_list = _split_csv(tag_key_exists)
        tag_key_matches_list = _split_csv(tag_key_matches)
        tag_value_matches_list = _split_csv(tag_value_matches)

        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.list_model_providers(
            name=name,
            model_provider_id=model_provider_id,
            tag_key_exists=tag_key_exists_list,
            tag_key_matches=tag_key_matches_list,
            tag_value_matches=tag_value_matches_list,
            tag_match_policy=tag_match_policy,
            limit=limit,
            offset=offset,
        )

        if result.success:
            echo_success(f"Total model providers: {result.data.get('total', 0)}")
            echo_success("Model providers:")
            echo_success(_format_output(result.data.get("model_providers", [])))
        else:
            _handle_error("listing model providers", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


# Model service commands


@custom_model_provider.command("create-model")
def create_model(
    model_provider_id: Annotated[str, typer.Argument(help="Model provider ID")],
    model: Annotated[str | None, typer.Option("--model", help="Model name, e.g. qwen2.5-72b")] = None,
    model_service_name: Annotated[str | None, typer.Option("--model-service-name", help="Model service display name")] = None,
    type_: Annotated[str | None, typer.Option("--type", help="Model types (comma-separated), e.g. completions")] = None,
    protocol: Annotated[str | None, typer.Option("--protocol", help="API protocol (openai/anthropic/maas_v1)")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="Model description")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Create a new model under a model provider

    Examples:
        agentarts custom-model-provider create-model 123 --model qwen2.5-72b --model-service-name my-model --type completions --protocol openai
    """
    try:
        type_list = _split_csv(type_)

        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.create_model(
            model_provider_id=model_provider_id,
            model=model,
            model_service_name=model_service_name,
            type_=type_list,
            protocol=protocol,
            description=description,
        )

        if result.success:
            echo_success("Model created successfully:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("creating model", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@custom_model_provider.command("update-model")
def update_model(
    model_provider_id: Annotated[str, typer.Argument(help="Model provider ID")],
    model_id: Annotated[str, typer.Argument(help="Model ID")],
    model: Annotated[str | None, typer.Option("--model", help="Model name, e.g. qwen2.5-72b")] = None,
    model_service_name: Annotated[str | None, typer.Option("--model-service-name", help="Model service display name")] = None,
    type_: Annotated[str | None, typer.Option("--type", help="Model types (comma-separated), e.g. completions")] = None,
    protocol: Annotated[str | None, typer.Option("--protocol", help="API protocol (openai/anthropic/maas_v1)")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="Model description")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Update an existing model under a model provider

    Examples:
        agentarts custom-model-provider update-model 123 456 --description "Updated description"
    """
    try:
        type_list = _split_csv(type_)

        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.update_model(
            model_provider_id=model_provider_id,
            model_id=model_id,
            model=model,
            model_service_name=model_service_name,
            type_=type_list,
            protocol=protocol,
            description=description,
        )

        if result.success:
            echo_success("Model updated successfully:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("updating model", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@custom_model_provider.command("delete-model")
def delete_model(
    model_provider_id: Annotated[str, typer.Argument(help="Model provider ID")],
    model_id: Annotated[str, typer.Argument(help="Model ID")],
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Delete a model under a model provider

    Examples:
        agentarts custom-model-provider delete-model 123 456
    """
    try:
        echo_warning(f"Are you sure you want to delete model {model_id} from model provider {model_provider_id}? This action cannot be undone.")
        if not typer.confirm("Do you want to proceed?"):
            echo_success("Deletion cancelled")
            return

        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.delete_model(
            model_provider_id=model_provider_id,
            model_id=model_id,
        )

        if result.success:
            echo_success("Model deleted successfully")
        else:
            _handle_error("deleting model", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@custom_model_provider.command("get-model")
def get_model(
    model_provider_id: Annotated[str, typer.Argument(help="Model provider ID")],
    model_id: Annotated[str, typer.Argument(help="Model ID")],
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Get details of a model under a model provider

    Examples:
        agentarts custom-model-provider get-model 123 456
    """
    try:
        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.get_model(
            model_provider_id=model_provider_id,
            model_id=model_id,
        )

        if result.success:
            echo_success("Model details:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("getting model", result)
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@custom_model_provider.command("list-models")
def list_models(
    model_provider_id: Annotated[str, typer.Argument(help="Model provider ID")],
    model_service_name: Annotated[str | None, typer.Option("--model-service-name", help="Model service display name")] = None,
    model_id: Annotated[str | None, typer.Option("--model-id", help="Model ID")] = None,
    limit: Annotated[int | None, typer.Option("--limit", help="Limit for pagination (default: 50, min: 1, max: 100)")] = None,
    offset: Annotated[int | None, typer.Option("--offset", help="Offset for pagination (default: 0, min: 0, max: 100000)")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    List models under a model provider

    Examples:
        agentarts custom-model-provider list-models 123 --limit 10
    """
    try:
        limit, offset = _validate_pagination(limit, offset)

        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.list_models(
            model_provider_id=model_provider_id,
            model_service_name=model_service_name,
            model_id=model_id,
            limit=limit,
            offset=offset,
        )

        if result.success:
            echo_success(f"Total models: {result.data.get('total', 0)}")
            echo_success("Models:")
            echo_success(_format_output(result.data.get("models", [])))
        else:
            _handle_error("listing models", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


# Model proxy commands


@custom_model_provider.command("create-proxy")
def create_proxy(
    custom_model_provider_id: Annotated[str, typer.Option("--custom-model-provider-id", help="Model provider ID")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Model proxy name")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="Model proxy description")] = None,
    inbound_authorizer_type: Annotated[str, typer.Option("--inbound-authorizer-type", help="Inbound authorizer type (default: iam)")] = "iam",
    agency_name: Annotated[str | None, typer.Option("--agency-name", help="Agency name")] = None,
    inbound_authorizer_configuration: Annotated[str | None, typer.Option("--inbound-authorizer-configuration", help="Inbound authorizer configuration (JSON format)")] = None,
    agent_gateway_id: Annotated[str | None, typer.Option("--agent-gateway-id", help="Agent gateway ID")] = None,
    tags: Annotated[str | None, typer.Option("--tags", help="Resource tags (JSON format)")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Create a new model proxy

    Examples:
        agentarts custom-model-provider create-proxy --custom-model-provider-id 123
    """
    try:
        inbound_authorizer_config = _parse_json(inbound_authorizer_configuration)
        tags_config = _parse_json(tags)

        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.create_model_proxy(
            custom_model_provider_id=custom_model_provider_id,
            name=name,
            description=description,
            inbound_authorizer_type=inbound_authorizer_type,
            agency_name=agency_name,
            inbound_authorizer_configuration=inbound_authorizer_config,
            agent_gateway_id=agent_gateway_id,
            tags=tags_config,
        )

        if result.success:
            echo_success("Model proxy created successfully:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("creating model proxy", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@custom_model_provider.command("update-proxy")
def update_proxy(
    gateway_id: Annotated[str, typer.Argument(help="Model proxy gateway ID")],
    tags: Annotated[str | None, typer.Option("--tags", help="Resource tags (JSON format)")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Update an existing model proxy

    Examples:
        agentarts custom-model-provider update-proxy 123 --tags '[{"key": "Environment", "value": "test"}]'
    """
    try:
        tags_config = _parse_json(tags)

        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.update_model_proxy(
            gateway_id=gateway_id,
            tags=tags_config,
        )

        if result.success:
            echo_success("Model proxy updated successfully:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("updating model proxy", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


@custom_model_provider.command("disassociate-proxies")
def disassociate_proxies(
    unbindings: Annotated[str, typer.Option("--unbindings", help="Unbindings list (JSON format), each item is {\"custom_model_provider_id\": \"...\", \"gateway_id\": \"...\"}")],
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    Batch disassociate model proxies from model providers

    Examples:
        agentarts custom-model-provider disassociate-proxies --unbindings '[{"custom_model_provider_id": "123", "gateway_id": "456"}]'
    """
    try:
        unbindings_list = _parse_json(unbindings)

        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.batch_disassociate_model_proxies(
            unbindings=unbindings_list,
        )

        if result.success:
            echo_success("Model proxies disassociated successfully:")
            echo_success(_format_output(result.data))
        else:
            _handle_error("disassociating model proxies", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")


# Quota commands


@custom_model_provider.command("list-quotas")
def list_quotas(
    custom_model_provider_id: Annotated[str | None, typer.Option("--custom-model-provider-id", help="Model provider ID")] = None,
    limit: Annotated[int | None, typer.Option("--limit", help="Limit for pagination (default: 50, min: 1, max: 100)")] = None,
    offset: Annotated[int | None, typer.Option("--offset", help="Offset for pagination (default: 0, min: 0, max: 100000)")] = None,
    skip_ssl_verification: Annotated[bool, typer.Option("--skip-ssl-verification", "-k", help="Skip SSL certificate verification")] = False,
):
    """
    List model management quotas

    Examples:
        agentarts custom-model-provider list-quotas
    """
    try:
        limit, offset = _validate_pagination(limit, offset)

        client = _get_model_provider_client(verify_ssl=not skip_ssl_verification)
        result = client.list_model_management_quotas(
            custom_model_provider_id=custom_model_provider_id,
            limit=limit,
            offset=offset,
        )

        if result.success:
            echo_success(f"Total quotas: {result.data.get('total', 0)}")
            echo_success("Quotas:")
            echo_success(_format_output(result.data.get("quotas", [])))
        else:
            _handle_error("listing quotas", result)
    except ValueError as e:
        echo_error(f"{e}")
    except Exception as e:
        echo_error(f"Unexpected error: {e}")
