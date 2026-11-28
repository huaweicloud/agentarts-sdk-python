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
| `search_memories` | `query`, `strategy_type`, `kind`, `category`, `top_k=5`, `min_score=0.7`, `start_time`, `end_time` | 语义检索云端记忆，可按策略、编程记忆种类及分类、时间范围（Unix 毫秒）过滤。`query` 必填；`top_k/min_score` 有默认值，其余过滤参数未传时省略。`strategy_type` 支持：`semantic` / `episodic` / `user_preference` / `summary` / `procedural`；传入 `kind` 或 `category` 时自动使用 `procedural`。 |

`user_id` 不作为工具参数（模型不应控制身份），由服务端从环境变量解析（见下表）。
`rerank`（搜索结果重排序）同样不暴露给模型：后端默认开启，本服务**默认关闭**，
运维通过 `AGENTARTS_MEMORY_RERANK` 开启。

### 编程记忆：kind 与 category

`kind` 和 `category` 都是可选的**单个字符串**，无默认分类。模型应按检索目的选择：

- `kind="observation"`：检索已记录的技术事实，例如具体改动、调查发现、修复结果、设计决策及其依据。
- `kind="experience"`：检索能指导未来工作的可复用工程方法、诊断路径、验证方法和失败教训，结合其适用条件使用。
- 无法判断某个维度时省略该字段；不要猜测分类，也不要传空字符串、`null` 或 `"all"`。两个字段均省略时不增加种类或分类过滤，仍受原有策略、用户、时间及相似度等条件约束。

`category` 的可选值随 `kind` 分为两套体系。observation 沿用 Claude-mem 的 `plugin/modes/code.json` 九分类（原 `type` 字段，不是 `concepts`）：

| observation category | 含义 |
| --- | --- |
| `bugfix` | 原先有问题的行为已修复 |
| `feature` | 新增能力或功能 |
| `refactor` | 代码结构调整，行为不变 |
| `change` | 文档、配置等一般修改 |
| `discovery` | 对已有系统的调查发现 |
| `decision` | 有依据的架构或设计选择 |
| `security_alert` | 需要及时关注的安全问题 |
| `security_note` | 值得记录但不紧急的安全发现 |
| `sensitive` | 不宜在不适当上下文中传播的信息 |

experience 使用与经验抽取侧约定的四分类，按经验自身的核心问题分类，不直接继承来源 observation 的类别：

| experience category | 含义 |
| --- | --- |
| `feature` | 功能实现、接口集成、能力设计及实现取舍的方法 |
| `bugfix` | 定位、解释和纠正非预期行为的可复用结论或诊断路径 |
| `testing` | 测试设计、覆盖、断言、mock、fixture、隔离和可靠性的方法 |
| `build-env` | 构建、依赖、运行环境、CI/CD、操作系统、shell、配置及工具链适配的方法 |

过滤组合与策略规则：

| 调用参数 | 请求行为 |
| --- | --- |
| 两者均不传 | 保留原逻辑：显式 `strategy_type` 原样传递，未传则省略 |
| 仅传 `kind` | 自动发送 `strategy_type="procedural"`，不限制该 kind 下的 category |
| 仅传 `category` | 允许两套分类的并集；自动发送 `strategy_type="procedural"`，由云端跨 kind 按 category 过滤，例如 `bugfix` 可匹配两种 kind |
| 同时传入 | 自动发送 `strategy_type="procedural"`，category 必须属于该 kind 的分类体系 |

两种 kind 都存储在程序化记忆下，因此只要提供任一分类字段，服务端就会将
`strategy_type` 设置为 `procedural`，即使调用方显式传入了其他策略。非法枚举值或不匹配的
kind/category 组合会在本地拒绝，不向云端发送搜索请求。

工具调用示例：

```json
{"query":"如何避免测试之间的状态污染","kind":"experience","category":"testing"}
```

```json
{"query":"认证模块最近修复了什么","kind":"observation","category":"bugfix"}
```

```json
{"query":"锁文件相关的修复","category":"bugfix"}
```

```json
{"query":"之前遇到过哪些构建问题"}
```

若希望搜索 **procedural 下所有 kind/category**，应显式指定策略，而不是依赖云端默认策略：

```json
{"query":"测试单独通过但组合运行失败，如何排查共享状态","strategy_type":"procedural"}
```

### 模型检索指导

工具描述、字段描述和 MCP 服务端 instructions 已覆盖以下选参建议：

- 用户提到之前的工作，或历史发现、决策、方法能帮助当前实现、排错、测试和环境问题时检索。
- 一次查询聚焦一个问题，包含技术对象、已知症状或错误文本和必要条件，避免粘贴整轮会话或编造细节。
- 需要“发生过什么、发现了什么、为何这样决策”时选 observation；需要“类似问题怎么处理”时选 experience；两者都有帮助或无法判断时省略 kind。
- category 只在有把握时设置。当前任务是修 bug，不代表历史上有用的事实只属于 bugfix，也可能属于 discovery 或 decision。
- 不确定的分类和时间条件应省略。召回为空或不相关时，可尝试一次更宽的查询，移除不确定的过滤条件；编程记忆仍显式使用 procedural。
- `top_k` 仅增加返回名额，不放宽过滤条件；降低 `min_score` 可能纳入较弱匹配，需检查适用性，分数不是正确概率。
- 空结果不等于历史上没有相关记忆；错误返回需要先处理错误。历史记忆也需与当前代码和证据核对。

