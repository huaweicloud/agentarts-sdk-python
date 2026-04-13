# MCP Gateway CLI 文档

## 概述

MCP (Model Context Protocol) Gateway CLI 提供了用于管理 MCP 网关及其目标的命令。本文档涵盖了所有可用的 CLI 命令、其参数和使用示例。

## 命令结构

所有 MCP Gateway 命令都通过 `agentarts mcp-gateway` 命名空间访问：

```bash
agentarts mcp-gateway [command]
```

## 网关命令

### create-mcp-gateway

创建新的 MCP 网关。

**参数：**
- `--name, -n`：网关名称（可选）
- `--description, -d`：网关描述（可选）
- `--protocol-type`：协议类型（默认：mcp）
- `--authorizer-type`：授权器类型（默认：iam）
- `--agency-name`：代理名称（可选）
- `--authorizer-configuration`：授权器配置（JSON 格式）（可选）
- `--log-delivery-configuration`：日志投递配置（JSON 格式）（可选）
- `--outbound-network-configuration`：出站网络配置（JSON 格式）（可选）
- `--tags`：网关标签（可选）

**示例：**
```bash
agentarts mcp-gateway create-mcp-gateway --name my-gateway --description "我的 MCP 网关"
```

### update-mcp-gateway

更新现有的 MCP 网关。

**参数：**
- `gateway_id`：网关 ID（必需，位置参数）
- `--description, -d`：网关描述（可选）
- `--authorizer-configuration`：授权器配置（JSON 格式）（可选）
- `--log-delivery-configuration`：日志投递配置（JSON 格式）（可选）
- `--outbound-network-configuration`：出站网络配置（JSON 格式）（可选）
- `--tags`：网关标签（可选）

**示例：**
```bash
agentarts mcp-gateway update-mcp-gateway 123 --description "更新后的描述"
```

### delete-mcp-gateway

删除 MCP 网关。

**参数：**
- `gateway_id`：网关 ID（必需，位置参数）

**示例：**
```bash
agentarts mcp-gateway delete-mcp-gateway 123
```

### get-mcp-gateway

获取 MCP 网关的详细信息。

**参数：**
- `gateway_id`：网关 ID（必需，位置参数）

**示例：**
```bash
agentarts mcp-gateway get-mcp-gateway 123
```

### list-mcp-gateways

列出 MCP 网关，可选择过滤条件。

**参数：**
- `--name`：网关名称过滤器（可选）
- `--status`：网关状态过滤器（可选）
- `--gateway-id`：网关 ID 过滤器（可选）
- `--tags`：网关标签过滤器（可选）
- `--limit`：分页限制（默认：50，最小：1，最大：50）（可选）
- `--offset`：分页偏移量（默认：0，最小：0，最大：1000000）（可选）

**示例：**
```bash
agentarts mcp-gateway list-mcp-gateways --limit 10
```

## 目标命令

### create-mcp-gateway-target

创建新的 MCP 网关目标。

**参数：**
- `gateway_id`：网关 ID（必需，位置参数）
- `--name, -n`：目标名称（可选）
- `--description, -d`：目标描述（可选）
- `--target-configuration`：目标配置（JSON 格式）（可选）
- `--credential-provider-configuration`：凭证提供者配置（JSON 格式）（可选）

**示例：**
```bash
agentarts mcp-gateway create-mcp-gateway-target 123 --name my-target
```

### update-mcp-gateway-target

更新现有的 MCP 网关目标。

**参数：**
- `gateway_id`：网关 ID（必需，位置参数）
- `target_id`：目标 ID（必需，位置参数）
- `--name, -n`：目标名称（可选）
- `--description, -d`：目标描述（可选）
- `--target-configuration`：目标配置（JSON 格式）（可选）
- `--credential-provider-configuration`：凭证提供者配置（JSON 格式）（可选）

**示例：**
```bash
agentarts mcp-gateway update-mcp-gateway-target 123 456 --name updated-target
```

### delete-mcp-gateway-target

删除 MCP 网关目标。

**参数：**
- `gateway_id`：网关 ID（必需，位置参数）
- `target_id`：目标 ID（必需，位置参数）

**示例：**
```bash
agentarts mcp-gateway delete-mcp-gateway-target 123 456
```

### get-mcp-gateway-target

获取 MCP 网关目标的详细信息。

**参数：**
- `gateway_id`：网关 ID（必需，位置参数）
- `target_id`：目标 ID（必需，位置参数）

**示例：**
```bash
agentarts mcp-gateway get-mcp-gateway-target 123 456
```

### list-mcp-gateway-targets

列出 MCP 网关目标，支持分页。

**参数：**
- `gateway_id`：网关 ID（必需，位置参数）
- `--limit`：分页限制（默认：50，最小：1，最大：50）（可选）
- `--offset`：分页偏移量（默认：0，最小：0，最大：1000000）（可选）

**示例：**
```bash
agentarts mcp-gateway list-mcp-gateway-targets 123 --limit 10
```
