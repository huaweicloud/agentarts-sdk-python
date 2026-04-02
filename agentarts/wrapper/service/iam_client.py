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
        from huaweicloudsdkiam.v5.region.iam_region import IamRegion
        from huaweicloudsdkcore.auth.credentials import BasicCredentials
        from huaweicloudsdkcore.http.http_config import HttpConfig
        from agentarts.wrapper.utils.constant import (
            HUAWEICLOUD_SDK_AK,
            HUAWEICLOUD_SDK_SK,
            HUAWEICLOUD_SDK_PROJECT_ID,
            get_region
        )
        
        # Get credentials from constant
        ak = HUAWEICLOUD_SDK_AK
        sk = HUAWEICLOUD_SDK_SK
        project_id = HUAWEICLOUD_SDK_PROJECT_ID
        region_id = get_region()
        
        # Create credentials
        credentials = BasicCredentials(
            ak=ak,
            sk=sk,
            project_id=project_id
        )
        
        # Create HTTP config with ignore_ssl_verification=True
        http_config = HttpConfig.get_default_config()
        http_config.ignore_ssl_verification = True
        
        # Create Region object using IamRegion.value_of
        region = IamRegion.value_of(region_id)
        
        # Create IamClient using builder pattern
        builder = IamClient.new_builder()\
            .with_credentials(credentials)\
            .with_region(region)\
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
