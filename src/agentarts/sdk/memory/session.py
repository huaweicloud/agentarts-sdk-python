"""
Agent Memory SDK - Session Management
会话管理模块，提供MemorySession类
"""

import logging
from typing import List, Optional, Union

from .inner.config import (
    SessionCreateRequest,
    MessageInfo,
    MessageListResponse,
    MessageBatchResponse,
    MemoryInfo,
    MemoryListResponse,
    MemorySearchResponse,
    TextMessage,
    ToolCallMessage,
    ToolResultMessage,
    MessageRequest,
    MemorySearchFilter,
    MemoryListFilter,
)
from .inner.controlplane import _ControlPlane
from .inner.dataplane import _DataPlane

logger = logging.getLogger(__name__)


class RetrievalConfig:
    """
    检索配置类，用于配置记忆检索相关参数

    Attributes:
        user_id: 用户 ID，用于个性化检索
        max_tokens: 检索结果的最大 token 数，0 表示不限制
        top_k: 返回 Top-K 条记忆，默认为 2
        score_threshold: 相似度分数阈值，低于此分数的结果会被过滤
    """
    user_id: Optional[str] = None
    max_tokens: int = 0
    top_k: int = 2
    score_threshold: float = 0.6

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return f"RetrievalConfig(user_id={self.user_id}, max_tokens={self.max_tokens}, top_k={self.top_k}, score_threshold={self.score_threshold})"


