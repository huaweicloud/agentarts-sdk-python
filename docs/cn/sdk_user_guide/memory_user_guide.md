# Memory SDK 使用指南

## 概述

AgentArts Memory SDK 提供记忆管理功能，支持创建、存储和检索对话记忆。本文档介绍如何使用 Memory SDK 进行记忆空间的创建、会话管理和记忆操作。

## 环境要求

- Python 3.10+
- 已安装 AgentArts SDK：`pip install agentarts`

## 认证配置

### 华为云 AK/SK 认证

Memory SDK 使用华为云 AK/SK 进行身份认证。请通过以下方式配置：

**方式一：环境变量配置（推荐）**

```bash
# 设置华为云 AK/SK
export HUAWEICLOUD_SDK_AK="your-access-key"
export HUAWEICLOUD_SDK_SK="your-secret-key"
```

**方式二：代码中直接配置**

```python
import os
os.environ["HUAWEICLOUD_SDK_AK"] = "your-access-key"
os.environ["HUAWEICLOUD_SDK_SK"] = "your-secret-key"
```

### 获取 AK/SK

1. 登录华为云控制台
2. 进入"我的凭证"页面
3. 在"访问密钥"标签页创建或查看 AK/SK

### API Key 配置

创建 Space 后会生成 API Key，用于数据面操作。配置方式：

**方式一：环境变量配置**

```bash
export HUAWEICLOUD_SDK_MEMORY_API_KEY="your-memory-api-key"
```

**方式二：代码中直接传入**

```python
from agentarts.sdk.memory import MemoryClient

client = MemoryClient(api_key="your-memory-api-key")
```

## SDK 架构

Memory SDK 提供两种使用模式：

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| Client 模式 | 功能完整的客户端 | 需要控制所有操作的应用场景 |
| Session 模式 | 基于绑定的会话进行记忆管理 | 特定用户/对话场景 |

## 快速开始

### Client 模式示例

```python
import os
import time
from agentarts.sdk.memory import MemoryClient
from agentarts.sdk.memory.inner.config import TextMessage

# 验证环境变量
assert os.getenv('HUAWEICLOUD_SDK_AK'), "请设置 HUAWEICLOUD_SDK_AK"
assert os.getenv('HUAWEICLOUD_SDK_SK'), "请设置 HUAWEICLOUD_SDK_SK"

def client_mode_example():
    """Client 模式完整示例"""
    
    # 1. 创建 Space
    with MemoryClient() as client:
        print("创建记忆空间...")
        space = client.create_space(
            name="my-memory-space",
            message_ttl_hours=168,
            description="示例记忆空间",
            memory_strategies_builtin=["semantic", "user_preference", "episodic"]
        )
        space_id = space.id
        print(f"Space ID: {space_id}")
        print(f"API Key ID: {space.api_key_id}")

        # 2. 创建会话
        print("\n创建会话...")
        session_data = client.create_memory_session(
            space_id=space_id,
            actor_id="user-001",
            assistant_id="assistant-001"
        )
        session_id = session_data.id
        print(f"Session ID: {session_id}")

        # 3. 添加消息
        print("\n添加对话消息...")
        messages = [
            TextMessage(
                role="user",
                content="你好，我想了解机器学习的基础知识",
                actor_id="user-001"
            ),
            TextMessage(
                role="assistant",
                content="机器学习是人工智能的一个分支，主要研究如何让计算机从数据中学习规律。",
                actor_id="assistant-001"
            )
        ]
        
        client.add_messages(
            space_id=space_id,
            session_id=session_id,
            messages=messages
        )
        print("消息添加成功")

        # 4. 等待记忆生成
        print("\n等待记忆系统处理...")
        time.sleep(30)

        # 5. 查询记忆
        print("\n查询记忆列表...")
        memories = client.list_memories(space_id=space_id, limit=10)
        print(f"发现 {len(memories.items)} 条记忆")

        # 6. 搜索记忆
        print("\n搜索相关记忆...")
        from agentarts.sdk.memory.inner.config import MemorySearchFilter
        search_results = client.search_memories(
            space_id=space_id,
            filters=MemorySearchFilter(query="机器学习", top_k=3)
        )
        print(f"找到 {len(search_results.results)} 条相关记忆")

        return space_id, session_id

if __name__ == "__main__":
    client_mode_example()
```

