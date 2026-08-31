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
    get_browser_data_plane_endpoint,
    get_control_plane_endpoint,
    get_region,
)

logger = logging.getLogger(__name__)

DEFAULT_SESSION_TIMEOUT = 900  # 15 minutes

ACTION_TYPES = (
    "mouse_click",
    "mouse_move",
    "mouse_drag",
    "mouse_scroll",
    "key_press",
    "key_type",
    "key_shortcut",
    "navigate",
    "go_back",
    "go_forward",
    "refresh",
    "get_page_info",
    "screenshot",
    "wait",
    "list_tabs",
    "switch_tab",
    "close_tab",
    "new_tab",
)


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
        # Priority: env var > constructor parameter > AGENTARTS_RUNTIME_DATA_ENDPOINT
        endpoint_url = get_browser_data_plane_endpoint(endpoint=data_endpoint)

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
        session_name: str,
        session_id: str | None = None,
        viewport: dict | None = None,
        profile_configuration: dict | None = None,
        allowed_domains: list[str] | None = None,
        blocked_domains: list[str] | None = None,
        proxy_configuration: dict | None = None,
        session_timeout: int = DEFAULT_SESSION_TIMEOUT,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Start a browser session.

        Args:
            browser_name: Name of the browser resource.
            session_name: Session name specified by the client.
            session_id: Optional session ID specified by the client. When None,
                the server generates one.
            viewport: Optional viewport configuration dict.
            profile_configuration: Optional profile configuration dict.
            allowed_domains: Optional list of allowed domain patterns.
            blocked_domains: Optional list of blocked domain patterns.
            proxy_configuration: Optional proxy configuration dict.
            session_timeout: Session timeout in seconds, default 900 (15 min).
            api_key: API Key for authentication. When None and auth_type is
                "API_KEY", the key is read from environment variable
                ``HUAWEICLOUD_SDK_BROWSER_API_KEY``.

        Returns:
            Dict containing session metadata (automation_endpoint,
            live_view_endpoint, etc.). The Browser instance caches these values
            internally so subsequent calls do not need to repeat them.

        Example:
            >>> client.start_session(
            ...     browser_name="my-browser",
            ...     session_name="my-session",
            ... )
        """
        logger.info("Starting session for browser: %s", browser_name)

        # Validate session_name
        session_name_pattern = r"^[a-zA-Z0-9_-]{1,128}$"
        if not bool(re.match(session_name_pattern, session_name)):
            msg = (
                "session_name must contain only letters, digits, underscores, and "
                "hyphens, and be 1-128 characters long."
            )
            raise ValueError(msg)

        # allowed_domains and blocked_domains are mutually exclusive
        if allowed_domains and blocked_domains:
            msg = "allowed_domains and blocked_domains cannot be set at the same time."
            raise ValueError(msg)

        request_params: dict[str, Any] = {
            "name": session_name,
            "session_timeout": session_timeout,
        }
        if viewport:
            request_params["viewport"] = viewport
        if profile_configuration:
            request_params["profile_configuration"] = profile_configuration
        if allowed_domains:
            request_params["allowed_domains"] = allowed_domains
        if blocked_domains:
            request_params["blocked_domains"] = blocked_domains
        if proxy_configuration:
            request_params["proxy_configuration"] = proxy_configuration

        if self._data_plane_client.open_ak_sk:
            result = self._data_plane_client.start_session(
                browser_name=browser_name,
                request_params=request_params,
                session_id=session_id,
            )
        else:
            api_key = api_key or os.getenv("HUAWEICLOUD_SDK_BROWSER_API_KEY")
            if api_key is None:
                msg = "API Key is not provided and not found in environment variable."
                raise ValueError(msg)
            result = self._data_plane_client.start_session(
                browser_name=browser_name,
                request_params=request_params,
                session_id=session_id,
                api_key=api_key,
            )

        self._browser_name = result.get("browser_name")
        self._session_id = result.get("session_id")

        streams = result.get("streams") or {}
        self._automation_endpoint = (
            streams.get("automation_stream") or {}
        ).get("stream_endpoint")
        self._live_view_endpoint = (
            streams.get("live_view_stream") or {}
        ).get("stream_endpoint")

        return result

    def stop_session(self, api_key: str | None = None) -> bool:
        """Stop the current browser session.

        If no active session exists, returns ``True`` immediately (no-op).

        Args:
            api_key: API Key for authentication.

        Returns:
            True when no active session or after successfully stopping.

        Example:
            >>> client.stop_session()
        """
        if not self._session_id or not self._browser_name:
            return True

        logger.info("Stopping browser session...")
        if self._data_plane_client.open_ak_sk:
            result = self._data_plane_client.stop_session(
                browser_name=self._browser_name,
                session_id=self._session_id,
            )
        else:
            api_key = api_key or os.getenv("HUAWEICLOUD_SDK_BROWSER_API_KEY")
            if api_key is None:
                msg = "API Key is not provided and not found in environment variable."
                raise ValueError(msg)
            result = self._data_plane_client.stop_session(
                browser_name=self._browser_name,
                session_id=self._session_id,
                api_key=api_key,
            )

        self._session_id = None
        self._browser_name = None
        self._automation_endpoint = None
        self._live_view_endpoint = None

        return True

    def get_session(self, api_key: str | None = None) -> dict[str, Any]:
        """Get the current browser session details.

        Requires a session to have been started (session_id must be set).

        Args:
            api_key: API Key for authentication.

        Returns:
            Dict containing session details.

        Example:
            >>> client.get_session()
        """
        logger.info("Getting browser session...")

        if not self._session_id or not self._browser_name:
            msg = "No active session. Call start_session first."
            raise ValueError(msg)
        if self._data_plane_client.open_ak_sk:
            return self._data_plane_client.get_session(
                browser_name=self._browser_name,
                session_id=self._session_id,
            )
        else:
            api_key = api_key or os.getenv("HUAWEICLOUD_SDK_BROWSER_API_KEY")
            if api_key is None:
                msg = "API Key is not provided and not found in environment variable."
                raise ValueError(msg)
            return self._data_plane_client.get_session(
                browser_name=self._browser_name,
                session_id=self._session_id,
                api_key=api_key,
            )

    # ------------------------------------------------------------------
    # Data plane: browser operations
    # ------------------------------------------------------------------

    def save_profile(
        self,
        profile_id: str,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Save current browser session state to a profile.

        Args:
            profile_id: Profile ID to save state to.
            api_key: API Key for authentication.

        Returns:
            Dict containing the save result.

        Example:
            >>> client.save_profile("profile-123")
        """
        logger.info("Saving browser profile...")

        if not self._session_id or not self._browser_name:
            msg = "No active session. Call start_session first."
            raise ValueError(msg)

        if self._data_plane_client.open_ak_sk:
            return self._data_plane_client.save_profile(
                browser_name=self._browser_name,
                session_id=self._session_id,
                profile_id=profile_id,
            )
        else:
            api_key = api_key or os.getenv("HUAWEICLOUD_SDK_BROWSER_API_KEY")
            if api_key is None:
                msg = "API Key is not provided and not found in environment variable."
                raise ValueError(msg)
            return self._data_plane_client.save_profile(
                browser_name=self._browser_name,
                session_id=self._session_id,
                profile_id=profile_id,
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

        Example:
            >>> client.update_stream("enabled")
        """
        logger.info("Updating stream status to '%s'...", stream_status)

        if not self._session_id or not self._browser_name:
            msg = "No active session. Call start_session first."
            raise ValueError(msg)

        if stream_status not in ("disabled", "enabled"):
            msg = 'stream_status must be "disabled" or "enabled".'
            raise ValueError(msg)
        if self._data_plane_client.open_ak_sk:
            return self._data_plane_client.update_stream(
                browser_name=self._browser_name,
                session_id=self._session_id,
                stream_status=stream_status,
                client_token=client_token,
            )
        else:
            api_key = api_key or os.getenv("HUAWEICLOUD_SDK_BROWSER_API_KEY")
            if api_key is None:
                msg = "API Key is not provided and not found in environment variable."
                raise ValueError(msg)
            return self._data_plane_client.update_stream(
                browser_name=self._browser_name,
                session_id=self._session_id,
                stream_status=stream_status,
                client_token=client_token,
                api_key=api_key,
            )

    def take_control(
        self,
        client_token: str | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Take human control of the browser (disable automation).

        Convenience wrapper for ``update_stream("disabled")``.

        Args:
            client_token: Optional client token for idempotency.
            api_key: API Key for authentication.

        Returns:
            Dict containing the update result.

        Example:
            >>> client.take_control()
        """
        return self.update_stream("disabled", client_token=client_token, api_key=api_key)

    def release_control(
        self,
        client_token: str | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Release human control of the browser (enable automation).

        Convenience wrapper for ``update_stream("enabled")``.

        Args:
            client_token: Optional client token for idempotency.
            api_key: API Key for authentication.

        Returns:
            Dict containing the update result.

        Example:
            >>> client.release_control()
        """
        return self.update_stream("enabled", client_token=client_token, api_key=api_key)

    def generate_automation_url(
        self,
        api_key: str | None = None,
    ) -> tuple[str, dict]:
        """Generate the WebSocket URL and headers for the automation stream.

        The automation stream allows programmatic control of the browser
        (navigation, clicks, screenshots, etc.) over a WebSocket connection.

        Does not send an HTTP request — the URL is the ``stream_endpoint``
        cached from :meth:`start_session`'s ``streams.automation_stream``.

        Args:
            api_key: API Key for API_KEY auth mode.

        Returns:
            Tuple of ``(ws_url, ws_headers)``.

        Example:
            >>> ws_url, ws_headers = client.generate_automation_url()
        """
        if not self._session_id or not self._automation_endpoint:
            msg = "No active session. Call start_session first."
            raise ValueError(msg)

        automation_ws_url = self._automation_endpoint
        automation_ws_headers = self._data_plane_client.build_ws_headers(
            session_id=self._session_id,
            ws_url=automation_ws_url,
            api_key=api_key,
        )
        return automation_ws_url, automation_ws_headers

    def generate_live_view_url(
        self,
        api_key: str | None = None,
    ) -> tuple[str, dict]:
        """Generate the WebSocket URL and headers for the live-view stream.

        The live-view stream provides a real-time visual feed of the browser
        so a human operator can watch what the browser is doing.

        Does not send an HTTP request — the URL is the ``stream_endpoint``
        cached from :meth:`start_session`'s ``streams.live_view_stream``.

        Args:
            api_key: API Key for API_KEY auth mode.

        Returns:
            Tuple of ``(ws_url, ws_headers)``.

        Example:
            >>> ws_url, ws_headers = client.generate_live_view_url()
        """
        if not self._session_id or not self._live_view_endpoint:
            msg = "No active session. Call start_session first."
            raise ValueError(msg)

        live_view_ws_url = self._live_view_endpoint
        live_view_ws_headers = self._data_plane_client.build_ws_headers(
            session_id=self._session_id,
            ws_url=live_view_ws_url,
            api_key=api_key,
        )
        return live_view_ws_url, live_view_ws_headers

    # ------------------------------------------------------------------
    # Data plane: browser operations
    # ------------------------------------------------------------------

    def invoke(
        self,
        type: str,
        action: dict,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Invoke a browser operation.

        All browser operations (navigate, click, screenshot, etc.) are
        dispatched through this single entry point.

        Args:
            type: Action type, one of the supported operation types
                (e.g. "mouse_click", "navigate", "screenshot").
            action: Action parameters dict (e.g. {"x": 312, "y": 482}).
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.invoke("mouse_click", {"x": 312, "y": 482})
        """
        logger.info("Invoking browser operation...")

        if type not in ACTION_TYPES:
            msg = f"Unsupported action type: {type}."
            raise ValueError(msg)

        if not self._session_id or not self._browser_name:
            msg = "No active session. Call start_session first."
            raise ValueError(msg)

        if self._data_plane_client.open_ak_sk:
            return self._data_plane_client.invoke(
                browser_name=self._browser_name,
                session_id=self._session_id,
                type=type,
                action=action,
            )
        else:
            api_key = api_key or os.getenv("HUAWEICLOUD_SDK_BROWSER_API_KEY")
            if api_key is None:
                msg = "API Key is not provided and not found in environment variable."
                raise ValueError(msg)
            return self._data_plane_client.invoke(
                browser_name=self._browser_name,
                session_id=self._session_id,
                type=type,
                action=action,
                api_key=api_key,
            )

    # ------------------------------------------------------------------
    # Convenience methods — each maps to an invoke action
    # ------------------------------------------------------------------

    def mouse_click(
        self,
        x: int,
        y: int,
        button: str = "left",
        click_count: int = 1,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Click the mouse at the specified position.

        Args:
            x: X coordinate.
            y: Y coordinate.
            button: Mouse button, "left", "right", or "middle".
                Defaults to "left".
            click_count: Number of clicks. Defaults to 1.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.mouse_click(312, 482)
            >>> client.mouse_click(312, 482, button="right")
            >>> client.mouse_click(312, 482, click_count=2)
        """
        return self.invoke(
            type="mouse_click",
            action={"x": x, "y": y, "button": button, "click_count": click_count},
            api_key=api_key,
        )

    def left_mouse_click(
        self,
        x: int,
        y: int,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Left mouse click at the specified position.

        Args:
            x: X coordinate.
            y: Y coordinate.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.left_mouse_click(312, 482)
        """
        return self.mouse_click(x, y, button="left", click_count=1, api_key=api_key)

    def right_mouse_click(
        self,
        x: int,
        y: int,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Right mouse click at the specified position.

        Args:
            x: X coordinate.
            y: Y coordinate.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.right_mouse_click(312, 482)
        """
        return self.mouse_click(x, y, button="right", click_count=1, api_key=api_key)

    def double_mouse_click(
        self,
        x: int,
        y: int,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Double mouse click at the specified position.

        Args:
            x: X coordinate.
            y: Y coordinate.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.double_mouse_click(312, 482)
        """
        return self.mouse_click(x, y, button="left", click_count=2, api_key=api_key)

    def mouse_move(
        self,
        x: int,
        y: int,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Move the mouse to the specified position.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.mouse_move(312, 482)
        """
        return self.invoke(
            type="mouse_move",
            action={"x": x, "y": y},
            api_key=api_key,
        )

    def mouse_drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        button: str = "left",
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Drag the mouse from one position to another.

        Args:
            start_x: Start X coordinate.
            start_y: Start Y coordinate.
            end_x: End X coordinate.
            end_y: End Y coordinate.
            button: Mouse button, "left", "right", or "middle".
                Defaults to "left".
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.mouse_drag(100, 100, 200, 200)
        """
        if button not in ("left", "right", "middle"):
            msg = 'button must be "left", "right", or "middle".'
            raise ValueError(msg)

        return self.invoke(
            type="mouse_drag",
            action={
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "button": button,
            },
            api_key=api_key,
        )

    def mouse_scroll(
        self,
        x: int,
        y: int,
        delta_x: int | None = None,
        delta_y: int | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Scroll at the specified position.

        Args:
            x: X coordinate of the scroll position.
            y: Y coordinate of the scroll position.
            delta_x: Optional horizontal scroll amount in pixels.
            delta_y: Optional vertical scroll amount in pixels.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.mouse_scroll(500, 300, 0, -100)
        """
        action = {"x": x, "y": y}
        if delta_x is not None:
            action["delta_x"] = delta_x
        if delta_y is not None:
            action["delta_y"] = delta_y
        return self.invoke(
            type="mouse_scroll",
            action=action,
            api_key=api_key,
        )

    def key_press(
        self,
        key: str,
        presses: int = 1,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Press a key.

        Args:
            key: Key name (e.g. "Enter", "Tab", "a").
            presses: Number of times to press the key, 1-100.
                Defaults to 1.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.key_press("Enter")
            >>> client.key_press("Tab", presses=3)
        """
        if not 1 <= presses <= 100:
            msg = "presses must be between 1 and 100."
            raise ValueError(msg)

        return self.invoke(
            type="key_press",
            action={"key": key, "presses": presses},
            api_key=api_key,
        )

    def key_type(
        self,
        text: str,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Type text into the focused element.

        Args:
            text: The text string to type.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.key_type("Hello, World!")
        """
        return self.invoke(
            type="key_type",
            action={"text": text},
            api_key=api_key,
        )

    def key_shortcut(
        self,
        keys: list[str],
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Press a key combination (multiple keys simultaneously).

        Args:
            keys: List of key names, max 5 keys (e.g. ["Control", "c"]).
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.key_shortcut(["Control", "c"])
            >>> client.key_shortcut(["Control", "Shift", "T"])
        """
        if not keys or len(keys) > 5:
            msg = "keys must contain 1 to 5 items."
            raise ValueError(msg)

        return self.invoke(
            type="key_shortcut",
            action={"keys": keys},
            api_key=api_key,
        )

    def navigate(
        self,
        url: str,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Navigate to a URL.

        Args:
            url: Target URL.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.navigate("https://example.com")
        """
        return self.invoke(
            type="navigate",
            action={"url": url},
            api_key=api_key,
        )

    def go_back(self, api_key: str | None = None) -> dict[str, Any]:
        """Go back to the previous page."""
        return self.invoke(type="go_back", action={}, api_key=api_key)

    def go_forward(self, api_key: str | None = None) -> dict[str, Any]:
        """Go forward to the next page."""
        return self.invoke(type="go_forward", action={}, api_key=api_key)

    def refresh(self, api_key: str | None = None) -> dict[str, Any]:
        """Refresh the current page."""
        return self.invoke(type="refresh", action={}, api_key=api_key)

    def get_page_info(self, api_key: str | None = None) -> dict[str, Any]:
        """Get information about the current page."""
        return self.invoke(type="get_page_info", action={}, api_key=api_key)

    def screenshot(
        self,
        format: str = "jpeg",
        quality: int = 80,
        full_page: bool = False,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Take a screenshot of the current page.

        Args:
            format: Image format, "png" or "jpeg". Defaults to "jpeg".
            quality: JPEG compression quality, 1-100. Only effective when
                format is "jpeg". Defaults to 80.
            full_page: Whether to capture the full page. Defaults to False.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.screenshot()
            >>> client.screenshot(format="png", full_page=True)
        """
        if format not in ("png", "jpeg"):
            msg = 'format must be "png" or "jpeg".'
            raise ValueError(msg)
        if not 1 <= quality <= 100:
            msg = "quality must be between 1 and 100."
            raise ValueError(msg)

        return self.invoke(
            type="screenshot",
            action={"format": format, "quality": quality, "full_page": full_page},
            api_key=api_key,
        )

    def wait(
        self,
        duration: float,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Wait for a specified duration.

        Args:
            duration: Wait duration in seconds, 0.1 to 30.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.wait(2.5)
        """
        if not 0.1 <= duration <= 30:
            msg = "duration must be between 0.1 and 30."
            raise ValueError(msg)

        return self.invoke(
            type="wait",
            action={"duration": duration},
            api_key=api_key,
        )

    def list_tabs(self, api_key: str | None = None) -> dict[str, Any]:
        """List all open tabs."""
        return self.invoke(type="list_tabs", action={}, api_key=api_key)

    def switch_tab(
        self,
        tab_id: str,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Switch to a specific tab.

        Args:
            tab_id: Target tab ID.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.switch_tab("tab-123")
        """
        return self.invoke(
            type="switch_tab",
            action={"tab_id": tab_id},
            api_key=api_key,
        )

    def close_tab(
        self,
        tab_id: str | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Close a tab.

        Args:
            tab_id: Target tab ID. If not provided, closes the current tab.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.close_tab("tab-123")
            >>> client.close_tab()
        """
        action = {}
        if tab_id is not None:
            action["tab_id"] = tab_id
        return self.invoke(
            type="close_tab",
            action=action,
            api_key=api_key,
        )

    def new_tab(
        self,
        url: str | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Open a new tab.

        Args:
            url: URL to open in the new tab. If not provided, opens a
                blank page.
            api_key: API Key for authentication.

        Returns:
            Dict containing the operation result.

        Example:
            >>> client.new_tab("https://example.com")
            >>> client.new_tab()
        """
        action = {}
        if url is not None:
            action["url"] = url
        return self.invoke(
            type="new_tab",
            action=action,
            api_key=api_key,
        )


@contextmanager
def browser_session(
    region: str,
    browser_name: str,
    session_name: str,
    session_id: str | None = None,
    auth_type: str = "API_KEY",
    api_key: str | None = None,
    verify_ssl: bool | str = True,
    viewport: dict | None = None,
    profile_configuration: dict | None = None,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
    proxy_configuration: dict | None = None,
    session_timeout: int = DEFAULT_SESSION_TIMEOUT,
) -> Generator[Browser, None, None]:
    """Browser session context manager.

    Starts a session on enter and automatically stops it on exit.

    Args:
        region: Region name, e.g., "cn-southwest-2".
        browser_name: Browser resource name.
        session_name: Session name specified by the client.
        session_id: Optional session ID specified by the client.
        auth_type: Authentication type, "API_KEY" or "IAM". Defaults to "API_KEY".
        api_key: API Key for authentication (API_KEY mode).
        verify_ssl: SSL verification. True to verify, False to skip,
            or a string path to a CA bundle. Defaults to True.
        viewport: Optional viewport configuration dict.
        profile_configuration: Optional browser profile configuration dict.
        allowed_domains: Optional list of allowed domain patterns.
        blocked_domains: Optional list of blocked domain patterns. Mutually
            exclusive with allowed_domains.
        proxy_configuration: Optional proxy configuration dict.
        session_timeout: Session timeout in seconds. Defaults to 900.

    Yields:
        Browser: Browser instance with an active session.

    Example:
        >>> with browser_session("cn-southwest-2", "my-browser", "my-session") as b:
        >>>     b.invoke("navigate", {"url": "https://example.com"})
    """
    client = Browser(region=region, auth_type=auth_type, verify_ssl=verify_ssl)
    client.start_session(
        browser_name=browser_name,
        session_name=session_name,
        session_id=session_id,
        viewport=viewport,
        profile_configuration=profile_configuration,
        allowed_domains=allowed_domains,
        blocked_domains=blocked_domains,
        proxy_configuration=proxy_configuration,
        session_timeout=session_timeout,
        api_key=api_key,
    )
    try:
        yield client
    finally:
        client.stop_session(api_key=api_key)