class MemorySession:
    """
    Memory 会话封装类

    提供对特定 Space 和 Session 的便捷操作。
    与 MemoryClient 相比，MemorySession 预先绑定了 space_id 和 session_id，
    调用方法时无需重复传入这两个参数。

    与 MemoryClient 的区别:
        - MemoryClient: 适用于需要操作多个 Space 或 Session 的场景
        - MemorySession: 适用于专注于单一 Session 对话管理的场景

    使用方式:
        1. 创建 MemorySession 时指定 space_id 和 actor_id，自动创建新 Session
        2. 或指定已有的 session_id，复用已有 Session

    Environment Variables:
        HW_API_KEY: 必填，从 Space 获取的 API Key
    """

    def __init__(
            self,
            space_id: str,
            actor_id: str,
            session_id: Optional[str] = None,
            region_name: Optional[str] = None
    ):
        """
        初始化 MemorySession

        创建一个 MemorySession 实例，绑定到指定的 Space 和 Actor。

        实现逻辑:
            1. 初始化 DataPlane（用于数据面 API 调用）
            2. 如果未提供 session_id，自动调用后端 API 创建新 Session
            3. 将 space_id、session_id、actor_id 绑定到实例属性

        Args:
            space_id: Space ID，必填。指定要操作的 Space
            actor_id: 参与者 ID，必填。标识会话的用户或实体
            session_id: Session ID，可选。
                - 不传: 自动创建新 Session
                - 传值: 复用已有 Session
            region_name: 华为云区域名称，可选，默认 "cn-north-4"

        Raises:
            ValueError: 当创建 Session 失败时

        Examples:
            >>> # 方式1: 自动创建新 Session
            >>> session = MemorySession(space_id="space-123", actor_id="user-456")
            >>> print(f"New Session ID: {session.session_id}")

            >>> # 方式2: 复用已有 Session
            >>> session = MemorySession(
            ...     space_id="space-123",
            ...     actor_id="user-456",
            ...     session_id="session-789"
            ... )
        """
        if region_name is None:
            region_name = "cn-north-4"

        self.space_id = space_id
        self.actor_id = actor_id
        self._region_name = region_name

        self._data_plane = _DataPlane(region_name=region_name)

        # 如果没有提供session_id，调用后端 API 创建新的session
        if session_id is None:
            session_config = SessionCreateRequest(actor_id=actor_id)
            session_info = self._data_plane.create_memory_session(space_id, session_config.to_dict())
            self.session_id = session_info.id
            if not self.session_id:
                raise ValueError(f"Failed to create session: {session_info}")
            logger.info(f"Session created via API: {self.session_id}")
        else:
            self.session_id = session_id

    # ==================== Session 创建 ====================

    @classmethod
    def of(
            cls,
            space_id: str,
            actor_id: str,
            session_id: Optional[str] = None,
            region_name: Optional[str] = None
    ) -> "MemorySession":
        """
        工厂方法：创建 MemorySession

        提供更语义化的实例创建方式，功能等同于直接调用构造函数。
        推荐使用此方法创建 MemorySession，使代码更易读。

        Args:
            space_id: Space ID，必填
            actor_id: 参与者 ID，必填
            session_id: Session ID，可选
            region_name: 华为云区域名称，可选

        Returns:
            MemorySession: 新建的会话实例

        Examples:
            >>> # 使用工厂方法创建 Session
            >>> session = MemorySession.of(space_id="space-123", actor_id="user-456")

            >>> # 复用已有 Session
            >>> session = MemorySession.of(
            ...     space_id="space-123",
            ...     actor_id="user-456",
            ...     session_id="session-789"
            ... )
        """
        return cls(
            space_id=space_id,
            actor_id=actor_id,
            session_id=session_id,
            region_name=region_name
        )

    def __repr__(self) -> str:
        """
        返回会话的字符串表示

        Returns:
            str: 格式化的会话信息
        """
        return f"MemorySession(space_id='{self.space_id}', session_id='{self.session_id}', region_name='{self.region_name}')"

    # ==================== 消息管理 ====================

    def get_last_k_messages(
            self,
            k: int
    ) -> List[MessageInfo]:
        """
        获取当前绑定的会话中最近 K 条消息

        Args:
            k: 获取 K 条消息

        Returns:
            List[MessageInfo]: 消息列表，包含详细信息

        Note:
            此操作在绑定的 space_id 和 session_id 上执行
            需要事先设置 HW_API_KEY 环境变量
        """
        logger.info(f"Getting last {k} messages for session: {self.session_id}")
        return self._data_plane.get_last_k_messages(self.session_id, k, self.space_id)

    def add_messages(
            self,
            messages: List[Union[TextMessage, ToolCallMessage, ToolResultMessage]],
            *,
            timestamp: Optional[int] = None,
            idempotency_key: Optional[str] = None,
            is_force_extract: bool = False
    ) -> MessageBatchResponse:
        """
        向当前绑定的会话添加消息 - 支持文本消息、工具调用消息和工具结果消息
        
        Args:
            messages: 消息列表，支持TextMessage、ToolCallMessage和ToolResultMessage对象混合使用
            timestamp: 客户端调用API时间（毫秒时间戳，可选）
            idempotency_key: 批量操作的幂等键（防重试重复写）
            is_force_extract: 是否强制触发记忆抽取，默认False

        Returns:
            MessageBatchResponse: 添加成功的消息列表

        Examples:
            >>> # 方法1: 使用TextMessage对象
            >>> session.add_messages([TextMessage(role="user", content="你好"), TextMessage(role="user", content="请帮助我")])
            
            >>> # 方法2: 使用工具调用消息
            >>> tool_call = ToolCallMessage(
            ...     id="call_123",
            ...     name="query_weather",
            ...     arguments={"city": "北京"}
            ... )
            >>> session.add_messages([tool_call])
            
            >>> # 方法3: 混合使用多种消息类型
            >>> messages = [
            ...     TextMessage(role="user", content="查询北京天气"),
            ...     tool_call,
            ...     ToolResultMessage(
            ...         tool_call_id="call_123",
            ...         content="北京今天晴天，气温25°C"
            ...     )
            ... ]
            >>> session.add_messages(messages)

        Note:
            此操作在绑定的 space_id 和 session_id 上执行
            需要事先设置 HW_API_KEY 环境变量
        """
        logger.info(f"Adding {len(messages)} messages to session: {self.session_id}")

        # 转换为OpenAPI格式
        message_requests = []

        for msg in messages:
            if isinstance(msg, (TextMessage, ToolCallMessage, ToolResultMessage)):
                message_requests.append(msg.to_dict())
            else:
                raise ValueError(f"不支持的消息类型: {type(msg)}")

        # 调用数据面 API
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
        列出当前绑定的会话中的消息

        Args:
            limit: 最大返回消息数量，默认10 (可选)
            offset: 偏移量，默认0 (可选)

        Returns:
            MessageListResponse: 包含items和total的响应对象

        Note:
            此操作在绑定的 space_id 和 session_id 上执行
            需要事先设置 HW_API_KEY 环境变量
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
        获取当前绑定的会话中的特定消息

        Args:
            message_id: 消息ID

        Returns:
            MessageInfo: 消息详情

        Note:
            此操作在绑定的 space_id 和 session_id 上执行
            需要事先设置 HW_API_KEY 环境变量
        """
        logger.info(f"Getting message: {message_id}")
        return self._data_plane.get_message(self.space_id, self.session_id, message_id)

    def search_memories(
            self,
            filters: Optional[MemorySearchFilter] = None
    ) -> MemorySearchResponse:
        """
        在当前绑定的 session 中搜索记忆

        Args:
            filters: 过滤条件，包含搜索查询、策略类型、时间范围、返回数量、分数阈值等

        Returns:
            MemorySearchResponse: 类型化的记忆搜索结果，包含records和total等字段

        Note:
            此操作在绑定的 space_id 上执行
            需要事先设置 HW_API_KEY 环境变量
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
            filters: Optional[MemoryListFilter] = None
    ) -> MemoryListResponse:
        """
        列出当前绑定的 session 中的记忆记录

        Args:
            limit: 每页返回数量
            offset: 偏移量
            filters: 过滤条件

        Returns:
            MemoryListResponse: 类型化的记忆记录列表，包含items和total字段

        Note:
            此操作在绑定的 space_id 上执行
            需要事先设置 HW_API_KEY 环境变量
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
        获取当前绑定的 session 中特定的记忆记录

        Args:
            memory_id: 记忆记录ID

        Returns:
            MemoryInfo: 记录详情

        Note:
            此操作在绑定的 space_id 上执行
            需要事先设置 HW_API_KEY 环境变量
        """
        logger.info(f"Getting memory record: {memory_id}")
        return self._data_plane.get_memory(self.space_id, memory_id)

    def delete_memory(self, memory_id: str) -> None:
        """
        删除当前绑定的会话中特定的记忆记录

        Args:
            memory_id: 记忆记录ID

        Note:
            此操作在绑定的 space_id 上执行
            需要事先设置 HW_API_KEY 环境变量
        """
        logger.info(f"Deleting memory record: {memory_id}")
        self._data_plane.delete_memory(self.space_id, memory_id)
