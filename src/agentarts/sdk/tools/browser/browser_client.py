"""Client for interacting with the Browser sandbox service.

This module provides a client for Huawei Cloud Browser tool, supporting
operations like creating, listing, updating, getting, deleting browser
resources, managing browser profiles, and executing browser automation
operations (navigation, clicks, screenshots, etc.) in a managed sandbox
environment.

Control Plane:
    Manages the full lifecycle of browser resources
    (create, list, update, get, delete) and browser profiles
    (create, list, get, delete)

Data Plane:
    Manages the full lifecycle of browser sessions
    (create, stop, get, invoke, update_stream)
"""

import base64
import logging
import os
import re
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from agentarts.sdk.service.tools_http import (
    ControlBrowserHttpClient,
    DataBrowserHttpClient,
)
from agentarts.sdk.utils.constant import (
    get_control_plane_endpoint,
    get_region,
)

logger = logging.getLogger(__name__)

DEFAULT_SESSION_TIMEOUT = 900  # 15 minutes


class Browser:
    """Client for interacting with the Browser sandbox service.

    This client handles the full lifecycle and method invocations for
    browser sandbox sessions, providing interfaces for executing browser
    automation operations, managing browser resources and profiles.

    Attributes:
        control_plane_client: Client for interacting with control plane API
            (manages browser/profile resources, AK/SK signed).
        data_plane_client: Client for interacting with data plane API
            (manages sessions and operation execution). Initialized when
            the first data-plane interface is added.
    """

    def __init__(
        self,
        region: str | None,
        data_endpoint: str | None = None,
        auth_type: str = "API_KEY",
        verify_ssl: bool | str = True,
    ) -> None:
        """Initialize the browser client in the specified region.

        Args:
            region: The specified region. Falls back to the region derived
                from environment variables when ``None``.
            data_endpoint: Data plane endpoint, optional. If not provided,
                will be retrieved from environment variable
                ``AGENTARTS_BROWSER_DATA_ENDPOINT`` when the data plane
                client is initialized.
            auth_type: Authentication type for the data plane, optional.
                Defaults to "API_KEY". Can be "API_KEY" or "IAM".
            verify_ssl: Whether to verify the SSL certificate of the
                server, optional. Defaults to True. If a string, it is
                used as the CA bundle path.
        """
        region = region or get_region()

        # Control plane client for managing browser resources and profiles.
        self.control_plane_client = ControlBrowserHttpClient(
            region_name=region,
            endpoint_url=get_control_plane_endpoint(region=region),
            verify_ssl=verify_ssl,
        )

        # Data plane client for managing browser sessions.
        # Priority: constructor parameter > AGENTARTS_BROWSER_DATA_ENDPOINT
        # environment variable. Falls back to empty string if neither is
        # configured (the request will fail at call time, not construction).
        endpoint_url = data_endpoint or os.getenv(
            "AGENTARTS_BROWSER_DATA_ENDPOINT"
        ) or ""

        if auth_type == "IAM":
            self._data_plane_client = DataBrowserHttpClient(
                region_name=region,
                endpoint_url=endpoint_url,
                auth_type=auth_type,
                verify_ssl=verify_ssl,
            )
        else:
            self._data_plane_client = DataBrowserHttpClient(
                region_name=region,
                endpoint_url=endpoint_url,
                verify_ssl=verify_ssl,
            )

        # Cached session state, populated by start_session and consumed by
        # subsequent data-plane calls so callers do not need to repeat the
        # browser_name / session_id / stream endpoints on every invocation.
        self._browser_name = None
        self._session_id = None
        self._automation_endpoint = None
        self._live_view_endpoint = None

    # ------------------------------------------------------------------
    # Session-state accessors
    # ------------------------------------------------------------------

    @property
    def browser_name(self) -> str | None:
        """Get the current browser name."""
        return self._browser_name

    @browser_name.setter
    def browser_name(self, name: str) -> None:
        """Set the current browser name."""
        self._browser_name = name

    @property
    def session_id(self) -> str | None:
        """Get the current session ID."""
        return self._session_id

    @session_id.setter
    def session_id(self, session_id: str) -> None:
        """Set the current session ID."""
        self._session_id = session_id

    @property
    def automation_endpoint(self) -> str | None:
        """Get the automation stream endpoint."""
        return self._automation_endpoint

    @property
    def live_view_endpoint(self) -> str | None:
        """Get the live-view stream endpoint."""
        return self._live_view_endpoint

    # ------------------------------------------------------------------
    # Control plane: browser resource management
    # ------------------------------------------------------------------

    def create_browser(
        self,
        name: str,
        auth_type: str = "API_KEY",
        api_key_name: str | None = None,
        description: str | None = None,
        execution_agency_name: str | None = None,
        observability: dict | None = None,
        network_config: dict | None = None,
        agent_gateway_id: str | None = None,
        tags: list[dict] | None = None,
    ) -> dict:
        """Create a browser resource.

        Creates a new browser through the control plane.

        Args:
            name (str): Browser name, must be unique within the account.
                Pattern: ^[a-z][a-z0-9-]{0,38}[a-z0-9]$ (2-40 chars,
                lowercase start/end, lowercase letters/digits/hyphens only).
            auth_type (str): Authentication type, "API_KEY" or "IAM".
                Defaults to "API_KEY".
            api_key_name (Optional[str]): API Key name, required when
                auth_type is "API_KEY".
                Pattern: ^[a-zA-Z0-9_-]{1,64}$ (1-64 chars, alphanumeric,
                underscore, hyphen).
            description (Optional[str]): Browser description, max 4096
                characters.
            execution_agency_name (Optional[str]): IAM agency name for
                cloud service access, 1-64 chars.
            observability (Optional[dict]): Observability configuration.
                - logs.enabled (bool): Enable log collection, default false
                - logs.group_id (str): Log group ID
                - logs.stream_id (str): Log stream ID
                - metrics.enabled (bool): Enable custom metrics, default false
                - metrics.instance_id (str): Instance ID for metrics
                - tracing.enabled (bool): Enable tracing, default false
                - tracing.service_group (str): Tracing service group
            network_config (Optional[dict]): Outbound network configuration.
                - network_mode (str): Required when provided. "PUBLIC" or "VPC"
                - vpc_config.vpc_id (str): VPC ID, required when vpc_config provided
                - vpc_config.subnet_id (str): Subnet ID, required when vpc_config provided
                - vpc_config.security_group_ids (list[str]): Security group IDs
            agent_gateway_id (Optional[str]): AgentGateway ID, UUID format.
                Uses default gateway if not provided.
            tags (Optional[list[dict]]): Resource tags, max 20 items, key
                must be unique. Each tag: {"key": str (required),
                "value": str (required)}.

        Returns:
            Dict: Dictionary containing the newly created browser info.
                - id (str): Browser ID (UUID)
                - name (str): Browser name
                - description (str): Browser description
                - auth_type (str): Authentication type
                - api_key_name (str): API Key name
                - execution_agency_name (str): IAM agency name
                - agent_gateway_id (str): AgentGateway ID
                - observability (dict): Observability configuration
                - network_config (dict): Network configuration
                - workload_identity (dict): Workload identity info
                    - urn (str): Identity URN
                - access_endpoint (str): Access endpoint URL
                - tags (list[dict]): Resource tags
                - created_at (str): Creation time (ISO 8601)
                - updated_at (str): Update time (ISO 8601)

        Example:
            >>> browser = client.create_browser(
            ...     name="my-browser",
            ...     auth_type="API_KEY",
            ...     api_key_name="demo-key",
            ...     description="Demo browser instance",
            ...     execution_agency_name="my_agency",
            ...     observability={
            ...         "logs": {"enabled": True, "group_id": "lg-xxx",
            ...                  "stream_id": "ls-xxx"},
            ...         "metrics": {"enabled": True, "instance_id": "inst-xxx"},
            ...         "tracing": {"enabled": False, "service_group": "sg-xxx"},
            ...     },
            ...     network_config={"network_mode": "PUBLIC"},
            ...     agent_gateway_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            ...     tags=[{"key": "env", "value": "prod"}],
            ... )
            >>> browser_id = browser["id"]
        """
        logger.info("Creating browser with name: %s", name)

        # Validate name: same rule as CodeInterpreter resources.
        name_pattern = r"[a-z][a-z0-9-]{0,38}[a-z0-9]$"
        if not bool(re.match(name_pattern, name)):
            msg = (
                "Name must start with a lowercase letter, end with a lowercase "
                "letter or digit, contain only lowercase letters, digits, and "
                "hyphens, and be 2-40 characters long."
            )
            raise ValueError(msg)

        # Validate auth_type is one of the allowed values.
        if auth_type not in ("API_KEY", "IAM"):
            msg = 'auth_type must be "API_KEY" or "IAM".'
            raise ValueError(msg)

        # API_KEY auth requires an api_key_name.
        if auth_type == "API_KEY" and api_key_name is None:
            msg = "API_KEY auth_type requires api_key_name."
            raise ValueError(msg)

        # Validate api_key_name format when provided.
        if api_key_name:
            api_key_pattern = r"[a-zA-Z0-9_-]{1,64}$"
            if not bool(re.match(api_key_pattern, api_key_name)):
                msg = (
                    "api_key_name must match ^[a-zA-Z0-9_-]{1,64}$ "
                    "(1-64 chars, alphanumeric, underscore, hyphen)."
                )
                raise ValueError(msg)

        # Validate tags: max 20 items, key must be unique.
        if tags:
            if len(tags) > 20:
                msg = "tags must contain at most 20 items."
                raise ValueError(msg)
            seen_keys: set = set()
            for tag in tags:
                key = tag.get("key")
                if key in seen_keys:
                    msg = f"Duplicate tag key: {key}. Tag keys must be unique."
                    raise ValueError(msg)
                seen_keys.add(key)

        request_params: dict[str, Any] = {"name": name, "auth_type": auth_type}

        if api_key_name:
            request_params["api_key_name"] = api_key_name
        if description:
            request_params["description"] = description
        if execution_agency_name:
            request_params["execution_agency_name"] = execution_agency_name
        if observability:
            request_params["observability"] = observability
        if network_config:
            request_params["network_config"] = network_config
        if agent_gateway_id:
            request_params["agent_gateway_id"] = agent_gateway_id
        if tags:
            request_params["tags"] = tags

        return self.control_plane_client.create_browser(request_params=request_params)

    def list_browsers(
        self,
        name: str | None = None,
        offset: int = 0,
        limit: int = 10,
        sort_key: str = "created_at",
        sort_dir: str = "desc",
        tag_key_exists: list[str] | None = None,
        tag_key_matches: list[str] | None = None,
        tag_value_matches: list[str] | None = None,
        tag_match_policy: str = "ALL",
    ) -> dict:
        """List browsers with optional filters and pagination.

        Args:
            name (Optional[str]): Filter by browser name, 2-40 characters
            offset (int): Pagination offset, default 0
            limit (int): Page size, default 10
            sort_key (str): Sort field, "created_at" or "updated_at",
                default "created_at"
            sort_dir (str): Sort direction, "asc" or "desc", default "desc"
            tag_key_exists (Optional[list[str]]): Filter by tag key existence,
                max 10 keys
            tag_key_matches (Optional[list[str]]): Tag key match, must pair
                with tag_value_matches, max 10
            tag_value_matches (Optional[list[str]]): Tag value match, must
                pair with tag_key_matches, max 10
            tag_match_policy (str): Tag match policy, "ALL" or "ANY",
                default "ALL"

        Returns:
            Dict: Dictionary containing browser list
                - items (list[dict]): Browser list, each item same as
                  create_browser response
                - total_count (int): Total count of matching browsers

        Example:
            >>> result = client.list_browsers(
            ...     name="my-browser",
            ...     limit=20,
            ...     sort_key="updated_at",
            ...     sort_dir="asc",
            ...     tag_key_exists=["env"],
            ...     tag_match_policy="ALL",
            ... )

        """
        logger.info("Listing browsers")
        if sort_key and sort_key not in ("created_at", "updated_at"):
            msg = "sort_key must be either 'created_at' or 'updated_at'"
            raise ValueError(msg)
        if sort_dir and sort_dir not in ("asc", "desc"):
            msg = "sort_dir must be either 'asc' or 'desc'"
            raise ValueError(msg)

        # Validate name length: 2-40 characters.
        if name is not None and not (2 <= len(name) <= 40):
            msg = "name must be between 2 and 40 characters."
            raise ValueError(msg)

        # Validate tag_match_policy is one of the allowed values.
        if tag_match_policy not in ("ALL", "ANY"):
            msg = 'tag_match_policy must be "ALL" or "ANY".'
            raise ValueError(msg)

        # Validate tag filter arrays: max 10 items, items must be unique.
        for tag_param, param_name in (
            (tag_key_exists, "tag_key_exists"),
            (tag_key_matches, "tag_key_matches"),
            (tag_value_matches, "tag_value_matches"),
        ):
            if tag_param is not None:
                if len(tag_param) > 10:
                    msg = f"{param_name} must contain at most 10 items."
                    raise ValueError(msg)
                if len(set(tag_param)) != len(tag_param):
                    msg = f"{param_name} must not contain duplicate items."
                    raise ValueError(msg)

        # tag_key_matches and tag_value_matches must be used together with
        # equal length.
        if (tag_key_matches is None) != (tag_value_matches is None):
            msg = (
                "tag_key_matches and tag_value_matches must be used together."
            )
            raise ValueError(msg)
        if (
            tag_key_matches is not None
            and tag_value_matches is not None
            and len(tag_key_matches) != len(tag_value_matches)
        ):
            msg = (
                "tag_key_matches and tag_value_matches must have the same "
                "number of items."
            )
            raise ValueError(msg)

        request_params = {
            "name": name,
            "limit": limit,
            "offset": offset,
            "sort_key": sort_key,
            "sort_dir": sort_dir,
            "tag_key_exists": tag_key_exists,
            "tag_key_matches": tag_key_matches,
            "tag_value_matches": tag_value_matches,
        }

        # Only include tag_match_policy when tag filters are actually used
        has_tag_filters = any(
            p is not None
            for p in (tag_key_exists, tag_key_matches, tag_value_matches)
        )
        if has_tag_filters:
            request_params["tag_match_policy"] = tag_match_policy

        # Remove None values
        request_params = {k: v for k, v in request_params.items() if v is not None}

        return self.control_plane_client.list_browsers(request_params=request_params)

    def get_browser(self, browser_id: str) -> dict:
        """Get browser details by ID.

        Args:
            browser_id (str): Browser ID (UUID format)

        Returns:
            Dict: Dictionary containing browser details, same structure as
                create_browser response

        Example:
            >>> browser = client.get_browser(
            ...     browser_id="9ca9f2a6-18e4-4777-b23b-8c21e978a1ad"
            ... )

        """
        logger.info("Getting browser %s", browser_id)
        uuid_pattern = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        if not bool(re.match(uuid_pattern, browser_id)):
            msg = "browser_id must be a valid UUID (e.g., 9ca9f2a6-18e4-4777-b23b-8c21e978a1ad)."
            raise ValueError(msg)
        return self.control_plane_client.get_browser(browser_id=browser_id)

    def update_browser(
        self,
        browser_id: str,
        observability: dict | None = None,
        tags: list[dict] | None = None,
    ) -> dict:
        """Update browser configuration. Only observability and tags can be updated.

        Args:
            browser_id (str): Browser ID (UUID format)
            observability (Optional[dict]): Observability configuration, same
                structure as create_browser.
            tags (Optional[list[dict]]): Resource tags, max 20 items, key
                must be unique. Same structure as create_browser.

        Returns:
            Dict: Dictionary containing updated browser info.
                - id (str): Browser ID
                - name (str): Browser name
                - description (str): Browser description
                - execution_agency_name (str): IAM agency name
                - observability (dict): Updated observability configuration
                - workload_identity (dict): Workload identity info
                - access_endpoint (str): Access endpoint URL
                - tags (list[dict]): Updated resource tags
                - created_at (str): Creation time (ISO 8601)
                - updated_at (str): Update time (ISO 8601)
                - updated_by (str): IAM user ID who performed the update

        Example:
            >>> browser = client.update_browser(
            ...     browser_id="9ca9f2a6-18e4-4777-b23b-8c21e978a1ad",
            ...     observability={"logs": {"enabled": False}},
            ...     tags=[{"key": "env", "value": "prod"}],
            ... )

        """
        logger.info("Updating browser %s", browser_id)

        # Validate browser_id: UUID format (same as get_browser).
        uuid_pattern = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        if not bool(re.match(uuid_pattern, browser_id)):
            msg = "browser_id must be a valid UUID (e.g., 9ca9f2a6-18e4-4777-b23b-8c21e978a1ad)."
            raise ValueError(msg)

        # Validate tags: max 20 items, key must be unique (same as create_browser).
        if tags:
            if len(tags) > 20:
                msg = "tags must contain at most 20 items."
                raise ValueError(msg)
            seen_keys: set = set()
            for tag in tags:
                key = tag.get("key")
                if key in seen_keys:
                    msg = f"Duplicate tag key: {key}. Tag keys must be unique."
                    raise ValueError(msg)
                seen_keys.add(key)

        request_params: dict[str, Any] = {}
        if observability:
            request_params["observability"] = observability
        if tags:
            request_params["tags"] = tags

        return self.control_plane_client.update_browser(
            browser_id=browser_id, request_params=request_params
        )

    def delete_browser(self, browser_id: str) -> bool:
        """Delete a browser by ID.

        Args:
            browser_id (str): Browser ID (UUID format)

        Returns:
            bool: True if deletion succeeded (HTTP 204)

        Example:
            >>> result = client.delete_browser(
            ...     browser_id="9ca9f2a6-18e4-4777-b23b-8c21e978a1ad"
            ... )

        """
        logger.info("Deleting browser %s", browser_id)

        # Validate browser_id: UUID format (same as get_browser).
        uuid_pattern = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        if not bool(re.match(uuid_pattern, browser_id)):
            msg = "browser_id must be a valid UUID (e.g., 9ca9f2a6-18e4-4777-b23b-8c21e978a1ad)."
            raise ValueError(msg)

        self.control_plane_client.delete_browser(browser_id=browser_id)
        return True

    # ------------------------------------------------------------------
    # Control plane: browser profile management
    # ------------------------------------------------------------------

    def create_browser_profile(
        self,
        name: str,
        description: str | None = None,
        tags: list[dict] | None = None,
    ) -> dict:
        """Create a browser profile.

        Args:
            name (str): Profile name, must be unique within the account.
                Pattern: ^[a-z][a-z0-9-]{0,38}[a-z0-9]$ (2-40 chars,
                lowercase start/end, lowercase letters/digits/hyphens only).
            description (Optional[str]): Profile description, max 4096
                characters.
            tags (Optional[list[dict]]): Resource tags, max 20 items, key
                must be unique. Each tag: {"key": str (required),
                "value": str (required)}.

        Returns:
            Dict: Dictionary containing created profile info.
                - id (str): Profile ID (UUID)
                - name (str): Profile name
                - description (str): Profile description
                - last_saved_browser_id (str): Last saved browser ID
                - last_saved_browser_session_id (str): Last saved browser
                    session ID
                - last_saved_at (str): Last saved time (ISO 8601)
                - tags (list[dict]): Resource tags
                - created_at (str): Creation time (ISO 8601)

        Example:
            >>> profile = client.create_browser_profile(
            ...     name="my-profile",
            ...     description="Demo browser profile",
            ...     tags=[{"key": "env", "value": "dev"}],
            ... )

        """
        logger.info("Creating browser profile with name: %s", name)

        # Validate name: same rule as browser resources.
        name_pattern = r"[a-z][a-z0-9-]{0,38}[a-z0-9]$"
        if not bool(re.match(name_pattern, name)):
            msg = (
                "Name must start with a lowercase letter, end with a lowercase "
                "letter or digit, contain only lowercase letters, digits, and "
                "hyphens, and be 2-40 characters long."
            )
            raise ValueError(msg)

        # Validate description length: max 4096 characters.
        if description and len(description) > 4096:
            msg = "description must be at most 4096 characters."
            raise ValueError(msg)

        # Validate tags: max 20 items, key must be unique (same as create_browser).
        if tags:
            if len(tags) > 20:
                msg = "tags must contain at most 20 items."
                raise ValueError(msg)
            seen_keys: set = set()
            for tag in tags:
                key = tag.get("key")
                if key in seen_keys:
                    msg = f"Duplicate tag key: {key}. Tag keys must be unique."
                    raise ValueError(msg)
                seen_keys.add(key)

        request_params: dict[str, Any] = {"name": name}
        if description:
            request_params["description"] = description
        if tags:
            request_params["tags"] = tags

        return self.control_plane_client.create_browser_profile(request_params=request_params)

    def list_browser_profiles(
        self,
        name: str | None = None,
        offset: int = 0,
        limit: int = 10,
        sort_key: str = "created_at",
        sort_dir: str = "desc",
        tag_key_exists: list[str] | None = None,
        tag_key_matches: list[str] | None = None,
        tag_value_matches: list[str] | None = None,
        tag_match_policy: str = "ALL",
    ) -> dict:
        """List browser profiles with optional filters and pagination.

        Args:
            name (Optional[str]): Filter by profile name, 2-40 characters
            offset (int): Pagination offset, default 0
            limit (int): Page size, default 10
            sort_key (str): Sort field, "created_at" or "updated_at",
                default "created_at"
            sort_dir (str): Sort direction, "asc" or "desc", default "desc"
            tag_key_exists (Optional[list[str]]): Filter by tag key existence,
                max 10 keys
            tag_key_matches (Optional[list[str]]): Tag key match, must pair
                with tag_value_matches, max 10
            tag_value_matches (Optional[list[str]]): Tag value match, must
                pair with tag_key_matches, max 10
            tag_match_policy (str): Tag match policy, "ALL" or "ANY",
                default "ALL"

        Returns:
            Dict: Dictionary containing profile list
                - items (list[dict]): Profile list, each item same as
                  create_browser_profile response
                - total_count (int): Total count of matching profiles

        Example:
            >>> result = client.list_browser_profiles(
            ...     name="my-profile",
            ...     limit=20,
            ...     tag_key_exists=["env"],
            ... )

        """
        logger.info("Listing browser profiles")
        if sort_key and sort_key not in ("created_at", "updated_at"):
            msg = "sort_key must be either 'created_at' or 'updated_at'"
            raise ValueError(msg)
        if sort_dir and sort_dir not in ("asc", "desc"):
            msg = "sort_dir must be either 'asc' or 'desc'"
            raise ValueError(msg)

        # Validate name length: 2-40 characters.
        if name is not None and not (2 <= len(name) <= 40):
            msg = "name must be between 2 and 40 characters."
            raise ValueError(msg)

        # Validate tag_match_policy is one of the allowed values.
        if tag_match_policy not in ("ALL", "ANY"):
            msg = 'tag_match_policy must be "ALL" or "ANY".'
            raise ValueError(msg)

        # Validate tag filter arrays: max 10 items, items must be unique.
        for tag_param, param_name in (
            (tag_key_exists, "tag_key_exists"),
            (tag_key_matches, "tag_key_matches"),
            (tag_value_matches, "tag_value_matches"),
        ):
            if tag_param is not None:
                if len(tag_param) > 10:
                    msg = f"{param_name} must contain at most 10 items."
                    raise ValueError(msg)
                if len(set(tag_param)) != len(tag_param):
                    msg = f"{param_name} must not contain duplicate items."
                    raise ValueError(msg)

        # tag_key_matches and tag_value_matches must be used together with
        # equal length.
        if (tag_key_matches is None) != (tag_value_matches is None):
            msg = (
                "tag_key_matches and tag_value_matches must be used together."
            )
            raise ValueError(msg)
        if (
            tag_key_matches is not None
            and tag_value_matches is not None
            and len(tag_key_matches) != len(tag_value_matches)
        ):
            msg = (
                "tag_key_matches and tag_value_matches must have the same "
                "number of items."
            )
            raise ValueError(msg)

        request_params = {
            "name": name,
            "limit": limit,
            "offset": offset,
            "sort_key": sort_key,
            "sort_dir": sort_dir,
            "tag_key_exists": tag_key_exists,
            "tag_key_matches": tag_key_matches,
            "tag_value_matches": tag_value_matches,
        }

        # Only include tag_match_policy when tag filters are actually used,
        # per spec: tag key existence, tag_key_matches, tag_value_matches
        has_tag_filters = any(
            p is not None
            for p in (tag_key_exists, tag_key_matches, tag_value_matches)
        )
        if has_tag_filters:
            request_params["tag_match_policy"] = tag_match_policy

        # Remove None values
        request_params = {k: v for k, v in request_params.items() if v is not None}

        return self.control_plane_client.list_browser_profiles(request_params=request_params)

    def get_browser_profile(self, profile_id: str) -> dict:
        """Get browser profile details by ID.

        Args:
            profile_id (str): Profile ID (UUID format)

        Returns:
            Dict: Dictionary containing profile details, same structure as
                create_browser_profile response.

        Example:
            >>> profile = client.get_browser_profile(
            ...     profile_id="9ca9f2a6-18e4-4777-b23b-8c21e978a1ad"
            ... )

        """
        logger.info("Getting browser profile %s", profile_id)

        # Validate profile_id: UUID format (same as browser_id).
        uuid_pattern = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        if not bool(re.match(uuid_pattern, profile_id)):
            msg = "profile_id must be a valid UUID (e.g., 9ca9f2a6-18e4-4777-b23b-8c21e978a1ad)."
            raise ValueError(msg)
        return self.control_plane_client.get_browser_profile(profile_id=profile_id)

    def delete_browser_profile(self, profile_id: str) -> bool:
        """Delete a browser profile by ID.

        Args:
            profile_id (str): Profile ID (UUID format)

        Returns:
            bool: True if deletion succeeded (HTTP 204)

        Example:
            >>> result = client.delete_browser_profile(
            ...     profile_id="9ca9f2a6-18e4-4777-b23b-8c21e978a1ad"
            ... )

        """
        logger.info("Deleting browser profile %s", profile_id)

        # Validate profile_id: UUID format (same as browser_id).
        uuid_pattern = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        if not bool(re.match(uuid_pattern, profile_id)):
            msg = "profile_id must be a valid UUID (e.g., 9ca9f2a6-18e4-4777-b23b-8c21e978a1ad)."
            raise ValueError(msg)

        self.control_plane_client.delete_browser_profile(profile_id=profile_id)
        return True

    # ------------------------------------------------------------------
    # Data plane: session management
    # ------------------------------------------------------------------

    def start_session(
        self,
        browser_name: str,
        session_id: str,
        session_name: str = "default-session-name",
        profile_id: str | None = None,
        session_timeout: int = DEFAULT_SESSION_TIMEOUT,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Start a browser session.

        Args:
            browser_name: Name of the browser resource.
            session_id: Session ID specified by the client.
            session_name: Session name, defaults to "default-session-name".
            profile_id: Optional browser profile ID to load saved state.
            session_timeout: Session timeout in seconds, default 900 (15 min).
            api_key: API Key for authentication. When None and auth_type is
                "API_KEY", the key is read from environment variable
                ``HUAWEICLOUD_SDK_BROWSER_API_KEY``.

        Returns:
            Dict containing session metadata (automation_endpoint,
            live_view_endpoint, etc.). The Browser instance caches these values
            internally so subsequent calls do not need to repeat them.
        """
        logger.info("Starting session %s for browser: %s", session_id, browser_name)

        request_params: dict[str, Any] = {
            "session_name": session_name,
            "session_timeout": session_timeout,
        }
        if profile_id:
            request_params["profile_id"] = profile_id

        result = self._data_plane_client.start_session(
            browser_name=browser_name,
            session_id=session_id,
            request_params=request_params,
            api_key=api_key,
        )

        self._browser_name = browser_name
        self._session_id = session_id
        self._automation_endpoint = result.get("automation_endpoint")
        self._live_view_endpoint = result.get("live_view_endpoint")

        return result

    def stop_session(self, api_key: str | None = None) -> dict[str, Any]:
        """Stop the current browser session.

        Requires a session to have been started (session_id must be set).

        Args:
            api_key: API Key for authentication.

        Returns:
            Dict containing the stop response.
        """
        if not self._session_id or not self._browser_name:
            msg = "No active session. Call start_session first."
            raise ValueError(msg)

        logger.info("Stopping session %s", self._session_id)
        result = self._data_plane_client.stop_session(
            browser_name=self._browser_name,
            session_id=self._session_id,
            api_key=api_key,
        )

        self._session_id = None
        self._browser_name = None
        self._automation_endpoint = None
        self._live_view_endpoint = None

        return result

    def get_session(self, api_key: str | None = None) -> dict[str, Any]:
        """Get the current browser session details.

        Requires a session to have been started (session_id must be set).

        Args:
            api_key: API Key for authentication.

        Returns:
            Dict containing session details.
        """
        if not self._session_id or not self._browser_name:
            msg = "No active session. Call start_session first."
            raise ValueError(msg)

        logger.info("Getting session %s", self._session_id)
        return self._data_plane_client.get_session(
            browser_name=self._browser_name,
            session_id=self._session_id,
            api_key=api_key,
        )

    # ------------------------------------------------------------------
    # Data plane: browser operations
    # ------------------------------------------------------------------

    def invoke(
        self,
        action: dict,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Invoke a browser operation.

        All browser operations (navigate, click, screenshot, etc.) are
        dispatched through this single entry point.

        Args:
            action: Operation action dict (e.g. {"operate_type": "navigate",
                "arguments": {"url": "https://example.com"}}).
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Raises:
            ValueError: If no active session.
        """
        if not self._session_id or not self._browser_name:
            msg = "No active session. Call start_session first."
            raise ValueError(msg)

        logger.info("Invoking on session %s", self._session_id)
        return self._data_plane_client.invoke(
            browser_name=self._browser_name,
            session_id=self._session_id,
            action=action,
            api_key=api_key,
        )

    # ------------------------------------------------------------------
    # Data plane: stream management
    # ------------------------------------------------------------------

    def update_stream(
        self,
        stream_status: str,
        client_token: str | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Update the browser session stream status (human handoff control).

        Args:
            stream_status: Stream status, "disabled" or "enabled".
            client_token: Optional client token for idempotency.
            api_key: API Key for authentication.

        Returns:
            Dict containing the update result.

        Raises:
            ValueError: If stream_status is not "disabled" or "enabled",
                or if no active session.
        """
        if not self._session_id or not self._browser_name:
            msg = "No active session. Call start_session first."
            raise ValueError(msg)

        if stream_status not in ("disabled", "enabled"):
            msg = 'stream_status must be "disabled" or "enabled".'
            raise ValueError(msg)

        logger.info("Updating stream status to '%s' for session %s", stream_status, self._session_id)
        return self._data_plane_client.update_stream(
            browser_name=self._browser_name,
            session_id=self._session_id,
            stream_status=stream_status,
            client_token=client_token,
            api_key=api_key,
        )


@contextmanager
def browser_session(
    region: str,
    browser_name: str,
    session_id: str,
    auth_type: str = "API_KEY",
    api_key: str | None = None,
    verify_ssl: bool | str = True,
) -> Generator[Browser, None, None]:
    """Browser session context manager.

    Starts a session on enter and automatically stops it on exit.

    Args:
        region: Region name, e.g., "cn-southwest-2".
        browser_name: Browser resource name.
        session_id: Session ID specified by the client.
        auth_type: Authentication type, "API_KEY" or "IAM". Defaults to "API_KEY".
        api_key: API Key for authentication (API_KEY mode).
        verify_ssl: SSL verification. True to verify, False to skip,
            or a string path to a CA bundle. Defaults to True.

    Yields:
        Browser: Browser instance with an active session.

    Example:
        >>> with browser_session("cn-southwest-2", "my-browser", "session-123") as b:
        >>>     b.invoke("navigate", {"url": "https://example.com"})
        >>>     content = b.invoke("get_content", {})
    """
    client = Browser(region=region, auth_type=auth_type, verify_ssl=verify_ssl)
    client.start_session(browser_name=browser_name, session_id=session_id, api_key=api_key)
    try:
        yield client
    finally:
        client.stop_session(api_key=api_key)
