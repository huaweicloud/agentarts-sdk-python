# 个人理财助手 Demo（Google ADK + AgentArts Memory/Code Interpreter）

个人理财助手演示，基于 Google ADK 构建，集成 AgentArts Memory（跨会话偏好追踪）和 Code Interpreter（pandas 数据分析 + matplotlib 图表生成）。

## 功能特性

- **支出记录** — 按日期/分类记录和查询支出（本地 JSON 存储）
- **数据分析** — 在 Code Interpreter 沙箱中运行 pandas 分析（汇总、趋势、对比）
- **图表生成** — 通过 Code Interpreter 生成 matplotlib 饼图/柱状图/折线图
- **跨会话记忆** — 跨对话记住用户预算、消费习惯和偏好
- **双通道记忆** — 通过 `before_model_callback` 自动注入 + 通过 `recall_memory` 工具按需召回

## AgentArts Memory 如何工作

LLM Agent 本身是无状态的——每次会话都从空白上下文开始。AgentArts Memory
通过提供一个跨会话的长期存储，弥补了这个缺口：

- **四种内置提取策略**（semantic、episodic、user_preference、summary）
  在服务端自动运行，把对话历史转化为结构化、可搜索的记忆条目。
- **自动注入** — `before_model_callback` 在每次 LLM 调用前检索记忆存储，
  将最相关的 3 条注入上下文，Agent 无需用户重复说明就知道预算和习惯。
- **按需召回** — 当自动注入的预览不够用时，`recall_memory` 工具可用
  定向查询做更深层的检索。
- **异步提取** — `after_agent_callback` 把对话写入记忆服务但不阻塞响应，
  接受最终一致性。

## 架构

```
用户输入
  │
  ▼
ADK Runner
  ├── before_model_callback  → search_memory → 注入 [Memory Context]
  ├── LlmAgent (LiteLLM)     → 按需调用工具
  │     ├── record_expense / query_expenses  （本地 JSON）
  │     ├── analyze_spending / generate_chart （Code Interpreter）
  │     └── recall_memory                     （Memory Service）
  └── after_agent_callback   → add_session_to_memory（异步提取）
```

## 环境准备

### 0. 安装 AgentArts SDK（在仓库根目录执行）

`requirements.txt` 中的 `agentarts-sdk` 是本仓库内的包（未发布到 PyPI），
需要先从仓库根目录安装：

```bash
uv sync            # 或：pip install -e .
```

### 1. 安装演示依赖

```bash
uv pip install -r examples/finance_adk/requirements.txt
```

### 2. 配置环境变量

```bash
cd examples/finance_adk
cp .env.example .env
```

编辑 `.env`，填入 LLM API Key 和 Base URL。

### 3. 创建 Memory Space

```bash
uv run python examples/finance_adk/setup_memory.py
```

创建 AgentArts Memory 空间，启用全部 4 种内置策略（semantic、episodic、user_preference、summary），并将凭证写入 `.env`。

### 4. 创建 Code Interpreter 资源

```bash
uv run python examples/finance_adk/setup_code_interpreter.py
```

创建 Code Interpreter 资源，并将其名称写入 `.env`。

## 使用方法

```bash
# 普通模式
uv run python examples/finance_adk/finance_agent.py

# 调试模式（输出详细的记忆搜索/提取日志）
uv run python examples/finance_adk/finance_agent.py --debug
```

### 演示流程

**会话 1：**
```
You: 我今天午饭花了 35，打车 18，买了一本书 49
Assistant: 已记录 3 笔支出：餐饮 35、交通 18、购物 49，合计 102 元

You: 我每个月预算 5000 元，想控制餐饮在 1500 以内
Assistant: 明白了。月预算 5000 元，餐饮预算 1500 元。
  → after_agent_callback 触发记忆提取

You: 分析一下我这个月的消费结构
Assistant: [调用 analyze_spending → Code Interpreter pandas]
  本月总支出 3,245 元：餐饮 37%、购物 27%、交通 14%、其他 22%

You: 画个饼图看看
Assistant: [调用 generate_chart → Code Interpreter matplotlib]
  已生成饼图，保存在 chart_pie_this_month.png
```

