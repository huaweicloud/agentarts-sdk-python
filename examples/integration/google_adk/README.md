# Google ADK Integration Example

展示如何使用 Google ADK（Agent Development Kit）创建 Agent，并通过 AgentArts 实现会话和记忆的云端持久化。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export HUAWEICLOUD_SDK_MEMORY_API_KEY="your-agentarts-api-key"
export AGENTARTS_MEMORY_SPACE_ID="your-space-id"
export OPENAI_API_KEY="your-openai-api-key"
export OPENAI_MODEL_NAME="openai/gpt-4o-mini"   # 可选，默认 openai/gpt-4o-mini
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选

# 运行示例
python google_adk_agent.py
```

## 工作原理

本示例展示了 Google ADK 与 AgentArts 的集成方式：

```
Google ADK                    AgentArts
┌─────────────┐              ┌──────────────────┐
│   Agent     │              │  AsyncMemoryClient│
│  (with tools)│             │  (Memory Backend) │
└─────┬───────┘              └────────┬─────────┘
      │                               │
┌─────┴───────────────────────────────┴─────────┐
│                  Runner                        │
│                                               │
│  ┌─────────────────────┐ ┌──────────────────┐ │
│  │ AgentArtsSession     │ │ AgentArtsMemory  │ │
│  │ Service              │ │ Service          │ │
│  │ (会话持久化)          │ │ (记忆抽取与搜索)  │ │
│  └─────────────────────┘ └──────────────────┘ │
└───────────────────────────────────────────────┘
```

- **AgentArtsSessionService**：将 ADK 的会话（Session）和事件（Event）持久化到 AgentArts 后端，支持 O(1) 复杂度的状态读取
- **AgentArtsMemoryService**：将对话事件写入 AgentArts 记忆系统，支持语义搜索，自动去重（基于 idempotency_key）

## 跨会话用户偏好

本示例演示了跨会话的用户偏好恢复：

```
Session 1  "我每个月预算 5000 元"
   │  → 对话内容入库 → 后端异步抽取为 user_preference 记忆
   ▼
Session 2  （新的 session_id，同一用户）
   │  → get_session 时从记忆中搜索偏好
   │  → 注入到 instruction 模板的 {user:preferences?} 位置
   ▼
Agent 参考"月预算 5000"回答消费建议
```

- **写入**：用户口头表达的偏好随对话入库，由后端抽取管道异步提取为 `user_preference` 记忆
- **读取**：`AgentArtsSessionService` 在恢复会话时搜索该用户的偏好，合并进 `session.state`
- **注入**：instruction 模板中的 `{user:preferences?}` 渲染出全部偏好文本（`?` 表示可选引用——首次会话无偏好时渲染为空，不报错）
- **异步最终一致**：偏好抽取是异步的。新会话立即开始可能搜不到刚表达的偏好，示例默认在两个会话间等待 30 秒（可用 `PREFERENCE_EXTRACT_WAIT_SECONDS` 调整）

## Agent 配置

Agent 配备了两个工具：

1. **calculate** - 计算数学表达式（支持 sqrt、sin、cos、log 等）
2. **get_current_time** - 获取当前日期和时间

Agent 的 `instruction` 引用 `{user:preferences?}` 模板，使偏好能进入提示词。

## 模型配置

ADK 的 `Agent.model` 接受 LiteLLM 格式的字符串，支持多种 LLM 提供商：

| 提供商 | model 字符串 | 所需环境变量 |
|--------|-------------|-------------|
| OpenAI | `openai/gpt-4o-mini` | `OPENAI_API_KEY` |
| Gemini | `gemini/gemini-2.0-flash` | `GOOGLE_API_KEY` |

## 环境变量

| 变量名 | 说明 | 必需 |
|-------|------|------|
| `HUAWEICLOUD_SDK_MEMORY_API_KEY` | AgentArts API Key | 是 |
| `AGENTARTS_MEMORY_SPACE_ID` | Memory Space ID | 否（默认 `default`） |
| `OPENAI_API_KEY` | OpenAI API Key | 是（使用 OpenAI 模型时） |
| `OPENAI_MODEL_NAME` | 模型名称（LiteLLM 格式） | 否（默认 `openai/gpt-4o-mini`） |
| `OPENAI_BASE_URL` | API Base URL | 否 |
| `PREFERENCE_EXTRACT_WAIT_SECONDS` | 会话间等待异步抽取的秒数 | 否（默认 `30`） |

## 常见问题

### 多轮对话报错 `Missing reasoning_content`

使用 DeepSeek 等推理模型时，多轮对话可能在第 4 轮左右报错：

```
BadRequestError: Missing `reasoning_content` field in the assistant message at index N
```

这是因为推理模型默认开启深度思考模式，返回的 assistant 消息包含 `reasoning_content` 字段，而 ADK 在后续轮次发送历史消息时不会携带该字段，导致 API 校验失败。

**解决方法**：通过 `generate_content_config` 关闭深度思考模式。本示例的 `google_adk_agent.py` 中已预留了相关注释代码，取消注释即可。具体参数名称和取值取决于所使用的 LLM API，请参考对应 API 文档。示例：

```python
from google.genai.types import GenerateContentConfig, HttpOptions

agent = Agent(
    ...
    generate_content_config=GenerateContentConfig(
        http_options=HttpOptions(
            extra_body={"thinking": {"type": "disabled"}}  # 参数因 API 而异
        )
    ),
)
```

## 与其他示例的对比

| 特性 | LangChain | LangGraph | Google ADK |
|------|-----------|-----------|------------|
| 框架 | LangChain AgentExecutor | LangGraph StateGraph | ADK Runner |
| 持久化方式 | 由 LangChain 管理 | AgentArtsMemorySessionSaver | AgentArtsSessionService |
| 记忆搜索 | 无 | 无 | 有（MemoryService） |
| 状态管理 | 消息列表 | Checkpoint | Session State（O(1) 读取） |
| 适用场景 | 简单工具调用 | 复杂状态流 | 工具调用 + 记忆管理 |
