"""Type aliases for improved developer experience.

This module provides user-friendly type aliases for types used throughout the SDK.
These aliases make injected types discoverable without reading source code.
"""

import sys
from typing import TypeAlias

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


from huaweicloudsdkagentidentity.v1 import (
    CredentialProviderVendor,
    GetResourceStsTokenResponseBodyCredentials,
    Oauth2Discovery,
)

StsCredentials: TypeAlias = GetResourceStsTokenResponseBodyCredentials
"""Type alias for STS token credentials.

This type is injected by the @require_sts_token decorator into your function.

Attributes:
    access_key_id: The access key ID for authentication
    secret_access_key: The secret access key for authentication
    security_token: The temporary security token
    expiration: The expiration time of the credentials

Example:
    >>> from agentarts import require_sts_token, StsCredentials
    >>> @require_sts_token(provider_name="huaweicloud-iam", agency_session_name="example-session")
    ... async def my_func(sts_credentials: StsCredentials | None = None):
    ...     print(sts_credentials.access_key_id)
"""

OAuth2Discovery: TypeAlias = Oauth2Discovery


class OAuth2Vendor(StrEnum):
    """OAuth2 credential provider vendors.

    Values are sourced from the SDK's CredentialProviderVendor class constants.

    Example:
        >>> from agentarts import OAuth2Vendor
        >>> OAuth2Vendor.GOOGLEOAUTH2
        'GoogleOauth2'
    """

    GITHUBOAUTH2 = CredentialProviderVendor.GITHUBOAUTH2
    GOOGLEOAUTH2 = CredentialProviderVendor.GOOGLEOAUTH2
    MICROSOFTOAUTH2 = CredentialProviderVendor.MICROSOFTOAUTH2
    CUSTOMOAUTH2 = CredentialProviderVendor.CUSTOMOAUTH2
