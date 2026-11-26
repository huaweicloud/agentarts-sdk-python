# 模型提供商 CLI 使用指南

## 概述

模型提供商 CLI 提供命令行工具，用于管理模型网关下的模型提供商、模型服务与模型代理。本文档介绍如何使用 CLI 命令进行模型提供商、模型服务、模型代理的创建、配置和管理，以及模型管理配额查询。

## 环境要求

- Python 3.10+
- 已安装 AgentArts SDK：`pip install agentarts-sdk`

## 认证配置

### 华为云 AK/SK 认证

模型提供商 CLI 使用华为云 AK/SK 进行身份认证。请通过以下方式配置：

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

所有模型提供商命令都通过 `agentarts custom-model-provider` 命名空间访问：

```bash
agentarts custom-model-provider [command] [options]
```

所有命令均支持 `--skip-ssl-verification / -k` 选项跳过 SSL 证书验证（默认验证）。

## 模型提供商命令

### create-provider

创建新的模型提供商。

```bash
agentarts custom-model-provider create-provider <name> <base_url> [options]
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| name | 无 | 是 | - | 模型提供商名称（位置参数） |
| base_url | 无 | 是 | - | 模型提供商 API 基础地址（位置参数） |
| --credential-configuration | 无 | 是 | None | 凭证配置（JSON 格式） |
| --network-configuration | 无 | 否 | None | 网络配置（JSON 格式） |
| --description | -d | 否 | None | 模型提供商描述 |
| --tags | 无 | 否 | None | 资源标签（JSON 格式） |

**使用示例**：

```bash
# 基本创建
agentarts custom-model-provider create-provider my-provider https://example.com/v1 \
  --credential-configuration '{"provider_configuration": {"credential_provider_type": "api_key", "credential_provider": {"api_key_credential_provider": {"provider_name": "my-provider-key", "credential_location": "header"}}}}'
# 完整配置
agentarts custom-model-provider create-provider my-provider https://example.com/v1 \
  --credential-configuration '{"provider_configuration": {}}' \
  --description "生产环境模型提供商" \
  --tags '[{"key": "Environment", "value": "prod"}]'
```

### update-provider

更新现有的模型提供商。

```bash
agentarts custom-model-provider update-provider <model_provider_id> [options]
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | 无 | 是 | - | 模型提供商 ID（位置参数） |
| --name | -n | 否 | None | 模型提供商名称 |
| --base-url | 无 | 否 | None | 模型提供商 API 基础地址 |
| --credential-configuration | 无 | 否 | None | 凭证配置（JSON 格式） |
| --network-configuration | 无 | 否 | None | 网络配置（JSON 格式） |
| --description | -d | 否 | None | 模型提供商描述 |
| --tags | 无 | 否 | None | 资源标签（JSON 格式） |

**使用示例**：

```bash
# 更新描述
agentarts custom-model-provider update-provider 123 --description "更新后的描述"
# 更新名称
agentarts custom-model-provider update-provider 123 --name new-provider-name
```

### delete-provider

删除模型提供商。

```bash
agentarts custom-model-provider delete-provider <model_provider_id>
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | 无 | 是 | - | 模型提供商 ID（位置参数） |

**使用示例**：

```bash
agentarts custom-model-provider delete-provider 123
```

删除前会进行二次确认，输入 y 确认删除，输入 n 取消删除。

### get-provider

获取模型提供商的详细信息。

```bash
agentarts custom-model-provider get-provider <model_provider_id>
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | 无 | 是 | - | 模型提供商 ID（位置参数） |

**使用示例**：

```bash
agentarts custom-model-provider get-provider 123
```

### list-providers

列出模型提供商，可选择过滤条件。

```bash
agentarts custom-model-provider list-providers [options]
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --name | 无 | 否 | None | 模型提供商名称过滤器 |
| --model-provider-id | 无 | 否 | None | 模型提供商 ID 过滤器 |
| --tag-key-exists | 无 | 否 | None | 按标签键存在过滤（逗号分隔） |
| --tag-key-matches | 无 | 否 | None | 按标签键值对过滤-键（逗号分隔） |
| --tag-value-matches | 无 | 否 | None | 按标签键值对过滤-值（逗号分隔） |
| --tag-match-policy | 无 | 否 | None | 标签匹配模式（ALL/ANY） |
| --limit | 无 | 否 | 50 | 分页限制（1-100） |
| --offset | 无 | 否 | 0 | 分页偏移量 |

**使用示例**：

```bash
# 列出所有模型提供商
agentarts custom-model-provider list-providers
# 按名称过滤
agentarts custom-model-provider list-providers --name my-provider
# 分页查询
agentarts custom-model-provider list-providers --limit 10 --offset 0
```

## 模型服务命令

### create-model

在模型提供商下创建新的模型服务。

```bash
agentarts custom-model-provider create-model <model_provider_id> [options]
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | 无 | 是 | - | 模型提供商 ID（位置参数） |
| --model | 无 | 否 | None | 模型名称，如 qwen2.5-72b |
| --model-service-name | 无 | 否 | None | 模型服务显示名称 |
| --type | 无 | 否 | None | 模型类型（逗号分隔），如 completions |
| --protocol | 无 | 否 | None | API 协议（openai/anthropic/maas_v1） |
| --description | -d | 否 | None | 模型描述 |

**使用示例**：

```bash
# 基本创建
agentarts custom-model-provider create-model 123 \
  --model qwen2.5-72b \
  --model-service-name my-model \
  --type completions \
  --protocol openai
# 完整配置
agentarts custom-model-provider create-model 123 \
  --model qwen2.5-72b \
  --model-service-name my-model \
  --type completions,embeddings \
  --protocol openai \
  --description "我的模型服务"
```

### update-model

更新模型提供商下现有的模型服务。

```bash
agentarts custom-model-provider update-model <model_provider_id> <model_id> [options]
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | 无 | 是 | - | 模型提供商 ID（位置参数） |
| model_id | 无 | 是 | - | 模型 ID（位置参数） |
| --model | 无 | 否 | None | 模型名称 |
| --model-service-name | 无 | 否 | None | 模型服务显示名称 |
| --type | 无 | 否 | None | 模型类型（逗号分隔） |
| --protocol | 无 | 否 | None | API 协议（openai/anthropic/maas_v1） |
| --description | -d | 否 | None | 模型描述 |

**使用示例**：

```bash
# 更新描述
agentarts custom-model-provider update-model 123 456 --description "更新后的描述"
# 更新显示名称
agentarts custom-model-provider update-model 123 456 --model-service-name new-model-name
```

### delete-model

删除模型提供商下的模型服务。

```bash
agentarts custom-model-provider delete-model <model_provider_id> <model_id>
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | 无 | 是 | - | 模型提供商 ID（位置参数） |
| model_id | 无 | 是 | - | 模型 ID（位置参数） |

**使用示例**：

```bash
agentarts custom-model-provider delete-model 123 456
```

删除前会进行二次确认，输入 y 确认删除，输入 n 取消删除。

### get-model

获取模型提供商下模型服务的详细信息。

```bash
agentarts custom-model-provider get-model <model_provider_id> <model_id>
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | 无 | 是 | - | 模型提供商 ID（位置参数） |
| model_id | 无 | 是 | - | 模型 ID（位置参数） |

**使用示例**：

```bash
agentarts custom-model-provider get-model 123 456
```

### list-models

列出模型提供商下的模型服务，支持分页。

```bash
agentarts custom-model-provider list-models <model_provider_id> [options]
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | 无 | 是 | - | 模型提供商 ID（位置参数） |
| --model-service-name | 无 | 否 | None | 模型服务显示名称过滤器 |
| --model-id | 无 | 否 | None | 模型 ID 过滤器 |
| --limit | 无 | 否 | 50 | 分页限制（1-100） |
| --offset | 无 | 否 | 0 | 分页偏移量 |

**使用示例**：

```bash
# 列出所有模型服务
agentarts custom-model-provider list-models 123
# 按显示名称过滤
agentarts custom-model-provider list-models 123 --model-service-name my-model
# 分页查询
agentarts custom-model-provider list-models 123 --limit 10 --offset 0
```

## 模型代理命令

### create-proxy

为模型提供商创建新的模型代理。

```bash
agentarts custom-model-provider create-proxy [options]
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --custom-model-provider-id | 无 | 是 | - | 模型提供商 ID |
| --name | -n | 否 | model-proxy-{random} | 模型代理名称 |
| --description | -d | 否 | None | 模型代理描述 |
| --inbound-authorizer-type | 无 | 否 | iam | 入站认证类型（iam/api_key） |
| --agency-name | 无 | 否 | None | 委托名称。未提供时自动创建名为 AgentArtsCoreGateway 的委托 |
| --inbound-authorizer-configuration | 无 | 否 | None | 入站认证配置（JSON 格式） |
| --agent-gateway-id | 无 | 否 | None | 入网配置 ID，关联底层 AgentGateway 实例 |
| --tags | 无 | 否 | None | 资源标签（JSON 格式） |

**使用示例**：

```bash
# 基本创建（IAM 认证 + 自动创建委托）
agentarts custom-model-provider create-proxy --custom-model-provider-id 123
# 指定名称与描述
agentarts custom-model-provider create-proxy \
  --custom-model-provider-id 123 \
  --name my-proxy \
  --description "我的模型代理" \
  --agency-name AgentArtsCoreGateway
```

### update-proxy

更新现有的模型代理。

```bash
agentarts custom-model-provider update-proxy <gateway_id> [options]
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | 无 | 是 | - | 模型代理网关 ID（位置参数） |
| --tags | 无 | 否 | None | 资源标签（JSON 格式） |

**使用示例**：

```bash
# 更新标签
agentarts custom-model-provider update-proxy 123 --tags '[{"key": "Environment", "value": "test"}]'
```

### disassociate-proxies

批量解绑模型代理。当模型代理没有任何模型提供商关联时，会自动删除。

```bash
agentarts custom-model-provider disassociate-proxies [options]
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --unbindings | 无 | 是 | - | 解绑详情列表（JSON 格式），每项为 {"custom_model_provider_id": "...", "gateway_id": "..."} |

**使用示例**：

```bash
# 解绑单个模型代理
agentarts custom-model-provider disassociate-proxies \
  --unbindings '[{"custom_model_provider_id": "123", "gateway_id": "456"}]'
# 解绑多个模型代理
agentarts custom-model-provider disassociate-proxies \
  --unbindings '[{"custom_model_provider_id": "123", "gateway_id": "456"}, {"custom_model_provider_id": "123", "gateway_id": "789"}]'
```

## 配额命令

### list-quotas

查询当前认证账号的模型提供商、模型代理、模型的有效配额信息。

```bash
agentarts custom-model-provider list-quotas [options]
```

**参数说明**：

| 参数 | 简写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --custom-model-provider-id | 无 | 否 | None | 模型提供商 ID。指定时仅返回按提供商维度的配额 |
| --limit | 无 | 否 | 50 | 分页限制（1-100） |
| --offset | 无 | 否 | 0 | 分页偏移量 |

**使用示例**：

```bash
# 查询账号级配额
agentarts custom-model-provider list-quotas
# 查询指定模型提供商的配额
agentarts custom-model-provider list-quotas --custom-model-provider-id 123
# 分页查询
agentarts custom-model-provider list-quotas --limit 10 --offset 0
```

## 最佳实践

### 1. 模型提供商命名规范

- 使用有意义的模型提供商名称，便于识别和管理
- 名称需以小写字母开头、以小写字母或数字结尾，中间可包含小写字母、数字或连字符
- 例如：`myapp-prod-openai-compatible`

### 2. 凭证配置

- api_key 类型：适合提供 OpenAI 兼容 API 的外部模型服务
- iam 类型：适合华为云内部服务调用

### 3. 网络配置

- 公网模式（public）：适合公网可访问的模型服务
- VPC 内网模式（vpc）：适合 VPC 内部服务调用，安全性更高

### 4. 资源管理

- 及时解绑并清理不再使用的模型代理（无关联的模型代理会自动删除）
- 先删除模型提供商下的模型服务，再删除模型提供商
- 使用标签进行资源分类和管理
- 定期检查模型管理配额的使用情况

### 5. JSON 配置格式

- 确保 JSON 格式正确，使用单引号包裹
- 复杂配置建议使用文件或环境变量
- 注意特殊字符转义

## 常见问题

### Q1: 创建模型代理时提示委托创建失败？

**原因**：系统自动创建委托失败，可能是权限不足。

**解决方案**：
1. 检查 AK/SK 是否有 IAM 权限
2. 手动创建委托并提供 `--agency-name` 参数

### Q2: 更新模型提供商时提示参数错误？

**原因**：未提供任何更新参数。

**解决方案**：
确保至少提供一个更新参数（--name、--description 等）。

### Q3: JSON 配置格式错误？

**原因**：JSON 字符串格式不正确。

**解决方案**：
1. 验证 JSON 格式有效性
2. 使用单引号包裹 JSON 字符串
3. 检查特殊字符转义

### Q4: 如何选择模型服务的协议类型？

根据模型服务端点支持的 API 风格选择：
- **openai**：标准 OpenAI 协议，兼容性最好
- **anthropic**：Anthropic 协议
- **maas_v1**：MaaS 标准 API V1

### Q5: 如何清理模型代理？

模型代理通过解绑（disassociate-proxies）而非直接删除：
1. 调用 `agentarts custom-model-provider disassociate-proxies`，传入 --unbindings '[{"custom_model_provider_id": "...", "gateway_id": "..."}]'
2. 当模型代理没有任何模型提供商关联时，系统会自动删除该代理