这些描述旨在减少漏调工具、查询过于宽泛及分类过度过滤；实际召回质量仍需用真实查询集评估。

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
- REST 线格式：请求路径、Bearer 头、请求体默认值（top_k=5 / min_score=0.7 / actor_id）、
  5xx 错误透传——这些"标准答案"逐项对照 Python SDK 的实现
  （`memory_service.py` 数据面分支 + `agentarts_client.py` 归一化逻辑）；
- 编程记忆过滤：两套分类、单独和组合传参、未传字段省略、自动设置 `procedural`、
  覆盖显式冲突策略，以及非法分类值或组合不触发云端请求；
- 只读保证：全程无任何 `/sessions` 写路径端点被调用。

这些测试验证 MCP 行为与约定的请求格式，不代表已经完成真实云端的分类召回联调。

## 数据面接口参考

可单独转发给云端同事的说明见 [编程记忆搜索接口对接说明](CLOUD_API_INTEGRATION.md)。

服务器直接调用以下 REST 接口（Bearer 认证，`Content-Type: application/json`）：

完整 HTTP 请求示例（所有当前可发送字段均列出，标识及时间范围仅为示例）：

```http
POST https://memory.cn-southwest-2.huaweicloud-agentarts.com/v1/core/spaces/<space_id>/memories/search
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "query": "测试单独运行通过、组合运行失败时，如何排查共享缓存和 fixture 状态污染",
  "strategy_type": "procedural",
  "kind": "experience",
  "category": "testing",
  "top_k": 5,
  "min_score": 0.7,
  "actor_id": "<与写入侧一致的 actor_id>",
  "start_time": 1760000000000,
  "end_time": 1770000000000,
  "rerank": false
}
```

实际地址由区域或 `AGENTARTS_MEMORY_DATA_ENDPOINT` 决定；`space_id` 位于 URL 路径，
不是请求体字段。无需时间限制时应删除两个时间字段。

以下为 **当前 TS MCP 发往云端的请求约定与本地校验**，不代表云端已验证的约束：

| 字段 | 类型 | 默认值 / 省略规则 / 来源 |
| --- | --- | --- |
| `query` | string | 模型必传；建议使用有具体检索意图的非空文本，当前本地仅校验字符串类型 |
| `strategy_type` | string | 可选；文档支持 semantic / episodic / user_preference / summary / procedural。本地仅校验字符串；任一 kind/category 存在时强制覆盖为 procedural，否则原样传递或省略 |
| `kind` | string 枚举 | observation / experience；无默认值，未传省略 |
| `category` | string 枚举 | 对应 kind 的分类；无 kind 时接受两套分类的 11 值并集；未传省略 |
| `top_k` | integer | 1–100，默认 5，始终发送 |
| `min_score` | number | 0–1，默认 0.7，始终发送 |
| `actor_id` | string | 服务端从 AGENTARTS_MEMORY_USER_ID 或平台默认值解析，必须与写入侧一致；始终发送，模型不能设置 |
| `start_time` | integer | 可选非负 Unix 毫秒时间戳；未传省略 |
| `end_time` | integer | 可选非负 Unix 毫秒时间戳；未传省略 |
| `rerank` | boolean | 服务端配置，默认 false，始终发送；AGENTARTS_MEMORY_RERANK=1 / true 开启，模型不能设置 |

分类值精确匹配、区分大小写，不自动去除空白，不接受数组、多选、空字符串、`null` 或 `"all"`。
过滤条件按交集生效：策略 AND 用户范围 AND kind（如有）AND category（如有）AND 时间（如有），
结果还受相似度阈值和返回数量限制。“不限种类”指不添加该维度的过滤，不是返回全部记录。
分类过滤由云端执行，TS MCP 只校验并传递，不在召回后做本地分类过滤。

对接验收至少覆盖：两种 kind 的合法分类配对；仅 kind；仅 category（含跨 kind 的 feature/bugfix）；
仅 procedural、不限制 kind/category；不传三个字段的原搜索行为；有分类时覆盖其他 strategy_type；
未知枚举与不匹配组合在本地报错且不发送请求。

时间参数当前未在本地校验起止先后，工具描述会引导正确填写；云端采用哪个时间字段、
是否包含边界，以及反向时间区间的处理，需在联调时确认。

| 操作 | 接口 | 请求体 |
| --- | --- | --- |
| 语义检索 | `POST /v1/core/spaces/{space_id}/memories/search` | `{query, strategy_type?, kind?, category?, top_k, min_score, actor_id, start_time?, end_time?, rerank}`（可选过滤字段未设时省略；`rerank` 由服务端环境变量控制，非工具参数）→ `{records: [{record, score}]}` |

`kind/category` 当前按约定作为 JSON 请求体的**顶层可选字符串**实现；这是编程记忆扩展，
尚未完成云端接口联调，也不属于当前 Python SDK 的 `MemorySearchFilter` 字段。
如果云端格式后续调整，在 `src/memory-client.ts` 的请求体构造处修改映射。
例如上述 experience/testing 工具调用会发送：

```json
{
  "query": "如何避免测试之间的状态污染",
  "strategy_type": "procedural",
  "kind": "experience",
  "category": "testing",
  "top_k": 5,
  "min_score": 0.7,
  "actor_id": "<由服务端解析的用户标识>",
  "rerank": false
}
```

错误处理：接口失败时工具返回 `{"error": "...", "results": [], "total": 0}` 而非抛协议错误，
模型可以看到错误文本。

## 目录结构

```
src/               # TypeScript 源码（5 个模块：协议层/REST/客户端/配置/分类过滤）
src/search-filters.ts # kind/category 分类定义与过滤规则
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
