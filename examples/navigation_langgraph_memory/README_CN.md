# 导航 Agent 示例

基于 LangGraph 和 AgentArts Memory SDK 构建的本地交互式导航助手。该 Agent 能够搜索地点、规划路线、生成地图链接，并召回用户的长期偏好。

## 架构

```
[用户输入] -> [Auto-Recall] -> [LangGraph agent (LLM + tools)]
                     |               |                 |
                Store.search    tool_calls?          no tool_calls
                     |               v                 v
              [AgentArts        [ToolNode] <--- loop --  [回复]
               Memory Store]         |
                              geocode_address / search_poi / plan_route
                              / generate_map_link / recall_memory
                                      |
                          [高德地图 API] / [AgentArts Memory 搜索]
```

- **短期记忆**：`AgentArtsMemorySessionSaver` 检查点将对话状态持久化到 AgentArts Memory。后端使用四种内置策略（语义、情景、用户偏好、摘要）自动提取记忆。
- **长期召回（混合模式）**：
  - *自动注入*：`auto_recall` 节点在每次 LLM 调用前搜索 `AgentArtsMemoryStore`（LangGraph Store），将最相关的 Top-K 记忆自动注入系统提示词。常见偏好无需工具调用，省去一次 LLM 调用轮次（搜索本身仍有网络延迟）。
  - *按需工具*：`recall_memory` 工具用于超出自动注入范围的更深层或更具体的查询。
  - 此混合模式（Store 自动注入 + 按需工具）符合 LangGraph 推荐的长期记忆集成最佳实践。
- **导航**：使用高德地图 Web Service API 进行 POI 搜索和路线规划。未设置 `AMAP_KEY` 时回退到模拟数据。

## 前置条件

```bash
# 安装依赖（langgraph + tui）
uv sync --extra langgraph --extra tui
uv pip install langchain-openai   # demo 专用：ChatOpenAI LLM 客户端
# 或：pip install -r examples/navigation_langgraph_memory/requirements.txt

# 复制环境变量模板并填写凭据
cp examples/navigation_langgraph_memory/.env.example examples/navigation_langgraph_memory/.env
# 编辑 examples/navigation_langgraph_memory/.env 填入 API 密钥
```

## 快速开始

### 1. 创建记忆空间（运行一次）

```bash
uv run python examples/navigation_langgraph_memory/setup_memory.py
```

这会创建记忆空间，并自动将 `AGENTARTS_MEMORY_SPACE_ID` 和 `HUAWEICLOUD_SDK_MEMORY_API_KEY` 写入 `examples/navigation_langgraph_memory/.env`。

### 2. 填写 LLM 凭据

编辑 `examples/navigation_langgraph_memory/.env` 并设置 LLM 提供商密钥：

```
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4o-mini
```

### 3. （可选）设置高德地图密钥以获取真实导航数据

在 `examples/navigation_langgraph_memory/.env` 中：

```
AMAP_KEY=your-amap-web-service-key
```

未设置此密钥时，Agent 使用模拟 POI/路线数据，仍可测试图逻辑。

### 4. 启动 Agent

```bash
# TUI 模式（默认）
uv run python examples/navigation_langgraph_memory/nav_agent.py

# 经典 CLI 模式（无 SDK 日志）
uv run python examples/navigation_langgraph_memory/nav_agent.py --cli

# 调试模式（CLI + SDK 日志）
uv run python examples/navigation_langgraph_memory/nav_agent.py --debug
```

## 示例会话

```
you: 帮我找附近的加油站
agent: [调用 search_poi] 找到附近 3 个加油站：
  1. 中石化朝阳加油站 - 朝阳路88号
  2. 中石油建国路加油站 - 建国路100号
  3. 壳牌三环加油站 - 南三环西路6号
  您想导航到哪个？

you: 帮我规划到第一个的驾车路线
agent: [调用 plan_route] 到 中石化朝阳加油站 的驾车路线：
  距离：12.5km，预计时间：~28分钟
  导航链接：https://uri.amap.com/navigation?to=...

you: 我喜欢走高速
agent: 好的，您偏好高速路线。我会记住这个偏好。

you: 我之前说过什么偏好？
agent: [调用 recall_memory] 您提到过：您偏好高速路线。
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `config.py` | 环境变量、常量、共享配置 |
| `setup_memory.py` | 一次性：创建记忆空间 |
| `amap_tools.py` | 高德地图 API 封装（geocode_address、search_poi、plan_route、generate_map_link） |
| `prompts.py` | 系统提示词集中管理 |
| `message_utils.py` | 消息内容提取和历史查询共享逻辑 |
| `memory_tools.py` | recall_memory 工具（按需深度语义搜索） |
| `session_manager.py` | 多会话管理（创建/恢复/列表） |
| `nav_agent.py` | LangGraph agent（auto_recall 节点 + LLM + 工具）+ CLI/TUI |
| `tui_app.py` | Textual TUI 界面 |
| `tui_encoding.py` | Windows UTF-8 兼容性 |
| `cli_flags.py` | 共享 DEBUG 标志 |
| `.env.example` | 环境变量模板 |
| `requirements.txt` | pip 用户依赖 |

## 注意事项

- `VERIFY_SSL` 默认为 `true`。对于使用自签名证书的内网环境，在 `.env` 中设置为 `false`。
- 会话在 Agent 启动时按需创建；元数据存储在本地 `sessions.json` 中，以便恢复之前的对话。
- 后端记忆提取在约 30 秒空闲计时器后运行；测试 `recall_memory` 或期望新会话中出现自动注入的记忆前，请先等待。
- 可通过在 `config.py` 中设置 `AUTO_RECALL_ENABLED = False` 来禁用自动召回（用于对比测试或调试）。
