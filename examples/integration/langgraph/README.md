# LangGraph Integration Example

展示如何将 LangGraph 与 AgentArts Memory Service 集成，实现持久化的对话状态。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 设置 OpenAI 环境变量
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL_NAME="gpt-4o-mini"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选

# 本地模式运行（使用内存存储）
python langgraph_agent.py

# 使用 AgentArts Memory 模式
export USE_AGENTARTS_MEMORY=true
export AGENTARTS_MEMORY_SPACE_ID="your-space-id"
export HUAWEICLOUD_SDK_MEMORY_API_KEY="your-api-key"
python langgraph_agent.py
```

## 测试

```bash
# 发送消息
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, who are you?"}'

# 使用相同 thread 继续对话
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What did we talk about?", "thread_id": "xxx"}'

# 查看对话历史
curl http://localhost:8080/threads/xxx/history
```

## 功能说明

- `/chat` - 聊天接口，使用 LangGraph 管理对话状态
- `/threads/{thread_id}/history` - 获取对话历史
- `/health` - 健康检查（显示当前使用的存储模式）

## 环境变量

### 基础配置（必需）

| 变量名 | 说明 | 必需 |
|-------|------|------|
| `OPENAI_API_KEY` | OpenAI API Key | 是 |
| `OPENAI_MODEL_NAME` | 模型名称 | 否（默认 gpt-4o-mini） |
| `OPENAI_BASE_URL` | API Base URL | 否 |

### AgentArts Memory 配置（可选）

| 变量名 | 说明 | 必需 |
|-------|------|------|
| `USE_AGENTARTS_MEMORY` | 是否使用 AgentArts Memory | 否（默认 false） |
| `AGENTARTS_MEMORY_SPACE_ID` | Memory Space ID | 使用 Memory 时必需 |
| `HUAWEICLOUD_SDK_MEMORY_API_KEY` | Memory API Key | 使用 Memory 时必需 |

## 两种模式对比

| 特性 | 本地模式 | AgentArts Memory |
|------|---------|------------------|
| 状态存储 | 内存 | 云端持久化 |
| 跨进程共享 | 不支持 | 支持 |
| 适用场景 | 开发测试 | 生产环境 |