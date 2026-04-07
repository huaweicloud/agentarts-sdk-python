"""
Metadata utilities for credential management.
"""

from functools import wraps
from huaweicloudsdkcore.auth.provider import (
    EnvCredentialProvider,
    ProfileCredentialProvider,
    CredentialProviderChain
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
    # Create credential providers
    env_provider = EnvCredentialProvider.get_basic_credential_env_provider()
    profile_provider = ProfileCredentialProvider.get_basic_credential_profile_provider()
    
    # Create credential provider chain
    chain = CredentialProviderChain([env_provider, profile_provider])
    
    # Get credentials from the chain
    return chain.get_credentials()


def requires_credentials(*, key: str = "credentials"):
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
            # Create credentials if not provided
            if key not in kwargs:
                kwargs[key] = create_credential()
            
            # Call the original function
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator
