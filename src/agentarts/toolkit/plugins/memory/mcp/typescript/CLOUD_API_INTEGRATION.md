# 编程记忆搜索接口对接说明

更新日期：2026-11-16

本文面向云端接口开发与联调人员，描述当前 TypeScript MCP 发往云端的 HTTP 请求及预期过滤语义。`kind`、`category` 已按 **JSON 请求体顶层可选字符串**实现；本地 mock 端到端测试已通过，真实云端接口尚未联调。后续若云端字段位置调整，再同步修改请求映射。

## 1. 接口与完整请求示例

- 方法：`POST`
- 路径：`/v1/core/spaces/{space_id}/memories/search`
- 认证：`Authorization: Bearer <api-key>`
- 请求格式：`Content-Type: application/json`
- 默认地址：`https://memory.cn-southwest-2.huaweicloud-agentarts.com`，可通过区域或 `AGENTARTS_MEMORY_DATA_ENDPOINT` 配置覆盖。
- `space_id` 位于 URL 路径，不放入请求体。

以下示例列出当前 MCP 可发送的全部请求字段。凭证、用户标识和时间范围仅为示例；没有时间限制时，应省略 `start_time`、`end_time`。

```http
POST /v1/core/spaces/<space_id>/memories/search HTTP/1.1
Host: memory.cn-southwest-2.huaweicloud-agentarts.com
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

这是 **MCP 服务端最终发出的 HTTP 请求**。模型调用 `search_memories` 时不传 `actor_id` 或 `rerank`，它们由 MCP 服务端配置填入。

## 2. 请求字段说明

下表中的默认值及校验规则属于当前 TS MCP，不等同于已验证的云端默认值或约束。

| 字段 | JSON 类型 | 当前 MCP 行为 |
| --- | --- | --- |
| `query` | string | 模型必传，始终发送。建议使用具体、非空的检索问题；当前本地仅校验字符串类型，未限制非空或长度 |
| `strategy_type` | string | 可选，无默认值。支持值见下文；任意一个 `kind/category` 存在时强制发送 `procedural`，否则原样传递或省略 |
| `kind` | string | 可选枚举：`observation`、`experience`。无默认值，未传则省略 |
| `category` | string | 可选枚举，随 kind 使用对应分类；未指定 kind 时接受两套分类的并集。无默认值，未传则省略 |
| `top_k` | integer | 范围 1–100，默认 5，始终发送；表示最多返回多少条结果 |
| `min_score` | number | 范围 0–1，默认 0.7，始终发送；表示最低相似度阈值 |
| `actor_id` | string | 始终发送。优先读取 `AGENTARTS_MEMORY_USER_ID`，否则采用平台默认值；必须与写入侧一致 |
| `start_time` | integer | 可选非负整数，Unix 毫秒时间戳，不是秒；未传则省略 |
| `end_time` | integer | 可选非负整数，Unix 毫秒时间戳，不是秒；未传则省略 |
| `rerank` | boolean | 始终发送，默认 `false`。服务端设置 `AGENTARTS_MEMORY_RERANK=1` 或 `true` 时发送 `true`，其中 `true` 不区分大小写 |

`strategy_type` 的现有文档支持值为：`semantic`、`episodic`、`user_preference`、`summary`、`procedural`。当前 MCP 对它只做字符串类型校验，没有本地枚举校验；没有分类参数时，其他值会原样传到云端，由云端校验。

`actor_id` 的平台默认值为：Claude Code 使用 `cc-user`，Codex 使用 `codex-user`，OpenCode 使用 `opencode-user`，未识别平台使用 `__default__`。联调时建议显式配置成与写入侧一致的标识，避免因用户范围不同而得到空结果。

## 3. kind 与 category 分类体系

两个 kind 都存储在 `strategy_type="procedural"` 下。`kind` 区分记忆形态，`category` 进一步区分该形态内的内容类别；它们不是 `strategy_type` 或现有 SDK `memory_type` 的别名。

| kind | 定义 | 典型检索目的 |
| --- | --- | --- |
| `observation` | 记录具体技术事实，包括改动、调查发现、修复结果、设计决策及依据 | 之前发生了什么、发现了什么、为什么这样设计 |
| `experience` | 从证据中提炼的可复用工程方法、诊断路径、失败教训和适用边界 | 类似问题应该如何处理、验证或避免重复踩坑 |

### 3.1 observation：九分类

沿用 Claude-mem `plugin/modes/code.json` 的 observation type 分类，不是 concepts 标签。

| category | 含义 |
| --- | --- |
| `bugfix` | 原先有问题的行为已修复 |
| `feature` | 新增能力或功能 |
| `refactor` | 调整代码结构，行为不变 |
| `change` | 文档、配置等一般修改 |
| `discovery` | 对已有系统的调查发现 |
| `decision` | 有依据的架构或设计选择 |
| `security_alert` | 继续工作前需要关注的安全问题 |
| `security_note` | 值得记录但不紧急的安全发现 |
| `sensitive` | 不宜在不适当上下文中传播的信息 |

### 3.2 experience：四分类

使用与经验抽取侧约定的 type 四分类。分类由经验本身的核心问题决定，不直接继承来源 observation 的类型。

| category | 含义 |
| --- | --- |
| `feature` | 功能实现、接口集成、能力设计及实现取舍的方法 |
| `bugfix` | 定位、解释和纠正非预期行为的可复用结论、诊断路径或失败修复教训 |
| `testing` | 测试设计、覆盖、断言、mock、fixture、隔离及可靠性的方法 |
| `build-env` | 构建、依赖、运行环境、CI/CD、操作系统、shell、配置及工具链适配的方法 |

未传 `kind` 时，`category` 可使用以下 **11 个不同值**：

```text
bugfix, feature, refactor, change, discovery, decision,
security_alert, security_note, sensitive, testing, build-env
```

其中 `bugfix`、`feature` 为两个 kind 共享的 category；其余值仅属于各自分类体系。

## 4. 过滤与省略规则

### 4.1 参数组合

| 模型提供的分类参数 | MCP 发出的策略字段 | 云端预期过滤语义 |
| --- | --- | --- |
| 仅 `kind` | 强制 `strategy_type="procedural"` | 限制 kind，不限制该 kind 下的 category |
| 仅 `category` | 强制 `strategy_type="procedural"` | 限制 category，不附加 kind 过滤；例如 bugfix 可匹配两种 kind |
| `kind` 与 `category` 都传 | 强制 `strategy_type="procedural"` | 同时匹配 kind 和 category；category 必须属于该 kind |
| 两者都不传 | 保留原逻辑：传了策略就原样发送，未传则省略 | 不附加 kind/category 过滤，仍遵循其他请求条件 |

只要传入任意一个分类字段，MCP 就会覆盖调用方显式提供的其他 `strategy_type`。例如模型传入 `strategy_type="semantic"`、`kind="experience"`，最终云端收到的是 `strategy_type="procedural"`、`kind="experience"`。

**两个分类字段都省略，不会自动设置 procedural。** 如果目标是搜索所有编程记忆种类和分类，应显式传入 `strategy_type="procedural"`，同时省略 `kind/category`。

### 4.2 字段值与组合校验

- `kind/category` 均为可选单值字符串，无默认分类；模型无法判断时可省略。
- 省略字段表示不限制该维度；不发送空字符串、`null` 或 `"all"` 作为通配符。
- 枚举值精确匹配、区分大小写，不自动去除前后空白，不接受数组或多个值拼接。
- 两者同时存在时必须配对合法；例如 `observation/testing`、`experience/discovery` 都无效。
- 未知枚举、错误类型或不合法配对会在 MCP 本地报错，不向云端发送该次搜索请求。
- 对直接调用 HTTP 接口、绕过 MCP 的客户端，云端校验与错误码需在联调时另行确认。

### 4.3 条件组合

预期各维度按交集过滤：策略 AND 用户范围 AND kind（如有）AND category（如有）AND 时间条件（如有）。结果还受相似度阈值和 `top_k` 限制。

“不限种类/分类”表示不增加该维度的过滤，**不是返回全部记录**，也不是忽略 `actor_id`、策略或其他条件。分类筛选由云端执行；TS MCP 仅校验并传递字段，不在召回后做本地分类过滤。

## 5. 常用请求体

以下均为最终 HTTP 请求体，使用第 1 节相同的 URL 与认证头。

### 5.1 召回两种 kind 下所有分类的编程记忆

```json
{
  "query": "测试组合运行失败时有哪些排查方法和历史发现",
  "strategy_type": "procedural",
  "top_k": 5,
  "min_score": 0.7,
  "actor_id": "<与写入侧一致的 actor_id>",
  "rerank": false
}
```

### 5.2 仅查 observation，不限制 category

```json
{
  "query": "认证模块之前做过哪些修改和设计决策",
  "strategy_type": "procedural",
  "kind": "observation",
  "top_k": 5,
  "min_score": 0.7,
  "actor_id": "<与写入侧一致的 actor_id>",
  "rerank": false
}
```

### 5.3 仅按 bugfix 分类，跨 kind 检索

```json
{
  "query": "共享缓存引发的状态污染修复",
  "strategy_type": "procedural",
  "category": "bugfix",
  "top_k": 5,
  "min_score": 0.7,
  "actor_id": "<与写入侧一致的 actor_id>",
  "rerank": false
}
```

### 5.4 保留原搜索行为，不指定策略或新分类

```json
{
  "query": "此前记录的相关上下文",
  "top_k": 5,
  "min_score": 0.7,
  "actor_id": "<与写入侧一致的 actor_id>",
  "rerank": false
}
```

此请求未限定为 procedural；策略字段缺省时的实际检索范围由云端原有规则决定。

## 6. 联调确认与验收

本地已验证 MCP 参数校验、最终请求体以及省略/覆盖行为，云端联调需确认：

1. 搜索接口接收顶层 `kind/category` 并实际执行过滤，字段含义与写入数据一致。
2. 两种 kind 的全部合法分类配对、仅 kind、仅 category，以及 procedural 下不限制分类的召回结果正确；特别覆盖共享 category `feature/bugfix` 的跨 kind 检索。
3. 不传新字段时保持原接口行为，原有用户范围、策略、阈值及数量限制继续生效。
4. 时间过滤对应的云端时间字段、起止端点是否包含，以及反向时间区间的处理。当前 MCP 仅校验时间为非负整数，未校验 `start_time <= end_time`。

本文不预设云端新增字段的错误码或时间边界语义。后续接口调整应同步更新本说明及 TS MCP 请求映射。