### Session 模式示例

```python
import os
import time
from agentarts.sdk.memory import MemoryClient
from agentarts.sdk.memory.session import MemorySession
from agentarts.sdk.memory.inner.config import TextMessage

# 验证环境变量
assert os.getenv('HUAWEICLOUD_SDK_AK'), "请设置 HUAWEICLOUD_SDK_AK"
assert os.getenv('HUAWEICLOUD_SDK_SK'), "请设置 HUAWEICLOUD_SDK_SK"

def session_mode_example():
    """Session 模式完整示例"""
    
    # 1. 创建 Space
    with MemoryClient() as client:
        print("创建记忆空间...")
        space = client.create_space(
            name="session-mode-space",
            message_ttl_hours=168,
            description="Session 模式示例空间",
            memory_strategies_builtin=["semantic", "user_preference"]
        )
        space_id = space.id
        print(f"Space ID: {space_id}")

        # 2. 创建并绑定会话
        print("\n创建并绑定会话...")
        session = MemorySession(
            space_id=space_id,
            actor_id="user-002",
            assistant_id="assistant-002"
        )
        print(f"Session ID: {session.session_id}")

        # 3. 添加消息
        print("\n添加对话消息...")
        messages = [
            TextMessage(role="user", content="我是一名 Python 开发者"),
            TextMessage(role="assistant", content="Python 是一门优秀的编程语言！")
        ]
        
        session.add_messages(messages)
        print("消息添加成功")

        # 4. 等待记忆生成
        print("\n等待记忆系统处理...")
        time.sleep(30)

        # 5. 查询记忆
        print("\n查询记忆列表...")
        memories = session.list_memories(limit=10)
        print(f"发现 {len(memories.items)} 条记忆")

        # 6. 搜索记忆
        print("\n搜索相关记忆...")
        from agentarts.sdk.memory.inner.config import MemorySearchFilter
        search_results = session.search_memories(
            filters=MemorySearchFilter(query="Python", top_k=3)
        )
        print(f"找到 {len(search_results.results)} 条相关记忆")

        return space_id, session.session_id

if __name__ == "__main__":
    session_mode_example()
```

## API 参考

### MemoryClient 类

#### 初始化

```python
MemoryClient(region_name="cn-southwest-2", api_key=None)
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| region_name | str | 否 | cn-southwest-2 | 华为云区域名称 |
| api_key | str | 否 | None | 数据面 API 密钥，不传入则从环境变量读取 |

**环境变量要求**：
- `HUAWEICLOUD_SDK_AK`：华为云 Access Key
- `HUAWEICLOUD_SDK_SK`：华为云 Secret Key
- `HUAWEICLOUD_SDK_MEMORY_API_KEY`：数据面 API 密钥（可选，也可通过参数传入）

#### Space 管理方法

##### create_space

创建记忆空间。

```python
create_space(
    name: str,
    message_ttl_hours: int = 168,
    description: str = None,
    tags: List[Dict] = None,
    memory_strategies_builtin: List[str] = None,
    public_access_enable: bool = True
) -> SpaceInfo
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| name | str | 是 | - | Space 名称，长度 1-128 |
| message_ttl_hours | int | 否 | 168 | 消息 TTL 时间（小时），范围 1-8760 |
| description | str | 否 | None | 描述信息 |
| tags | List[Dict] | 否 | None | 标签列表 |
| memory_strategies_builtin | List[str] | 否 | None | 内置记忆策略列表 |
| public_access_enable | bool | 否 | True | 是否开启公网访问 |

**返回值**：`SpaceInfo` 对象

