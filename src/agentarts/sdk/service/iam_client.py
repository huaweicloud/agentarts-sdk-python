"""
IAM Client Module

Provides HTTP client implementation for IAM (Identity and Access Management) operations.
"""


class IAMClient:
    """
    IAM Client for making API calls to IAM service.

    Uses huaweicloudsdkiam.v5.IamClient to make API calls.

    Args:
        verify_ssl: SSL verification setting (default: True). Can be:
            - True: Verify SSL certificates using system CA bundle
            - False: Skip SSL verification (not recommended for production)
            - str: Path to custom CA certificate file
    """

    def __init__(self, verify_ssl: bool | str = True):
        """
        Initialize IAM client.

        All configuration will be loaded from environment variables via constant module.

        Args:
            verify_ssl: SSL verification setting (default: True)
        """
        self._verify_ssl = verify_ssl

    def _get_iam_client(self):
        """
        Get IAM client instance.

        Returns:
            IamClient: IAM client instance
        """
        # Import modules here to avoid dependency issues
        from huaweicloudsdkcore.http.http_config import HttpConfig
        from huaweicloudsdkcore.region.region import Region
        from huaweicloudsdkiam.v5 import IamClient

        from agentarts.sdk.utils.constant import get_iam_endpoint, get_region
        from agentarts.sdk.utils.metadata import create_credential

        # Create credentials
        credentials = create_credential()

        # Create HTTP config
        http_config = HttpConfig.get_default_config()
        if isinstance(self._verify_ssl, str):
            http_config.ssl_ca_cert = self._verify_ssl
        else:
            http_config.ignore_ssl_verification = not self._verify_ssl

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
        path: str | None = None,
        max_session_duration: int | None = None,
        description: str | None = None
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
        from huaweicloudsdkiam.v5.model import CreateAgencyReqBody, CreateAgencyV5Request

        # Get IAM client
        iam_client = self._get_iam_client()

        # Create request
        body = CreateAgencyReqBody(
            agency_name=agency_name,
            trust_policy=trust_policy,
            path=path or "",
            max_session_duration=max_session_duration or 3600,
            description=description
        )
        request = CreateAgencyV5Request(body=body)

        # Call the API and return the response
        return iam_client.create_agency_v5(request)

    def list_policies(
        self,
        policy_type: str | None = None,
        limit: int | None = None,
        marker: str | None = None,
        path_prefix: str | None = None,
        only_attached: bool | None = None
    ):
        """
        List IAM policies.

        Args:
            policy_type: Policy type filter - "custom" or "system" (optional)
            limit: Number of items per page, range [1, 200], default 100
            marker: Page marker for pagination
            path_prefix: Resource path prefix (optional)
            only_attached: Only list policies with attached entities (optional)

        Returns:
            Response object from huaweicloudsdkiam.v5

        Reference: https://support.huaweicloud.com/api-iam5/ListPoliciesV5.html
        """
        from huaweicloudsdkiam.v5.model import ListPoliciesV5Request

        iam_client = self._get_iam_client()

        request = ListPoliciesV5Request()
        if policy_type is not None:
            request.policy_type = policy_type
        if limit is not None:
            request.limit = limit
        if marker is not None:
            request.marker = marker
        if path_prefix is not None:
            request.path_prefix = path_prefix
        if only_attached is not None:
            request.only_attached = only_attached

        return iam_client.list_policies_v5(request)

    def list_agencies(
        self,
        name: str | None = None,
        limit: int | None = None,
        marker: str | None = None,
        path_prefix: str | None = None,
        only_attached: bool | None = None
    ):
        """
        List IAM agencies.

        Args:
            name: Agency name to filter by (optional)
            limit: Number of items per page, range [1, 200], default 100
            marker: Page marker for pagination
            path_prefix: Resource path prefix (optional)
            only_attached: Only list agencies with attached entities (optional)

        Returns:
            Response object from huaweicloudsdkiam.v5

        Reference: https://support.huaweicloud.com/api-iam5/ListAgenciesV5.html
        """
        from huaweicloudsdkiam.v5.model import ListAgenciesV5Request

        iam_client = self._get_iam_client()

        request = ListAgenciesV5Request()
        if name is not None:
            request.name = name
        if limit is not None:
            request.limit = limit
        if marker is not None:
            request.marker = marker
        if path_prefix is not None:
            request.path_prefix = path_prefix
        if only_attached is not None:
            request.only_attached = only_attached

        return iam_client.list_agencies_v5(request)

    def attach_agency_policy(
        self,
        agency_id: str,
        policy_id: str
    ):
        """
        Attach a policy to an IAM agency.

        Args:
            agency_id: Agency ID (UUID format)
            policy_id: Policy ID to attach

        Returns:
            Response object from huaweicloudsdkiam.v5

        Reference: https://support.huaweicloud.com/api-iam5/AttachAgencyPolicyV5.html
        """
        from huaweicloudsdkiam.v5.model import AttachAgencyPolicyReqBody, AttachAgencyPolicyV5Request

        iam_client = self._get_iam_client()

        body = AttachAgencyPolicyReqBody(agency_id=agency_id)
        request = AttachAgencyPolicyV5Request(
            policy_id=policy_id,
            body=body
        )

        return iam_client.attach_agency_policy_v5(request)

    def create_agency_with_policy(
        self,
        agency_name: str,
        trust_policy: str,
        policy_name: str,
        path: str | None = None,
        max_session_duration: int | None = None,
        description: str | None = None
    ):
        """
        Create an IAM agency and attach a policy to it.

        This is a convenience method that combines:
        1. create_agency
        2. list_policies (to find the policy by name)
        3. attach_agency_policy

        Args:
            agency_name: Agency name, length 1-64 characters
            trust_policy: Trust policy document as a JSON string
            policy_name: Name of the policy to attach (e.g., "AgentArtsCoreGatewayIdentityAgencyPolicy")
            path: Resource path, default is empty string
            max_session_duration: Maximum session duration in seconds, range [3600, 43200]
            description: Agency description, max length 1000

        Returns:
            Response object from create_agency if successful

        Raises:
            ValueError: If the specified policy is not found
            Exception: If any API call fails (except 409 Conflict for agency already exists)
        """
        agency_id = None

        try:
            create_response = self.create_agency(
                agency_name=agency_name,
                trust_policy=trust_policy,
                path=path,
                max_session_duration=max_session_duration,
                description=description
            )
            agency_id = create_response.agency_id
        except Exception as e:
            if "409" not in str(e):
                raise
            # Agency already exists, need to get its ID from list_agencies
            list_response = self.list_agencies(name=agency_name)

            agencies = list_response.agencies or []
            matching_agency = None
            for agency in agencies:
                if agency.agency_name == agency_name:
                    matching_agency = agency
                    break

            if not matching_agency:
                raise ValueError(f"Agency '{agency_name}' already exists but cannot be found in list")

            agency_id = matching_agency.agency_id

        if not agency_id:
            raise ValueError("Failed to get agency_id")

        matching_policy = None
        marker = None

        while True:
            list_response = self.list_policies(
                policy_type="system",
                limit=200,
                marker=marker
            )
            policies = list_response.policies or []

            for policy in policies:
                if policy.policy_name == policy_name:
                    matching_policy = policy
                    break

            if matching_policy:
                break

            page_info = list_response.page_info
            if not page_info or not page_info.next_marker:
                break

            marker = page_info.next_marker

        if not matching_policy:
            raise ValueError(f"Policy '{policy_name}' not found in system policies")

        try:
            self.attach_agency_policy(
                agency_id=agency_id,
                policy_id=matching_policy.policy_id
            )
        except Exception as e:
            # If policy already attached (409), ignore the error
            if "409" not in str(e):
                raise

        return create_response if "create_response" in locals() else None
