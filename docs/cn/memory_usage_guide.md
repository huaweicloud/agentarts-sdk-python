# Huawei Cloud Memory SDK 使用指南

本文档介绍如何使用华为云记忆管理SDK（AgentRunSDK）进行记忆的创建、查看和管理，主要用于开发环境联调。

## 📋 环境要求

- Python 3.7+
- 已安装 AgentRunSDK：`pip install AgentRunSDK`

## 🔧 环境变量配置

```
# 开发环境端点信息
export AGENTARTS_MEMORY_CONTROL_ENDPOINT="http://100.85.127.26"
export AGENTARTS_MEMORY_DATA_ENDPOINT="http://100.85.223.199"

# 华为云访问密钥，用于调用管理面创建space接口认证
export HUAWEICLOUD_SDK_AK="你的AK"
export HUAWEICLOUD_SDK_SK="你的SK"

# 创建space后，会返回API Key，请将其设置为环境变量，用于调用数据面接口认证
# 也可以通过 api_key 参数直接传入
export HUAWEICLOUD_SDK_MEMORY_API_KEY="你的数据面API密钥"
```

## 🏗️ SDK 架构

AgentRunSDK Memory SDK 提供两种使用模式：

1. **Client 模式**：功能完整的客户端，适合需要控制所有操作的应用场景
2. **Session 模式**：基于绑定的会话进行记忆管理，适合特定用户/对话场景

## 🚀 使用案例

### 1. Client 模式完整案例

```python
#!/usr/bin/env python3
"""
Client模式完整使用案例
创建Space -> 创建Session -> 发送Message -> 查询Memory -> 搜索Memory
"""
import os
import time
from hw_agentrun_wrapper.memory import MemoryClient
from hw_agentrun_wrapper.memory.inner.config import TextMessage

# 确保环境变量已设置
assert os.getenv('HUAWEICLOUD_SDK_AK'), "请设置 HUAWEICLOUD_SDK_AK"
assert os.getenv('HUAWEICLOUD_SDK_SK'), "请设置 HUAWEICLOUD_SDK_SK"

def client_mode_example():
    """Client模式完整示例"""
    print("=== Client模式完整示例 ===")

    # 1. 创建Space
    with MemoryClient() as client:
        print("1. 创建测试Space")
        space = client.create_space(
            name=f"client_test_space_{int(time.time())}",
            message_ttl_hours=168,
            description="Client模式测试专用空间",
            memory_strategies_builtin=["semantic", "user_preference", "episodic"]
        )
        space_id = space.id
        print(f"✓ Space创建成功: {space_id}")
        print(f"  API Key ID: {space.api_key_id}")

        # 2. 创建会话
        print("\n2. 创建会话")
        session_data = client.create_memory_session(
            space_id=space_id,
            actor_id="client-test-user",
            assistant_id="client-test-assistant"
        )
        session_id = session_data.id
        print(f"✓ Session创建成功: {session_id}")

        # 3. 发送消息（使用TextMessage对象）
        print("\n3. 发送对话消息")
        messages = [
            TextMessage(
                role="user",
                content="你好，我想了解电商推荐算法，能够根据用户行为进行个性化推荐的算法有哪些？",
                actor_id="client-test-user"
            ),
            TextMessage(
                role="assistant",
                content="电商推荐算法主要包括：1) 协同过滤算法，基于用户行为相似性推荐；2) 基于内容的推荐，分析商品特征；3) 深度学习算法，能更准确捕捉用户偏好。推荐组合使用多种算法提升准确率。",
                actor_id="client-test-assistant"
            ),
            TextMessage(
                role="user",
                content="我对机器学习的监督学习特别感兴趣，深度学习和传统机器学习有什么区别？",
                actor_id="client-test-user"
            )
        ]

        add_result = client.add_messages(
            space_id=space_id,
            session_id=session_id,
            messages=messages
        )
        print(f"✓ 已添加 {len(add_result.items)} 条消息")

        # 4. 等待记忆系统处理消息
        print("\n4. 等待记忆系统处理消息...")
        time.sleep(30)

        # 5. 列出记忆
        print("\n5. 查询记忆列表")
        memories = client.list_memories(
            space_id=space_id,
            limit=10
        )
        print(f"✓ 发现 {len(memories.items)} 条记忆")

        for i, memory in enumerate(memories.items[:3]):
            print(f"  {i+1}. {memory.content[:50]}...")
            print(f"     策略: {memory.strategy_type}")

        # 6. 搜索记忆（使用MemorySearchFilter对象）
        print("\n6. 搜索相关记忆")
        from hw_agentrun_wrapper.memory.inner.config import MemorySearchFilter
        search_results = client.search_memories(
            space_id=space_id,
            filters=MemorySearchFilter(query="机器学习", top_k=3)
        )

        print(f"✓ 找到 {len(search_results.results)} 条相关记忆")
        for i, result in enumerate(search_results.results):
            score = result.get('score', 0)
            content = result.get('record', {}).get('content', '')[:60]
            print(f"  {i+1}. [{score:.2f}] {content}...")

        # 7. 获取特定记忆详情
        if memories.items:
            print("\n7. 获取记忆详情")
            memory_id = memories.items[0].id
            memory_detail = client.get_memory(space_id, memory_id)
            print(f"✓ 记忆ID: {memory_detail.id}")
            print(f"   内容: {memory_detail.content[:80]}...")
            print(f"   策略: {memory_detail.strategy_type}")

        return space_id, session_id

if __name__ == "__main__":
    client_mode_example()
```

