# agentarts-memory-dsh

`agentarts-memory-dsh` 提供 DeepSeek Harness（DSH）与华为云 AgentArts Memory 之间集成能力。

## 功能概述

- **回合同步（写通路）**：每轮 DSH 交互结束（`turn/end` 事件）后，将该轮中的用户输入与 Agent 回复异步写入 AgentArts Memory——只投影人类可读的对话，排除工具协议载荷与私有推理；
- **MCP 工具（读写通路）**：基于 AgentArts SDK 的可选 `memory-mcp` extra 拉起 `agentarts-memory-mcp` 常驻 stdio 子进程，向模型注入 `ltm_search` 及 SDK 内置的记忆工具；
- **身份隔离**：写入与检索同时限定在配置的 Actor / Assistant 范围内，模型无法在工具调用时越权扩大范围；
- **凭据安全**：插件配置仅保存凭据引用（`apiKeyEnv`），由 DSH 的凭据服务在运行时解析，API Key 不展开进 Cordis YAML。

## 前置条件

- Node.js `^22.19` 或 `>=24`；管理 Profile 插件需要 `pnpm`；
- Python 3.10+ 与 `uv`（通过 `agentarts-sdk[memory-mcp]` 安装 `agentarts-memory-mcp` 服务）；
- 已创建 AgentArts 记忆库，取得记忆库 ID 与 Data Plane API Key。

## 安装

### 通过安装器安装（推荐）

[`agentarts-memory-installer`](../agentarts-memory-installer) 一条命令完成 MCP 服务安装（缺失时经 `uv tool install`）、插件 pnpm 依赖安装与 Profile 补丁合并：

```bash
agentarts-memory install dsh --profile web
```

- 要求目标 Profile 已存在（运行过 `dsh web`），且 `pnpm` 可用；
- `--dev` 使用本仓库本地源码安装插件并改用 git 版 MCP 服务，适合开发联调；
- 环境变量（含必填的 `AGENTARTS_MEMORY_ACTOR_ID`）见下文配置一节：安装器会把已提供/交互输入的 API Key 写入 `$DSH_HOME/.credentials.yaml`（凭据服务托管层，与上文凭据引用配套），其余四键写入 `$DSH_HOME/.env`（DSH 启动时作为用户环境层加载，已导出的环境变量优先）；缺失项在安装完成后打印清单提醒。

卸载：`agentarts-memory uninstall dsh --profile web`（移除依赖、补丁条目与我们写入的凭证/配置键）。

### 手动安装

1. 安装 MCP 检索服务（稳定版）：

   ```bash
   uv tool install 'agentarts-sdk[memory-mcp]'
   ```

   开发版（本仓库 main 分支）：

   ```bash
   uv tool install \
     'agentarts-sdk[memory-mcp] @ git+https://github.com/huaweicloud/agentarts-sdk-python.git@main'
   ```

2. 把插件安装进目标 Profile（DSH 的插件以 pnpm 依赖的形式装入 Profile，裸 `npm install` 不会生效）：

   ```bash
   dsh plugin --profile web add agentarts-memory-dsh
   ```

   开发联调可改用本地源码路径：`dsh plugin --profile web add /path/to/agentarts-sdk-python/plugins/agentarts-memory-dsh`。

3. 应用 Profile 覆盖层激活插件。临时体验可经 `--patch` 传入：

   ```bash
   dsh web --patch /path/to/agentarts-memory.cordis.yml
   ```

   持久启用则把 [`agentarts-memory.cordis.yml`](agentarts-memory.cordis.yml) 的插入条目合并进 `$DSH_HOME/profiles/web/cordis.patch.yml`（不要整文件覆盖——其中可能已有你自己的补丁）。

## 配置

将 [`agentarts-memory.cordis.yml`](agentarts-memory.cordis.yml) 作为可选的 Profile 覆盖层应用，或插入等效的配置项：

```yaml
- insert:
    - id: agentarts-memory
      name: agentarts-memory-dsh
      config:
        apiKeyEnv: HUAWEICLOUD_SDK_MEMORY_API_KEY
        spaceId: !!js process.env.AGENTARTS_MEMORY_SPACE_ID
        actorId: !!js process.env.AGENTARTS_MEMORY_ACTOR_ID
        assistantId: !!js process.env.AGENTARTS_MEMORY_ASSISTANT_ID || 'deepseek-harness'
        region: !!js process.env.HUAWEICLOUD_SDK_REGION || 'cn-southwest-2'
        dataEndpoint: !!js process.env.AGENTARTS_MEMORY_DATA_ENDPOINT
```

### 配置项列表