| 属性 | 类型 | 说明 |
|------|------|------|
| id | str | Space ID |
| name | str | Space 名称 |
| api_key | str | API Key（仅创建时可见） |
| api_key_id | str | API Key ID |
| status | str | Space 状态 |
| created_at | int | 创建时间戳 |

##### list_spaces

列出所有 Space。

```python
list_spaces(limit: int = 20, offset: int = 0) -> SpaceListResponse
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| limit | int | 否 | 20 | 每页数量，范围 1-100 |
| offset | int | 否 | 0 | 偏移量 |

**返回值**：`SpaceListResponse` 对象

##### get_space

获取 Space 详情。

```python
get_space(space_id: str) -> SpaceInfo
```

##### update_space

更新 Space 配置。

```python
update_space(
    space_id: str,
    name: str = None,
    description: str = None,
    message_ttl_hours: int = None
) -> SpaceInfo
```

##### delete_space

删除 Space。

```python
delete_space(space_id: str) -> None
```

#### Session 管理方法

##### create_memory_session

创建 Memory Session。

```python
create_memory_session(
    space_id: str,
    actor_id: str = None,
    assistant_id: str = None,
    meta: Dict = None
) -> SessionInfo
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| space_id | str | 是 | - | Space ID |
| actor_id | str | 否 | None | 参与者 ID |
| assistant_id | str | 否 | None | 助手 ID |
| meta | Dict | 否 | None | 元数据 |

**返回值**：`SessionInfo` 对象

#### 消息管理方法

##### add_messages

添加消息。

```python
add_messages(
    space_id: str,
    session_id: str,
    messages: List[Union[TextMessage, ToolCallMessage, ToolResultMessage]],
    timestamp: int = None,
    idempotency_key: str = None,
    is_force_extract: bool = False
) -> MessageBatchResponse
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| space_id | str | 是 | - | Space ID |
| session_id | str | 是 | - | Session ID |
| messages | List | 是 | - | 消息列表 |
| timestamp | int | 否 | None | 客户端时间戳（毫秒） |
| idempotency_key | str | 否 | None | 幂等键 |
| is_force_extract | bool | 否 | False | 是否强制触发记忆抽取 |

**消息类型**：

- `TextMessage`：文本消息
  ```python
  TextMessage(
      role="user",  # user/assistant/system
      content="消息内容",
      actor_id="用户ID",
      assistant_id="助手ID"
  )
  ```

- `ToolCallMessage`：工具调用消息
  ```python
  ToolCallMessage(
      id="调用ID",
      name="工具名称",
      arguments={"参数": "值"}
  )
  ```

- `ToolResultMessage`：工具结果消息
  ```python
  ToolResultMessage(
      tool_call_id="调用ID",
      content="结果内容"
  )
  ```

##### list_messages

列出消息。

```python
list_messages(
    space_id: str,
    session_id: str = None,
    limit: int = 10,
    offset: int = 0
) -> MessageListResponse
```

#### 记忆管理方法

##### search_memories

搜索记忆。

```python
search_memories(
    space_id: str,
    filters: MemorySearchFilter = None
) -> MemorySearchResponse
```

**MemorySearchFilter 参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| query | str | 否 | None | 搜索查询字符串 |
| strategy_type | str | 否 | None | 策略类型过滤 |
| actor_id | str | 否 | None | 参与者 ID 过滤 |
| session_id | str | 否 | None | 会话 ID 过滤 |
| top_k | int | 否 | 10 | 返回前 K 个结果 |
| min_score | float | 否 | 0.5 | 最小相关性分数（0-1） |

##### list_memories

列出记忆记录。

```python
list_memories(
    space_id: str,
    limit: int = 10,
    offset: int = 0,
    filters: MemoryListFilter = None
) -> MemoryListResponse
```

##### get_memory

获取记忆详情。

```python
get_memory(space_id: str, memory_id: str) -> MemoryInfo
```

##### delete_memory

删除记忆记录。

```python
delete_memory(space_id: str, memory_id: str) -> None
```

### MemorySession 类

#### 初始化

```python
MemorySession(
    space_id: str,
    actor_id: str,
    session_id: str = None,
    region_name: str = None,
    api_key: str = None
)
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| space_id | str | 是 | - | Space ID |
| actor_id | str | 是 | - | 参与者 ID |
| session_id | str | 否 | None | Session ID，不提供时自动创建 |
| region_name | str | 否 | None | 区域名称 |
| api_key | str | 否 | None | 数据面 API 密钥 |