### 2. Session 模式完整案例

```python
#!/usr/bin/env python3
"""
Session模式完整使用案例
创建Space -> 绑定会话 -> 发送Message -> 查询Memory -> 搜索Memory
"""
import os
import time
from hw_agentrun_wrapper.memory import MemoryClient
from hw_agentrun_wrapper.memory.session import MemorySession
from hw_agentrun_wrapper.memory.inner.config import TextMessage

# 确保环境变量已设置
assert os.getenv('HUAWEICLOUD_SDK_AK'), "请设置 HUAWEICLOUD_SDK_AK"
assert os.getenv('HUAWEICLOUD_SDK_SK'), "请设置 HUAWEICLOUD_SDK_SK"

def session_mode_example():
    """Session模式完整示例"""
    print("=== Session模式完整示例 ===")

    # 1. 创建Space
    with MemoryClient() as client:
        print("1. 创建测试Space")
        space = client.create_space(
            name=f"session-test-space-{int(time.time())}",
            message_ttl_hours=168,
            description="Session模式测试专用空间",
            memory_strategies_builtin=["semantic", "user_preference", "episodic"]
        )
        space_id = space.id
        print(f"✓ Space创建成功: {space_id}")

        # 2. 创建并绑定会话
        print("\n2. 创建并绑定会话")
        session_obj = MemorySession(
            space_id=space_id,
            actor_id="session-test-user",
            assistant_id="session-test-assistant"
        )
        session_id = session_obj.session_id
        print(f"✓ Session创建并绑定成功: {session_id}")

        # 3. 发送对话消息（使用TextMessage对象）
        print("\n3. 模拟用户与AI助手对话")
        messages = [
            TextMessage(
                role="user",
                content="我是一个数据分析师，主要使用Python和SQL进行数据处理"
            ),
            TextMessage(
                role="assistant",
                content="数据分析师是很有前景的职业！Python方面，pandas、numpy、matplotlib是核心库。"
            ),
            TextMessage(
                role="user",
                content="我最感兴趣的是可视化和机器学习方向，有什么推荐的学习路径吗？"
            ),
            TextMessage(
                role="assistant",
                content="可视化推荐学习matplotlib、seaborn、plotly；机器学习可以从scikit-learn入门，然后学习深度学习框架如TensorFlow或PyTorch。"
            ),
            TextMessage(
                role="user",
                content="我对Python数据分析很熟练，但机器学习经验还比较少，应该从哪里开始？"
            )
        ]

        add_result = session_obj.add_messages(messages)
        print(f"✓ 已添加 {len(messages)} 条对话消息")

        # 4. 等待记忆系统处理
        print("\n4. 等待记忆系统生成...")
        time.sleep(30)

        # 5. 查询消息（在绑定会话上下文中）
        print("\n5. 查询当前会话的消息")
        messages_response = session_obj.list_messages(limit=10)
        print(f"✓ 会话中有 {messages_response.total} 条消息")

        # 6. 获取会话中的记忆列表
        print("\n6. 查看生成的记忆")
        memories = session_obj.list_memories(limit=10)
        memory_list = memories.items

        print(f"✓ 总共发现 {len(memory_list)} 条记忆")
        for i, memory in enumerate(memory_list):
            content = memory.content[:50]
            strategy = memory.strategy_type or 'unknown'
            print(f"  {i+1}. [{strategy}] {content}...")

        # 7. 在会话上下文中搜索记忆（使用MemorySearchFilter对象）
        print("\n7. 搜索Python相关记忆")
        from hw_agentrun_wrapper.memory.inner.config import MemorySearchFilter
        search_results = session_obj.search_memories(
            filters=MemorySearchFilter(query="Python", top_k=3)
        )

        print(f"✓ 找到 {len(search_results.results)} 条相关记忆")
        for i, result in enumerate(search_results.results):
            score = result.get('score', 0)
            content = result.get('record', {}).get('content', '')[:60]
            print(f"  {i+1}. [{score:.2f}] {content}...")

        # 8. 获取特定记忆详情
        if memory_list:
            print("\n8. 获取第一条记忆详情")
            memory_id = memory_list[0].id
            memory_detail = session_obj.get_memory(memory_id)
            print(f"✓ 记忆ID: {memory_detail.id}")
            print(f"   内容: {memory_detail.content[:80]}...")
            print(f"   策略: {memory_detail.strategy_type}")
            print(f"   来源策略: {memory_detail.strategy_id or 'N/A'}")

        return space_id, session_id

if __name__ == "__main__":
    session_mode_example()
```

