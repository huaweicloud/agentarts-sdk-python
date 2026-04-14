import asyncio
import logging
import uuid
from functools import wraps
from typing import Any, Callable, Dict, List, Literal, Optional

from huaweicloudsdkagentidentity.v1 import (
    GetResourceStsTokenResponseBodyCredentials,
    StsTag,
    WorkloadIdentity,
)

from agentarts.sdk.identity.config import Config
from agentarts.sdk.runtime.context import (
    AgentArtsRuntimeContext,
    run_async_in_sync_context,
)
from agentarts.sdk.service.identity.identity_client import IdentityClient
from agentarts.sdk.service.identity.polling.token_poller import TokenPoller
from agentarts.sdk.utils.constant import get_region

logger = logging.getLogger(__name__)


def require_access_token(
    *,
    provider_name: str,
    into: str = "access_token",
    scopes: Optional[List[str]] = None,
    on_auth_url: Optional[Callable[[str], Any]] = None,
    auth_flow: Literal["M2M", "USER_FEDERATION"],
    callback_url: Optional[str] = None,
    force_authentication: bool = False,
    token_poller: Optional[TokenPoller] = None,
    custom_state: Optional[str] = None,
    custom_parameters: Optional[Dict[str, str]] = None,
    ignore_ssl_verification: Optional[bool] = None,
) -> Callable:
    """Decorator that fetches an OAuth2 access token before calling the decorated function.

    Args:
        provider_name: The credential provider name
        into: Parameter name to inject the token into
        scopes: OAuth2 scopes to request
        on_auth_url: Callback for handling authorization URLs
        auth_flow: Authentication flow type ("M2M" or "USER_FEDERATION")
        callback_url: OAuth2 callback URL
        force_authentication: Force re-authentication
        token_poller: Custom token poller implementation
        custom_state: A state that allows applications to verify the validity of callbacks to callback_url
        custom_parameters: A map of custom parameters to include in authorization request to the credential provider
                           Note: these parameters are in addition to standard OAuth 2.0 flow parameters
        ignore_ssl_verification: Whether to ignore SSL verification

    Returns:
        Decorator function
    """
    client = IdentityClient(
        region=get_region(), ignore_ssl_verification=ignore_ssl_verification
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs_func: Any) -> Any:
            token = await _get_resource_oauth2_token()
            kwargs_func[into] = token
            return await func(*args, **kwargs_func)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs_func: Any) -> Any:
            token = run_async_in_sync_context(_get_resource_oauth2_token())
            kwargs_func[into] = token
            return func(*args, **kwargs_func)

        # Return the appropriate wrapper based on a function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    async def _get_resource_oauth2_token() -> str:
        """Common token fetching logic."""
        return await client.get_resource_oauth2_token(
            provider_name=provider_name,
            workload_access_token=_get_workload_access_token(client),
            scopes=scopes,
            on_auth_url=on_auth_url,
            auth_flow=auth_flow,
            callback_url=_get_oauth2_callback_url(callback_url),
            force_authentication=force_authentication,
            token_poller=token_poller,
            custom_state=_get_oauth2_custom_state(custom_state),
            custom_parameters=custom_parameters,
        )

    return decorator


