# agentarts-memory-mcp

华为云 AgentArts Memory 的本地 stdio MCP 服务。服务通过 `AsyncMemoryClient` 访问一个预先配置的记忆空间，并向 MCP Host 暴露只读的长期记忆检索工具。

## 功能概述

- 使用官方 MCP Python SDK v2 的高层 `MCPServer` API。
- 通过 stdin/stdout 与本地 MCP Host 通信。
- 进程启动时绑定一个 AgentArts Memory Space，调用者不能切换 Space。
- 可选绑定一个 Actor 和 Assistant，并将相应 ID 应用于每次检索。
- 只暴露只读工具 `ltm_search`，不开放空间管理、写入或删除操作。
- 每个服务进程复用一个异步 Memory Client，并在服务退出时关闭连接。
- 返回结构化结果；服务端异常记录到 stderr，工具调用仅收到脱敏错误。

## 前置条件

- Python 3.10 或更高版本。
- 已创建可用的 AgentArts Memory Space。
- 已取得该 Space 的 ID 和 Data Plane API Key。

## 安装

在当前仓库中开发或运行：

```bash
cd agentarts-memory-plugins/agentarts-memory-mcp
uv sync --locked
```

安装已发布的独立包：

```bash
uv tool install agentarts-memory-mcp
```

安装完成后，稳定入口命令为：

```bash
agentarts-memory-mcp
```

不做全局安装，也可以使用 `uvx` 在隔离环境中直接运行已发布的包：

```bash
uvx agentarts-memory-mcp
```

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|---|---:|---|---|
| `HUAWEICLOUD_SDK_MEMORY_API_KEY` | 是 | — | 绑定 Space 的 Data Plane API Key |
| `AGENTARTS_MEMORY_SPACE_ID` | 是 | — | 服务进程绑定的 Memory Space ID |
| `AGENTARTS_MEMORY_ACTOR_ID` | 否 | — | 检索限定的 Actor ID；未设置时在整个 Space 内检索 |
| `AGENTARTS_MEMORY_ASSISTANT_ID` | 否 | — | 检索限定的 Assistant ID；未设置时不按 Assistant 过滤 |
| `HUAWEICLOUD_SDK_REGION` | 否 | `cn-southwest-2` | 华为云区域；未设置时使用 SDK 默认值 |
| `AGENTARTS_MEMORY_DATA_ENDPOINT` | 否 | 按区域生成 | SDK 已支持的 Data Plane Endpoint 覆盖项 |

缺少必填变量时，进程在启动阶段以退出码 2 失败。错误只列出缺失变量名，不会
输出凭据值。

未设置 `AGENTARTS_MEMORY_ACTOR_ID` 时，服务会在启动阶段记录 warning，提示检索
范围包含该 Space 内的所有 Actor。

## MCP Host 配置

推荐使用 `uvx`，由 MCP Host 按需创建隔离环境并启动服务：

```json
{
  "mcpServers": {
    "agentarts-memory": {
      "command": "uvx",
      "args": ["agentarts-memory-mcp"],
      "env": {
        "HUAWEICLOUD_SDK_MEMORY_API_KEY": "<memory-api-key>",
        "AGENTARTS_MEMORY_SPACE_ID": "<space-id>",
        "AGENTARTS_MEMORY_ACTOR_ID": "<actor-id>",
        "AGENTARTS_MEMORY_ASSISTANT_ID": "<assistant-id>",
        "HUAWEICLOUD_SDK_REGION": "cn-southwest-2"
      }
    }
  }
}
```

如果已经通过 `uv tool install agentarts-memory-mcp` 完成全局安装，可移除
`args`，并将 `command` 改为 `agentarts-memory-mcp`。

不要把真实 API Key 提交到仓库。应由 MCP Host 的 Secret 管理机制或本地环境
注入。

## MCP 工具说明

### `ltm_search`

对绑定 Space 内的长期记忆执行语义检索。设置
`AGENTARTS_MEMORY_ACTOR_ID` 后，每次检索都会附带该 Actor 过滤条件，且 MCP
调用者不能覆盖。可选的 `AGENTARTS_MEMORY_ASSISTANT_ID` 以相同方式限定
Assistant。工具契约与
`agentarts-memory-hermes` 中的同名工具保持兼容。

| 参数 | 类型 | 必填 | 默认值 | 约束 | 说明 |
|---|---|---:|---|---|---|
| `query` | string | 是 | — | 至少包含一个非空白字符 | 检索文本 |
| `top_k` | integer | 否 | `5` | `1..100` | 返回最相关结果的数量 |

结构化返回示例：

```json
{
  "query": "用户的出行偏好",
  "results": [
    {
      "content": "用户更喜欢靠窗座位。",
      "score": 0.91,
      "strategy_type": "user_preference"
    }
  ]
}
```

每条结果固定包含 `content`、`score` 和 `strategy_type`。字段没有值时使用
`null`，无结果时返回空数组。

## 运行与故障处理

stdio 的 stdout 专用于 MCP JSON-RPC 消息。诊断日志写入 stderr。

如果工具返回 `AgentArts Memory search failed; check the server logs`，检查：

1. API Key 与 Space ID 是否匹配。
2. Actor ID 是否与目标记忆一致。
3. Region 是否正确。
4. Space 是否处于可用状态。
5. 网络是否能访问 Memory Data Plane Endpoint。

## 开发验证

```bash
uv run --locked ruff format --check src tests
uv run --locked ruff check src tests
uv run --locked mypy src
uv run --locked pytest
uv build
```

架构词汇见 [CONTEXT.md](CONTEXT.md)，实现步骤与验收标准见
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)，关键决策见
[docs/adr](docs/adr)。