## 📝 API方法说明

### Client 类详细API

#### 初始化方法

**`__init__(region_name="cn-north-4", api_key=None)`**
- **功能**: 初始化MemoryClient客户端
- **入参**:
  - `region_name` (str, 可选, 默认"cn-north-4"): 华为云区域名称
  - `api_key` (str, 可选): 数据面API密钥，如果不传入则从环境变量 `HUAWEICLOUD_SDK_MEMORY_API_KEY` 读取
- **出参**: 无 (初始化实例)
- **环境要求**: 需设置HUAWEICLOUD_SDK_AK和HUAWEICLOUD_SDK_SK环境变量

#### 控制面方法 (Space管理)

**`create_space(name, message_ttl_hours=168, description=None, tags=None, memory_extract_idle_seconds=None, memory_extract_max_tokens=None, memory_extract_max_messages=None, public_access_enable=True, private_vpc_id=None, private_subnet_id=None, memory_strategies_builtin=None, memory_strategies_customized=None)`**
- **功能**: 创建记忆空间
- **入参**:
  - `name` (str, 必填): Space名称，长度1-128
  - `message_ttl_hours` (int, 可选, 默认168): 消息TTL时间(小时)，范围1-8760
  - `description` (str, 可选): 描述信息
  - `tags` (List[Dict], 可选): 标签列表
  - `memory_extract_idle_seconds` (int, 可选): 记忆抽取空闲时间
  - `memory_extract_max_tokens` (int, 可选): 记忆抽取最大token数
  - `memory_extract_max_messages` (int, 可选): 记忆抽取最大消息数
  - `public_access_enable` (bool, 可选, 默认True): 是否开启公网访问
  - `private_vpc_id` (str, 可选): 内网VPC ID，需与private_subnet_id同时提供
  - `private_subnet_id` (str, 可选): 内网子网ID
  - `memory_strategies_builtin` (List[str], 可选): 内置记忆策略列表
  - `memory_strategies_customized` (List[Dict], 可选): 自定义记忆策略列表
- **出参**: `SpaceInfo` - 创建的Space信息，是类型化对象，属性包括:
  - `id`: Space ID
  - `name`: Space名称
  - `api_key`: API Key（仅创建时可见）
  - `api_key_id`: API Key ID
  - `description`: 描述信息
  - `message_ttl_hours`: 消息TTL
  - `status`: Space状态 (creating/running/deleted/create_failed)
  - `created_at`: 创建时间
  - `updated_at`: 更新时间
  - `public_access`: 公网访问配置
  - `private_access`: 内网访问配置

**`list_spaces(limit=20, offset=0)`**
- **功能**: 列出所有Space
- **入参**:
  - `limit` (int, 可选, 默认20): 每页数量，范围1-100
  - `offset` (int, 可选, 默认0): 偏移量
- **出参**: `SpaceListResponse` - 包含以下属性:
  - `items`: SpaceInfo对象列表
  - `total`: 总数量

**`get_space(space_id)`**
- **功能**: 获取Space详情
- **入参**:
  - `space_id` (str, 必填): Space ID
- **出参**: `SpaceInfo` - Space详细信息

**`update_space(space_id, name=None, description=None, message_ttl_hours=None, memory_extract_enabled=None, memory_extract_idle_seconds=None, memory_extract_max_tokens=None, memory_extract_max_messages=None, tags=None, memory_strategies_builtin=None)`**
- **功能**: 更新Space配置
- **入参**:
  - `space_id` (str, 必填): Space ID
  - `name` (str, 可选): 新名称
  - `description` (str, 可选): 新描述
  - `message_ttl_hours` (int, 可选): 新TTL时间
  - `memory_extract_enabled` (bool, 可选): 是否开启记忆抽取
  - `memory_extract_idle_seconds` (int, 可选): 记忆抽取空闲时间
  - `memory_extract_max_tokens` (int, 可选): 记忆抽取最大token数
  - `memory_extract_max_messages` (int, 可选): 记忆抽取最大消息数
  - `tags` (List[Dict], 可选): 标签列表
  - `memory_strategies_builtin` (List[str], 可选): 内置记忆策略列表
- **出参**: `SpaceInfo` - 更新后的Space信息

**`delete_space(space_id)`**
- **功能**: 删除Space
- **入参**:
  - `space_id` (str, 必填): Space ID
- **出参**: None

#### 数据面方法 (Session管理)

**`create_memory_session(space_id, actor_id=None, assistant_id=None, meta=None)`**
- **功能**: 创建Memory Session
- **入参**:
  - `space_id` (str, 必填): Space ID
  - `actor_id` (str, 可选): 参与者ID
  - `assistant_id` (str, 可选): 助手ID
  - `meta` (Dict, 可选): 元数据
- **出参**: `SessionInfo` - Session信息，包含:
  - `id`: Session ID
  - `space_id`: Space ID
  - `actor_id`: 参与者ID
  - `assistant_id`: 助手ID
  - `meta`: 元数据
  - `created_at`: 创建时间
  - `updated_at`: 更新时间

#### 数据面方法 (消息管理)

**`add_messages(space_id, session_id, messages, *, timestamp=None, idempotency_key=None, is_force_extract=False)`**
- **功能**: 添加消息（支持文本消息、工具调用消息和工具结果消息）
- **入参**:
  - `space_id` (str, 必填): Space ID
  - `session_id` (str, 必填): Session ID
  - `messages` (List[Union[TextMessage, ToolCallMessage, ToolResultMessage]]): 消息列表
    - 文本消息使用 `TextMessage(role="user"/"assistant"/"system", content="...", actor_id=..., assistant_id=...)`
    - 工具调用消息使用 `ToolCallMessage(id="...", name="...", arguments={...})`
    - 工具结果消息使用 `ToolResultMessage(tool_call_id="...", content="...", asset_ref=...)`
  - `timestamp` (int, 可选): 客户端时间戳(毫秒)
  - `idempotency_key` (str, 可选): 幂等键，防止重复请求
  - `is_force_extract` (bool, 可选, 默认False): 是否强制触发记忆抽取
- **出参**: `MessageBatchResponse` - 添加结果，包含:
  - `items`: 添加成功的MessageInfo列表

**`get_last_k_messages(session_id, k, space_id)`**
- **功能**: 获取最近K条消息
- **入参**:
  - `session_id` (str, 必填): Session ID
  - `k` (int, 必填): 获取的消息数量
  - `space_id` (str, 必填): Space ID
- **出参**: `List[MessageInfo]` - 消息列表，每个MessageInfo包含:
  - `id`: 消息ID
  - `session_id`: 会话ID
  - `seq`: 序号
  - `role`: 消息角色
  - `parts`: 消息内容
  - `actor_id`: 参与者ID
  - `assistant_id`: 助手ID
  - `created_at`: 创建时间

**`get_message(message_id, space_id, session_id)`**
- **功能**: 获取单条消息
- **入参**:
  - `message_id` (str, 必填): 消息ID
  - `space_id` (str, 必填): Space ID
  - `session_id` (str, 必填): Session ID
- **出参**: `MessageInfo` - 消息详情

**`list_messages(space_id, session_id=None, limit=10, offset=0)`**
- **功能**: 列出消息
- **入参**:
  - `space_id` (str, 必填): Space ID
  - `session_id` (str, 可选): Session ID，为空时列出所有会话消息
  - `limit` (int, 可选, 默认10): 每页数量
  - `offset` (int, 可选, 默认0): 偏移量
- **出参**: `MessageListResponse` - 消息列表，包含:
  - `items`: MessageInfo对象列表
  - `total`: 总数量

#### 数据面方法 (记忆管理)

**`search_memories(space_id, filters=None)`**
- **功能**: 搜索记忆
- **入参**:
  - `space_id` (str, 必填): Space ID
  - `filters` (MemorySearchFilter, 可选): 过滤条件，可包含:
    - `query` (str): 搜索查询字符串
    - `strategy_type` (str): 策略类型过滤 (semantic/summary/user_preference/episodic/event/custom)
    - `strategy_id` (str): 策略ID过滤
    - `actor_id` (str): 参与者ID过滤
    - `assistant_id` (str): 助手ID过滤
    - `session_id` (str): 会话ID过滤
    - `memory_type` (str): 记忆类型过滤 (memory/episode/reflection)
    - `start_time` (int): 开始时间戳(毫秒)
    - `end_time` (int): 结束时间戳(毫秒)
    - `top_k` (int, 默认10): 返回前K个结果
    - `min_score` (float, 默认0.5): 最小相关性分数(0-1)
- **出参**: `MemorySearchResponse` - 搜索结果，包含:
  - `results`: 结果列表，每个元素包含 `record` 和 `score`
  - `total`: 总数量

**`list_memories(space_id, limit=10, offset=0, filters=None)`**
- **功能**: 列出记忆记录
- **入参**:
  - `space_id` (str, 必填): Space ID
  - `limit` (int, 可选, 默认10): 每页返回数量
  - `offset` (int, 可选, 默认0): 偏移量
  - `filters` (MemoryListFilter, 可选): 过滤条件，可包含:
    - `strategy_type` (str): 策略类型过滤
    - `strategy_id` (str): 策略ID过滤
    - `actor_id` (str): 参与者ID过滤
    - `assistant_id` (str): 助手ID过滤
    - `session_id` (str): 会话ID过滤
    - `start_time` (int): 开始时间戳(毫秒)
    - `end_time` (int): 结束时间戳(毫秒)
    - `sort_by` (str): 排序字段 (created_at/updated_at)
    - `sort_order` (str): 排序方向 (asc/desc)
- **出参**: `MemoryListResponse` - 记忆记录列表，包含:
  - `items`: MemoryInfo对象列表
  - `total`: 总数量

**`get_memory(space_id, memory_id)`**
- **功能**: 获取记忆记录详情
- **入参**:
  - `space_id` (str, 必填): Space ID
  - `memory_id` (str, 必填): 记忆ID
- **出参**: `MemoryInfo` - 记录详情，包含:
  - `id`: 记忆ID
  - `space_id`: Space ID
  - `content`: 记忆内容
  - `strategy_type`: 策略类型
  - `strategy_id`: 策略ID
  - `actor_id`: 参与者ID
  - `assistant_id`: 助手ID
  - `session_id`: 会话ID
  - `memory_type`: 记忆类型
  - `created_at`: 创建时间
  - `updated_at`: 更新时间

**`delete_memory(space_id, memory_id)`**
- **功能**: 删除记忆记录
- **入参**:
  - `space_id` (str, 必填): Space ID
  - `memory_id` (str, 必填): 记忆ID
- **出参**: None

### Session 类详细API

#### 初始化方法

**`__init__(space_id, actor_id, session_id=None, region_name=None, api_key=None)`**
- **功能**: 初始化MemorySession对象
- **入参**:
  - `space_id` (str, 必填): Space ID
  - `actor_id` (str, 必填): 参与者ID
  - `session_id` (str, 可选): Session ID，不提供时自动调用API创建
  - `region_name` (str, 可选): 区域名称，默认"cn-north-4"
  - `api_key` (str, 可选): 数据面API密钥，如果不传入则从环境变量 `HUAWEICLOUD_SDK_MEMORY_API_KEY` 读取
- **出参**: 无 (初始化实例)
- **特点**: 创建时自动绑定space_id和session_id

**`of(space_id, actor_id, session_id=None, region_name=None, api_key=None)` (classmethod)**
- **功能**: 工厂方法创建MemorySession
- **入参**: 同`__init__`方法
- **出参**: MemorySession实例

#### 消息管理方法

**`add_messages(messages, *, timestamp=None, idempotency_key=None, is_force_extract=False)`**
- **功能**: 向当前绑定的会话添加消息（支持文本消息、工具调用消息和工具结果消息）
- **入参**:
  - `messages` (List[Union[TextMessage, ToolCallMessage, ToolResultMessage]]): 消息列表
    - 文本消息使用 `TextMessage(role="user"/"assistant"/"system", content="...", actor_id=..., assistant_id=...)`
    - 工具调用消息使用 `ToolCallMessage(id="...", name="...", arguments={...})`
    - 工具结果消息使用 `ToolResultMessage(tool_call_id="...", content="...", asset_ref=...)`
  - `timestamp` (int, 可选): 客户端时间戳(毫秒)
  - `idempotency_key` (str, 可选): 幂等键
  - `is_force_extract` (bool, 可选, 默认False): 是否强制触发记忆抽取
- **出参**: `MessageBatchResponse` - 添加结果，包含:
  - `items`: 添加成功的MessageInfo列表
- **特点**: 自动使用绑定的space_id和session_id

**`get_message(message_id)`**
- **功能**: 获取当前绑定会话中的特定消息
- **入参**:
  - `message_id` (str, 必填): 消息ID
- **出参**: `MessageInfo` - 消息详情
- **特点**: 自动使用绑定的space_id和session_id

**`list_messages(limit=10, offset=0)`**
- **功能**: 列出当前绑定会话中的消息
- **入参**:
  - `limit` (int, 可选, 默认10): 每页数量
  - `offset` (int, 可选, 默认0): 偏移量
- **出参**: `MessageListResponse` - 消息列表，包含:
  - `items`: MessageInfo对象列表
  - `total`: 总数量
- **特点**: 自动使用绑定的space_id和session_id

**`get_last_k_messages(k)`**
- **功能**: 获取当前绑定会话中最近K条消息
- **入参**:
  - `k` (int, 必填): 获取的消息数量
- **出参**: `List[MessageInfo]` - 消息列表
- **特点**: 自动使用绑定的space_id和session_id

#### 记忆管理方法

**`search_memories(filters=None)`**
- **功能**: 在当前绑定的会话中搜索记忆
- **入参**:
  - `filters` (MemorySearchFilter, 可选): 过滤条件，可包含:
    - `query` (str): 搜索查询字符串
    - `strategy_type` (str): 策略类型过滤
    - `strategy_id` (str): 策略ID过滤
    - `actor_id` (str): 参与者ID过滤
    - `assistant_id` (str): 助手ID过滤
    - `session_id` (str): 会话ID过滤
    - `memory_type` (str): 记忆类型过滤
    - `start_time` (int): 开始时间戳(毫秒)
    - `end_time` (int): 结束时间戳(毫秒)
    - `top_k` (int, 默认10): 返回前K个结果
    - `min_score` (float, 默认0.5): 最小相关性分数
- **出参**: `MemorySearchResponse` - 搜索结果，包含:
  - `results`: 结果列表，每个元素包含 `record` 和 `score`
  - `total`: 总数量
- **特点**: 自动使用绑定的space_id

**`list_memories(limit=10, offset=0, filters=None)`**
- **功能**: 列出当前绑定会话中的记忆记录
- **入参**:
  - `limit` (int, 可选, 默认10): 每页返回数量
  - `offset` (int, 可选, 默认0): 偏移量
  - `filters` (MemoryListFilter, 可选): 过滤条件
- **出参**: `MemoryListResponse` - 记忆记录列表，包含:
  - `items`: MemoryInfo对象列表
  - `total`: 总数量
- **特点**: 自动使用绑定的space_id

**`get_memory(memory_id)`**
- **功能**: 获取当前绑定会话中特定的记忆记录
- **入参**:
  - `memory_id` (str, 必填): 记忆记录ID
- **出参**: `MemoryInfo` - 记录详情
- **特点**: 自动使用绑定的space_id

**`delete_memory(memory_id)`**
- **功能**: 删除当前绑定会话中特定的记忆记录
- **入参**:
  - `memory_id` (str, 必填): 记录ID
- **出参**: None
- **特点**: 自动使用绑定的space_id

### 资源管理方法

**`close()`**
- **功能**: 关闭客户端连接，释放资源
- **入参**: 无
- **出参**: 无

**`__enter__()` 和 `__exit__()`**
- **功能**: 支持上下文管理器语法 (with语句)
- **用法**: `with MemoryClient() as client:`

## 🔄 错误处理

常见的错误类型和处理方式：

```python
import logging
from hw_agentrun_wrapper.memory import MemoryClient
from hw_agentrun_wrapper.memory.inner.config import TextMessage

try:
    with MemoryClient() as client:
        # 进行各种操作
        space = client.create_space(
            name="test-space",
            message_ttl_hours=168
        )
        session = client.create_memory_session(
            space_id=space.id,
            actor_id="user-123"
        )
        memories = client.list_memories(space_id=space.id)

except ValueError as e:
    # 参数验证错误
    logging.error(f"参数错误: {e}")

except Exception as e:
    # 网络、认证或其他系统错误
    logging.error(f"系统错误: {e}")
    # 可以重试或联系技术支持
```

## 📚 API 参考

