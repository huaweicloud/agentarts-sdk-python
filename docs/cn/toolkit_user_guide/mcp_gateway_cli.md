# MCP Gateway CLI 使用指南

## 概述

MCP Gateway CLI 提供命令行工具，用于管理 MCP（Model Context Protocol）网关及其目标。本文档介绍如何使用 CLI 命令进行网关和目标的创建、配置和管理。

## 环境要求

- Python 3.10+
- 已安装 AgentArts SDK：`pip install agentarts`

## 认证配置

### 华为云 AK/SK 认证

MCP Gateway CLI 使用华为云 AK/SK 进行身份认证。请通过以下方式配置：

**方式一：环境变量配置（推荐）**

```bash
# 设置华为云 AK/SK
export HUAWEICLOUD_SDK_AK="your-access-key"
export HUAWEICLOUD_SDK_SK="your-secret-key"
```

### 获取 AK/SK

1. 登录华为云控制台
2. 进入"我的凭证"页面
3. 在"访问密钥"标签页创建或查看 AK/SK

## 命令结构

所有 MCP Gateway 命令都通过 `agentarts mcp-gateway` 命名空间访问：

```bash
agentarts mcp-gateway [command] [options]
```

## 网关命令
### create-mcp-gateway
创建新的 MCP 网关。
```bash
agentarts mcp-gateway create-mcp-gateway [options]
```
**参数说明**：
| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --name | -n | 否 | gateway-{random} | 网关名称 |
| --description | -d | 否 | None | 网关描述 |
| --protocol-type | 无 | 否 | mcp | 协议类型 |
| --authorizer-type | 无 | 否 | iam | 授权器类型（custom_jwt/iam/api_key） |
| --agency-name | 无 | 否 | None | 代理名称 |
| --authorizer-configuration | 无 | 否 | None | 授权器配置（JSON 格式） |
| --log-delivery-configuration | 无 | 否 | None | 日志投递配置（JSON 格式） |
| --outbound-network-configuration | 无 | 否 | None | 出站网络配置（JSON 格式） |
**使用示例**：
```bash
# 基本创建
agentarts mcp-gateway create-mcp-gateway --name my-gateway --description "我的 MCP 网关"
# 完整配置
agentarts mcp-gateway create-mcp-gateway \
  --name my-gateway \
  --description "生产环境网关" \
  --authorizer-type iam
```
### update-mcp-gateway
更新现有的 MCP 网关。
```bash
agentarts mcp-gateway update-mcp-gateway <gateway_id> [options]
```
**参数说明**：
| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | 无 | 是 | - | 网关 ID（位置参数） |
| --description | -d | 否 | None | 网关描述 |
| --authorizer-configuration | 无 | 否 | None | 授权器配置（JSON 格式） |
| --log-delivery-configuration | 无 | 否 | None | 日志投递配置（JSON 格式） |
**使用示例**：
```bash
# 更新描述
agentarts mcp-gateway update-mcp-gateway 123 --description "更新后的描述"
# 更新多个配置
agentarts mcp-gateway update-mcp-gateway 123 \
  --description "新描述" \
  --log-delivery-configuration '{"enabled": true}'
```
### delete-mcp-gateway
删除 MCP 网关。
```bash
agentarts mcp-gateway delete-mcp-gateway <gateway_id>
```
**参数说明**：
| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | 无 | 是 | - | 网关 ID（位置参数） |
**使用示例**：
```bash
agentarts mcp-gateway delete-mcp-gateway 123
```
### get-mcp-gateway
获取 MCP 网关的详细信息。
```bash
agentarts mcp-gateway get-mcp-gateway <gateway_id>
```
**参数说明**：
| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | 无 | 是 | - | 网关 ID（位置参数） |
**使用示例**：
```bash
agentarts mcp-gateway get-mcp-gateway 123
```
### list-mcp-gateways
列出 MCP 网关，可选择过滤条件。
```bash
agentarts mcp-gateway list-mcp-gateways [options]
```
**参数说明**：
| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --name | 无 | 否 | None | 网关名称过滤器 |
| --status | 无 | 否 | None | 网关状态过滤器 |
| --gateway-id | 无 | 否 | None | 网关 ID 过滤器 |
| --limit | 无 | 否 | 50 | 分页限制（1-50） |
| --offset | 无 | 否 | 0 | 分页偏移量 |
**使用示例**：
```bash
# 列出所有网关
agentarts mcp-gateway list-mcp-gateways
# 按名称过滤
agentarts mcp-gateway list-mcp-gateways --name my-gateway
# 分页查询
agentarts mcp-gateway list-mcp-gateways --limit 10 --offset 0
```
## 目标命令
### create-mcp-gateway-target
创建新的 MCP 网关目标。
```bash
agentarts mcp-gateway create-mcp-gateway-target <gateway_id> [options]
```
**参数说明**：
| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | 无 | 是 | - | 网关 ID（位置参数） |
| --name | -n | 否 | target-{random} | 目标名称 |
| --description | -d | 否 | None | 目标描述 |
| --target-configuration | 无 | 否 | None | 目标配置（JSON 格式） |
| --credential-provider-configuration | 无 | 否 | None | 凭证提供者配置（JSON 格式） |
**使用示例**：
```bash
# 基本创建
agentarts mcp-gateway create-mcp-gateway-target 123 --name my-target
# 完整配置
agentarts mcp-gateway create-mcp-gateway-target 123 \
  --name my-target \
  --description "API 目标" \
  --target-configuration '{"endpoint": "https://api.example.com", "timeout": 30}'
```
### update-mcp-gateway-target
更新现有的 MCP 网关目标。
```bash
agentarts mcp-gateway update-mcp-gateway-target <gateway_id> <target_id> [options]
```
**参数说明**：
| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | 无 | 是 | - | 网关 ID（位置参数） |
| target_id | 无 | 是 | - | 目标 ID（位置参数） |
| --name | -n | 否 | None | 目标名称 |
| --description | -d | 否 | None | 目标描述 |
| --target-configuration | 无 | 否 | None | 目标配置（JSON 格式） |
| --credential-provider-configuration | 无 | 否 | None | 凭证提供者配置（JSON 格式） |
**使用示例**：
```bash
# 更新名称
agentarts mcp-gateway update-mcp-gateway-target 123 456 --name updated-target
# 更新配置
agentarts mcp-gateway update-mcp-gateway-target 123 456 \
  --name updated-target \
  --description "更新后的目标"
```
### delete-mcp-gateway-target
删除 MCP 网关目标。
```bash
agentarts mcp-gateway delete-mcp-gateway-target <gateway_id> <target_id>
```
**参数说明**：
| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | 无 | 是 | - | 网关 ID（位置参数） |
| target_id | 无 | 是 | - | 目标 ID（位置参数） |
**使用示例**：
```bash
agentarts mcp-gateway delete-mcp-gateway-target 123 456
```
### get-mcp-gateway-target
获取 MCP 网关目标的详细信息。
```bash
agentarts mcp-gateway get-mcp-gateway-target <gateway_id> <target_id>
```
**参数说明**：
| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | 无 | 是 | - | 网关 ID（位置参数） |
| target_id | 无 | 是 | - | 目标 ID（位置参数） |
**使用示例**：
```bash
agentarts mcp-gateway get-mcp-gateway-target 123 456
```
### list-mcp-gateway-targets
列出 MCP 网关目标，支持分页。
```bash
agentarts mcp-gateway list-mcp-gateway-targets <gateway_id> [options]
```
**参数说明**：
| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | 无 | 是 | - | 网关 ID（位置参数） |
| --limit | 无 | 否 | 50 | 分页限制（1-50） |
| --offset | 无 | 否 | 0 | 分页偏移量 |
**使用示例**：
```bash
# 列出所有目标
agentarts mcp-gateway list-mcp-gateway-targets 123
# 分页查询
agentarts mcp-gateway list-mcp-gateway-targets 123 --limit 10 --offset 0
```
## 最佳实践
### 1. 网关命名规范
- 使用有意义的网关名称，便于识别和管理
- 建议使用格式：`{project}-{environment}-{function}`
- 例如：`myapp-prod-api-gateway`
### 2. 授权器配置
- IAM 授权器：适合华为云内部服务调用
- API Key 授权器：适合外部系统集成
- Custom JWT 授权器：适合自定义认证场景
### 3. 网络配置
- 公网模式：适合公网访问场景
- VPC 内网模式：适合内部服务调用，安全性更高
### 4. 资源管理
- 及时清理不再使用的网关和目标
- 使用标签进行资源分类和管理
- 定期检查网关状态和配置
### 5. JSON 配置格式
- 确保 JSON 格式正确，使用单引号包裹
- 复杂配置建议使用文件或环境变量
- 注意特殊字符转义
## 常见问题
### Q1: 创建网关时提示代理创建失败？
**原因**：系统自动创建代理失败，可能是权限不足。
**解决方案**：
1. 检查 AK/SK 是否有 IAM 权限
2. 手动创建代理并提供 `--agency-name` 参数
### Q2: 更新网关时提示参数错误？
**原因**：未提供任何更新参数。
**解决方案**：
确保至少提供一个更新参数（--description、--authorizer-configuration 等）。
### Q3: JSON 配置格式错误？
**原因**：JSON 字符串格式不正确。
**解决方案**：
1. 验证 JSON 格式有效性
2. 使用单引号包裹 JSON 字符串
3. 检查特殊字符转义
### Q4: 如何选择授权器类型？
根据使用场景选择：
- **iam**：华为云内部服务调用
- **api_key**：外部系统集成，简单易用
- **custom_jwt**：需要自定义认证逻辑
### Q5: 网关创建后无法访问？
**检查项**：
1. 网关状态是否为 running
2. 网络配置是否正确
3. 目标配置是否正确
4. 认证信息是否有效
