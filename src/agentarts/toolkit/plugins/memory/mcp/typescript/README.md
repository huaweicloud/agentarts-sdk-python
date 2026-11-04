# agentarts-memory-mcp

AgentArts Memory（华为云）的 MCP 服务器，TypeScript 实现，**运行时零依赖**。

为什么不用 Python 版：Python 版依赖 `agentarts-sdk`（连带 `mcp`、`requests` 等一串包），
部署负担重；本包构建后产出**单个 `dist/index.mjs`（约 750KB，所有依赖已内联）**，
运行时零依赖——目标机器只需要 Node >= 18，不需要 Python 环境。

## 它提供什么

目前只暴露一个只读召回工具（`list_memories` / `search_summary` 暂未用到，已移除，
需要时从 git 历史恢复）：

| Tool | 参数 | 说明 |
| --- | --- | --- |
| `search_memories` | `query`, `strategy_type`, `top_k=5`, `min_score=0.7`, `start_time`, `end_time` | 语义检索云端记忆，可按记忆类型和时间范围（Unix 毫秒）过滤；可选参数未传时不进请求体。`strategy_type` 支持：`semantic` / `episodic` / `user_preference` / `summary` / `procedural`（非法值会被后端拒绝：`Malformed request body`） |

`user_id` 不作为工具参数（模型不应控制身份），由服务端从环境变量解析（见下表）。
`rerank`（搜索结果重排序）同样不暴露给模型：后端默认开启，本服务**默认关闭**，
运维通过 `AGENTARTS_MEMORY_RERANK` 开启。

## 快速开始

```bash
npm install
npm run build              # typecheck + esbuild bundle -> dist/index.mjs
node dist/index.mjs        # stdio transport，进程由 MCP 宿主拉起
```

`dist/index.mjs` 是构建产物（不进 git），把所有依赖内联成一个文件，
部署时只需要这一个文件 + Node。

## 配置（环境变量）

| 变量 | 必填 | 说明 | 默认 |
| --- | --- | --- | --- |
| `HUAWEICLOUD_SDK_MEMORY_API_KEY` | ✅ | 数据面 API Key（Bearer 认证） | — |
| `AGENTARTS_MEMORY_SPACE_ID` | ✅ | Space ID | — |
| `HUAWEICLOUD_SDK_REGION` | | 区域（也认 `HUAWEICLOUD_REGION` / `OS_REGION_NAME`） | `cn-southwest-2` |
| `AGENTARTS_MEMORY_DATA_ENDPOINT` | | 数据面地址覆盖 | `https://memory.{region}.huaweicloud-agentarts.com` |
| `AGENTARTS_MEMORY_USER_ID` | ⚠️ | 记忆 actor_id，**必须与写入侧一致**，否则检索静默返回空 | 按平台推断：`cc-user` / `codex-user` / `opencode-user` / `__default__` |
| `AGENTARTS_MEMORY_RERANK` | | 搜索结果重排序（SDK 0.1.9 后端默认开启，本服务默认**关闭**） | `false`；设 `1` / `true` 开启 |
| `AGENTARTS_MEMORY_PLATFORM` | | 平台标识 | 自动探测（`*_PLUGIN_ROOT` 环境变量） |



## MCP 配置（客户端注册）

### OpenCode（`~/.config/opencode/opencode.json` 或项目 `.opencode/opencode.json`）

```json
{
  "mcp": {
    "agentarts_memory": {
      "type": "local",
      "command": ["node", "/path/to/mcp/typescript/dist/index.mjs"],
      "environment": {
        "HUAWEICLOUD_SDK_MEMORY_API_KEY": "<api-key>",
        "AGENTARTS_MEMORY_SPACE_ID": "<space-id>",
        "AGENTARTS_MEMORY_USER_ID": "<actor-id>"
      },
      "enabled": true,
      "timeout": 30000
    }
  }
}
```

> OpenCode 的 per-server `timeout` 默认 **5000ms**；数据面调用跨公网，建议显式调大。

