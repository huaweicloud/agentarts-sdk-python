# status 命令使用文档

## 命令用途

`status` 命令用于检查已部署 Agent 的健康状态。该命令会向 Agent 发送健康检查请求，返回当前运行状态、响应时间和健康指标，帮助开发者监控 Agent 运行情况。

## 参数解释

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--agent` | `-a` | Agent 名称 | 使用默认 Agent |
| `--region` | `-r` | 华为云区域 | 从配置文件读取 |
| `--mode` | `-m` | 检查模式（local/cloud） | `cloud` |
| `--port` | `-p` | 本地模式端口 | `8080` |
| `--bearer-token` | `-bt` | Bearer 认证令牌 | 无 |
| `--endpoint` | `-e` | 指定端点名称 | 无 |
| `--session` | `-s` | 会话 ID（用于有状态 Agent） | 无 |
| `--user-id` | `-u` | 用户 ID（用于 OAuth2 出站凭据） | 无 |

## 健康状态说明

### 状态类型

| 状态 | 说明 |
|------|------|
| `Healthy` | Agent 运行正常，可正常响应请求 |
| `Healthy_Busy` | Agent 运行正常，但当前有任务正在处理 |
| `Unhealthy` | Agent 运行异常，无法正常响应请求 |
| `Unknown` | 无法获取 Agent 状态 |

### 状态判断依据

健康检查会评估以下指标：
- Agent 进程是否存活
- HTTP 服务是否响应
- 响应时间是否在正常范围
- 系统资源使用情况

## 执行效果

### 成功响应

```
Agent Status Check

Agent: my-agent
Region: cn-southwest-2
Status: Healthy
Response Time: 45ms
Last Update: 2024-01-15 10:30:00

Details:
  - HTTP Endpoint: ✓ Responding
  - Process Status: ✓ Running
  - Memory Usage: 256MB / 512MB
  - CPU Usage: 15%
```

### 异常响应

```
Agent Status Check

Agent: my-agent
Region: cn-southwest-2
Status: Unhealthy
Error: Connection timeout

Details:
  - HTTP Endpoint: ✗ Not responding
  - Process Status: ✗ Unknown
  - Last Successful Check: 2024-01-15 09:00:00

Suggestions:
  1. Check if the agent is deployed
  2. Verify network connectivity
  3. Check agent logs for errors
```

## 使用示例

### 示例 1: 检查默认 Agent 状态

```bash
agentarts status
```

### 示例 2: 检查指定 Agent 状态

```bash
agentarts status --agent my-agent
```

或使用简写：
```bash
agentarts status -a my-agent
```

### 示例 3: 指定区域检查

```bash
agentarts status --agent my-agent --region cn-southwest-2
```

或使用简写：
```bash
agentarts status -a my-agent -r cn-southwest-2
```

### 示例 4: 本地模式检查

```bash
agentarts status --mode local
```

或指定端口：
```bash
agentarts status --mode local --port 8080
```

### 示例 5: 使用 Bearer Token 认证

```bash
agentarts status --agent my-agent --bearer-token "your-token"
```

### 示例 6: 检查指定端点

```bash
agentarts status --agent my-agent --endpoint custom-endpoint
```

### 示例 7: 使用会话 ID

```bash
agentarts status --agent my-agent --session my-session-123
```

### 示例 8: 完整参数示例

```bash
agentarts status \
  --agent my-agent \
  --region cn-southwest-2 \
  --bearer-token "your-token"
