import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, List, Literal, Optional

from huaweicloudsdkagentidentity.v1 import (
    AgentIdentityClient,
    ApiKeyCredentialProvider,
    CompleteResourceTokenAuthRequest,
    CompleteResourceTokenAuthRequestBody,
    CompleteResourceTokenAuthResponse,
    CreateApiKeyCredentialProviderReqBody,
    CreateApiKeyCredentialProviderRequest,
    CreateApiKeyCredentialProviderResponse,
    CreateOauth2CredentialProviderReqBody,
    CreateOauth2CredentialProviderRequest,
    CreateOauth2CredentialProviderResponse,
    CreateStsCredentialProviderReqBody,
    CreateStsCredentialProviderRequest,
    CreateStsCredentialProviderResponse,
    StsCredentialProvider,
    Tag,
    CreateWorkloadIdentityReqBody,
    CreateWorkloadIdentityRequest,
    CreateWorkloadIdentityResponse,
    CustomOauth2ProviderConfigInput,
    GetResourceApiKeyRequest,
    GetResourceApiKeyRequestBody,
    GetResourceApiKeyResponse,
    GetResourceOauth2TokenRequest,
    GetResourceOauth2TokenRequestBody,
    GetResourceOauth2TokenResponse,
    GetResourceStsTokenRequest,
    GetResourceStsTokenRequestBody,
    GetResourceStsTokenResponse,
    CreateWorkloadAccessTokenForJwtRequest,
    CreateWorkloadAccessTokenForJwtRequestBody,
    CreateWorkloadAccessTokenForJwtResponse,
    CreateWorkloadAccessTokenForUserIdRequest,
    CreateWorkloadAccessTokenForUserIdRequestBody,
    CreateWorkloadAccessTokenForUserIdResponse,
    CreateWorkloadAccessTokenRequest,
    CreateWorkloadAccessTokenRequestBody,
    CreateWorkloadAccessTokenResponse,
    GithubOauth2ProviderConfigInput,
    GoogleOauth2ProviderConfigInput,
    MicrosoftOauth2ProviderConfigInput,
    Oauth2CredentialProvider,
    Oauth2ProviderConfigInput,
    StsTag,
    UpdateWorkloadIdentityReqBody,
    UpdateWorkloadIdentityRequest,
    UpdateWorkloadIdentityResponse,
    UserIdentifier,
    WorkloadIdentity,
    AuthorizerType,
)
from huaweicloudsdkagentidentity.v1.region.agentidentity_region import (
    AgentIdentityRegion,
)
from huaweicloudsdkcore.exceptions.exceptions import (
    SdkException,
    ServiceResponseException,
)
from huaweicloudsdkcore.region.region import Region
from huaweicloudsdkcore.http.http_config import HttpConfig
from huaweicloudsdkcore.retry.backoff_strategy import BackoffStrategies
from huaweicloudsdkcore.sdk_response import SdkResponse

from agentarts.sdk.service.identity.polling.token_poller import (
    DefaultApiTokenPoller,
    PollingResult,
    PollingStatus,
    TokenPoller,
)
from agentarts.sdk.identity.types import (
    OAuth2Discovery,
    OAuth2Vendor,
    StsCredentials,
)
from agentarts.sdk.utils.constant import get_identity_endpoint