### 认证信息
- **管理面（控制面）**：使用 AK/SK 认证，通过 `HUAWEICLOUD_SDK_AK` 和 `HUAWEICLOUD_SDK_SK` 环境变量
- **数据面**：使用 API Key 认证，可通过以下两种方式提供：
  - 通过 `api_key` 参数直接传入
  - 通过 `HUAWEICLOUD_SDK_MEMORY_API_KEY` 环境变量提供

### 请求流程
1. 使用 AK/SK 创建 Space（控制面）
2. SDK 自动创建 API Key 并返回 `api_key`（仅创建时可见）和 `api_key_id`
3. SDK 内部自动使用 API Key 进行数据面操作
4. 配置数据面端点（可选，通过环境变量）

### 类型化返回值
SDK 使用类型化对象作为返回值，便于代码提示和类型检查：

| 返回类型 | 说明 | 重要属性 |
|---------|------|---------|
| `SpaceInfo` | Space 信息 | id, name, api_key, api_key_id, status, created_at |
| `SpaceListResponse` | Space 列表 | items (SpaceInfo列表), total, limit, offset |
| `SessionInfo` | Session 信息 | id, space_id, actor_id, assistant_id, created_at |
| `MessageInfo` | 消息信息 | id, session_id, role, parts, actor_id, created_at |
| `MessageListResponse` | 消息列表 | items (MessageInfo列表), total, limit, offset |
| `MessageBatchResponse` | 批量消息响应 | items (MessageInfo列表) |
| `MemoryInfo` | 记忆信息 | id, space_id, content, strategy_type, strategy_id, created_at |
| `MemoryListResponse` | 记忆列表 | items (MemoryInfo列表), total, limit, offset |
| `MemorySearchResponse` | 搜索结果 | results (列表，含record和score), total, query |

### 类型化请求对象
SDK 提供类型化的请求对象用于构建参数：

| 请求类型 | 用途 |
|---------|------|
| `TextMessage` | 文本消息，参数: role, content, actor_id, assistant_id |
| `ToolCallMessage` | 工具调用消息，参数: id, name, arguments |
| `ToolResultMessage` | 工具结果消息，参数: tool_call_id, content, asset_ref |
| `MemorySearchFilter` | 记忆搜索过滤，参数: query, top_k, min_score 等 |
| `MemoryListFilter` | 记忆列表过滤，参数: strategy_type, actor_id, sort_by 等 |

### 使用最佳实践
- 始终检查环境变量是否正确设置
- 根据场景选择 Client 或 Session 模式
- 理解记忆生成的延迟时间
- 合理设置 Space 的 TTL 时间
- 及时清理测试数据


## 🚨 使用注意事项

### 1. 环境变量重要性
- **AK/SK**：用于管理Space的创建和操作
- **HUAWEICLOUD_SDK_MEMORY_API_KEY**：用于数据面的消息和记忆操作，必须在创建Space后从响应中获取并设置，也可以通过 `api_key` 参数直接传入
- **端点配置**：开发环境需要设置自定义端点，生产环境使用华为云默认端点

### 2. 参数验证
- `content` 不能为空，最大长度为 10000 字符
- `strategy_type` 必须是支持的值之一
- `strategy_id`、`session_id` 等必须是有效的UUID格式
- `actor_id`、`assistant_id` 长度不能超过 64 个字符

### 3. 会话绑定（Session模式）
- Session 对象创建时自动绑定 `space_id` 和 `session_id`
- Session 模式下的操作都在绑定的会话上下文中进行
- 创建记忆时如果不提供 `actor_id`，将使用创建会话时的 `actor_id`

### 4. 记忆生成延迟
- 系统需要时间从对话消息中生成记忆
- 建议在发送消息后等待至少30秒再进行查询或搜索
- 搜索功能需要记忆生成完成才能返回结果

### 5. 资源清理
- 开发测试完成后建议清理测试数据
- 删除不再需要的Space可以释放资源
- 使用SDK的清理功能可以批量删除测试数据
