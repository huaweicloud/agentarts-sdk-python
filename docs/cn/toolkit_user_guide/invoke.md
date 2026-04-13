# invoke 命令使用文档

## 命令用途

`invoke` 命令用于调用已部署的 Agent，向其发送请求并获取响应。支持同步调用和流式调用两种模式，适用于测试 Agent 功能、调试业务逻辑以及生产环境调用。

## 参数解释

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--agent` | `-a` | Agent 名称 | 使用默认 Agent |
| `--payload` | `-p` | JSON 格式的请求数据 | 无 |
| `--input` | `-i` | 简单文本输入（自动转换为 JSON） | 无 |
| `--region` | `-r` | 华为云区域 | 从配置文件读取 |
| `--mode` | `-m` | 调用模式（local/cloud） | `cloud` |
| `--port` | 无 | 本地模式端口 | `8080` |
| `--endpoint` | `-e` | 指定端点名称 | 无 |
| `--session` | `-s` | 会话 ID（用于有状态 Agent） | 自动生成 UUID |
| `--bearer-token` | 无 | Bearer 认证令牌 | 无 |
| `--timeout` | `-t` | 请求超时时间（秒） | `900` |

## 调用模式

### Cloud 模式（默认）

调用华为云上已部署的 Agent：

```bash
agentarts invoke --agent my-agent --payload '{"message": "Hello"}'
```

### Local 模式

调用本地运行的 Agent（用于开发测试）：

```bash
agentarts invoke --mode local --payload '{"message": "Hello"}'
```

## 执行效果

### 同步调用

对于普通 Agent，返回完整的响应结果：

```
Response:
{
  "response": "Hello! How can I help you today?",
  "status": "success",
  "agent": "my-agent"
}
```

### 流式调用

对于支持流式输出的 Agent，实时返回响应片段：

```
Streaming Response:
data: {"content": "Hello"}
data: {"content": "! How"}
data: {"content": " can I"}
data: {"content": " help?"}
```

## 使用示例

### 示例 1: 基本调用

```bash
agentarts invoke --agent my-agent --payload '{"message": "你好"}'
```

### 示例 2: 使用简写参数

```bash
agentarts invoke -a my-agent -p '{"message": "你好"}'
```

### 示例 3: 使用简单文本输入

```bash
agentarts invoke --agent my-agent --input "你好"
```

或使用简写：
```bash
agentarts invoke -a my-agent -i "你好"
```

### 示例 4: 指定区域调用

```bash
agentarts invoke --agent my-agent --region cn-southwest-2 --payload '{"message": "你好"}'
```

### 示例 5: 本地模式调用

```bash
agentarts invoke --mode local --payload '{"message": "你好"}'
```

或指定端口：
```bash
agentarts invoke --mode local --port 8080 --payload '{"message": "你好"}'
```

### 示例 6: 有状态会话调用

```bash
agentarts invoke --agent my-agent --session "my-session-123" --payload '{"message": "继续之前的对话"}'
```

### 示例 7: 使用 Bearer Token 认证

```bash
agentarts invoke --agent my-agent --bearer-token "your-token" --payload '{"message": "你好"}'
```

### 示例 8: 指定端点调用

```bash
agentarts invoke --agent my-agent --endpoint custom-endpoint --payload '{"message": "你好"}'
```

### 示例 9: 设置超时时间

```bash
agentarts invoke --agent my-agent --timeout 60 --payload '{"message": "你好"}'
```

### 示例 10: 复杂数据调用

```bash
agentarts invoke --agent my-agent --payload '{
  "message": "分析这段文本",
  "context": {
    "language": "zh",
    "detail_level": "high"
  },
  "options": {
    "format": "json"
  }
}'
```

## Payload 格式说明

### 基本格式

```json
{
  "message": "用户输入的消息"
}
```

### 扩展格式

```json
{
  "message": "用户输入的消息",
  "context": {
    "key": "value"
  },
  "options": {
    "streaming": true,
    "timeout": 60
  }
}
```

### 模板支持的字段

不同模板支持的 Payload 字段：

| 模板 | 支持字段 |
|------|---------|
| basic | `message` |
| langgraph | `message` |
| langchain | `message`, `system_prompt` |
| google-adk | `message`, `system_instruction` |

## 认证方式

### IAM 认证（默认）

Agent 配置为 IAM 认证时，使用 AK/SK 自动签名：

```yaml
runtime:
  identity_configuration:
    authorizer_type: IAM
```

### Bearer Token 认证

Agent 配置为其他认证类型时，需要提供 Bearer Token：

```bash
agentarts invoke --agent my-agent --bearer-token "your-token" --payload '{"message": "你好"}'
```

## 会话管理

### 会话 ID 作用

会话 ID 用于标识用户会话，支持：
- 多轮对话上下文保持
- 会话状态管理
- 并发会话隔离

### 会话 ID 生成

- 未指定时自动生成 UUID
- 可手动指定固定 ID 用于测试
- 建议使用有意义的 ID 便于追踪

## 响应格式

### 成功响应

```json
{
  "response": "Agent 的响应内容",
  "status": "success",
  "agent": "my-agent",
  "model": "gpt-4o-mini"
}
```

### 错误响应

```json
{
  "error": "错误类型",
  "message": "错误详情",
  "status_code": 400
}
```

## 常见问题

### Q1: 调用超时

**原因**: Agent 处理时间过长或网络延迟

**解决方案**:
1. 增加 `--timeout` 参数值
2. 优化 Agent 处理逻辑
3. 检查网络连接

### Q2: 认证失败

**原因**: AK/SK 配置错误或 Token 过期

**解决方案**:
1. 检查 AK/SK 配置
2. 更新 Bearer Token
3. 确认认证类型匹配

### Q3: Agent 未找到

**原因**: Agent 名称错误或未部署

**解决方案**:
1. 检查 Agent 名称拼写
2. 确认 Agent 已成功部署
3. 检查区域配置

### Q4: Payload 格式错误

**原因**: JSON 格式不正确

**解决方案**:
1. 验证 JSON 格式有效性
2. 使用单引号包裹 JSON 字符串
3. 检查特殊字符转义

## 注意事项

1. **Payload 格式**: 必须为有效的 JSON 格式
2. **认证方式**: 根据 Agent 配置选择正确的认证方式
3. **超时设置**: 长时间处理任务建议增加超时时间
4. **会话管理**: 有状态 Agent 需要保持会话 ID 一致
5. **本地测试**: 使用 `--mode local` 进行本地开发测试
6. **流式响应**: 支持 SSE（Server-Sent Events）格式的流式输出
