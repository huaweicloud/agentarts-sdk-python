# agentarts-memory-dsh

`agentarts-memory-dsh` 提供 DeepSeek Harness（DSH）与华为云 AgentArts Memory 之间集成能力。

- 每轮 DSH 交互结束（`turn/end`事件）后，将该轮交互中的用户输入和Agent回复异步写入 AgentArts Memory；
- 基于 [`agentarts-memory-mcp`](../agentarts-memory-mcp)，注入记忆检索工具供模型调用。

## 前置条件

- Node.js `^22.19` 或 `>=24`；
- 新建或使用已有 AgentArts 记忆库，获取记忆库ID及访问 API Key；

## 安装依赖

安装 AgentArts Memory MCP 服务和本插件：

```bash
uv tool install agentarts-memory-mcp
npm install agentarts-memory-dsh
```

## 配置

```text
HUAWEICLOUD_SDK_MEMORY_API_KEY='<记忆库访问 API Key>'
AGENTARTS_MEMORY_SPACE_ID='<记忆库 ID>'
AGENTARTS_MEMORY_ACTOR_ID='<用户标识>'
AGENTARTS_MEMORY_ASSISTANT_ID='<助手标识>'
HUAWEICLOUD_SDK_REGION='cn-southwest-2'
```

> **注意事项**
>
> 对于需要共享长期记忆的所有 DSH 会话，`AGENTARTS_MEMORY_ACTOR_ID` 和
> `AGENTARTS_MEMORY_ASSISTANT_ID` 必须保持稳定。在多用户部署中，至少应为每个用户使用不同的
> Actor ID；不同用户使用相同的值会导致数据混淆。插件会把 `actorId` 和 `assistantId` 同时附加到
> 写入的会话与消息，并将二者传给 MCP 子进程，因此每次记忆检索都会被限定到相同的 Actor 和
> Assistant 范围，模型无法在工具调用时覆盖该范围。

将 [`agentarts-memory.cordis.yml`](agentarts-memory.cordis.yml) 作为可选的 Profile 覆盖层应用，
或插入等效的配置项：

```yaml
- insert:
    - id: agentarts-memory
      name: agentarts-memory-dsh
      config:
        apiKey: !!js process.env.HUAWEICLOUD_SDK_MEMORY_API_KEY
        spaceId: !!js process.env.AGENTARTS_MEMORY_SPACE_ID
        actorId: !!js process.env.AGENTARTS_MEMORY_ACTOR_ID
        assistantId: !!js process.env.AGENTARTS_MEMORY_ASSISTANT_ID || 'deepseek-harness'
        region: !!js process.env.HUAWEICLOUD_SDK_REGION || 'cn-southwest-2'
```

### 配置项列表

| 字段 | 必填 | 默认值 | 用途 |
|---|---:|---|---|
| `apiKey` | 是 | — | AgentArts Memory 数据面 API Key；也会显式传递给已清理环境变量的 MCP 子进程 |
| `spaceId` | 是 | — | 已有的 AgentArts Memory Space |
| `actorId` | 是 | — | 附加到同步数据并限定 MCP 检索范围的稳定用户/租户标识 |
| `assistantId` | 否 | `deepseek-harness` | 附加到同步数据并限定 MCP 检索范围的助手标识 |
| `region` | 否 | `cn-southwest-2` | 用于推导数据面端点的区域 |
| `dataEndpoint` | 否 | 根据区域推导 | 显式指定的 HTTP(S) 数据面端点 |
| `requestTimeoutMs` | 否 | `30000` | 创建会话和添加消息请求的超时时间 |
| `maxRetries` | 否 | `2` | 网络错误、`429` 和 `5xx` 错误的重试次数 |
| `retryBaseDelayMs` | 否 | `250` | 指数退避的初始延迟 |
| `forceExtract` | 否 | `false` | 每个回合结束后请求立即提取记忆 |
| `mcpEnabled` | 否 | `true` | 挂载仅提供搜索能力的 MCP 服务 |
| `mcpServerName` | 否 | `agentarts-memory` | DSH MCP 工具的命名空间 |
| `mcpCommand` | 否 | `agentarts-memory-mcp` | 已安装的 MCP 子进程可执行文件 |
| `mcpArgs` | 否 | `[]` | 传递给 MCP 子进程的参数 |
| `mcpCwd` | 否 | 插件加载时 DSH 进程的工作目录 | MCP 子进程的工作目录 |
| `mcpToolCallTimeoutMs` | 否 | `60000` | 每次搜索的超时时间 |
| `mcpFailOnStartupError` | 否 | `true` | 搜索工具发现失败时拒绝激活插件 |

## 回合同步行为

插件监听 DSH 已提交的 `session/event` 事件流，并在收到 `turn/end` 时执行同步。它会保持事件顺序，
只包含用户直接发出的消息和可见的助手文本，将用户图片表示为 `[image]`，并排除插件注入的上下文、
工具协议载荷和私有推理。没有合格内容的回合不会触发远端写入。

每个 DSH 会话都会确定性地映射为 AgentArts 所要求的 UUID：常规的 `session-<uuid>` 形式直接使用其
UUID 后缀，其他不透明 ID 则映射为稳定的 UUIDv8。原始 DSH ID 仍会保留在会话和消息元数据中。
远端会话创建返回 `409` 表示会话恢复或热重载，此时会复用映射后的 ID。每个回合写入都会根据 DSH
会话 ID、回合编号和结束事件序号生成确定性的幂等键，因此重试不会产生重复的消息批次。

同一会话的写入会按顺序串行执行。`session/flush` 和插件卸载会等待已经接受的任务完成；AgentArts
服务不可用时只会记录日志，不会中断 Agent 回合。MCP 默认采用严格启动策略，因为集成成功激活后
应当能够提供记忆召回能力。

## 开发

```bash
npm install
npm run check
```
