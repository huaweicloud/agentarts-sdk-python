"""
Metadata utilities for credential management.
"""

import json
import logging
from functools import wraps

import requests
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.auth.provider import (
    CredentialProvider,
    CredentialProviderChain,
    EnvCredentialProvider,
    ProfileCredentialProvider,
)


def create_credential():
    """
    Create credentials using CredentialProviderChain.

    This method chains multiple credential providers in order:
    1. EnvCredentialProvider - reads credentials from environment variables
    2. ProfileCredentialProvider - reads credentials from configuration files

    Returns:
        Credentials: The created credentials object
    """
    env_provider = EnvCredentialProvider.get_basic_credential_env_provider()
    profile_provider = ProfileCredentialProvider.get_basic_credential_profile_provider()

    chain = CredentialProviderChain([env_provider, profile_provider, MetadataProvider()])

    return chain.get_credentials()


def require_credentials(*, key: str = "credentials"):
    """
    Decorator to ensure credentials are available for a function.

    This decorator creates credentials using create_credential() and passes them
    to the decorated function as a keyword argument with the specified key.

    Args:
        key: The keyword argument name to use for passing credentials

    Returns:
        Callable: The decorated function
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if key not in kwargs:
                kwargs[key] = create_credential()

            return func(*args, **kwargs)

        return wrapper

    return decorator


class MetadataProvider(CredentialProvider):
    """Credential provider that fetches credentials from metadata service."""

    METADATA_ENDPOINT = "http://169.254.169.254"
    GET_SECURITY_KEY_PATH = "v1/metadata/securitykey"
    DEFAULT_TIMEOUT = (3, 3)

    def __init__(self):
        self.logger = logging.getLogger("agentarts.sdk.metadata_provider")

    def get_credentials(self) -> BasicCredentials:
        """
        Get credentials from metadata service.

        Returns:
            BasicCredentials: The credentials object

        Raises:
            ValueError: If credentials cannot be obtained
        """
        url = self.METADATA_ENDPOINT + "/" + self.GET_SECURITY_KEY_PATH
        headers = {}

        try:
            resp = requests.get(url=url, headers=headers, timeout=self.DEFAULT_TIMEOUT)

            if resp.status_code < 300:
                metadata = json.loads(resp.text)
                self.logger.info(f"Get metadata credentials with expired time: {metadata['expires_at']}")
                return BasicCredentials() \
                    .with_ak(metadata["access"]) \
                    .with_sk(metadata["secret"]) \
                    .with_security_token(metadata["securitytoken"])

            self.logger.warning(f"Get metadata credentials failed with status: {resp.status_code}")
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Failed to connect to metadata service: {e}")

        msg = (
            "Authentication failed: Could not find valid credentials. "
            "Please configure one of the following:\n"
            "1. AK/SK Authentication: Set HUAWEICLOUD_SDK_AK, HUAWEICLOUD_SDK_SK\n"
            "2. OIDC Token: Set HUAWEICLOUD_SDK_IDP_ID, HUAWEICLOUD_SDK_ID_TOKEN_FILE, "
            "and HUAWEICLOUD_SDK_PROJECT_ID\n"
            "3. Metadata: Running on the AgentArts runtime"
        )
        raise ValueError(
            msg
        )
