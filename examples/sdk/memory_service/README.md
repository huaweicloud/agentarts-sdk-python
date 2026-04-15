# Memory Service Example

展示如何使用 AgentArts Memory Service 存储对话历史。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export AGENTARTS_MEMORY_DATA_ENDPOINT="https://your-space.memory.cn-southwest-2.agentarts.myhuaweicloud.com"

# 运行 Agent
python agent_with_memory.py
```

## 测试

```bash
# 发送消息（会自动创建 session）
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "user_id": "user1"}'

# 使用相同 session 继续对话
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What did I say before?", "session_id": "xxx", "user_id": "user1"}'

# 查看对话历史
curl http://localhost:8080/sessions/xxx/history?user_id=user1

# 清除对话历史
curl -X DELETE http://localhost:8080/sessions/xxx?user_id=user1
```

## 功能说明

- `/chat` - 聊天接口，自动存储对话历史
- `/sessions/{session_id}/history` - 获取对话历史
- `/sessions/{session_id}` - 清除对话历史

## 环境变量

| 变量名 | 说明 | 必需 |
|-------|------|------|
| `AGENTARTS_MEMORY_DATA_ENDPOINT` | Memory 服务地址 | 是 |