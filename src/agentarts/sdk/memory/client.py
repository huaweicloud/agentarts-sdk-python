"""
Agent Memory SDK - MemoryClient

Main entry class providing all public methods.
"""

import threading
from typing import Optional, Dict, List, Any, Union

from .inner.config import (
    SpaceCreateRequest,
    SpaceUpdateRequest,
    SessionCreateRequest,
    SpaceInfo,
    SpaceListResponse,
    MessageInfo,
    MessageListResponse,
    MessageBatchResponse,
    MemoryInfo,
    MemoryListResponse,
    MemorySearchResponse,
    TextMessage,
    ToolCallMessage,
    ToolResultMessage,
    MemorySearchFilter,
    MemoryListFilter,
    SessionInfo,
)
from .inner.controlplane import _ControlPlane
from .inner.dataplane import _DataPlane


class MemoryClient:
    """
    Memory Client - Main entry class.

    Provides complete Memory service capabilities, including Space management,
    Session management, and message/memory CRUD operations.

    Authentication:
        - Control plane API (Space management): Uses AK/SK authentication via
          HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK environment variables
        - Data plane API (messages/memories): Uses API Key authentication via
          HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable or api_key parameter

    Architecture:
        - Control plane (_ControlPlane): Handles Space creation, query, update,
          deletion and other management operations
        - Data plane (_DataPlane): Handles Session, message, memory and other
          data operations, uses Space-bound API Key for authentication
        - Control plane uses lazy loading, initialized only on first call

    Method Groups:

        Space Management (Control Plane):
            - create_space: Create Memory Space resource on Huawei Cloud
            - get_space: Query detailed information of specified Space
            - list_spaces: Paginated query of all user Spaces
            - update_space: Modify Space configuration (TTL, tags, memory strategies, etc.)
            - delete_space: Delete specified Space (also deletes associated Sessions,
              messages and memories)

        Session (Data Plane):
            - create_memory_session: Create new session in specified Space

        Message Management (Data Plane):
            - add_messages: Add messages to session (supports text, tool call,
              tool result types)
            - get_last_k_messages: Get last K messages from session
            - get_message: Get specified single message details
            - list_messages: Paginated query of session messages

        Memory Management (Data Plane):
            - search_memories: Semantic search for memory records in Space
            - list_memories: Paginated list of memory records
            - get_memory: Get single memory details
            - delete_memory: Delete specified memory record
    """

    def __init__(
            self,
            region_name: Optional[str] = "cn-north-4",
            api_key: Optional[str] = None
    ):
        """
        Initialize Memory Client.

        Creates a MemoryClient instance for calling all Memory service APIs.

        Initialization:
        - Directly creates DataPlane instance (data plane) for handling
          message/memory operations
        - ControlPlane (control plane) uses lazy loading, initialized only
          when Space management API is first called

        Args:
            region_name: Huawei Cloud region name, default "cn-north-4"
            api_key: API Key for data plane authentication (optional, falls back
                to HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable)

        Environment Variables:
            HUAWEICLOUD_SDK_AK: Access Key, required for control plane API
            HUAWEICLOUD_SDK_SK: Secret Key, required for control plane API
            HUAWEICLOUD_SDK_MEMORY_API_KEY: API Key, required for data plane API
                (can be overridden by api_key parameter)

        Raises:
            ValueError: If control plane AK/SK is not configured (only triggered
                when calling Space management API)

        Examples:
            >>> # Basic usage - set environment variables first
            >>> import os
            >>> os.environ["HUAWEICLOUD_SDK_AK"] = "your-ak"
            >>> os.environ["HUAWEICLOUD_SDK_SK"] = "your-sk"
            >>> os.environ["HUAWEICLOUD_SDK_MEMORY_API_KEY"] = "your-api-key"
            >>> client = MemoryClient()

            >>> # Or pass API key directly (recommended)
            >>> client = MemoryClient(api_key="your-api-key")

            >>> # Specify region
            >>> client = MemoryClient(region_name="cn-east-3", api_key="your-api-key")
        """
        self.region_name = region_name

        self._control_plane = None  # Lazy loading
        self._data_plane = _DataPlane(region_name=region_name, api_key=api_key)
        self._control_plane_init_lock = threading.Lock()

    def _ensure_control_plane_initialized(self, region_name: str):
        """
        Ensure control plane is initialized (thread-safe lazy loading).

        Args:
            region_name: Huawei Cloud region name
        """
        with self._control_plane_init_lock:
            if self._control_plane is None:
                self._control_plane = _ControlPlane(region_name=region_name)

    # ==================== Control Plane - Space Management ====================

    def create_space(
            self,
            name: str,
            message_ttl_hours: int = 168,
            description: Optional[str] = None,
            tags: Optional[List[Dict[str, str]]] = None,
            memory_extract_idle_seconds: Optional[int] = None,
            memory_extract_max_tokens: Optional[int] = None,
            memory_extract_max_messages: Optional[int] = None,
            public_access_enable: bool = True,
            private_vpc_id: Optional[str] = None,
            private_subnet_id: Optional[str] = None,
            memory_strategies_builtin: Optional[List[str]] = None,
            memory_strategies_customized: Optional[List[Dict[str, Any]]] = None
    ) -> SpaceInfo:
        """
        Create Space.

        Creates a new Space resource in Huawei Cloud Memory service.
        Space is the core resource unit of Memory, used to isolate data
        between different applications or users.
        After creation, an API Key is generated for data plane API authentication.

        Implementation:
            1. Encapsulates parameters into SpaceCreateRequest object
            2. Lazy loads ControlPlane initialization (control plane)
            3. Calls control plane API to create Space
            4. Returns SpaceInfo object containing Space ID and API Key

        Args:
            name: Space name, 1-128 characters
            message_ttl_hours: Default message retention time (hours), default 168 (7 days),
                range 1-8760
            description: Space description, optional
            tags: Space tag list for resource grouping and filtering, optional
            memory_extract_idle_seconds: Memory extraction idle time (seconds),
                triggers automatic extraction after exceeding, optional
            memory_extract_max_tokens: Memory extraction max token count,
                single extraction limit, optional
            memory_extract_max_messages: Memory extraction max message count,
                single extraction limit, optional
            public_access_enable: Enable public network access, default True
            private_vpc_id: Private VPC ID, required when enabling private network access,
                must be used with private_subnet_id
            private_subnet_id: Private subnet ID, required when enabling private network access,
                must be used with private_vpc_id
            memory_strategies_builtin: Built-in memory strategy list, e.g.
                ["semantic", "episodic", "user_preference"], optional
            memory_strategies_customized: Custom memory strategy list, JSON array format, optional

        Returns:
            SpaceInfo: Successfully created Space object, containing key attributes:
                - id: Space unique identifier
                - name: Space name
                - api_key: API Key required for data plane authentication
                    (only shown once after creation)
                - message_ttl_hours: Message TTL
                - created_at: Creation time

        Raises:
            HTTPError: When API call fails (insufficient permissions, invalid parameters, etc.)

        Examples:
            >>> # 1. Basic usage - create basic Space
            >>> space = client.create_space("my-chat-app")
            >>> print(f"Space ID: {space.id}")
            >>> print(f"API Key: {space.api_key}")  # Note: API Key shown only once after creation
            >>> # Subsequent use: os.environ["HUAWEICLOUD_SDK_MEMORY_API_KEY"] = space.api_key

            >>> # 2. Customize message retention time and description
            >>> space = client.create_space(
            ...     name="long-term-memory",
            ...     message_ttl_hours=720,  # 30 days
            ...     description="Space for long-term memory storage"
            ... )

            >>> # 3. Enable private network access (need to specify VPC and subnet)
            >>> space = client.create_space(
            ...     name="internal-space",
            ...     public_access_enable=False,
            ...     private_vpc_id="vpc-0i2i8y2y2y2y2i2i8",
            ...     private_subnet_id="subnet-0i2i8y2y2y2y2i2i8"
            ... )

            >>> # 4. Enable memory extraction strategies
            >>> space = client.create_space(
            ...     name="extract-space",
            ...     memory_strategies_builtin=["semantic", "episodic"],
            ...     memory_extract_idle_seconds=3600,  # Auto extract after 1 hour idle
            ...     memory_extract_max_tokens=4000
            ... )
        """
        request = SpaceCreateRequest(
            name=name,
            message_ttl_hours=message_ttl_hours,
            description=description,
            tags=tags,
            memory_extract_idle_seconds=memory_extract_idle_seconds,
            memory_extract_max_tokens=memory_extract_max_tokens,
            memory_extract_max_messages=memory_extract_max_messages,
            public_access_enable=public_access_enable,
            private_vpc_id=private_vpc_id,
            private_subnet_id=private_subnet_id,
            memory_strategies_builtin=memory_strategies_builtin,
            memory_strategies_customized=memory_strategies_customized
        )

        self._ensure_control_plane_initialized(self.region_name)

        return self._control_plane.create_space(request)

    def get_space(self, space_id: str) -> SpaceInfo:
        """
        Get Space details.

        Queries complete configuration information of specified Space,
        including resource status, API Key, memory strategies, etc.
        Note: API Key can only be obtained during first query after Space creation,
        subsequent queries will not return it.

        Implementation:
            1. Lazy loads ControlPlane initialization (if not yet initialized)
            2. Calls control plane API to query Space details
            3. Returns SpaceInfo object

        Args:
            space_id: Space unique identifier ID

        Returns:
            SpaceInfo: Space complete configuration information, containing:
                - id: Space ID
                - name: Space name
                - api_key: API Key (returned only on first query after creation)
                - message_ttl_hours: Message TTL
                - status: Space status
                - created_at / updated_at: Creation and update times
                - memory_strategies_builtin: Enabled memory strategies

        Raises:
            HTTPError: When Space doesn't exist or no permission

        Examples:
            >>> space = client.get_space("space-123")
            >>> print(f"Name: {space.name}")
            >>> print(f"TTL: {space.message_ttl_hours}h")
            >>> print(f"Status: {space.status}")
            >>> print(f"Strategies: {space.memory_strategies_builtin}")
        """
        self._ensure_control_plane_initialized(self._data_plane._region_name)
        return self._control_plane.get_space(space_id)

    def list_spaces(
            self,
            limit: int = 20,
            offset: int = 0
    ) -> SpaceListResponse:
        """
        List all Spaces.

        Paginated query of all Space resources owned by current user.
        Results are sorted by creation time in descending order.

        Implementation:
            1. Lazy loads ControlPlane initialization (if not yet initialized)
            2. Calls control plane API to paginated query Space list
            3. Returns SpaceListResponse object containing items (Space list) and total

        Args:
            limit: Number per page, default 20, max 100
            offset: Pagination offset, default 0, number of records to skip

        Returns:
            SpaceListResponse: Paginated result object, containing:
                - items: List[SpaceInfo], current page Space list
                - total: int, total number of all Spaces (for calculating pagination)
                - limit / offset: Current request pagination parameters

        Examples:
            >>> # Query first page
            >>> result = client.list_spaces(limit=10)
            >>> for space in result.items:
            ...     print(f"{space.id}: {space.name}")

            >>> # Paginated traversal of all Spaces
            >>> offset = 0
            >>> while True:
            ...     result = client.list_spaces(limit=50, offset=offset)
            ...     if not result.items:
            ...         break
            ...     for space in result.items:
            ...         print(space.name)
            ...     offset += len(result.items)
        """
        self._ensure_control_plane_initialized(self._data_plane._region_name)
        return self._control_plane.list_spaces(limit, offset)

    def update_space(
            self,
            space_id: str,
            name: Optional[str] = None,
            description: Optional[str] = None,
            message_ttl_hours: Optional[int] = None,
            memory_extract_enabled: Optional[bool] = None,
            memory_extract_idle_seconds: Optional[int] = None,
            memory_extract_max_tokens: Optional[int] = None,
            memory_extract_max_messages: Optional[int] = None,
            tags: Optional[List[Dict[str, str]]] = None,
            memory_strategies_builtin: Optional[List[str]] = None
    ) -> SpaceInfo:
        """
        Update Space configuration.

        Modifies configuration information of specified Space, supports partial update
        (only pass fields that need modification).
        Note: Some fields like memory_strategies_builtin may trigger memory rebuild,
        which takes longer.

        Implementation:
            1. Encapsulates parameters into SpaceUpdateRequest object (only non-None fields)
            2. Lazy loads ControlPlane initialization (if not yet initialized)
            3. Calls control plane API to execute update
            4. Returns updated SpaceInfo object

        Args:
            space_id: Space ID, required
            name: New Space name, optional
            description: New description, optional
            message_ttl_hours: New message TTL (hours), optional, range 1-8760
            memory_extract_enabled: Enable memory extraction, optional
            memory_extract_idle_seconds: Memory extraction idle time (seconds), optional
            memory_extract_max_tokens: Memory extraction max token count, optional
            memory_extract_max_messages: Memory extraction max message count, optional
            tags: New tag list (replaces original tags), optional
            memory_strategies_builtin: New built-in memory strategy list, optional

        Returns:
            SpaceInfo: Updated Space object

        Raises:
            HTTPError: When Space doesn't exist or parameters invalid

        Examples:
            >>> # Only update name
            >>> client.update_space("space-123", name="new-name")

            >>> # Extend message retention time to 14 days
            >>> client.update_space("space-123", message_ttl_hours=336)

            >>> # Update tags
            >>> client.update_space("space-123", tags=[{"key": "env", "value": "prod"}])

            >>> # Modify memory strategy (note: may trigger memory rebuild, takes longer)
            >>> client.update_space("space-123", memory_strategies_builtin=["semantic"])
        """
        request = SpaceUpdateRequest(
            name=name,
            description=description,
            message_ttl_hours=message_ttl_hours,
            memory_extract_enabled=memory_extract_enabled,
            memory_extract_idle_seconds=memory_extract_idle_seconds,
            memory_extract_max_tokens=memory_extract_max_tokens,
            memory_extract_max_messages=memory_extract_max_messages,
            tags=tags,
            memory_strategies_builtin=memory_strategies_builtin
        )

        self._ensure_control_plane_initialized(self._data_plane._region_name)
        return self._control_plane.update_space(space_id, request)

    def delete_space(self, space_id: str) -> None:
        """
        Delete Space.

        Deletes specified Space and all associated data (Sessions, messages, memories).

        Implementation:
            1. Lazy loads ControlPlane initialization (if not yet initialized)
            2. Calls control plane API to delete Space
            3. No return value

        Args:
            space_id: Space ID, required

        Raises:
            HTTPError: When Space doesn't exist or no permission

        Examples:
            >>> # Delete Space (also deletes all Sessions, messages and memories)
            >>> client.delete_space("space-123")
        """
        self._ensure_control_plane_initialized(self._data_plane._region_name)
        return self._control_plane.delete_space(space_id)

    # ==================== Data Plane - Session Management ====================

    def create_memory_session(
            self,
            space_id: str,
            id: Optional[str] = None,
            actor_id: Optional[str] = None,
            assistant_id: Optional[str] = None,
            meta: Optional[Dict[str, Any]] = None
    ) -> SessionInfo:
        """
        Create Memory Session.

        Creates a new session in specified Space for managing conversation history
        and memories.

        Args:
            space_id: Space ID, required. Specifies Space to create session in
            id: Session ID, optional. Specifies session ID to create
            actor_id: Actor ID, optional. Identifies user or entity in session
            assistant_id: Assistant ID, optional. Identifies service endpoint or
                assistant in session
            meta: Metadata, optional. For storing extra session information

        Returns:
            SessionInfo: Created session information, containing session_id field

        Examples:
            >>> # Basic usage
            >>> session = client.create_memory_session(space_id="space-123")
            >>> print(f"Session ID: {session.id}")

            >>> # With participant information
            >>> session = client.create_memory_session(
            ...     space_id="space-123",
            ...     actor_id="user-456",
            ...     assistant_id="assistant-789"
            ... )
        """
        session_request = SessionCreateRequest(
            id=id,
            actor_id=actor_id,
            assistant_id=assistant_id,
            meta=meta
        )

        return self._data_plane.create_memory_session(space_id, session_request)

    # ==================== Data Plane - Message Management ====================

    def get_last_k_messages(
            self,
            session_id: str,
            k: int,
            space_id: str
    ) -> List[MessageInfo]:
        """
        Get last K messages.

        Gets last K messages from specified session, sorted by time in descending order.
        Commonly used for conversation completion (Context), checking conversation
        history, etc.

        Implementation:
            1. Directly calls DataPlane's get_last_k_messages method
            2. Returns message list (sorted by time descending, most recent first)

        Args:
            session_id: Session ID, specifies session to query
            k: Number of messages to retrieve, positive integer
            space_id: Space ID, Space the session belongs to

        Returns:
            List[MessageInfo]: Message list, sorted by time descending (most recent first),
                each MessageInfo contains:
                - id: Message ID
                - role: Role (user/assistant/system/tool)
                - parts: Message content list
                - created_at: Creation time

        Raises:
            HTTPError: When Session or Space doesn't exist

        Examples:
            >>> # Get last 5 messages
            >>> messages = client.get_last_k_messages("session-456", k=5, space_id="space-123")
            >>> for msg in messages:
            ...     print(f"[{msg.role}] {msg.parts}")

            >>> # For conversation completion
            >>> recent_msgs = client.get_last_k_messages(session_id, k=10, space_id=space_id)
            >>> context = "\\n".join([f"{m.role}: {m.parts[0]['text']}" for m in recent_msgs if m.parts])
        """
        return self._data_plane.get_last_k_messages(session_id, k, space_id)

    def get_message(self, message_id: str, space_id: str, session_id: str) -> MessageInfo:
        """
        Get single message.

        Queries complete information of single message by message ID.

        Implementation:
            1. Directly calls DataPlane's get_message method
            2. Returns single MessageInfo object

        Args:
            message_id: Message unique identifier ID
            space_id: Space ID, Space the message belongs to
            session_id: Session ID, Session the message belongs to

        Returns:
            MessageInfo: Message details object, containing:
                - id: Message ID
                - role: Role (user/assistant/system/tool)
                - parts: Message content list
                - created_at: Creation time
                - metadata: Metadata (if any)

        Raises:
            HTTPError: When message doesn't exist

        Examples:
            >>> msg = client.get_message("msg-123", space_id="space-123", session_id="session-456")
            >>> print(f"Role: {msg.role}")
            >>> print(f"Content: {msg.parts[0].text if msg.parts else 'N/A'}")
        """
        return self._data_plane.get_message(message_id, space_id, session_id)

    def add_messages(
            self,
            space_id: str,
            session_id: str,
            messages: List[Union[TextMessage, ToolCallMessage, ToolResultMessage]],
            *,
            timestamp: Optional[int] = None,
            idempotency_key: Optional[str] = None,
            is_force_extract: bool = False
    ) -> MessageBatchResponse:
        """
        Add messages.

        Adds one or more messages to specified session, supports three message types:
        - TextMessage: Text message (user input, assistant reply, etc.)
        - ToolCallMessage: Tool call message (AI request to call tool)
        - ToolResultMessage: Tool result message (result returned by tool)

        After adding messages, system automatically processes messages according to
        Space's configured memory strategies:
        - semantic: Semantic memory extraction
        - episodic: Episodic memory extraction
        - user_preference: User preference memory extraction

        Implementation:
            1. Iterates message list, converts each message to OpenAPI format
               (calls to_dict())
            2. Validates message types (only supports TextMessage, ToolCallMessage,
               ToolResultMessage)
            3. Calls DataPlane's add_messages method
            4. Returns MessageBatchResponse containing successfully added message list

        Args:
            space_id: Space ID, required
            session_id: Session ID, required
            messages: Message list, required, supports three types mixed:
                - TextMessage: Text message
                - ToolCallMessage: Tool call request
                - ToolResultMessage: Tool execution result
            timestamp: Message timestamp (milliseconds), specifies actual message
                occurrence time, optional
            idempotency_key: Idempotency key, prevents duplicate submission, optional
                - Duplicate requests with same idempotency_key will be ignored
                - Recommend using UUID or business unique identifier
            is_force_extract: Force trigger memory extraction, optional
                - True: Immediately trigger memory extraction (even if idle time
                    threshold not reached)
                - False: Trigger according to Space configured idle time threshold (default)

        Returns:
            MessageBatchResponse: Batch add result, containing:
                - items: List[MessageInfo], successfully added message list
                - count: Number of successfully added messages

        Raises:
            ValueError: When messages is empty or contains unsupported message types
            HTTPError: When Space or Session doesn't exist

        Examples:
            >>> # 1. Add text message
            >>> client.add_messages(
            ...     "space-123",
            ...     "session-456",
            ...     [TextMessage(role="user", content="Hello, please help me check weather")]
            ... )

            >>> # 2. Add multiple text messages
            >>> client.add_messages(
            ...     "space-123",
            ...     "session-456",
            ...     [
            ...         TextMessage(role="user", content="How's the weather today?"),
            ...         TextMessage(role="assistant", content="Beijing is sunny today, 25°C")
            ...     ]
            ... )

            >>> # 3. Add tool call message (AI calls external tool)
            >>> tool_call = ToolCallMessage(
            ...     id="call_123",
            ...     name="query_weather",
            ...     arguments={"city": "Beijing"}
            ... )
            >>> client.add_messages("space-123", "session-456", [tool_call])

            >>> # 4. Complete conversation flow: user asks -> AI calls tool -> tool returns result
            >>> messages = [
            ...     TextMessage(role="user", content="How's the weather in Beijing?"),
            ...     ToolCallMessage(
            ...         id="call_123",
            ...         name="query_weather",
            ...         arguments={"city": "Beijing"}
            ...     ),
            ...     ToolResultMessage(
            ...         tool_call_id="call_123",
            ...         content="Beijing is sunny today, temperature 25°C, southeast wind level 3"
            ...     )
            ... ]
            >>> client.add_messages("space-123", "session-456", messages)

            >>> # 5. Use idempotency key to prevent duplicate submission
            >>> import uuid
            >>> client.add_messages(
            ...     "space-123", "session-456",
            ...     [TextMessage(role="user", content="hello")],
            ...     idempotency_key=str(uuid.uuid4())
            ... )

            >>> # 6. Force trigger memory extraction
            >>> client.add_messages(
            ...     "space-123", "session-456",
            ...     [TextMessage(role="user", content="Important information")],
            ...     is_force_extract=True
            ... )
        """
        message_requests = []

        for msg in messages:
            if isinstance(msg, (TextMessage, ToolCallMessage, ToolResultMessage)):
                message_requests.append(msg.to_dict())
            else:
                raise ValueError(f"Unsupported message type: {type(msg)}")
        return self._data_plane.add_messages(
            space_id,
            session_id,
            message_requests,
            timestamp=timestamp,
            idempotency_key=idempotency_key,
            is_force_extract=is_force_extract
        )

    def list_messages(
            self,
            space_id: str,
            session_id: Optional[str] = None,
            limit: int = 10,
            offset: int = 0
    ) -> MessageListResponse:
        """
        List messages.

        Paginated query of message records. Can query messages from specified Session,
        or query all messages under Space.

        Implementation:
            1. Directly calls DataPlane's list_messages method
            2. Returns paginated result

        Args:
            space_id: Space ID, required
            session_id: Session ID, optional
                - Not passed: Query all messages under Space
                - Passed: Query messages from specified Session
            limit: Number per page, default 10, max 100
            offset: Pagination offset, default 0

        Returns:
            MessageListResponse: Paginated result, containing:
                - items: List[MessageInfo], message list
                - total: int, total count
                - limit / offset: Current pagination parameters

        Examples:
            >>> # Query all messages under Space
            >>> result = client.list_messages("space-123")
            >>> for msg in result.items:
            ...     print(f"{msg.role}: {msg.parts[0].text if msg.parts else ''}")

            >>> # Query messages from specified Session
            >>> result = client.list_messages("space-123", session_id="session-456")

            >>> # Paginated traversal
            >>> offset = 0
            >>> while True:
            ...     result = client.list_messages("space-123", limit=50, offset=offset)
            ...     if not result.items:
            ...         break
            ...     for msg in result.items:
            ...         print(msg.id)
            ...     offset += len(result.items)
        """
        return self._data_plane.list_messages(space_id, session_id, limit, offset)

    # ==================== Data Plane - Memory Management ====================

    def search_memories(
            self,
            space_id: str,
            filters: Optional[MemorySearchFilter] = None
    ) -> MemorySearchResponse:
        """
        Search memories.

        Searches memory records under Space based on semantic similarity.
        Uses vector retrieval to find memories most similar to query statement.

        Memory Types:
            - semantic: Semantic memory, essence information extracted from conversation
            - episodic: Episodic memory, records of specific scenarios/situations
            - user_preference: User preference, user habits and preference information

        Implementation:
            1. Converts MemorySearchFilter to request parameters
            2. Calls DataPlane's search_memories method
            3. Returns vector retrieval results

        Args:
            space_id: Space ID, required
            filters: Search filter conditions, optional, containing:
                - query: Search query (string)
                - top_k: Return count, default 5
                - min_score: Minimum similarity score, between 0-1
                - strategy_type: Memory type filter (semantic/episodic/user_preference)
                - created_start / created_end: Time range filter

        Returns:
            MemorySearchResponse: Search results, containing:
                - records: List[MemoryInfo], matched memory list
                - total: int, total match count
                - Each MemoryInfo contains:
                    - id: Memory ID
                    - content: Memory content summary
                    - score: Similarity score
                    - strategy: Memory type

        Examples:
            >>> # Basic semantic search
            >>> from agentarts.sdk.memory.inner.config import MemorySearchFilter
            >>> filters = MemorySearchFilter(query="user preference", top_k=3)
            >>> result = client.search_memories("space-123", filters)
            >>> for mem in result.records:
            ...     print(f"[{mem.score:.2f}] {mem.content}")

            >>> # Search with filter conditions
            >>> filters = MemorySearchFilter(
            ...     query="weather query habit",
            ...     top_k=5,
            ...     min_score=0.7,
            ...     strategy_type="user_preference"  # Only search user preferences
            ... )
            >>> result = client.search_memories("space-123", filters)

            >>> # Time range filter
            >>> import time
            >>> filters = MemorySearchFilter(
            ...     query="important matters",
            ...     created_start=int(time.time() * 1000) - 7 * 24 * 60 * 60 * 1000  # Last 7 days
            ... )
            >>> result = client.search_memories("space-123", filters)
        """
        return self._data_plane.search_memories(space_id, filters)

    def list_memories(
            self,
            space_id: str,
            limit: int = 10,
            offset: int = 0,
            filters: Optional[MemoryListFilter] = None
    ) -> MemoryListResponse:
        """
        List memory records.

        Paginated query of all memory records under Space (unlike search_memories,
        this is exact list query).

        Memory Types:
            - semantic: Semantic memory
            - episodic: Episodic memory
            - user_preference: User preference

        Implementation:
            1. Converts MemoryListFilter to dictionary
            2. Calls DataPlane's list_memories method
            3. Returns paginated result

        Args:
            space_id: Space ID, required
            limit: Number per page, default 10, max 100
            offset: Pagination offset, default 0
            filters: Filter conditions, optional, containing:
                - strategy_type: Filter by memory type
                - created_start / created_end: Filter by creation time
                - sort_by: Sort field (created_at, etc.)
                - sort_order: Sort direction (asc/desc)

        Returns:
            MemoryListResponse: Paginated result, containing:
                - items: List[MemoryInfo], memory list
                - total: int, total count

        Examples:
            >>> # List all memories
            >>> result = client.list_memories("space-123")
            >>> for mem in result.items:
            ...     print(f"{mem.strategy}: {mem.content[:50]}...")

            >>> # Filter by type
            >>> filters = MemoryListFilter(strategy_type="semantic")
            >>> result = client.list_memories("space-123", filters=filters)

            >>> # Sort by time
            >>> filters = MemoryListFilter(sort_by="created_at", sort_order="desc")
            >>> result = client.list_memories("space-123", filters=filters)
        """
        return self._data_plane.list_memories(space_id, limit, offset, filters)

    def get_memory(self, space_id: str, memory_id: str) -> MemoryInfo:
        """
        Get memory record.

        Gets complete information of single memory by memory ID.

        Implementation:
            1. Directly calls DataPlane's get_memory method
            2. Returns MemoryInfo object

        Args:
            space_id: Space ID, required
            memory_id: Memory ID, required

        Returns:
            MemoryInfo: Memory details, containing:
                - id: Memory ID
                - content: Memory content
                - strategy: Memory type (semantic/episodic/user_preference)
                - created_at: Creation time
                - metadata: Metadata

        Raises:
            HTTPError: When memory doesn't exist

        Examples:
            >>> mem = client.get_memory("space-123", "memory-456")
            >>> print(f"Type: {mem.strategy}")
            >>> print(f"Content: {mem.content}")
            >>> print(f"Created: {mem.created_at}")
        """
        return self._data_plane.get_memory(space_id, memory_id)

    def delete_memory(self, space_id: str, memory_id: str) -> None:
        """
        Delete memory record.

        Deletes single memory by memory ID. Please note this operation is irreversible.

        Implementation:
            1. Directly calls DataPlane's delete_memory method
            2. No return value

        Args:
            space_id: Space ID, required
            memory_id: Memory ID, required

        Raises:
            HTTPError: When memory doesn't exist

        Examples:
            >>> # Delete single memory
            >>> client.delete_memory("space-123", "memory-456")
        """
        return self._data_plane.delete_memory(space_id, memory_id)

    # ==================== Resource Management ====================

    def close(self):
        """
        Close Client connection.

        Releases all underlying connection resources, including:
        - ControlPlane's HTTP connection (if initialized)
        - DataPlane's HTTP connection

        Recommend calling this method after using Client, or use context
        manager (with statement).

        Examples:
            >>> # Method 1: Manual close
            >>> client = MemoryClient()
            >>> # ... use client
            >>> client.close()

            >>> # Method 2: Use context manager (recommended)
            >>> with MemoryClient() as client:
            ...     # ... use client
            >>> # close() called automatically
        """
        if self._control_plane is not None:
            self._control_plane.close()
        self._data_plane.close()

    def __enter__(self):
        """
        Context manager entry.

        Returns Client instance itself, supports with statement.

        Returns:
            MemoryClient: Current instance
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit.

        Automatically calls close() method to release resources.

        Args:
            exc_type: Exception type (if any)
            exc_val: Exception value (if any)
            exc_tb: Exception traceback (if any)
        """
        self.close()
