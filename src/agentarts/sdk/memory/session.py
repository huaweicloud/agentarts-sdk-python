"""
Agent Memory SDK - Session Management
Session management module, provides MemorySession class
"""

import logging

from .inner.config import (
    MemoryInfo,
    MemoryListFilter,
    MemoryListResponse,
    MemorySearchFilter,
    MemorySearchResponse,
    MessageBatchResponse,
    MessageInfo,
    MessageListResponse,
    SessionCreateRequest,
    TextMessage,
    ToolCallMessage,
    ToolResultMessage,
)
from .inner.dataplane import _DataPlane

logger = logging.getLogger(__name__)


class RetrievalConfig:
    """
    Retrieval configuration class for configuring memory retrieval parameters

    Attributes:
        user_id: User ID for personalized retrieval
        max_tokens: Maximum token count for retrieval results, 0 means no limit
        top_k: Return Top-K memories, default is 2
        score_threshold: Similarity score threshold, results below this score will be filtered
    """
    user_id: str | None = None
    max_tokens: int = 0
    top_k: int = 2
    score_threshold: float = 0.6

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return f"RetrievalConfig(user_id={self.user_id}, max_tokens={self.max_tokens}, top_k={self.top_k}, score_threshold={self.score_threshold})"


class MemorySession:
    """
    Memory session wrapper class

    Provides convenient operations for a specific Space and Session.
    Compared to MemoryClient, MemorySession pre-binds space_id and session_id,
    so you don't need to pass these parameters repeatedly when calling methods.

    Difference from MemoryClient:
        - MemoryClient: Suitable for scenarios requiring operations on multiple Spaces or Sessions
        - MemorySession: Suitable for scenarios focused on single Session conversation management

    Usage:
        1. Specify space_id and actor_id when creating MemorySession, automatically creates a new Session
        2. Or specify an existing session_id to reuse an existing Session

    Environment Variables:
        HUAWEICLOUD_SDK_MEMORY_API_KEY: Optional, API Key obtained from Space.
            If api_key parameter is not provided, will read from this environment variable.
    """

    def __init__(
            self,
            space_id: str,
            actor_id: str,
            session_id: str | None = None,
            region_name: str | None = None,
            api_key: str | None = None
    ):
        """
        Initialize MemorySession

        Creates a MemorySession instance bound to the specified Space and Actor.

        Implementation logic:
            1. Initialize DataPlane (for data plane API calls)
            2. If session_id is not provided, automatically call backend API to create a new Session
            3. Bind space_id, session_id, actor_id to instance attributes

        Args:
            space_id: Space ID, required. Specifies the Space to operate on
            actor_id: Participant ID, required. Identifies the user or entity in the session
            session_id: Session ID, optional.
                - Not provided: Automatically creates a new Session
                - Provided: Reuses an existing Session
            region_name: Huawei Cloud region name, optional, default "cn-southwest-2"
            api_key: API Key for data plane authentication, optional.
                If not provided, will read from HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable.

        Raises:
            ValueError: When Session creation fails

        Examples:
            >>> # Method 1: Automatically create a new Session
            >>> session = MemorySession(space_id="space-123", actor_id="user-456")
            >>> print(f"New Session ID: {session.session_id}")

            >>> # Method 2: Reuse an existing Session
            >>> session = MemorySession(
            ...     space_id="space-123",
            ...     actor_id="user-456",
            ...     session_id="session-789"
            ... )

            >>> # Method 3: With explicit API key
            >>> session = MemorySession(
            ...     space_id="space-123",
            ...     actor_id="user-456",
            ...     api_key="your-api-key"
            ... )
        """
        if region_name is None:
            region_name = "cn-southwest-2"

        self.space_id = space_id
        self.actor_id = actor_id
        self._region_name = region_name

        self._data_plane = _DataPlane(region_name=region_name, api_key=api_key)

        # If session_id is not provided, call backend API to create a new session
        if session_id is None:
            session_config = SessionCreateRequest(actor_id=actor_id)
            session_info = self._data_plane.create_memory_session(space_id, session_config.to_dict())
            self.session_id = session_info.id
            if not self.session_id:
                msg = f"Failed to create session: {session_info}"
                raise ValueError(msg)
            logger.info(f"Session created via API: {self.session_id}")
        else:
            self.session_id = session_id

    # ==================== Session Creation ====================

    @classmethod
    def of(
            cls,
            space_id: str,
            actor_id: str,
            session_id: str | None = None,
            region_name: str | None = None,
            api_key: str | None = None
    ) -> "MemorySession":
        """
        Factory method: Create MemorySession

        Provides a more semantic way to create instances, functionally equivalent to calling the constructor directly.
        Recommended to use this method for creating MemorySession, making code more readable.

        Args:
            space_id: Space ID, required
            actor_id: Participant ID, required
            session_id: Session ID, optional
            region_name: Huawei Cloud region name, optional
            api_key: API Key for data plane authentication, optional

        Returns:
            MemorySession: Newly created session instance

        Examples:
            >>> # Create Session using factory method
            >>> session = MemorySession.of(space_id="space-123", actor_id="user-456")

            >>> # Reuse an existing Session
            >>> session = MemorySession.of(
            ...     space_id="space-123",
            ...     actor_id="user-456",
            ...     session_id="session-789"
            ... )

            >>> # With explicit API key
            >>> session = MemorySession.of(
            ...     space_id="space-123",
            ...     actor_id="user-456",
            ...     api_key="your-api-key"
            ... )
        """
        return cls(
            space_id=space_id,
            actor_id=actor_id,
            session_id=session_id,
            region_name=region_name,
            api_key=api_key
        )

    def __repr__(self) -> str:
        """
        Return string representation of the session

        Returns:
            str: Formatted session information
        """
        return f"MemorySession(space_id='{self.space_id}', session_id='{self.session_id}', region_name='{self.region_name}')"

    # ==================== Message Management ====================

    def get_last_k_messages(
            self,
            k: int
    ) -> list[MessageInfo]:
        """
        Get the last K messages from the bound session

        Args:
            k: Number of messages to retrieve

        Returns:
            List[MessageInfo]: List of messages with detailed information

        Note:
            This operation executes on the bound space_id and session_id
            Requires HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable to be set
        """
        logger.info(f"Getting last {k} messages for session: {self.session_id}")
        return self._data_plane.get_last_k_messages(self.session_id, k, self.space_id)

    def add_messages(
            self,
            messages: list[TextMessage | ToolCallMessage | ToolResultMessage],
            *,
            timestamp: int | None = None,
            idempotency_key: str | None = None,
            is_force_extract: bool = False
    ) -> MessageBatchResponse:
        """
        Add messages to the bound session - supports text messages, tool call messages, and tool result messages

        Args:
            messages: List of messages, supports mixing TextMessage, ToolCallMessage, and ToolResultMessage objects
            timestamp: Client API call time (millisecond timestamp, optional)
            idempotency_key: Idempotency key for batch operations (prevents duplicate writes on retry)
            is_force_extract: Whether to force trigger memory extraction, default False

        Returns:
            MessageBatchResponse: List of successfully added messages

        Examples:
            >>> # Method 1: Use TextMessage objects
            >>> session.add_messages([TextMessage(role="user", content="Hello"), TextMessage(role="user", content="Please help me")])

            >>> # Method 2: Use tool call messages
            >>> tool_call = ToolCallMessage(
            ...     id="call_123",
            ...     name="query_weather",
            ...     arguments={"city": "Beijing"}
            ... )
            >>> session.add_messages([tool_call])

            >>> # Method 3: Mix multiple message types
            >>> messages = [
            ...     TextMessage(role="user", content="Query Beijing weather"),
            ...     tool_call,
            ...     ToolResultMessage(
            ...         tool_call_id="call_123",
            ...         content="Beijing is sunny today, temperature 25°C"
            ...     )
            ... ]
            >>> session.add_messages(messages)

        Note:
            This operation executes on the bound space_id and session_id
            Requires HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable to be set
        """
        logger.info(f"Adding {len(messages)} messages to session: {self.session_id}")

        # Convert to OpenAPI format
        message_requests = []

        for msg in messages:
            if isinstance(msg, (TextMessage, ToolCallMessage, ToolResultMessage)):
                message_requests.append(msg.to_dict())
            else:
                msg = f"Unsupported message type: {type(msg)}"
                raise ValueError(msg)

        # Call data plane API
        return self._data_plane.add_messages(
            space_id=self.space_id,
            session_id=self.session_id,
            messages=message_requests,
            timestamp=timestamp,
            idempotency_key=idempotency_key,
            is_force_extract=is_force_extract
        )

    def list_messages(
            self,
            limit: int = 10,
            offset: int = 0
    ) -> MessageListResponse:
        """
        List messages in the bound session

        Args:
            limit: Maximum number of messages to return, default 10 (optional)
            offset: Offset, default 0 (optional)

        Returns:
            MessageListResponse: Response object containing items and total

        Note:
            This operation executes on the bound space_id and session_id
            Requires HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable to be set
        """
        logger.info(f"Listing messages for session: {self.session_id}")
        return self._data_plane.list_messages(
            space_id=self.space_id,
            session_id=self.session_id,
            limit=limit,
            offset=offset
        )

    def get_message(self, message_id: str) -> MessageInfo:
        """
        Get a specific message from the bound session

        Args:
            message_id: Message ID

        Returns:
            MessageInfo: Message details

        Note:
            This operation executes on the bound space_id and session_id
            Requires HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable to be set
        """
        logger.info(f"Getting message: {message_id}")
        return self._data_plane.get_message(self.space_id, self.session_id, message_id)

    def search_memories(
            self,
            filters: MemorySearchFilter | None = None
    ) -> MemorySearchResponse:
        """
        Search memories in the bound session

        Args:
            filters: Filter conditions, including search query, strategy type, time range, return count, score threshold, etc.

        Returns:
            MemorySearchResponse: Typed memory search results, containing records and total fields

        Note:
            This operation executes on the bound space_id
            Requires HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable to be set
        """
        logger.info(f"Searching memories with filter: {filters}")

        return self._data_plane.search_memories(
            space_id=self.space_id,
            filters=filters
        )

    def list_memories(
            self,
            limit: int = 10,
            offset: int = 0,
            filters: MemoryListFilter | None = None
    ) -> MemoryListResponse:
        """
        List memory records in the bound session

        Args:
            limit: Number of items per page
            offset: Offset
            filters: Filter conditions

        Returns:
            MemoryListResponse: Typed list of memory records, containing items and total fields

        Note:
            This operation executes on the bound space_id
            Requires HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable to be set
        """
        logger.info(f"Listing memory records: limit={limit}, offset={offset}")

        return self._data_plane.list_memories(
            space_id=self.space_id,
            limit=limit,
            offset=offset,
            filters=filters
        )

    def get_memory(self, memory_id: str) -> MemoryInfo:
        """
        Get a specific memory record from the bound session

        Args:
            memory_id: Memory record ID

        Returns:
            MemoryInfo: Record details

        Note:
            This operation executes on the bound space_id
            Requires HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable to be set
        """
        logger.info(f"Getting memory record: {memory_id}")
        return self._data_plane.get_memory(self.space_id, memory_id)

    def delete_memory(self, memory_id: str) -> None:
        """
        Delete a specific memory record from the bound session

        Args:
            memory_id: Memory record ID

        Note:
            This operation executes on the bound space_id
            Requires HUAWEICLOUD_SDK_MEMORY_API_KEY environment variable to be set
        """
        logger.info(f"Deleting memory record: {memory_id}")
        self._data_plane.delete_memory(self.space_id, memory_id)
