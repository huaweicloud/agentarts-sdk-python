# MCP Gateway SDK 使用指南

## 概述

MCP Gateway SDK 提供网关管理功能，支持创建、配置和管理 MCP（Model Context Protocol）网关及其目标。本文档介绍如何使用 MCP Gateway SDK 进行网关的创建、配置和目标管理。

## 环境要求

- Python 3.10+
- 已安装 AgentArts SDK：`pip install agentarts`

## 认证配置

### 华为云 AK/SK 认证

MCP Gateway SDK 使用华为云 AK/SK 进行身份认证。请通过以下方式配置：

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

## 快速开始

### 基本用法示例

```python
from agentarts.sdk.mcpgateway import MCPGatewayClient

# 初始化客户端
client = MCPGatewayClient()

# 创建网关
result = client.create_mcp_gateway(
    name="my-gateway",
    description="我的 MCP 网关",
    protocol_type="mcp",
    authorizer_type="iam"
)

if result.success:
    gateway_id = result.data.get("id")
    print(f"网关创建成功，ID: {gateway_id}")
else:
    print(f"创建网关失败: {result.error}")

# 创建目标
if gateway_id:
    target_result = client.create_mcp_gateway_target(
        gateway_id=gateway_id,
        name="my-target",
        description="我的 MCP 目标",
        target_configuration={
            "endpoint": "https://api.example.com",
            "timeout": 30
        }
    )

    if target_result.success:
        target_id = target_result.data.get("id")
        print(f"目标创建成功，ID: {target_id}")
    else:
        print(f"创建目标失败: {target_result.error}")

# 列出网关
list_result = client.list_mcp_gateways()
if list_result.success:
    print(f"总网关数: {list_result.data.get('total', 0)}")
    for gateway in list_result.data.get('gateways', []):
        print(f"- {gateway.get('name')} (ID: {gateway.get('id')})")
```

## API 参考

### MCPGatewayClient 类

#### 初始化

