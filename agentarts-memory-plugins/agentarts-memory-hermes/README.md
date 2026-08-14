# agentarts-memory-hermes

Hermes Memory Provider 插件，将华为云 AgentArts Memory 作为 Hermes Agent 的长期记忆后端。

## 功能概述

- **跨会话记忆持久化**：每轮对话后自动写入 AgentArts Memory（非阻塞）
- **上下文注入**：LLM 调用前自动注入相关记忆（用户画像 / 情景 / 语义 + 历史摘要）
- **压缩保护**：上下文压缩前重新注入相关记忆，避免关键信息被裁掉
- **MEMORY.md 镜像**：将 Hermes 内置 `MEMORY.md` 的写入同步到 AgentArts
- **主动检索工具**：
  - `ltm_search` — 搜索长期记忆，返回与查询相关的记忆条目
  - `ltm_search_summary` — 获取记忆摘要列表

## 前置条件

1. 安装Hermes（安装教程：https://hermes-agent.nousresearch.com/docs/getting-started/installation）
2. 创建华为云AgentArts记忆库，获取到区域（`HUAWEICLOUD_SDK_REGION`）、记忆库 ID（`AGENTARTS_MEMORY_SPACE_ID`）、API Key（`HUAWEICLOUD_SDK_MEMORY_API_KEY`）

| 参数                             | 说明                        |
|----------------------------------|----------------------------|
| `AGENTARTS_MEMORY_SPACE_ID`      | AgentArts 记忆库ID          |
| `HUAWEICLOUD_SDK_MEMORY_API_KEY` | AgentArts 记忆库API Key     |
| `HUAWEICLOUD_SDK_REGION`         | 区域（默认 `cn-southwest-2`）|


## 安装

有两种安装方式，任选其一。

### 方式一：作为 memory provider 安装

将插件目录复制到 Hermes 的 memory provider 插件路径：

```bash
cp -r agentarts-memory-hermes  ~/.hermes/hermes-agent/plugins/memory/
```
通过 `hermes memory setup` 交互式配置，或手动设置上述环境变量。 按提示选择 `agentarts_memory` 并完成配置。

### 方式二：作为通用插件安装

将插件目录复制到 Hermes 的通用插件路径，通过 `hermes plugins` 命令注册：

```bash
cp -r agentarts-memory-hermes ~/.hermes/plugins/
```

通过 `hermes plugins` 交互式配置，或手动设置上述环境变量。 按提示选择 `agentarts_memory` 并完成配置。

## 配置

配置过程中会提示输入 API Key、Space ID 等。敏感字段（API Key）写入 `.env`，非敏感配置（`space_id`、`region`）写入 `$HERMES_HOME/agentarts.json`。

## 工具说明

### ltm_search

搜索 AgentArts 长期记忆，返回与查询相关的记忆条目。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `query` | string | 是 | — | 搜索查询字符串 |
| `top_k` | integer | 否 | 5 | 返回前 K 个结果 |

### ltm_search_summary

获取 AgentArts 记忆摘要列表。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `limit` | integer | 否 | 10 | 返回条目数量 |

## CLI 命令

插件注册后提供以下 CLI 子命令（仅在 provider 活跃时可用）：

| 命令 | 说明 |
|---|---|
| `hermes agentarts_memory status` | 显示 provider 状态和环境变量配置 |
| `hermes agentarts_memory config` | 显示已保存的非敏感配置 |
| `hermes agentarts_memory test` | 测试 provider 连通性 |

## 架构说明

- **Client 模式**：使用 `MemoryClient`（Client 模式），不依赖 Session 模式
- **非阻塞 sync**：`sync_turn` 在守护线程中执行 `add_messages`，不阻塞 Hermes 主循环
- **Profile 隔离**：所有路径使用 `initialize()` 中的 `hermes_home` kwarg
- **线程安全**：`_lock` 保护 `_client` 的并发读写

## 生命周期钩子

| 钩子 | 调用时机 | 职责 |
|---|---|---|
| `system_prompt_block` | 系统 prompt 组装时 | 注入记忆能力说明 |
| `prefetch` | 每次 LLM 调用前 | 搜索并注入相关记忆 |
| `sync_turn` | 每轮对话后 | 非阻塞写入对话内容 |
| `on_pre_compress` | 上下文压缩前 | 重新注入相关记忆 |
| `on_memory_write` | 内置 memory 写入时 | 镜像 MEMORY.md 到 AgentArts |
| `on_session_end` | 对话结束时 | no-op（逐轮已落库） |
| `shutdown` | 进程退出时 | 清理连接 |

## 常见问题

### 记忆搜索无结果？

AgentArts Memory 从对话消息生成记忆需要时间（约 30 秒）。`sync_turn` 写入后不会立即可搜索，`prefetch` 搜索的是此前轮次已生成的记忆。

### 认证失败？

检查：
1. API Key 是否有效
2. 区域配置是否正确
3. Space 状态是否为 `running`

## 开发

```bash
pip install -e ".[dev]"
pytest tests/unit/ -v
```