```

### 示例 9: 使用用户 ID（OAuth2 出站凭据）

```bash
agentarts status --agent my-agent --user-id "user-123"
```

或使用简写：
```bash
agentarts status -a my-agent -u "user-123"
```

## 检查模式

### Cloud 模式（默认）

检查华为云上已部署的 Agent：

```bash
agentarts status --agent my-agent
```

检查流程：
1. 获取 Agent 访问端点
2. 发送健康检查请求
3. 解析响应状态
4. 返回健康报告

### Local 模式

检查本地运行的 Agent：

```bash
agentarts status --mode local --port 8080
```

检查流程：
1. 连接本地 HTTP 服务
2. 发送 `/ping` 请求
3. 解析响应状态
4. 返回健康报告

## 健康检查端点

Agent 健康检查使用以下端点：

| 模式 | 端点 | 方法 |
|------|------|------|
| Cloud | `GET /agent/{agent_name}/ping` | GET |
| Local | `GET /ping` | GET |

## 响应格式

### 标准响应

```json
{
  "status": "Healthy",
  "time_of_last_update": 1705315800,
  "details": {
    "http_endpoint": "responding",
    "process_status": "running",
    "memory_usage": "256MB / 512MB",
    "cpu_usage": "15%"
  }
}
```

### 简化响应

```json
{
  "status": "Healthy",
  "time_of_last_update": 1705315800
}
```

## 状态监控最佳实践

### 1. 定期检查

建议定期执行健康检查，监控 Agent 运行状态：

```bash
# 每分钟检查一次
watch -n 60 agentarts status -a my-agent
```

### 2. 多 Agent 检查

对于多个 Agent，可以编写脚本批量检查：

```bash
#!/bin/bash
for agent in agent1 agent2 agent3; do
  echo "Checking $agent..."
  agentarts status -a $agent
done
```

### 3. 自动化监控

结合监控系统集成：

```bash
# 检查状态并记录日志
agentarts status -a my-agent >> /var/log/agent_status.log 2>&1
```

### 4. 告警集成

状态异常时发送告警：

```bash
#!/bin/bash
status=$(agentarts status -a my-agent --format json | jq -r '.status')
if [ "$status" != "Healthy" ]; then
  # 发送告警通知
  curl -X POST "webhook-url" -d "Agent my-agent is $status"
fi
```

## 常见问题

### Q1: 状态检查超时

**原因**: 网络延迟或 Agent 响应慢

**解决方案**:
1. 检查网络连接
2. 确认 Agent 资源配置充足
3. 检查 Agent 日志排查性能问题

### Q2: 状态显示 Unhealthy

**原因**: Agent 服务异常或配置错误

**解决方案**:
1. 检查 Agent 是否正常运行
2. 查看错误日志
3. 重启 Agent 服务
4. 检查网络和认证配置

### Q3: 无法连接本地 Agent

**原因**: 本地服务未启动或端口错误

**解决方案**:
1. 确认 `agentarts dev` 已启动
2. 检查端口配置是否正确
3. 确认防火墙未阻止连接

### Q4: 认证失败

**原因**: Token 过期或认证配置错误

**解决方案**:
1. 更新 Bearer Token
2. 检查 AK/SK 配置
3. 确认认证类型匹配

## 与其他命令配合使用

### 配合 invoke 命令

先检查状态，再调用 Agent：

```bash
# 检查状态
if agentarts status -a my-agent | grep -q "Healthy"; then
  # 状态正常，调用 Agent
  agentarts invoke '{"message": "你好"}' --agent my-agent
else
  echo "Agent is not healthy, skipping invocation"
fi
```

### 配合 deploy 命令

部署后验证状态：

```bash
# 部署 Agent
agentarts deploy -a my-agent

# 等待启动
sleep 30

# 检查状态
agentarts status -a my-agent
```

### 配合 destroy 命令

销毁前确认状态：

```bash
# 检查状态
agentarts status -a my-agent

# 确认后销毁
agentarts destroy -a my-agent
```

## 注意事项

1. **检查频率**: 避免过于频繁的健康检查，建议间隔 30 秒以上
2. **网络环境**: 确保网络连接稳定，避免误判
3. **认证配置**: 根据认证类型提供正确的认证信息
4. **本地测试**: 使用 `--mode local` 检查本地开发环境
5. **日志记录**: 建议记录健康检查结果，便于问题排查
6. **告警机制**: 生产环境建议配置自动告警
