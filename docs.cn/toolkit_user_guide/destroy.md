# destroy 命令使用文档

## 命令用途

`destroy` 命令用于从华为云 AgentArts 平台删除 Agent 及其相关资源。该命令会永久删除 Agent 实例、配置信息和相关资源，执行前会提示确认，防止误操作。

> **警告**: 此操作不可逆，删除后无法恢复 Agent 数据和配置。

## 参数解释

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--agent` | `-a` | Agent 名称 | 使用默认 Agent |
| `--region` | `-r` | 华为云区域 | 从配置文件读取 |
| `--yes` | `-y` | 跳过确认提示 | `false` |

## 删除流程

执行 `destroy` 命令会依次执行以下步骤：

### 1. 参数验证
- 验证 Agent 名称
- 确认区域配置
- 检查 Agent 是否存在

### 2. 确认提示
- 显示即将删除的 Agent 信息
- 提示用户确认操作
- 可通过 `--yes` 参数跳过

### 3. 资源清理
- 停止 Agent 运行实例
- 删除 Agent 配置
- 清理相关资源

### 4. 验证删除
- 确认 Agent 已删除
- 返回操作结果

## 执行效果

### 交互式删除

```
Destroy Agent

Agent: my-agent
Region: cn-southwest-2

Warning: This will permanently delete agent 'my-agent'
Are you sure you want to continue? [y/n]: y

Destroying agent...
✓ Agent 'my-agent' destroyed successfully
```

### 跳过确认删除

```
Destroy Agent

Agent: my-agent
Region: cn-southwest-2

Destroying agent...
✓ Agent 'my-agent' destroyed successfully
```

### Agent 不存在

```
Destroy Agent

Agent: my-agent
Region: cn-southwest-2

Error: Agent 'my-agent' not found
```

## 使用示例

### 示例 1: 交互式删除默认 Agent

```bash
agentarts destroy
```

执行后会提示确认，输入 `y` 确认删除。

### 示例 2: 删除指定 Agent

```bash
agentarts destroy --agent my-agent
```

或使用简写：
```bash
agentarts destroy -a my-agent
```

### 示例 3: 指定区域删除

```bash
agentarts destroy --agent my-agent --region cn-southwest-2
```

或使用简写：
```bash
agentarts destroy -a my-agent -r cn-southwest-2
```

### 示例 4: 跳过确认删除

```bash
agentarts destroy --agent my-agent --yes
```

或使用简写：
```bash
agentarts destroy -a my-agent -y
```

### 示例 5: 完整参数示例

```bash
agentarts destroy \
  --agent my-agent \
  --region cn-southwest-2 \
  --yes
```

### 示例 6: 批量删除脚本

```bash
#!/bin/bash
# 批量删除多个 Agent

agents=("agent1" "agent2" "agent3")

for agent in "${agents[@]}"; do
  echo "Destroying $agent..."
  agentarts destroy -a "$agent" -y
done
```

## 删除的资源

执行 `destroy` 命令会删除以下资源：

### Agent 相关资源

| 资源类型 | 说明 |
|---------|------|
| Agent 实例 | Agent 运行实例和配置 |
| 访问端点 | Agent 的 HTTP 访问端点 |
| 配置信息 | Agent 的运行时配置 |
| 日志数据 | Agent 运行日志（保留期限后删除） |

### 不会删除的资源

| 资源类型 | 说明 |
|---------|------|
| Docker 镜像 | SWR 中的镜像仍保留 |
| 本地配置 | 本地 `.agentarts_config.yaml` 文件 |
| 源代码 | 本地项目代码 |

## 删除前检查清单

在执行 `destroy` 命令前，建议检查以下事项：

### 1. 确认 Agent 信息

```bash
# 查看 Agent 详情
agentarts config get -a my-agent

# 检查 Agent 状态
agentarts status -a my-agent
```

### 2. 备份重要数据

```bash
# 导出配置
agentarts config get -a my-agent > my-agent-config.yaml