def require_api_key(
    *,
    provider_name: str,
    into: str = "api_key",
    ignore_ssl_verification: Optional[bool] = None,
) -> Callable:
    """Decorator that fetches an API key before calling the decorated function.

    Args:
        provider_name: The credential provider name
        into: Parameter name to inject the API key into
        ignore_ssl_verification: Whether to ignore SSL verification

    Returns:
        Decorator function
    """
    client = IdentityClient(
        region=get_region(), ignore_ssl_verification=ignore_ssl_verification
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            kwargs[into] = _get_api_key()
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            kwargs[into] = _get_api_key()
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    def _get_api_key():
        return client.get_resource_api_key(
            provider_name=provider_name,
            workload_access_token=_get_workload_access_token(client),
        )

    return decorator


def require_sts_token(
    *,
    provider_name: str,
    agency_session_name: str,
    duration_seconds: Optional[int] = None,
    policy: Optional[str] = None,
    source_identity: Optional[str] = None,
    tags: Optional[List[StsTag]] = None,
    transitive_tag_keys: Optional[List[str]] = None,
    into: str = "sts_credentials",
    ignore_ssl_verification: Optional[bool] = None,
) -> Callable:
    """Decorator that fetches an STS token before calling the decorated function.

    The decorator injects STS credentials into the decorated function's keyword
    arguments. The injected value is of type :class:`StsCredentials` (aliased from
    ``GetResourceStsTokenResponseBodyCredentials``).

    **Injected Type:** :class:`~agent_identity_dev_sdk.types.StsCredentials`

    **Injected Type Attributes:**
        - ``access_key_id`` (str): The access key ID for authentication
        - ``secret_access_key`` (str): The secret access key for authentication
        - ``security_token`` (str): The temporary security token
        - ``expiration`` (str): The expiration time of the credentials

    Args:
        provider_name: The credential provider name
        agency_session_name: An identifier for the assumed agency session.
        duration_seconds: The duration, in seconds, of the agency session
        policy: IAM policy to further restrict the permissions of the STS token
        source_identity: The source identity specified by the user
        tags: A list of session tags to apply to the STS token
        transitive_tag_keys: A list of keys for session tags that are transitive
        into: Parameter name to inject the STS token into
        ignore_ssl_verification: Whether to ignore SSL verification

    Returns:
        Decorator function

    Example:
        >>> from agentarts import require_sts_token, StsCredentials
        >>> @require_sts_token(provider_name="huaweicloud-iam", agency_session_name="example-session")
        ... async def access_resource(sts_credentials: StsCredentials | None = None):
        ...     print(f"AK: {sts_credentials.access_key_id}")
        ...     print(f"SK: {sts_credentials.secret_access_key}")
    """
    client = IdentityClient(
        region=get_region(), ignore_ssl_verification=ignore_ssl_verification
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            kwargs[into] = _get_sts_token()
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            kwargs[into] = _get_sts_token()
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    def _get_sts_token() -> GetResourceStsTokenResponseBodyCredentials:
        return client.get_resource_sts_token(
            provider_name=provider_name,
            workload_access_token=_get_workload_access_token(client),
            agency_session_name=agency_session_name,
            duration_seconds=duration_seconds,
            policy=policy,
            source_identity=source_identity,
            tags=tags,
            transitive_tag_keys=transitive_tag_keys,
        )

    return decorator


def _get_workload_access_token(client: IdentityClient) -> str:
    token = AgentArtsRuntimeContext.get_workload_access_token()
    if token is not None:
        logger.info("Retrieved workload access token from context")
        return token
    else:
        # workload access token context var was not set, so we should be running in a local dev environment
        logger.info(
            "No workload access token found in context. Falling back to local authentication setup."
        )
        return _set_up_local_auth(client)


def _get_oauth2_callback_url(
    user_provided_oauth2_callback_url: Optional[str],
) -> Optional[str]:
    if user_provided_oauth2_callback_url:
        return user_provided_oauth2_callback_url

    return AgentArtsRuntimeContext.get_oauth2_callback_url()


def _get_oauth2_custom_state(
    user_provided_custom_state: Optional[str],
) -> Optional[str]:
    if user_provided_custom_state:
        return user_provided_custom_state

    return AgentArtsRuntimeContext.get_oauth2_custom_state()


def _set_up_local_auth(client: IdentityClient) -> str:
    def _ensure_workload_identity(client: IdentityClient, config: Config) -> str:
        """Ensure a workload identity exists, either from config or by creating it."""
        workload_identity_name = config.workload_identity_name
        if workload_identity_name:
            logger.info(
                "Found existing workload identity from %s: %s",
                config.path.absolute(),
                workload_identity_name,
            )
        else:
            workload_identity: WorkloadIdentity = client.create_workload_identity()
            logger.info("Created a workload identity")
            workload_identity_name = workload_identity.name
            config.workload_identity_name = workload_identity.name
            config.save()
        return workload_identity_name

    def _ensure_user_id(config: Config) -> str:
        """Ensure a user ID exists, checking context, then config, then generating one."""
        user_id = AgentArtsRuntimeContext.get_user_id()
        if user_id:
            logger.info("Using user id from context: %s", user_id)
        else:
            # Fallback: User ID from config or generate
            user_id = config.user_id
            if user_id:
                logger.info(
                    "Found existing user id from %s: %s",
                    config.path.absolute(),
                    user_id,
                )
            else:
                user_id = uuid.uuid4().hex[:8]
                logger.info("Created an user id")
                config.user_id = user_id
                config.save()
        return user_id

    config = Config.load()

    workload_identity_name = _ensure_workload_identity(client, config)

    user_id = _ensure_user_id(config)

    return client.create_workload_access_token(workload_identity_name, user_id=user_id)

