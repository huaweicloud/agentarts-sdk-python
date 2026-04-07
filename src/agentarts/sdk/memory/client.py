"""
Agent Memory SDK - MemoryClient
统一入口类，提供所有公开方法

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
    MemoryListFilter, SessionInfo,
)
from .inner.controlplane import _ControlPlane
from .inner.dataplane import _DataPlane


class MemoryClient:
    """
    Memory Client 统一入口类

    提供 Memory 服务的完整调用能力，支持 Space 管理、Session 会话管理和消息/记忆的 CRUD 操作。

    认证方式:
        - 控制面 API (Space 管理): 使用 AK/SK 认证，环境变量 HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK
        - 数据面 API (消息/记忆): 使用 API Key 认证，环境变量 HW_API_KEY

    架构说明:
        - 控制面 (_ControlPlane): 处理 Space 的创建、查询、更新、删除等管理操作
        - 数据面 (_DataPlane): 处理 Session、消息、记忆等数据操作，使用 Space 绑定的 API Key 进行认证
        - 控制面采用懒加载模式，首次调用时才初始化

    方法分组:

        Space 管理 (控制面):
            - create_space: 在华为云创建 Memory Space 资源
            - get_space: 查询指定 Space 的详细信息
            - list_spaces: 分页查询用户所有 Space
            - update_space: 修改 Space 配置（TTL、标签、记忆策略等）
            - delete_space: 删除指定的 Space（会同时删除关联的 Session、消息和记忆）

        Session 会话 (数据面):
            - create_memory_session: 在指定 Space 中创建新会话

        消息管理 (数据面):
            - add_messages: 向会话添加消息（支持文本、工具调用、工具结果三种类型）
            - get_last_k_messages: 获取会话最近 K 条消息
            - get_message: 获取指定单条消息详情
            - list_messages: 分页查询会话消息

        记忆管理 (数据面):
            - search_memories: 语义搜索 Space 下的记忆记录
            - list_memories: 分页列出记忆记录
            - get_memory: 获取单条记忆详情
            - delete_memory: 删除指定记忆记录
    """

    def __init__(
            self,
            region_name: Optional[str] = "cn-north-4"
    ):
        """
        初始化 Memory Client

        创建一个 MemoryClient 实例，用于调用 Memory 服务的所有 API。

        初始化时:
        - 直接创建 DataPlane 实例（数据面），用于处理消息/记忆操作
        - ControlPlane（控制面）采用懒加载，第一次调用 Space 管理 API 时才初始化

        Args:
            region_name: 华为云区域名称，默认 "cn-north-4"

        Environment Variables:
            HUAWEICLOUD_SDK_AK: Access Key，控制面 API 必填
            HUAWEICLOUD_SDK_SK: Secret Key，控制面 API 必填
            HW_API_KEY: API Key，数据面 API 必填（需从 Space 获取）

        Raises:
            ValueError: 如果未配置控制面 AK/SK（仅在调用 Space 管理 API 时触发）

        Examples:
            >>> # 基础用法 - 设置环境变量后直接使用
            >>> import os
            >>> os.environ["HUAWEICLOUD_SDK_AK"] = "your-ak"
            >>> os.environ["HUAWEICLOUD_SDK_SK"] = "your-sk"
            >>> os.environ["HW_API_KEY"] = "your-api-key"  # 从 Space 获取
            >>>
            >>> client = MemoryClient()

            >>> # 指定区域（华为云各区域名称如 cn-north-4, cn-east-3 等）
            >>> client = MemoryClient(region_name="cn-east-3")
        """
        self.region_name = region_name

        self._control_plane = None  # 懒加载，首次调用控制面 API 时初始化
        self._data_plane = _DataPlane(region_name=region_name)  # 直接初始化
        self._control_plane_init_lock = threading.Lock()  # 线程安全锁

    def _ensure_control_plane_initialized(self, region_name: str):
        """
        确保控制面已初始化（线程安全的懒加载）

        Args:
            region_name: 华为云区域名称
        """
        with self._control_plane_init_lock:
            if self._control_plane is None:
                self._control_plane = _ControlPlane(region_name=region_name)

    # ==================== 控制面 - Space 管理 ====================

    def create_space(self, name: str, message_ttl_hours: int = 168, description: Optional[str] = None,
                     tags: Optional[List[Dict[str, str]]] = None,
                     memory_extract_idle_seconds: Optional[int] = None,
                     memory_extract_max_tokens: Optional[int] = None,
                     memory_extract_max_messages: Optional[int] = None,
                     public_access_enable: bool = True,
                     private_vpc_id: Optional[str] = None,
                     private_subnet_id: Optional[str] = None,
                     memory_strategies_builtin: Optional[List[str]] = None,
                     memory_strategies_customized: Optional[List[Dict[str, Any]]] = None) -> SpaceInfo:
        """
        创建 Space

        在华为云 Memory 服务中创建一个新的 Space 资源。
        Space 是 Memory 的核心资源单元，用于隔离不同应用或用户的数据。
        创建后会生成 API Key，用于数据面 API 的认证。

        实现逻辑:
            1. 将传入参数封装为 SpaceCreateRequest 对象
            2. 懒加载初始化 ControlPlane（控制面）
            3. 调用控制面 API 创建 Space
            4. 返回 SpaceInfo 对象，包含 Space ID 和 API Key 等信息

        Args:
            name: Space 名称，长度 1-128 字符
            message_ttl_hours: 消息默认保留时间（小时），默认 168（7天），范围 1-8760
            description: Space 描述信息，可选
            tags: Space 标签列表，用于资源分组和筛选，可选
            memory_extract_idle_seconds: 记忆抽取空闲时间（秒），超过后触发自动抽取，可选
            memory_extract_max_tokens: 记忆抽取最大 token 数，单次抽取上限，可选
            memory_extract_max_messages: 记忆抽取最大消息数，单次抽取上限，可选
            public_access_enable: 是否开启公网访问，默认 True
            private_vpc_id: 内网 VPC ID，开启内网访问时必填，需与 private_subnet_id 同时使用
            private_subnet_id: 内网子网 ID，开启内网访问时必填，需与 private_vpc_id 同时使用
            memory_strategies_builtin: 内置记忆策略列表，如 ["semantic", "episodic", "user_preference"]，可选
            memory_strategies_customized: 自定义记忆策略列表，JSON 数组格式，可选

        Returns:
            SpaceInfo: 创建成功的 Space 对象，包含以下关键属性:
                - id: Space 唯一标识
                - name: Space 名称
                - api_key: 数据面认证所需的 API Key（创建后只在返回中显示一次）
                - message_ttl_hours: 消息 TTL
                - created_at: 创建时间

        Raises:
            HTTPError: 当 API 调用失败时（权限不足、参数错误等）

        Examples:
            >>> # 1. 最简用法 - 创建基础 Space
            >>> space = client.create_space("my-chat-app")
            >>> print(f"Space ID: {space.id}")
            >>> print(f"API Key: {space.api_key}")  # 注意：API Key 只在创建后显示一次
            >>> # 后续使用: os.environ["HW_API_KEY"] = space.api_key

            >>> # 2. 自定义消息保留时间和描述
            >>> space = client.create_space(
            ...     name="long-term-memory",
            ...     message_ttl_hours=720,  # 30天
            ...     description="用于长期记忆存储的 Space"
            ... )

            >>> # 3. 开启内网访问（需要指定 VPC 和子网）
            >>> space = client.create_space(
            ...     name="internal-space",
            ...     public_access_enable=False,
            ...     private_vpc_id="vpc-0i2i8y2y2y2y2i2i8",
            ...     private_subnet_id="subnet-0i2i8y2y2y2y2i2i8"
            ... )

            >>> # 4. 启用记忆抽取策略
            >>> space = client.create_space(
            ...     name="extract-space",
            ...     memory_strategies_builtin=["semantic", "episodic"],
            ...     memory_extract_idle_seconds=3600,  # 空闲1小时后自动抽取
            ...     memory_extract_max_tokens=4000
            ... )
        """
        # 构建精简的创建请求
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

        # 确保控制面已初始化
        self._ensure_control_plane_initialized(self.region_name)

        # 调用control_plane方法
        return self._control_plane.create_space(request)

    def get_space(self, space_id: str) -> SpaceInfo:
        """
        获取 Space 详情

        查询指定 Space 的完整配置信息，包括资源状态、API Key、记忆策略等。
        注意：API Key 在 Space 创建后只能在首次查询时获取，后续查询不再返回。

        实现逻辑:
            1. 懒加载初始化 ControlPlane（如果尚未初始化）
            2. 调用控制面 API 查询 Space 详情
            3. 返回 SpaceInfo 对象

        Args:
            space_id: Space 的唯一标识 ID

        Returns:
            SpaceInfo: Space 的完整配置信息，包含:
                - id: Space ID
                - name: Space 名称
                - api_key: API Key（仅创建后首次查询返回）
                - message_ttl_hours: 消息 TTL
                - status: Space 状态
                - created_at / updated_at: 创建和更新时间
                - memory_strategies_builtin: 已启用的记忆策略

        Raises:
            HTTPError: 当 Space 不存在或无权限时

        Examples:
            >>> space = client.get_space("space-123")
            >>> print(f"Name: {space.name}")
            >>> print(f"TTL: {space.message_ttl_hours}h")
            >>> print(f"Status: {space.status}")
            >>> print(f"Strategies: {space.memory_strategies_builtin}")
        """
        # 确保控制面已初始化
        self._ensure_control_plane_initialized(self._data_plane._region_name)
        return self._control_plane.get_space(space_id)

    def list_spaces(
            self,
            limit: int = 20,
            offset: int = 0
    ) -> SpaceListResponse:
        """
        列出所有 Space

        分页查询当前用户拥有的所有 Space 资源。
        返回结果按创建时间倒序排列。

        实现逻辑:
            1. 懒加载初始化 ControlPlane（如果尚未初始化）
            2. 调用控制面 API 分页查询 Space 列表
            3. 返回 SpaceListResponse 对象，包含 items（Space 列表）和 total（总数）

        Args:
            limit: 每页返回数量，默认 20，最大支持 100
            offset: 分页偏移量，默认 0，用于跳过的记录数

        Returns:
            SpaceListResponse: 分页结果对象，包含:
                - items: List[SpaceInfo]，当前页的 Space 列表
                - total: int，所有 Space 的总数（用于计算分页）
                - limit / offset: 当前请求的分页参数

        Examples:
            >>> # 查询第一页
            >>> result = client.list_spaces(limit=10)
            >>> for space in result.items:
            ...     print(f"{space.id}: {space.name}")

            >>> # 分页遍历所有 Space
            >>> offset = 0
            >>> while True:
            ...     result = client.list_spaces(limit=50, offset=offset)
            ...     if not result.items:
            ...         break
            ...     for space in result.items:
            ...         print(space.name)
            ...     offset += len(result.items)
        """
        # 确保控制面已初始化
        self._ensure_control_plane_initialized(self._data_plane._region_name)
        return self._control_plane.list_spaces(limit, offset)

    def update_space(self, space_id: str, name: Optional[str] = None,
                     description: Optional[str] = None, message_ttl_hours: Optional[int] = None,
                     memory_extract_enabled: Optional[bool] = None,
                     memory_extract_idle_seconds: Optional[int] = None,
                     memory_extract_max_tokens: Optional[int] = None,
                     memory_extract_max_messages: Optional[int] = None,
                     tags: Optional[List[Dict[str, str]]] = None,
                     memory_strategies_builtin: Optional[List[str]] = None) -> SpaceInfo:
        """
        更新 Space 配置

        修改指定 Space 的配置信息，支持部分更新（只传需要修改的字段）。
        注意：某些字段如 memory_strategies_builtin 可能触发记忆重建，耗时较长。

        实现逻辑:
            1. 将传入参数封装为 SpaceUpdateRequest 对象（只包含非 None 字段）
            2. 懒加载初始化 ControlPlane（如果尚未初始化）
            3. 调用控制面 API 执行更新
            4. 返回更新后的 SpaceInfo 对象

        Args:
            space_id: Space ID，必填
            name: 新的 Space 名称，可选
            description: 新的描述信息，可选
            message_ttl_hours: 新的消息 TTL（小时），可选，范围 1-8760
            memory_extract_enabled: 是否开启记忆抽取，可选
            memory_extract_idle_seconds: 记忆抽取空闲时间（秒），可选
            memory_extract_max_tokens: 记忆抽取最大 token 数，可选
            memory_extract_max_messages: 记忆抽取最大消息数，可选
            tags: 新的标签列表（会替换原有标签），可选
            memory_strategies_builtin: 新的内置记忆策略列表，可选

        Returns:
            SpaceInfo: 更新后的 Space 对象

        Raises:
            HTTPError: 当 Space 不存在或参数无效时

        Examples:
            >>> # 只更新名称
            >>> client.update_space("space-123", name="new-name")

            >>> # 延长消息保留时间到 14 天
            >>> client.update_space("space-123", message_ttl_hours=336)

            >>> # 更新标签
            >>> client.update_space("space-123", tags=[{"key": "env", "value": "prod"}])

             >>> # 修改记忆策略（注意：可能触发记忆重建，耗时较长）
             >>> client.update_space("space-123", memory_strategies_builtin=["semantic"])
        """
        # 构建更新请求
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

        # 确保控制面已初始化
        self._ensure_control_plane_initialized(self._data_plane._region_name)
        return self._control_plane.update_space(space_id, request)

    def delete_space(self, space_id: str) -> None:
        """
        删除 Space

        删除指定的 Space 及其所有关联数据（Session、消息、记忆）。

        实现逻辑:
            1. 懒加载初始化 ControlPlane（如果尚未初始化）
            2. 调用控制面 API 删除 Space
            3. 无返回值

        Args:
            space_id: Space ID，必填

        Raises:
            HTTPError: 当 Space 不存在或无权限时

        Examples:
            >>> # 删除 Space（会同时删除所有 Session、消息和记忆）
            >>> client.delete_space("space-123")
        """
        # 确保控制面已初始化
        self._ensure_control_plane_initialized(self._data_plane._region_name)
        return self._control_plane.delete_space(space_id)

    # ==================== 数据面 - Session 管理 ====================

    def create_memory_session(
            self,
            space_id: str,
            id: Optional[str] = None,
            actor_id: Optional[str] = None,
            assistant_id: Optional[str] = None,
            meta: Optional[Dict[str, Any]] = None
    ) -> SessionInfo:
        """
        创建 Memory Session

        在指定的 Space 中创建一个新的会话，用于管理对话历史和记忆。

        Args:
            space_id: Space ID，必填。指定要创建会话的 Space
            id: Session ID，可选。指定要创建的会话 ID
            actor_id: 参与者 ID，可选。标识会话的用户或实体
            assistant_id: 助手 ID，可选。标识会话的服务端点或助手
            meta: 元数据，可选。用于存储会话的额外信息

        Returns:
            SessionInfo: 创建的会话信息，包含 session_id 等字段

        Examples:
            >>> # 基本用法
            >>> session = client.create_memory_session(space_id="space-123")
            >>> print(f"Session ID: {session.id}")

            >>> # 带有参与者信息
            >>> session = client.create_memory_session(
            ...     space_id="space-123",
            ...     actor_id="user-456",
            ...     assistant_id="assistant-789"
            ... )
        """
        # 使用SessionCreateRequest构建会话配置
        session_request = SessionCreateRequest(
            id=id,
            actor_id=actor_id,
            assistant_id=assistant_id,
            meta=meta
        )

        return self._data_plane.create_memory_session(space_id, session_request)

    # ==================== 数据面 - 消息管理 ====================

    def get_last_k_messages(
            self,
            session_id: str,
            k: int,
            space_id: str
    ) -> List[MessageInfo]:
        """
        获取最近 K 条消息

        从指定会话中获取最近的 K 条消息，按时间倒序排列。
        常用于对话补全（Context）、检查历史对话等场景。

        实现逻辑:
            1. 直接调用 DataPlane 的 get_last_k_messages 方法
            2. 返回消息列表（按时间倒序，最近的排在前面）

        Args:
            session_id: Session ID，指定要查询的会话
            k: 要获取的消息数量，正整数
            space_id: Space ID，会话所属的 Space

        Returns:
            List[MessageInfo]: 消息列表，按时间倒序排列（最近的消息在前），
                每个 MessageInfo 包含:
                - id: 消息 ID
                - role: 角色（user/assistant/system/tool）
                - parts: 消息内容列表
                - created_at: 创建时间

        Raises:
            HTTPError: 当 Session 或 Space 不存在时

        Examples:
            >>> # 获取最近 5 条消息
            >>> messages = client.get_last_k_messages("session-456", k=5, space_id="space-123")
            >>> for msg in messages:
            ...     print(f"[{msg.role}] {msg.parts}")

            >>> # 用于对话补全
            >>> recent_msgs = client.get_last_k_messages(session_id, k=10, space_id=space_id)
            >>> context = "\\n".join([f"{m.role}: {m.parts[0]['text']}" for m in recent_msgs if m.parts])
        """
        return self._data_plane.get_last_k_messages(session_id, k, space_id)

    def get_message(self, message_id: str, space_id: str, session_id: str) -> MessageInfo:
        """
        获取单条消息

        根据消息 ID 查询单条消息的完整信息。

        实现逻辑:
            1. 直接调用 DataPlane 的 get_message 方法
            2. 返回单条 MessageInfo 对象

        Args:
            message_id: 消息的唯一标识 ID
            space_id: Space ID，消息所属的 Space
            session_id: Session ID，消息所属的 Session

        Returns:
            MessageInfo: 消息详情对象，包含:
                - id: 消息 ID
                - role: 角色（user/assistant/system/tool）
                - parts: 消息内容列表
                - created_at: 创建时间
                - metadata: 元数据（如果有）

        Raises:
            HTTPError: 当消息不存在时

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
        添加消息

        向指定会话添加一条或多条消息，支持三种消息类型混合使用：
        - TextMessage: 文本消息（用户输入、助手回复等）
        - ToolCallMessage: 工具调用消息（AI 调用工具的请求）
        - ToolResultMessage: 工具结果消息（工具返回的结果）

        添加消息后，系统会根据 Space 配置的記憶策略自动处理消息：
        - semantic: 语义记忆提取
        - episodic: 情景记忆提取
        - user_preference: 用户偏好记忆提取

        实现逻辑:
            1. 遍历消息列表，将每条消息转换为 OpenAPI 格式（调用 to_dict()）
            2. 验证消息类型（只支持 TextMessage、ToolCallMessage、ToolResultMessage）
            3. 调用 DataPlane 的 add_messages 方法
            4. 返回 MessageBatchResponse，包含成功添加的消息列表

        Args:
            space_id: Space ID，必填
            session_id: Session ID，必填
            messages: 消息列表，必填，支持三种类型混合:
                - TextMessage: 文本消息
                - ToolCallMessage: 工具调用请求
                - ToolResultMessage: 工具执行结果
            timestamp: 消息时间戳（毫秒），用于指定消息的实际发生时间，可选
            idempotency_key: 幂等键，用于防止重复提交，可选
                - 相同 idempotency_key 的重复请求会被忽略
                - 建议使用 UUID 或业务唯一标识
            is_force_extract: 是否强制触发记忆抽取，可选
                - True: 立即触发记忆抽取（即使未达到空闲时间阈值）
                - False: 按照 Space 配置的空闲时间阈值触发（默认）

        Returns:
            MessageBatchResponse: 批量添加结果，包含:
                - items: List[MessageInfo]，成功添加的消息列表
                - count: 成功添加的消息数量

        Raises:
            ValueError: 当 messages 为空或包含不支持的消息类型时
            HTTPError: 当 Space 或 Session 不存在时

        Examples:
            >>> # 1. 添加文本消息
            >>> client.add_messages(
            ...     "space-123",
            ...     "session-456",
            ...     [TextMessage(role="user", content="你好，请帮我查询天气")]
            ... )

            >>> # 2. 添加多条文本消息
            >>> client.add_messages(
            ...     "space-123",
            ...     "session-456",
            ...     [
            ...         TextMessage(role="user", content="今天天气怎么样？"),
            ...         TextMessage(role="assistant", content="今天北京晴天，25°C")
            ...     ]
            ... )

            >>> # 3. 添加工具调用消息（AI 调用外部工具）
            >>> tool_call = ToolCallMessage(
            ...     id="call_123",
            ...     name="query_weather",
            ...     arguments={"city": "北京"}
            ... )
            >>> client.add_messages("space-123", "session-456", [tool_call])

            >>> # 4. 完整对话流程：用户提问 -> AI 调用工具 -> 工具返回结果
            >>> messages = [
            ...     TextMessage(role="user", content="北京天气怎么样？"),
            ...     ToolCallMessage(
            ...         id="call_123",
            ...         name="query_weather",
            ...         arguments={"city": "北京"}
            ...     ),
            ...     ToolResultMessage(
            ...         tool_call_id="call_123",
            ...         content="北京今天晴天，气温25°C，东南风3级"
            ...     )
            ... ]
            >>> client.add_messages("space-123", "session-456", messages)

            >>> # 5. 使用幂等键防止重复提交
            >>> import uuid
            >>> client.add_messages(
            ...     "space-123", "session-456",
            ...     [TextMessage(role="user", content="hello")],
            ...     idempotency_key=str(uuid.uuid4())
            ... )

            >>> # 6. 强制触发记忆抽取
            >>> client.add_messages(
            ...     "space-123", "session-456",
            ...     [TextMessage(role="user", content="重要信息")],
            ...     is_force_extract=True
            ... )
        """
        # 转换为OpenAPI格式
        message_requests = []

        for msg in messages:
            if isinstance(msg, (TextMessage, ToolCallMessage, ToolResultMessage)):
                message_requests.append(msg.to_dict())
            else:
                raise ValueError(f"不支持的消息类型: {type(msg)}")
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
        列出消息

        分页查询消息记录。可以查询指定 Session 的消息，也可以查询 Space 下所有消息。

        实现逻辑:
            1. 直接调用 DataPlane 的 list_messages 方法
            2. 返回分页结果

        Args:
            space_id: Space ID，必填
            session_id: Session ID，可选
                - 不传: 查询 Space 下所有消息
                - 传值: 查询指定 Session 的消息
            limit: 每页返回数量，默认 10，最大 100
            offset: 分页偏移量，默认 0

        Returns:
            MessageListResponse: 分页结果，包含:
                - items: List[MessageInfo]，消息列表
                - total: int，总数
                - limit / offset: 当前分页参数

        Examples:
            >>> # 查询 Space 下所有消息
            >>> result = client.list_messages("space-123")
            >>> for msg in result.items:
            ...     print(f"{msg.role}: {msg.parts[0].text if msg.parts else ''}")

            >>> # 查询指定 Session 的消息
            >>> result = client.list_messages("space-123", session_id="session-456")

            >>> # 分页遍历
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

    # ==================== 数据面 - 记忆管理 ====================

    def search_memories(
            self,
            space_id: str,
            filters: Optional[MemorySearchFilter] = None
    ) -> MemorySearchResponse:
        """
        搜索记忆

        基于语义相似度搜索 Space 下的记忆记录。
        使用向量检索找到与查询语句最相似的记忆。

        记忆类型说明:
            - semantic: 语义记忆，从对话内容中提取的精华信息
            - episodic: 情景记忆，特定场景/情境的记录
            - user_preference: 用户偏好，用户习惯和偏好信息

        实现逻辑:
            1. 将 MemorySearchFilter 转换为请求参数
            2. 调用 DataPlane 的 search_memories 方法
            3. 返回向量检索结果

        Args:
            space_id: Space ID，必填
            filters: 搜索过滤条件，可选，包含:
                - query: 搜索_query_（字符串）
                - top_k: 返回数量，默认 5
                - min_score: 最低相似度分数，0-1 之间
                - strategy_type: 记忆类型过滤（semantic/episodic/user_preference）
                - created_start / created_end: 时间范围过滤

        Returns:
            MemorySearchResponse: 搜索结果，包含:
                - records: List[MemoryInfo]，匹配的记忆列表
                - total: int，总匹配数
                - 每条 MemoryInfo 包含:
                    - id: 记忆 ID
                    - content: 记忆内容摘要
                    - score: 相似度分数
                    - strategy: 记忆类型

        Examples:
            >>> # 基本语义搜索
            >>> from agentarts.sdk.memory.inner.config import MemorySearchFilter
            >>> filters = MemorySearchFilter(query="用户偏好", top_k=3)
            >>> result = client.search_memories("space-123", filters)
            >>> for mem in result.records:
            ...     print(f"[{mem.score:.2f}] {mem.content}")

            >>> # 带过滤条件的搜索
            >>> filters = MemorySearchFilter(
            ...     query="天气查询习惯",
            ...     top_k=5,
            ...     min_score=0.7,
            ...     strategy_type="user_preference"  # 只搜索用户偏好
            ... )
            >>> result = client.search_memories("space-123", filters)

            >>> # 时间范围过滤
            >>> import time
            >>> filters = MemorySearchFilter(
            ...     query="重要事项",
            ...     created_start=int(time.time() * 1000) - 7 * 24 * 60 * 60 * 1000  # 最近7天
            ... )
            >>> result = client.search_memories("space-123", filters)
        """
        # 将Filter对象转换为请求体并调用dataplane
        return self._data_plane.search_memories(space_id, filters)

    def list_memories(
            self,
            space_id: str,
            limit: int = 10,
            offset: int = 0,
            filters: Optional[MemoryListFilter] = None
    ) -> MemoryListResponse:
        """
        列出记忆记录

        分页查询 Space 下的所有记忆记录（与 search_memories 不同，这是精确列表查询）。

        记忆类型:
            - semantic: 语义记忆
            - episodic: 情景记忆
            - user_preference: 用户偏好

        实现逻辑:
            1. 将 MemoryListFilter 转换为字典
            2. 调用 DataPlane 的 list_memories 方法
            3. 返回分页结果

        Args:
            space_id: Space ID，必填
            limit: 每页返回数量，默认 10，最大 100
            offset: 分页偏移量，默认 0
            filters: 过滤条件，可选，包含:
                - strategy_type: 按记忆类型过滤
                - created_start / created_end: 按创建时间过滤
                - sort_by: 排序字段（created_at 等）
                - sort_order: 排序方向（asc/desc）

        Returns:
            MemoryListResponse: 分页结果，包含:
                - items: List[MemoryInfo]，记忆列表
                - total: int，总数

        Examples:
            >>> # 列出所有记忆
            >>> result = client.list_memories("space-123")
            >>> for mem in result.items:
            ...     print(f"{mem.strategy}: {mem.content[:50]}...")

            >>> # 按类型过滤
            >>> filters = MemoryListFilter(strategy_type="semantic")
            >>> result = client.list_memories("space-123", filters=filters)

            >>> # 按时间排序
            >>> filters = MemoryListFilter(sort_by="created_at", sort_order="desc")
            >>> result = client.list_memories("space-123", filters=filters)
        """
        # 将Filter对象转换为字典并调用dataplane
        return self._data_plane.list_memories(space_id, limit, offset, filters)

    def get_memory(self, space_id: str, memory_id: str) -> MemoryInfo:
        """
        获取记忆记录

        根据记忆 ID 获取单条记忆的完整信息。

        实现逻辑:
            1. 直接调用 DataPlane 的 get_memory 方法
            2. 返回 MemoryInfo 对象

        Args:
            space_id: Space ID，必填
            memory_id: 记忆 ID，必填

        Returns:
            MemoryInfo: 记忆详情，包含:
                - id: 记忆 ID
                - content: 记忆内容
                - strategy: 记忆类型（semantic/episodic/user_preference）
                - created_at: 创建时间
                - metadata: 元数据

        Raises:
            HTTPError: 当记忆不存在时

        Examples:
            >>> mem = client.get_memory("space-123", "memory-456")
            >>> print(f"Type: {mem.strategy}")
            >>> print(f"Content: {mem.content}")
            >>> print(f"Created: {mem.created_at}")
        """
        return self._data_plane.get_memory(space_id, memory_id)

    def delete_memory(self, space_id: str, memory_id: str) -> None:
        """
        删除记忆记录

        根据记忆 ID 删除单条记忆。请注意，此操作不可恢复。

        实现逻辑:
            1. 直接调用 DataPlane 的 delete_memory 方法
            2. 无返回值

        Args:
            space_id: Space ID，必填
            memory_id: 记忆 ID，必填

        Raises:
            HTTPError: 当记忆不存在时

        Examples:
            >>> # 删除单条记忆
            >>> client.delete_memory("space-123", "memory-456")
        """
        return self._data_plane.delete_memory(space_id, memory_id)

    # ==================== 资源管理 ====================

    def close(self):
        """
        关闭 Client 连接

        释放所有底层连接资源，包括:
        - ControlPlane 的 HTTP 连接（如果已初始化）
        - DataPlane 的 HTTP 连接

        建议在使用完 Client 后调用此方法，或者使用上下文管理器（with 语句）。

        Examples:
            >>> # 方式1: 手动关闭
            >>> client = MemoryClient()
            >>> # ... 使用 client
            >>> client.close()

            >>> # 方式2: 使用上下文管理器（推荐）
            >>> with MemoryClient() as client:
            ...     # ... 使用 client
            >>> # 自动调用 close()
        """
        if self._control_plane is not None:
            self._control_plane.close()
        self._data_plane.close()

    def __enter__(self):
        """
        上下文管理器入口

        返回 Client 实例自身，支持 with 语句。

        Returns:
            MemoryClient: 当前实例
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器退出

        自动调用 close() 方法释放资源。

        Args:
            exc_type: 异常类型（如果有）
            exc_val: 异常值（如果有）
            exc_tb: 异常回溯（如果有）
        """
        self.close()