```python
MCPGatewayClient(config: Optional[RequestConfig] = None)
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| config | RequestConfig | 否 | None | 请求配置对象 |

**默认行为**：
- 如果未提供 `config`，将创建默认的 `RequestConfig`
- 如果未设置 `base_url`，客户端将使用控制平面端点
- 默认禁用 SSL 验证

### 网关管理方法

#### create_mcp_gateway

创建新的 MCP 网关。

```python
create_mcp_gateway(
    name: Optional[str] = None,
    description: Optional[str] = None,
    protocol_type: Optional[str] = "mcp",
    authorizer_type: Optional[str] = "iam",
    agency_name: Optional[str] = None,
    authorizer_configuration: Optional[Dict[str, Any]] = None,
    log_delivery_configuration: Optional[Dict[str, Any]] = None,
    outbound_network_configuration: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| name | str | 否 | gateway-{random} | 网关名称 |
| description | str | 否 | None | 网关描述 |
| protocol_type | str | 否 | mcp | 协议类型 |
| authorizer_type | str | 否 | iam | 授权器类型（custom_jwt/iam/api_key） |
| agency_name | str | 否 | None | 代理名称 |
| authorizer_configuration | Dict | 否 | None | 授权器配置 |
| log_delivery_configuration | Dict | 否 | {"enabled": False} | 日志投递配置 |
| outbound_network_configuration | Dict | 否 | {"network_mode": "public"} | 出站网络配置 |

**返回值**：`RequestResult` 对象

**异常**：`ValueError` - 如果代理创建失败且未提供 agency_name

#### update_mcp_gateway

更新现有的 MCP 网关。

```python
update_mcp_gateway(
    gateway_id: str,
    description: Optional[str] = None,
    authorizer_configuration: Optional[Dict[str, Any]] = None,
    log_delivery_configuration: Optional[Dict[str, Any]] = None,
    outbound_network_configuration: Optional[Dict[str, Any]] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | str | 是 | - | 网关 ID |
| description | str | 否 | None | 网关描述 |
| authorizer_configuration | Dict | 否 | None | 授权器配置 |
| log_delivery_configuration | Dict | 否 | None | 日志投递配置 |
| outbound_network_configuration | Dict | 否 | None | 出站网络配置 |

**返回值**：`RequestResult` 对象

**异常**：`ValueError` - 如果所有可选参数均为 None

#### delete_mcp_gateway

删除 MCP 网关。

```python
delete_mcp_gateway(gateway_id: str) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | str | 是 | - | 网关 ID |

**返回值**：`RequestResult` 对象

#### get_mcp_gateway

获取 MCP 网关的详细信息。

```python
get_mcp_gateway(gateway_id: str) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | str | 是 | - | 网关 ID |

**返回值**：`RequestResult` 对象

#### list_mcp_gateways

列出 MCP 网关，可选择过滤条件。

```python
list_mcp_gateways(
    name: Optional[str] = None,
    status: Optional[str] = None,
    gateway_id: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| name | str | 否 | None | 网关名称过滤器 |
| status | str | 否 | None | 网关状态过滤器 |
| gateway_id | str | 否 | None | 网关 ID 过滤器 |
| limit | int | 否 | None | 结果的最大数量 |
| offset | int | 否 | None | 分页偏移量 |

**返回值**：`RequestResult` 对象

### 目标管理方法

#### create_mcp_gateway_target

创建新的 MCP 网关目标。

```python
create_mcp_gateway_target(
    gateway_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    target_configuration: Optional[Dict[str, Any]] = None,
    credential_provider_configuration: Optional[Dict[str, Any]] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | str | 是 | - | 网关 ID |
| name | str | 否 | target-{random} | 目标名称 |
| description | str | 否 | None | 目标描述 |
| target_configuration | Dict | 否 | None | 目标配置 |
| credential_provider_configuration | Dict | 否 | {"credential_provider_type": "none"} | 凭证提供者配置 |

**返回值**：`RequestResult` 对象

#### update_mcp_gateway_target

更新现有的 MCP 网关目标。

```python
update_mcp_gateway_target(
    gateway_id: str,
    target_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    target_configuration: Optional[Dict[str, Any]] = None,
    credential_provider_configuration: Optional[Dict[str, Any]] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | str | 是 | - | 网关 ID |
| target_id | str | 是 | - | 目标 ID |
| name | str | 否 | None | 目标名称 |
| description | str | 否 | None | 目标描述 |
| target_configuration | Dict | 否 | None | 目标配置 |
| credential_provider_configuration | Dict | 否 | None | 凭证提供者配置 |

**返回值**：`RequestResult` 对象

**异常**：`ValueError` - 如果所有可选参数均为 None

#### delete_mcp_gateway_target

删除 MCP 网关目标。

```python
delete_mcp_gateway_target(gateway_id: str, target_id: str) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | str | 是 | - | 网关 ID |
| target_id | str | 是 | - | 目标 ID |

**返回值**：`RequestResult` 对象

#### get_mcp_gateway_target

获取 MCP 网关目标的详细信息。

```python
get_mcp_gateway_target(gateway_id: str, target_id: str) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | str | 是 | - | 网关 ID |
| target_id | str | 是 | - | 目标 ID |

**返回值**：`RequestResult` 对象

#### list_mcp_gateway_targets

列出 MCP 网关目标，支持分页。

```python
list_mcp_gateway_targets(
    gateway_id: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | str | 是 | - | 网关 ID |
| limit | int | 否 | None | 结果的最大数量 |
| offset | int | 否 | None | 分页偏移量 |

**返回值**：`RequestResult` 对象

## 返回类型说明

### RequestResult

所有方法返回的 `RequestResult` 对象具有以下属性：

| 属性 | 类型 | 说明 |
|------|------|------|
| success | bool | 表示请求是否成功 |
| data | dict/list | 响应数据 |
| error | str | 如果请求失败，则为错误消息 |
| status_code | int | HTTP 状态码 |

## 错误处理

```python
import logging
from agentarts.sdk.mcpgateway import MCPGatewayClient

try:
    client = MCPGatewayClient()
    result = client.create_mcp_gateway(name="my-gateway")
    
    if not result.success:
        logging.error(f"创建网关失败: {result.error}")
        
except ValueError as e:
    # 参数验证错误
    logging.error(f"参数错误: {e}")
    
except Exception as e:
    # 网络、认证或其他系统错误
    logging.error(f"系统错误: {e}")
```

## 最佳实践

### 1. 认证信息管理

- 使用环境变量存储 AK/SK，避免硬编码
- 生产环境建议使用密钥管理服务
- 定期轮换访问密钥

### 2. 网关命名规范

- 使用有意义的网关名称，便于识别和管理
- 建议使用格式：`{project}-{environment}-{function}`
- 例如：`myapp-prod-api-gateway`

### 3. 授权器配置

- IAM 授权器：适合华为云内部服务调用
- API Key 授权器：适合外部系统集成
- Custom JWT 授权器：适合自定义认证场景

### 4. 网络配置

- 公网模式：适合公网访问场景
- VPC 内网模式：适合内部服务调用，安全性更高

### 5. 资源管理

- 及时清理不再使用的网关和目标
- 使用标签进行资源分类和管理
- 定期检查网关状态和配置

## 常见问题

### Q1: 创建网关时提示代理创建失败？

**原因**：系统自动创建代理失败，可能是权限不足。

**解决方案**：
1. 检查 AK/SK 是否有 IAM 权限
2. 手动创建代理并提供 `agency_name` 参数

### Q2: 更新网关时提示参数错误？

**原因**：未提供任何更新参数。

**解决方案**：
确保至少提供一个更新参数（description、authorizer_configuration 等）。

### Q3: 如何选择授权器类型？

根据使用场景选择：
- **iam**：华为云内部服务调用
- **api_key**：外部系统集成，简单易用
- **custom_jwt**：需要自定义认证逻辑

### Q4: 网关创建后无法访问？

**检查项**：
1. 网关状态是否为 running
2. 网络配置是否正确
3. 目标配置是否正确
4. 认证信息是否有效

### Q5: 如何删除网关？

删除网关前确保：
1. 网关下没有正在运行的任务
2. 先删除所有关联的目标
3. 使用 `delete_mcp_gateway` 方法删除
