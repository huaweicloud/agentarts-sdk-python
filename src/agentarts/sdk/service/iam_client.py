"""
IAM Client Module

Provides HTTP client implementation for IAM (Identity and Access Management) operations.
"""
from typing import Optional


class IAMClient:
    """
    IAM Client for making API calls to IAM service.
    
    Uses huaweicloudsdkiam.v5.IamClient to make API calls.
    """
    
    def __init__(self):
        """
        Initialize IAM client.
        
        All configuration will be loaded from environment variables via constant module.
        """
        # Do not execute any code here
        pass
    
    def _get_iam_client(self):
        """
        Get IAM client instance.
        
        Returns:
            IamClient: IAM client instance
        """
        # Import modules here to avoid dependency issues
        from huaweicloudsdkiam.v5 import IamClient
        from huaweicloudsdkcore.region import Region
        from huaweicloudsdkcore.http.http_config import HttpConfig
        from agentarts.sdk.utils.metadata import get_credentials
        from agentarts.sdk.utils.constant import get_region, get_iam_endpoint
        
        # Create credentials
        credentials = get_credentials()
        
        # Create HTTP config with ignore_ssl_verification=True
        http_config = HttpConfig.get_default_config()
        http_config.ignore_ssl_verification = True
        
        # Create region object
        final_region = Region(id=get_region(), endpoint=get_iam_endpoint())

        # Create IamClient using builder pattern
        builder = IamClient.new_builder()\
            .with_credentials(credentials)\
            .with_region(final_region)\
            .with_http_config(http_config)
        
        # Build and return the client
        return builder.build()
    
    def create_agency(
        self,
        agency_name: str,
        trust_policy: str,
        path: Optional[str] = None,
        max_session_duration: Optional[int] = None,
        description: Optional[str] = None
    ):
        """
        Create a new IAM agency (trust delegation).
        
        Args:
            agency_name: Agency name, length 1-64 characters
            trust_policy: Trust policy document as a JSON string
            path: Resource path, default is empty string
            max_session_duration: Maximum session duration in seconds, range [3600, 43200]
            description: Agency description, max length 1000
            
        Returns:
            Response object from huaweicloudsdkiam.v5
            
        Reference: https://support.huaweicloud.com/api-iam5/CreateAgencyV5.html
        """
        # Import modules here to avoid dependency issues
        from huaweicloudsdkiam.v5.model import CreateAgencyV5Request
        
        # Get IAM client
        iam_client = self._get_iam_client()
        
        # Create request
        request = CreateAgencyV5Request()
        request.agency_name = agency_name
        request.trust_policy = trust_policy
        request.path = path
        request.max_session_duration = max_session_duration
        request.description = description
        
        # Call the API and return the response
        return iam_client.create_agency_v5(request)