#### 方法列表

Session 模式下的方法与 Client 模式类似，但自动使用绑定的 space_id 和 session_id：

| 方法 | 说明 |
|------|------|
| add_messages(messages) | 添加消息到当前会话 |
| list_messages(limit, offset) | 列出当前会话的消息 |
| search_memories(filters) | 搜索当前会话的记忆 |
| list_memories(limit, offset, filters) | 列出当前会话的记忆 |
| get_memory(memory_id) | 获取记忆详情 |
| delete_memory(memory_id) | 删除记忆记录 |

## 返回类型说明

### SpaceInfo

| 属性 | 类型 | 说明 |
|------|------|------|
| id | str | Space ID |
| name | str | Space 名称 |
| api_key | str | API Key（仅创建时可见） |
| api_key_id | str | API Key ID |
| description | str | 描述信息 |
| status | str | Space 状态 |
| created_at | int | 创建时间戳 |
| updated_at | int | 更新时间戳 |

### SessionInfo

| 属性 | 类型 | 说明 |
|------|------|------|
| id | str | Session ID |
| space_id | str | Space ID |
| actor_id | str | 参与者 ID |
| assistant_id | str | 助手 ID |
| created_at | int | 创建时间戳 |

### MemoryInfo

| 属性 | 类型 | 说明 |
|------|------|------|
| id | str | 记忆 ID |
| space_id | str | Space ID |
| content | str | 记忆内容 |
| strategy_type | str | 策略类型 |
| created_at | int | 创建时间戳 |

### MessageInfo

| 属性 | 类型 | 说明 |
|------|------|------|
| id | str | 消息 ID |
| session_id | str | 会话 ID |
| role | str | 消息角色 |
| parts | list | 消息内容 |
| created_at | int | 创建时间戳 |

## 错误处理

```python
import logging
from agentarts.sdk.memory import MemoryClient

try:
    with MemoryClient() as client:
        space = client.create_space(name="test-space")
        
except ValueError as e:
    # 参数验证错误
    logging.error(f"参数错误: {e}")
    
except Exception as e:
    # 网络、认证或其他系统错误
    logging.error(f"系统错误: {e}")
```

## 最佳实践

### 1. 认证信息管理

- 使用环境变量存储 AK/SK，避免硬编码
- 创建 Space 后妥善保存 API Key
- 生产环境建议使用密钥管理服务

### 2. 记忆生成延迟

- 系统需要时间从对话消息中生成记忆
- 发送消息后建议等待 30 秒再进行查询
- 搜索功能需要记忆生成完成才能返回结果

### 3. 资源管理

- 使用上下文管理器（with 语句）自动释放资源
- 开发测试完成后及时清理测试数据
- 删除不再使用的 Space 释放资源

### 4. 参数验证

- Space 名称长度 1-128 字符
- 消息内容最大长度 10000 字符
- actor_id、assistant_id 长度不超过 64 字符

## 常见问题

### Q1: 如何获取 API Key？

创建 Space 时会自动生成 API Key，仅在创建响应中返回一次。请妥善保存。

### Q2: 记忆搜索无结果？

确保：
1. 已等待足够时间让系统生成记忆（建议 30 秒以上）
2. 搜索关键词与对话内容相关
3. Space 状态为 running

### Q3: 认证失败怎么办？

检查：
1. AK/SK 是否正确配置
2. API Key 是否有效
3. 区域配置是否正确

### Q4: 如何选择 Client 或 Session 模式？

- **Client 模式**：需要管理多个 Space 或 Session，或需要完整的控制能力
- **Session 模式**：单一会话场景，代码更简洁