| 字段 | 必填 | 默认值 | 用途 |
|---|---|---|---|
| `apiKeyEnv` | 否 | `HUAWEICLOUD_SDK_MEMORY_API_KEY` | 由 DSH credentials 服务解析的 API Key 凭据引用 |
| `apiKey` | 否 | — | 直接提供密钥的兼容覆盖项；建议使用 `apiKeyEnv`，避免在插件配置中保存密钥 |
| `spaceId` | 是 | — | 已有的 AgentArts Memory Space |
| `actorId` | 是 | — | 附加到同步数据并限定 MCP 检索范围的稳定用户/租户标识 |
| `assistantId` | 否 | `deepseek-harness` | 附加到同步数据并限定 MCP 检索范围的助手标识 |
| `region` | 否 | `cn-southwest-2` | 用于推导数据面端点的区域 |
| `dataEndpoint` | 否 | 根据区域推导 | 显式指定的 HTTP(S) 数据面端点 |
| `requestTimeoutMs` | 否 | `30000` | 创建会话和添加消息请求的超时时间 |
| `maxRetries` | 否 | `2` | 网络错误、`429` 和 `5xx` 错误的重试次数 |
| `retryBaseDelayMs` | 否 | `250` | 指数退避的初始延迟 |
| `forceExtract` | 否 | `false` | 每个回合结束后请求立即提取记忆 |
| `mcpEnabled` | 否 | `true` | 挂载 AgentArts Memory MCP 服务 |
| `mcpServerName` | 否 | `agentarts-memory` | DSH MCP 工具的命名空间 |
| `mcpCommand` | 否 | `agentarts-memory-mcp` | 已安装的 MCP 子进程可执行文件 |
| `mcpArgs` | 否 | `[]` | 传递给 MCP 子进程的参数 |
| `mcpCwd` | 否 | 插件加载时 DSH 进程的工作目录 | MCP 子进程的工作目录 |
| `mcpToolCallTimeoutMs` | 否 | `60000` | 每次搜索的超时时间 |
| `mcpFailOnStartupError` | 否 | `true` | 搜索工具发现失败时拒绝激活插件 |

### 环境变量与凭据解析

```text
HUAWEICLOUD_SDK_MEMORY_API_KEY='<记忆库访问 API Key>'   # 凭据引用名，归属 $DSH_HOME/.credentials.yaml
AGENTARTS_MEMORY_SPACE_ID='<记忆库 ID>'
AGENTARTS_MEMORY_ACTOR_ID='<用户标识>'
AGENTARTS_MEMORY_ASSISTANT_ID='<助手标识>'
HUAWEICLOUD_SDK_REGION='cn-southwest-2'
```

插件配置仅保存凭据引用，不会把 API Key 展开到 Cordis YAML。默认引用 `HUAWEICLOUD_SDK_MEMORY_API_KEY`，由 DSH 的 `ctx.credentials` 在运行时解析；标准本地凭据提供方可从启动环境、`$DSH_HOME/.credentials.yaml`、项目 `.env` 或用户 `.env` 提供该值。直接写入 AgentArts 前会重新解析凭据，因此凭据存储中的密钥轮换会在下一次 HTTP 请求生效。

> **注意事项**
>
> 对于需要共享长期记忆的所有 DSH 会话，`AGENTARTS_MEMORY_ACTOR_ID` 和 `AGENTARTS_MEMORY_ASSISTANT_ID` 必须保持稳定。在多用户部署中，至少应为每个用户使用不同的 Actor ID；不同用户使用相同的值会导致数据混淆。插件会把 `actorId` 和 `assistantId` 同时附加到写入的会话与消息，并将二者传给 MCP 子进程，因此每次记忆检索都会被限定到相同的 Actor 和 Assistant 范围，模型无法在工具调用时覆盖该范围。

## 运行行为

插件监听 DSH 已提交的 `session/event` 事件流，并在收到 `turn/end` 时执行同步。它会保持事件顺序，只包含用户直接发出的消息和可见的助手文本，将用户图片表示为 `[image]`，并排除插件注入的上下文、工具协议载荷和私有推理。没有合格内容的回合不会触发远端写入。

符合 `^[a-zA-Z0-9\-_.]{1,64}$` 的 DSH 会话 ID 会原样用作 AgentArts 会话 ID；不符合该约束的 ID 则会确定性地映射为 UUIDv8。原始 DSH ID 始终保留在会话和消息元数据中。远端会话创建返回 `409` 表示会话恢复或热重载，此时会复用同一个 ID。每个回合写入都会根据 DSH 会话 ID、回合编号、结束事件序号以及必要时的消息分块生成确定性的幂等键，因此重试不会产生重复的消息批次。若单个回合超过 AgentArts 每次调用最多 100 条消息的限制，插件会按原顺序将其拆分为多个可独立幂等重试的请求。

同一会话的写入会按顺序串行执行。`session/flush` 和插件卸载会等待已经接受的任务完成；AgentArts 服务不可用时只会记录日志，不会中断 Agent 回合。MCP 默认采用严格启动策略，因为集成成功激活后应当能够提供记忆召回能力。

`agentarts-memory-mcp` 是常驻 stdio 子进程，其 API Key 在子进程启动时从同一凭据引用解析并注入（dsh-mcp-client 会清洗环境变量，故所需变量均显式传入）。修改 credentials 中的 Key 后，直接写入会自动使用新值；MCP 检索侧需要重载插件或重启 DSH，才能用新 Key 重建子进程环境。

## 验证

1. 重启 DSH（或热重载 Profile），确认模型可用工具中出现 `mcp__agentarts-memory__ltm_search`；
2. 进行一轮包含明确事实的对话（例如"记住我的验证口令是 lapsang-<随机后缀>"）；
3. 新建一个 DSH 会话，询问该事实并要求模型检索记忆，确认 `ltm_search` 能召回——同一 Actor/Assistant 之外的会话不应看到它。

## 开发

```bash
npm install
npm run check
```

`npm run check` = 类型检查 + vitest + 构建。
