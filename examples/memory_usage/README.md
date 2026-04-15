# Memory Service Example

展示如何使用 AgentArts Memory Service 存储对话历史。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export HUAWEICLOUD_SDK_MEMORY_API_KEY="your-api-key"
export HUAWEICLOUD_SDK_REGION="cn-southwest-2"
export AGENTARTS_MEMORY_SPACE_ID="your-space-id"

# 运行 Agent
python agent_with_memory.py
```

## 测试

```bash
# 发送消息（会自动创建 session）
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'

# 使用相同 session 继续对话
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "What did I say before?", "session_id": "xxx"}'
```

## 端点说明

- `POST /invocations` - 调用 Agent，自动存储对话历史
- `GET /ping` - 健康检查端点

## 请求参数

| 参数 | 说明 | 必需 |
|------|------|------|
| `message` | 用户消息 | 是 |
| `session_id` | 会话 ID（不传则自动创建） | 否 |
| `space_id` | Memory Space ID（或设置环境变量） | 是 |

## 环境变量

| 变量名 | 说明 | 必需 |
|-------|------|------|
| `HUAWEICLOUD_SDK_MEMORY_API_KEY` | Memory Service API Key | 是 |
| `HUAWEICLOUD_SDK_REGION` | 华为云区域 | 否（默认 cn-southwest-2） |
| `AGENTARTS_MEMORY_SPACE_ID` | Memory Space ID | 是（或在请求中传递） |