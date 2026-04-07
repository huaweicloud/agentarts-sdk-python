"""
Agent Memory SDK - Data Plane
数据面：处理消息、记忆等操作

根据华为云后端 API 定义的方法实现：
- create_memory_session: 创建 Session
- add_messages: 添加消息
- get_last_k_messages: 获取最近K条消息
- get_message: 获取单条消息
- list_messages: 列出消息
- search_memories: 搜索记忆
- list_memories: 列出记忆记录
- get_memory: 获取记忆记录
- delete_memory: 删除记忆记录
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from hw_agentrun_wrapper.services.memory_http import MemoryHttpService
from .config import (
    SessionCreateRequest,
    SessionInfo,
    MessageInfo,
    MessageListResponse,
    MessageBatchResponse,
    MemoryListResponse,
    MemoryInfo, MemorySearchFilter, MemoryListFilter, MemorySearchResponse
)

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """消息"""
    role: str  # "user" 或 "assistant"
    content: str


class _DataPlane:
    """
    数据面API - 根据华为云后端 API 实现
    """

    def __init__(self, region_name: Optional[str] = None):
        """
        初始化数据面

        Args:
            region_name: 华为云区域名称（可选）
        """
        self.client = MemoryHttpService(
            region_name=region_name,
            endpoint_type="data"
        )
        logger.info("DataPlane initialized")

    # ==================== 数据面方法 ====================

    def create_memory_session(
            self,
            space_id: str,
            request: SessionCreateRequest
    ) -> SessionInfo:
        """
        创建 Memory Session

        Args:
            space_id: Space ID
            session_config: Session 配置（可选），可包含 actor_id, assistant_id, meta 等

        Returns:
            Session 信息，包含 id 字段
        """
        logger.info(f"Creating memory session in space: {space_id}")

        result = self.client.create_session(space_id, request.to_dict())

        logger.info(f"Memory session created: {result.get('id')}")
        return SessionInfo.from_dict(result)

    def add_messages(
            self,
            space_id: str,
            session_id: str,
            messages: List[Dict[str, Any]],
            timestamp: Optional[int] = None,
            idempotency_key: Optional[str] = None,
            is_force_extract: bool = False
    ) -> MessageBatchResponse:
        """
        添加消息

        Args:
            space_id: Space ID（必填）
            session_id: Session ID
            messages: 消息列表（已经是OpenAPI格式字典）
            timestamp: 客户端调用API时间（毫秒时间戳，可选）
            idempotency_key: 批量操作的幂等键（防重试重复写）
            is_force_extract: 是否强制触发记忆抽取

        Returns:
            MessageBatchResponse: 添加成功的消息列表
        """
        if not space_id:
            raise ValueError("space_id is required for data plane operations")

        logger.info(f"Adding {len(messages)} messages to session: {session_id}")

        # 构建请求字典，使用OpenAPI格式
        request_data = {
            "messages": messages,  # messages已经是OpenAPI格式的字典列表
            "is_force_extract": is_force_extract
        }
        if timestamp is not None:
            request_data["timestamp"] = timestamp
        if idempotency_key is not None:
            request_data["idempotency_key"] = idempotency_key

        result = self.client.add_messages(space_id, session_id, request_data)
        logger.info(f"Messages added to session: {session_id}")
        return MessageBatchResponse.from_dict(result)

    def get_last_k_messages(
            self,
            session_id: str,
            k: int,
            space_id: str
    ) -> List[MessageInfo]:
        """
        获取最近 K 条消息

        Args:
            session_id: Session ID
            k: 获取 K 条消息
            space_id: Space ID（必填）

        Returns:
            List[MessageInfo]: 消息列表
        """
        if not space_id:
            raise ValueError("space_id is required")

        logger.info(f"Getting last {k} messages from session: {session_id}")

        # 先获取总数
        result = self.client.list_messages(space_id, session_id, limit=1, offset=0)
        total = result.get('total', 0)

        # 计算 offset
        offset = max(0, total - k)

        # 获取消息
        result = self.client.list_messages(space_id, session_id, limit=k, offset=offset)
        return [MessageInfo.from_dict(msg) for msg in result.get('items', [])]

    def get_message(
            self,
            message_id: str,
            space_id: str,
            session_id: str
    ) -> Dict[str, Any]:
        """
        获取单条消息

        Args:
            message_id: 消息 ID
            space_id: Space ID
            session_id: Session ID

        Returns:
            消息详情
        """
        logger.info(f"Getting message: {message_id}")
        return MessageInfo.from_dict(self.client.get_message(space_id, session_id, message_id))

    def list_messages(
            self,
            space_id: str,
            session_id: Optional[str] = None,
            limit: int = 10,
            offset: int = 0
    ) -> MessageListResponse:
        """
        列出消息

        Args:
            space_id: Space ID
            session_id: Session ID（可选，用于获取特定会话的消息）
            limit: 每页数量，默认10
            offset: 偏移量，默认0

        Returns:
            MessageListResponse: 消息列表响应，包含items和total等信息
        """
        logger.info(f"Listing messages in space: {space_id}, session: {session_id}")
        result = self.client.list_messages(space_id, session_id, limit=limit, offset=offset)
        return MessageListResponse.from_dict(result)

    def search_memories(
            self,
            space_id: str,
            filters: MemorySearchFilter = None
    ) -> Dict[str, Any]:
        """
        搜索记忆

        Args:
            space_id: Space ID
            filters: 过滤条件（可选）

        Returns:
            搜索结果
        """
        logger.info(f"Searching memories in space: {space_id}")

        filters_dict = filters.to_dict() if filters else {}
        result = self.client.search_memories(space_id, filters_dict)
        return MemorySearchResponse.from_dict(result)

    def list_memories(
            self,
            space_id: str,
            limit: int = 10,
            offset: int = 0,
            filters: MemoryListFilter = None
    ) -> MemoryListResponse:
        """
        列出记忆记录

        Args:
            space_id: Space ID
            limit: 每页返回数量，默认10
            offset: 偏移量，默认0
            filters: 过滤条件

        Returns:
            MemoryListResponse: 记忆记录列表响应，包含items和total等信息
        """
        logger.info(f"Listing memories in space: {space_id}")
        filters_dict = filters.to_dict() if filters else {}
        result = self.client.list_memories(
            space_id,
            limit=limit,
            offset=offset,
            filters=filters_dict
        )
        return MemoryListResponse.from_dict(result)

    def get_memory(self, space_id: str, memory_id: str) -> MemoryInfo:
        """
        获取记忆记录

        Args:
            space_id: Space ID
            memory_id: 记忆 ID

        Returns:
            MemoryInfo: 记录详情
        """
        logger.info(f"Getting memory: {memory_id}")
        result = self.client.get_memory(space_id, memory_id)
        return MemoryInfo.from_dict(result)

    def delete_memory(self, space_id: str, memory_id: str) -> None:
        """
        删除记忆记录

        Args:
            space_id: Space ID
            memory_id: 记忆 ID
        """
        logger.info(f"Deleting memory: {memory_id}")
        self.client.delete_memory(space_id, memory_id)