### Claude Code（`~/.claude/settings.json`）

```json
{
  "mcpServers": {
    "agentarts_memory": {
      "command": "node",
      "args": ["/path/to/mcp/typescript/dist/index.mjs"],
      "env": {
        "HUAWEICLOUD_SDK_MEMORY_API_KEY": "<api-key>",
        "AGENTARTS_MEMORY_SPACE_ID": "<space-id>",
        "AGENTARTS_MEMORY_USER_ID": "<actor-id>"
      }
    }
  }
}
```

### Codex（`~/.codex/config.toml`）

```toml
[mcp_servers.agentarts_memory]
command = "node"
args = ["/path/to/mcp/typescript/dist/index.mjs"]

[mcp_servers.agentarts_memory.env]
HUAWEICLOUD_SDK_MEMORY_API_KEY = "<api-key>"
AGENTARTS_MEMORY_SPACE_ID = "<space-id>"
AGENTARTS_MEMORY_USER_ID = "<actor-id>"
```

> **重要**：`AGENTARTS_MEMORY_USER_ID` 必须与写入侧（capture 插件 / hook 写入记忆时使用的
> actor_id）一致，否则检索会**静默返回空结果**（HTTP 200、零记录、无任何报错）——
> 这是实测确认的行为，排查时优先检查这一项。

## 安装方式

- **源码工程**：整个目录拷给对方，`npm install && npm run build` 后即可使用；
- **npm 包**：`npm pack` 生成 tgz（`prepare` 钩子会自动构建），对方
  `npm i -g agentarts-memory-mcp-1.0.0.tgz` 后用 `agentarts-memory-mcp` 命令启动。

## 测试

```bash
npm test
```

端到端验证，不需要网络和真实凭证：在本地起一个 mock 数据面，拉起 `dist/index.mjs`
（MCP 宿主实际运行的同一个产物），逐项断言：

- MCP 协议行为：initialize 握手、tools/list、tools/call、未知工具报错、无凭证降级；
- REST 线格式：请求路径、Bearer 头、请求体默认值（num=5 / threshold=0.7 / actor_id）、
  5xx 错误透传——这些"标准答案"逐项对照 Python SDK 的实现
  （`memory_service.py` 数据面分支 + `agentarts_client.py` 归一化逻辑）；
- 只读保证：全程无任何 `/sessions` 写路径端点被调用。

## 数据面接口参考

服务器直接调用以下 REST 接口（Bearer 认证，`Content-Type: application/json`）：

| 操作 | 接口 | 请求体 |
| --- | --- | --- |
| 语义检索 | `POST /v1/core/spaces/{space_id}/memories/search` | `{query, strategy_type?, top_k, min_score, actor_id, start_time?, end_time?, rerank}`（可选字段未设时省略；`rerank` 由服务端环境变量控制，非工具参数）→ `{records: [{record, score}]}` |

错误处理：接口失败时工具返回 `{"error": "...", "results": [], "total": 0}` 而非抛协议错误，
模型可以看到错误文本。

## 目录结构

```
src/               # TypeScript 源码（4 个模块：协议层/REST/客户端/配置）
test/              # 端到端测试（mock 数据面，node:test，零测试依赖）
dist/index.mjs     # 构建产物（npm run build 生成，gitignore）
```

## Packaging（不随 wheel 分发）

本包位于 `agentarts-sdk` 仓库 `src/agentarts/toolkit/plugins/memory/mcp/typescript/`，
与 Python 版 `mcp/server.py` 并列，**不进入 wheel/sdist**（`pyproject.toml` 的
`[tool.uv.build-backend]` 已通过 `source-exclude` / `wheel-exclude` 排除，
`node_modules` 亦被 uv_build 默认排除）。分发方式：

- 整个目录拷给对方（`npm install && npm run build` 后使用）；
- 或本地构建后只发 `dist/index.mjs`（740KB，对方零构建）。

## License

Apache-2.0