**会话 2（次日）：**
```
You: 我这个月还能花多少？
  → before_model_callback 自动注入："用户月预算 5000 元"
Assistant: 你的月预算是 5,000 元，已支出 3,245 元，剩余 1,755 元
```

## 文件结构

| 文件 | 说明 |
|------|------|
| `config.py` | 环境变量、常量 |
| `prompts.py` | 系统提示词 |
| `expense_store.py` | 本地 JSON 支出存储 |
| `finance_tools.py` | 5 个工具函数（支出、分析、图表、记忆） |
| `memory_tools.py` | `recall_memory` 工具 |
| `finance_agent.py` | ADK Agent + 回调 + CLI 入口 |
| `session_manager.py` | 多会话管理 |
| `setup_memory.py` | Memory Space 创建（首次运行） |
| `setup_code_interpreter.py` | Code Interpreter 资源创建（首次运行） |
| `cli_flags.py` | 调试标志 |

## 关键设计决策

- **`before_model_callback`** 用于记忆注入（ADK 原生支持，无需自定义节点）
- **`after_agent_callback`** 用于记忆提取（Runner 不会自动调用 `add_session_to_memory`）
- **`code_session`** 每次工具调用使用上下文管理器（自动清理，无长连接会话）
- **`auto_create_session=True`** 在 Runner 中设置（ADK 默认为 False）
- **LiteLLM 格式** 模型名称（`openai/deepseek-v4-flash`），通过 config 自动添加前缀
- **异步记忆提取** — 接受最终一致性，不阻塞响应

## 常见问题

### Code Interpreter 会话启动超时

`analyze_spending` / `generate_chart` 每次调用都会打开一个沙箱会话。
SDK 的默认 HTTP 请求超时为 30 秒，但 `start_session` 在冷启动时
（长时间未调用、或沙箱需要重新分配资源）可能需要 60 秒以上，从而触发超时报错。

Demo 默认使用 SDK 的 30s 超时。如果你遇到超时问题，可以在
`finance_tools.py` 的 `_code_session()` 中解除注释，将数据面请求超时提升到 180s：

```python
# 恢复 180s 超时的备选方案（默认使用 SDK 的 30s）：
#   from agentarts.sdk.service.http_client import RequestConfig
#   client.data_plane_client._config = RequestConfig(
#       base_url=client.data_plane_client._config.base_url,
#       timeout=180.0,
#       headers=client.data_plane_client._config.headers,
#       verify_ssl=client.data_plane_client._config.verify_ssl,
#   )
```

注意：`CodeInterpreter` / `DataToolsHttpClient` 目前不暴露 `timeout` 参数，
因此该方案需要访问内部属性。待 SDK 提供公开的 timeout 配置后即可移除。

### 多轮对话报错 `Missing reasoning_content`

推理模型（如 DeepSeek-V4-Flash）返回的 assistant 消息包含 `reasoning_content`
字段。部分平台要求历史 assistant 消息也必须携带该字段，而 ADK 不会持久化
该字段，因此多轮对话约在第 3-4 轮时报错：

```
BadRequestError: Missing `reasoning_content` field in the assistant message at index N
```

Demo **默认不启用**任何规避方案。如果你使用推理模型时遇到此问题，可以在
`finance_agent.py` 的 `build_agent()` 中取消 `generate_config` 块的注释，
并重新启用 `generate_content_config` 参数：

```python
generate_config = types.GenerateContentConfig(
    http_options=types.HttpOptions(
        extra_body={"thinking": {"type": "disabled"}}
    )
)
```

**重要提醒**：不同模型/平台的参数名称和取值并不相同（`thinking.type`、
`enable_thinking`、`thinking_budget` 等），请以你所使用的实际平台和模型
的 API 文档为准。