class IdentityClient:
    """A high-level client for Agent Identity."""

    def __init__(
        self,
        region: str,
        ignore_ssl_verification: Optional[bool] = None,
        client: Optional[AgentIdentityClient] = None,
    ) -> None:
        """Initialize the identity client with the specified region.

        Args:
            region: The region name (e.g., 'ap-southeast-4').
            ignore_ssl_verification: Whether to ignore SSL verification.
            client: Optional AgentIdentityClient instance to inject.
        """
        self.logger = logging.getLogger("agentarts.identity_client")
        self.region = region

        # Determine SSL verification behavior
        if ignore_ssl_verification is None:
            ignore_ssl_verification = False

        sdk_region = Region(id=region, endpoint=get_identity_endpoint(region))

        # Set HTTP configuration
        http_config = HttpConfig.get_default_config()
        http_config.ignore_ssl_verification = ignore_ssl_verification

        # Initialize clients using builder pattern
        if client is not None:
            self.client = client
        else:
            from agentarts.sdk.utils.metadata import create_credential
            credentials = create_credential()
            self.client = (
                AgentIdentityClient.new_builder()
                .with_region(sdk_region)
                .with_http_config(http_config)
                .with_credentials(credentials)
                .build()
            )

        self.logger.info(
            f"Initialized Huawei Cloud Agent Identity client for region: {region}"
        )

    @staticmethod
    def _should_retry(
        resp: Optional[SdkResponse], exception: Optional[SdkException]
    ) -> bool:
        """Determines if a request should be retried based on response or exception.

        Retries on:
        - Throttling (429)
        - Server Errors (5xx)
        - Network issues (Connection/Timeout errors)
        """
        if exception:
            if isinstance(exception, ServiceResponseException):
                # Retry on throttling (429) or Server Errors (5xx)
                return exception.status_code == 429 or exception.status_code >= 500
            # For other SdkExceptions (ConnectionException, TimeoutException), retry
            return True

        if resp and hasattr(resp, "status_code"):
            # Some responses might not raise exceptions but still return error codes
            return resp.status_code is not None and (
                resp.status_code == 429 or resp.status_code >= 500
            )

        return False

    def create_workload_identity(
        self,
        name: Optional[str] = None,
        allowed_resource_oauth2_return_urls: Optional[List[str]] = None,
        authorizer_type: Optional[str] = AuthorizerType.NONE,
        authorizer_configuration: Optional[Any] = None,
    ) -> WorkloadIdentity:
        """Create workload identity with optional name.

        Args:
            name: Optional name for the workload identity. If not provided, a random name is generated.
            allowed_resource_oauth2_return_urls: Optional list of OAuth2 callback URLs.
            authorizer_type: The type of authorizer for the workload identity. Defaults to AuthorizerType.NONE.
            authorizer_configuration: Optional authorizer configuration.

        Returns:
            The created WorkloadIdentity object.
        """
        self.logger.info("Creating workload identity...")
        if not name:
            name = f"workload-{uuid.uuid4().hex[:8]}"

        response: CreateWorkloadIdentityResponse = self.client.create_workload_identity(
            request=CreateWorkloadIdentityRequest(
                body=CreateWorkloadIdentityReqBody(
                    name=name,
                    allowed_resource_oauth2_return_urls=allowed_resource_oauth2_return_urls
                    or [],
                    authorizer_type=authorizer_type,
                    authorizer_configuration=authorizer_configuration,
                )
            )
        )

        # Convert response to dictionary format
        return response.workload_identity

    def update_workload_identity(
        self,
        name: str,
        allowed_resource_oauth2_return_urls: Optional[List[str]] = None,
        authorizer_configuration: Optional[Any] = None,
    ) -> WorkloadIdentity:
        """Updates an existing workload identity configuration.

        Args:
            name: The name of the workload identity to update.
            allowed_resource_oauth2_return_urls: Optional list of OAuth2 callback URLs.
            authorizer_configuration: Optional authorizer configuration.

        Returns:
            The updated WorkloadIdentity object.
        """
        self.logger.info(f"Updating workload identity: {name}")

        response: UpdateWorkloadIdentityResponse = self.client.update_workload_identity(
            request=UpdateWorkloadIdentityRequest(
                workload_identity_name=name,
                body=UpdateWorkloadIdentityReqBody(
                    allowed_resource_oauth2_return_urls=allowed_resource_oauth2_return_urls,
                    authorizer_configuration=authorizer_configuration,
                ),
            )
        )
        return response.workload_identity

    def create_api_key_credential_provider(
        self,
        name: str,
        api_key: str,
    ) -> ApiKeyCredentialProvider:
        """Creates a new API key credential provider.

        Args:
            name: The name of the credential provider.
            api_key: The API key for the credential provider.

        Returns:
            The created ApiKeyCredentialProvider object.
        """
        self.logger.info(f"Creating API key credential provider: {name}")

        response: CreateApiKeyCredentialProviderResponse = (
            self.client.create_api_key_credential_provider(
                request=CreateApiKeyCredentialProviderRequest(
                    body=CreateApiKeyCredentialProviderReqBody(
                        name=name, api_key=api_key
                    )
                )
            )
        )
        return response.credential_provider

    def create_oauth2_credential_provider(
        self,
        name: str,
        vendor: OAuth2Vendor,
        client_id: str,
        client_secret: str,
        tenant_id: Optional[str] = None,
        oauth_discovery: Optional[OAuth2Discovery] = None,
        tags: Optional[List[Tag]] = None,
    ) -> Oauth2CredentialProvider:
        """Creates a new OAuth2 credential provider.

        Args:
            name: The name of the credential provider.
            vendor: The vendor of the OAuth2 provider (OAuth2Vendor enum).
            client_id: The client ID for the OAuth2 provider.
            client_secret: The client secret for the OAuth2 provider.
            tenant_id: The tenant ID (required for MICROSOFTOAUTH2).
            oauth_discovery: The OAuth2 discovery configuration (required for CUSTOMOAUTH2).
            tags: Optional tags for the credential provider.

        Returns:
            The created Oauth2CredentialProvider object.

        Raises:
            ValueError: If an unsupported vendor is provided.
        """
        self.logger.info(f"Creating OAuth2 credential provider: {name}")

        config_kwargs = {"client_id": client_id, "client_secret": client_secret}

        if vendor == OAuth2Vendor.GITHUBOAUTH2:
            config = Oauth2ProviderConfigInput(
                github_oauth2_provider_config=GithubOauth2ProviderConfigInput(
                    **config_kwargs
                )
            )
        elif vendor == OAuth2Vendor.GOOGLEOAUTH2:
            config = Oauth2ProviderConfigInput(
                google_oauth2_provider_config=GoogleOauth2ProviderConfigInput(
                    **config_kwargs
                )
            )
        elif vendor == OAuth2Vendor.MICROSOFTOAUTH2:
            config = Oauth2ProviderConfigInput(
                microsoft_oauth2_provider_config=MicrosoftOauth2ProviderConfigInput(
                    tenant_id=tenant_id, **config_kwargs
                )
            )
        elif vendor == OAuth2Vendor.CUSTOMOAUTH2:
            config = Oauth2ProviderConfigInput(
                custom_oauth2_provider_config=CustomOauth2ProviderConfigInput(
                    oauth2_discovery=oauth_discovery, **config_kwargs
                )
            )
        else:
            raise ValueError(f"Unsupported vendor: {vendor}")

        response: CreateOauth2CredentialProviderResponse = (
            self.client.create_oauth2_credential_provider(
                request=CreateOauth2CredentialProviderRequest(
                    body=CreateOauth2CredentialProviderReqBody(
                        name=name,
                        credential_provider_vendor=vendor,
                        oauth2_provider_config_input=config,
                        tags=tags,
                    )
                )
            )
        )
        return response.credential_provider

    def create_sts_credential_provider(
        self,
        name: str,
        agency_urn: str,
        tags: Optional[List[Tag]] = None,
    ) -> StsCredentialProvider:
        """Creates a new STS credential provider.

        Args:
            name: The name of the credential provider.
            agency_urn: The IAM agency URN.
            tags: Optional tags for the credential provider.

        Returns:
            The created StsCredentialProvider object.
        """
        self.logger.info(f"Creating STS credential provider: {name}")

        response: CreateStsCredentialProviderResponse = (
            self.client.create_sts_credential_provider(
                request=CreateStsCredentialProviderRequest(
                    body=CreateStsCredentialProviderReqBody(
                        name=name, agency_urn=agency_urn, tags=tags
                    )
                )
            )
        )
        return response.credential_provider

    def create_workload_access_token(
        self,
        workload_name: str,
        user_token: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Get a workload access token using workload name and optionally user token.

        Args:
            workload_name: The name of the workload identity.
            user_token: Optional IAM user token for authentication.
            user_id: Optional user ID for authentication.

        Returns:
            The retrieved workload access token.
        """
        if user_token:
            if user_id is not None:
                self.logger.warning(
                    "Both user token and user id are supplied, using user token"
                )
            self.logger.info("Getting workload access token for JWT...")
            # Create request for JWT-based token
            invoker = self.client.create_workload_access_token_for_jwt_invoker(
                request=CreateWorkloadAccessTokenForJwtRequest(
                    body=CreateWorkloadAccessTokenForJwtRequestBody(
                        workload_name=workload_name, user_token=user_token
                    )
                )
            )
            resp: CreateWorkloadAccessTokenForJwtResponse = invoker.with_retry(
                retry_condition=self._should_retry,
                max_retries=3,
                backoff_strategy=BackoffStrategies.EQUAL_JITTER,
            ).invoke()
        elif user_id:
            self.logger.info("Getting workload access token for user id...")
            # Create request for user ID-based token
            invoker = self.client.create_workload_access_token_for_user_id_invoker(
                request=CreateWorkloadAccessTokenForUserIdRequest(
                    body=CreateWorkloadAccessTokenForUserIdRequestBody(
                        workload_name=workload_name, user_id=user_id
                    )
                )
            )
            resp: CreateWorkloadAccessTokenForUserIdResponse = invoker.with_retry(
                retry_condition=self._should_retry,
                max_retries=3,
                backoff_strategy=BackoffStrategies.EQUAL_JITTER,
            ).invoke()
        else:
            self.logger.info("Getting workload access token...")
            # Create basic workload access token request
            invoker = self.client.create_workload_access_token_invoker(
                request=CreateWorkloadAccessTokenRequest(
                    body=CreateWorkloadAccessTokenRequestBody(
                        workload_name=workload_name
                    )
                )
            )
            resp: CreateWorkloadAccessTokenResponse = invoker.with_retry(
                retry_condition=self._should_retry,
                max_retries=3,
                backoff_strategy=BackoffStrategies.EQUAL_JITTER,
            ).invoke()

        self.logger.info("Successfully retrieved workload access token")
        return resp.workload_access_token

    async def get_resource_oauth2_token(
        self,
        *,
        provider_name: str,
        scopes: Optional[List[str]] = None,
        workload_access_token: str,
        on_auth_url: Optional[Callable[[str], Any]] = None,
        auth_flow: Literal["M2M", "USER_FEDERATION"],
        callback_url: Optional[str] = None,
        force_authentication: bool = False,
        token_poller: Optional[TokenPoller] = None,
        custom_state: Optional[str] = None,
        custom_parameters: Optional[Dict[str, str]] = None,
    ) -> str:
        """Get an OAuth2 access token for the specified provider.

        Args:
            provider_name: The credential provider name
            scopes: Optional list of OAuth2 scopes to request
            workload_access_token: Agent identity token for authentication
            on_auth_url: Callback for handling authorization URLs
            auth_flow: Authentication flow type ("M2M" or "USER_FEDERATION")
            callback_url: OAuth2 callback URL (must be pre-registered)
            force_authentication: Force re-authentication even if token exists in the token vault
            token_poller: Custom token poller implementation
            custom_state: A state that allows applications to verify the validity of callbacks to callback_url
            custom_parameters: A map of custom parameters to include in authorization request to the credential provider
                               Note: these parameters are in addition to standard OAuth 2.0 flow parameters

        Returns:
            The access token string

        Raises:
            RuntimeError: If the Identity service does not return a token or an authorization URL.
        """
        self.logger.info("Getting OAuth2 token...")

        # Helper to execute the SDK request
        def get_token(
            current_session_uri: Optional[str] = None, is_polling: bool = False
        ) -> GetResourceOauth2TokenResponse:
            # Note: force_authentication should only be true on the initial call, not while polling
            effective_force_auth = force_authentication if not is_polling else False

            return self.client.get_resource_oauth2_token(
                GetResourceOauth2TokenRequest(
                    body=GetResourceOauth2TokenRequestBody(
                        resource_credential_provider_name=provider_name,
                        workload_access_token=workload_access_token,
                        oauth2_flow=auth_flow,
                        scopes=scopes,
                        resource_oauth2_return_url=callback_url,
                        force_authentication=effective_force_auth,
                        custom_state=custom_state,
                        custom_parameters=custom_parameters,
                        session_uri=current_session_uri,
                    )
                )
            )

        # Make initial call
        response: GetResourceOauth2TokenResponse = get_token()

        # If we got a token directly (usually M2M flow), return it
        if response.access_token:
            self.logger.info("Successfully retrieved OAuth2 token directly.")
            return response.access_token

        # Handle User Authorization flow (3LO)
        if response.authorization_url:
            auth_url = response.authorization_url
            session_uri = response.session_uri

            self.logger.info(f"User consent required. Auth URL: {auth_url}")

            # Notify the caller about the auth URL
            if on_auth_url:
                if asyncio.iscoroutinefunction(on_auth_url):
                    await on_auth_url(auth_url)
                else:
                    on_auth_url(auth_url)

            # Define the polling logic using the SDK
            def poll_fn() -> PollingResult:
                resp: GetResourceOauth2TokenResponse = get_token(
                    current_session_uri=session_uri, is_polling=True
                )
                if resp.access_token:
                    return PollingResult(access_token=resp.access_token)
                if resp.session_status == PollingStatus.FAILED:
                    return PollingResult(status=PollingStatus.FAILED)
                return PollingResult(status=PollingStatus.IN_PROGRESS)

            # Use the provided poller or the default one
            active_poller = token_poller or DefaultApiTokenPoller(auth_url, poll_fn)

            return await active_poller.poll_for_token()

        raise RuntimeError(
            "Identity service did not return a token or an authorization URL."
        )

    def get_resource_api_key(
        self, *, provider_name: str, workload_access_token: str
    ) -> str:
        """Programmatically retrieves an API key from the Identity service.

        Args:
            provider_name: The credential provider name.
            workload_access_token: Agent identity token for authentication.

        Returns:
            The API key string.
        """
        self.logger.info("Getting API key...")

        invoker = self.client.get_resource_api_key_invoker(
            request=GetResourceApiKeyRequest(
                body=GetResourceApiKeyRequestBody(
                    resource_credential_provider_name=provider_name,
                    workload_access_token=workload_access_token,
                )
            )
        )
        response: GetResourceApiKeyResponse = invoker.with_retry(
            retry_condition=self._should_retry,
            max_retries=3,
            backoff_strategy=BackoffStrategies.EQUAL_JITTER,
        ).invoke()

        return response.api_key

    def get_resource_sts_token(
        self,
        *,
        provider_name: str,
        workload_access_token: str,
        agency_session_name: str,
        duration_seconds: Optional[int] = None,
        policy: Optional[str] = None,
        source_identity: Optional[str] = None,
        tags: Optional[List[StsTag]] = None,
        transitive_tag_keys: Optional[List[str]] = None,
    ) -> StsCredentials:
        """Get STS token from the Identity service.

        Args:
            provider_name: The credential provider name.
            workload_access_token: Agent identity token for authentication.
            agency_session_name: The session name for the agency.
            duration_seconds: The duration of the STS token in seconds.
            policy: The custom policy for the STS token.
            source_identity: The source identity for the STS token.
            tags: Optional list of STS tags.
            transitive_tag_keys: Optional list of transitive tag keys.

        Returns:
            The STS credentials object.
        """
        self.logger.info("Getting STS token...")

        invoker = self.client.get_resource_sts_token_invoker(
            request=GetResourceStsTokenRequest(
                body=GetResourceStsTokenRequestBody(
                    resource_credential_provider_name=provider_name,
                    workload_access_token=workload_access_token,
                    agency_session_name=agency_session_name,
                    duration_seconds=duration_seconds,
                    policy=policy,
                    source_identity=source_identity,
                    tags=tags,
                    transitive_tag_keys=transitive_tag_keys,
                )
            )
        )
        response: GetResourceStsTokenResponse = invoker.with_retry(
            retry_condition=self._should_retry,
            max_retries=3,
            backoff_strategy=BackoffStrategies.EQUAL_JITTER,
        ).invoke()

        return response.credentials

    def complete_resource_token_auth(
        self,
        session_uri: str,
        user_identifier: UserIdentifier,
    ) -> CompleteResourceTokenAuthResponse:
        """Confirms the user authentication session for obtaining OAuth2.0 tokens for a resource.

        Args:
            session_uri: The session URI for the authentication request.
            user_identifier: The user identifier object.

        Returns:
            The CompleteResourceTokenAuthResponse object.
        """
        self.logger.info("Completing 3LO OAuth2 flow...")

        response: CompleteResourceTokenAuthResponse = (
            self.client.complete_resource_token_auth(
                request=CompleteResourceTokenAuthRequest(
                    body=CompleteResourceTokenAuthRequestBody(
                        user_identifier=user_identifier, session_uri=session_uri
                    )
                )
            )
        )

        # Return the response
        return response
