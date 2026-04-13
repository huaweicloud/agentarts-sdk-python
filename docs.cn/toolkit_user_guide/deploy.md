# deploy/launch 命令使用文档

## 命令用途

`deploy` 和 `launch` 命令用于将 Agent 部署到华为云 AgentArts 平台。该命令会构建 Docker 镜像、上传到 SWR（容器镜像服务），并创建或更新 Agent 实例。

> **注意**: `launch` 是 `deploy` 命令的别名，两者功能完全相同。

## 参数解释

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--agent` | `-a` | Agent 名称 | 使用默认 Agent |
| `--region` | `-r` | 华为云区域 | 从配置文件读取 |
| `--environment` | `-e` | 部署环境 | `production` |
| `--skip-build` | 无 | 跳过镜像构建 | `false` |
| `--skip-push` | 无 | 跳过镜像推送 | `false` |
| `--dry-run` | 无 | 仅显示部署计划，不执行 | `false` |
| `--yes` | `-y` | 跳过确认提示 | `false` |

## 部署流程

执行 `deploy` 命令会依次执行以下步骤：

### 1. 配置验证
- 检查 `.agentarts_config.yaml` 配置文件
- 验证必要配置项是否完整
- 确认 Agent 入口函数存在

### 2. 镜像构建
- 读取 Dockerfile 构建配置
- 构建包含 Agent 代码的 Docker 镜像
- 标记镜像版本（latest 和时间戳版本）

### 3. 镜像推送
- 登录华为云 SWR 服务
- 推送镜像到指定组织和仓库
- 验证镜像推送成功

### 4. Agent 创建/更新
- 调用 AgentArts 控制平面 API
- 创建新的 Agent 或更新现有 Agent
- 配置运行时参数和环境变量

### 5. 部署验证
- 检查 Agent 状态
- 验证服务可用性
- 输出访问端点信息

## 执行效果

### 成功部署后输出

```
✓ Building Docker image...
✓ Pushing image to SWR...
✓ Creating/Updating agent...

Agent deployed successfully!

Agent ID: agent-xxxx-xxxx-xxxx
Agent Name: my-agent
Region: cn-southwest-2
Status: Running
Endpoint: https://agentarts.cn-southwest-2.myhuaweicloud.com/v1/agent/my-agent
```

### 部署失败处理

如果部署失败，命令会：
1. 显示错误信息和失败原因
2. 提供故障排查建议
3. 保留构建日志供分析

## 使用示例

### 示例 1: 基本部署

```bash
agentarts deploy
```

使用默认 Agent 和配置进行部署。

### 示例 2: 指定 Agent 部署

```bash
agentarts deploy --agent my-agent
```

或使用简写：
```bash
agentarts deploy -a my-agent
```

### 示例 3: 指定区域部署

```bash
agentarts deploy --region cn-southwest-2
```

或使用简写：
```bash
agentarts deploy -r cn-southwest-2
```

### 示例 4: 指定环境部署

```bash
agentarts deploy --environment production
```

或使用简写：
```bash
agentarts deploy -e production
```

### 示例 5: 完整参数部署

```bash
agentarts deploy \
  --agent my-agent \
  --region cn-southwest-2 \
  --environment production
```

### 示例 6: 跳过确认部署

```bash
agentarts deploy --yes
```

或使用简写：
```bash
agentarts deploy -y
```

### 示例 7: 仅查看部署计划

```bash
agentarts deploy --dry-run
```

输出部署计划但不执行实际部署操作。

### 示例 8: 跳过镜像构建

```bash
agentarts deploy --skip-build
```

使用已有镜像进行部署，适用于镜像已构建的情况。

### 示例 9: 跳过镜像推送

```bash
agentarts deploy --skip-push
```

仅更新 Agent 配置，不推送新镜像。

### 示例 10: 使用 launch 别名

```bash
agentarts launch --agent my-agent --region cn-southwest-2
```

`launch` 命令与 `deploy` 功能完全相同。

## 部署前准备

### 1. 配置文件准备

确保 `.agentarts_config.yaml` 文件存在且配置正确：

```yaml
default_agent: my-agent

agents:
  my-agent:
    base:
      name: my-agent
      entrypoint: agent:create_app
      region: cn-southwest-2
    swr_config:
      organization: my-org
      repository: my-repo
```

### 2. 环境变量配置

在配置文件中设置必要的环境变量：

```yaml
runtime:
  environment_variables:
    - key: OPENAI_API_KEY
      value: "your-api-key"
```

### 3. 认证配置

确保已配置华为云认证信息：
- AK/SK 认证：通过环境变量或配置文件
- IAM 认证：通过华为云控制台获取临时凭证

### 4. 网络配置

根据需求配置网络访问模式：
- PUBLIC: 公网访问
- VPC: VPC 内网访问

```yaml
runtime:
  network_config:
    network_mode: PUBLIC
```

## 部署后操作

### 1. 查看 Agent 状态

```bash
agentarts status --agent my-agent
```

### 2. 调用 Agent

```bash
agentarts invoke --agent my-agent --payload '{"message": "Hello"}'
```

### 3. 查看 Agent 详情

```bash
agentarts config get --agent my-agent
```

## 常见问题

### Q1: 镜像构建失败

**原因**: Dockerfile 配置错误或依赖安装失败

**解决方案**:
1. 检查 Dockerfile 语法
2. 验证 requirements.txt 依赖版本
3. 查看构建日志定位具体错误

### Q2: 镜像推送失败

**原因**: SWR 权限不足或网络问题

**解决方案**:
1. 检查 AK/SK 权限
2. 确认 SWR 组织和仓库存在
3. 检查网络连接

### Q3: Agent 创建失败

**原因**: 配置参数错误或资源配额不足

**解决方案**:
1. 检查配置文件格式
2. 确认华为云账户配额充足
3. 查看错误日志

### Q4: 部署超时

**原因**: 镜像过大或网络延迟

**解决方案**:
1. 优化镜像大小
2. 使用更近的区域
3. 增加超时时间

## 注意事项

1. **首次部署**: 首次部署会创建新的 Agent 实例，后续部署会更新现有实例
2. **镜像版本**: 每次部署会生成新的镜像版本，保留历史版本便于回滚
3. **环境变量**: 敏感信息建议使用环境变量而非硬编码
4. **资源限制**: 注意华为云账户的资源配额限制
5. **网络配置**: 生产环境建议使用 VPC 网络模式提高安全性
6. **回滚操作**: 如需回滚，可通过指定镜像版本实现