# 保存重要日志
# （根据实际情况操作）
```

### 3. 通知相关人员

- 通知使用该 Agent 的用户
- 更新相关文档和配置
- 记录删除原因和时间

### 4. 验证依赖关系

- 确认没有其他服务依赖该 Agent
- 检查是否有正在进行的任务
- 确认删除不会影响生产环境

## 安全建议

### 1. 使用确认提示

建议保留确认提示，避免误删：

```bash
# 推荐：保留确认提示
agentarts destroy -a my-agent

# 不推荐：跳过确认（仅用于自动化脚本）
agentarts destroy -a my-agent -y
```

### 2. 权限控制

- 限制 `destroy` 命令的执行权限
- 在生产环境使用审批流程
- 记录删除操作日志

### 3. 环境区分

- 明确区分开发和生产环境
- 生产环境删除需要额外确认
- 使用不同的 Agent 命名规范

## 常见问题

### Q1: Agent 删除失败

**原因**: Agent 正在使用或权限不足

**解决方案**:
1. 确认 Agent 没有正在执行的任务
2. 检查 AK/SK 权限
3. 查看错误日志获取详细信息

### Q2: 误删 Agent 如何恢复

**原因**: 操作失误删除了 Agent

**解决方案**:
1. 无法直接恢复，需要重新部署
2. 使用本地配置重新创建 Agent
3. 重新部署 Docker 镜像

### Q3: 删除后镜像还在吗

**原因**: 想了解镜像资源是否被删除

**解决方案**:
- `destroy` 命令不会删除 SWR 镜像
- 镜像仍可用于重新部署
- 如需删除镜像，请手动操作

### Q4: 本地配置文件会被删除吗

**原因**: 担心本地配置丢失

**解决方案**:
- `destroy` 命令不影响本地文件
- `.agentarts_config.yaml` 保持不变
- 可继续使用配置重新部署

### Q5: 如何删除多个 Agent

**原因**: 需要批量清理测试 Agent

**解决方案**:
使用脚本批量删除：

```bash
#!/bin/bash
# 列出所有 Agent
agents=$(agentarts config list | grep -oP '(?<=- )[a-zA-Z0-9-]+')

# 批量删除
for agent in $agents; do
  echo "Destroying $agent..."
  agentarts destroy -a "$agent" -y
done
```

## 与其他命令配合使用

### 配合 status 命令

删除前检查状态：

```bash
# 检查状态
agentarts status -a my-agent

# 确认后删除
agentarts destroy -a my-agent
```

### 配合 config 命令

删除后清理配置：

```bash
# 删除云端 Agent
agentarts destroy -a my-agent

# 删除本地配置
agentarts config remove my-agent
```

### 配合 deploy 命令

重新部署流程：

```bash
# 删除旧版本
agentarts destroy -a my-agent -y

# 重新部署
agentarts deploy -a my-agent
```

## 自动化场景

### CI/CD 清理

在 CI/CD 流程中清理测试 Agent：

```yaml
# .gitlab-ci.yml
cleanup:
  stage: cleanup
  script:
    - agentarts destroy -a test-agent -y
  when: always
```

### 定时清理

定期清理测试环境 Agent：

```bash
# crontab 配置
0 2 * * * /path/to/cleanup-agents.sh
```

```bash
#!/bin/bash
# cleanup-agents.sh

# 删除所有测试 Agent
test_agents=$(agentarts config list | grep "test-" | cut -d' ' -f2)

for agent in $test_agents; do
  agentarts destroy -a "$agent" -y
done
```

## 注意事项

1. **不可逆操作**: 删除后无法恢复，请谨慎操作
2. **确认提示**: 建议保留确认提示，避免误删
3. **权限要求**: 需要足够的华为云权限
4. **资源清理**: 删除前确认没有正在执行的任务
5. **数据备份**: 重要数据请提前备份
6. **通知用户**: 删除前通知相关用户
7. **日志记录**: 记录删除操作，便于审计
8. **镜像保留**: 删除 Agent 不会删除 SWR 镜像
9. **配置保留**: 本地配置文件不受影响
10. **重新部署**: 可使用现有镜像和配置重新部署
