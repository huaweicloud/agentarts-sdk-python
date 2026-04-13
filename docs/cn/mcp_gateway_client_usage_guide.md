# MCP Gateway 客户端文档

## 概述

`MCPGatewayClient` 类提供了一个 Python 客户端，用于与 MCP（Model Context Protocol）Gateway 服务交互。本文档涵盖了客户端的初始化、方法、参数和使用示例。

## 类定义

```python
class MCPGatewayClient(BaseHTTPClient):
    """
    MCP Gateway 客户端，用于向 MCP Gateway 服务进行 API 调用。
    
    继承自 BaseHTTPClient 以提供特定服务的 API 方法。
    """
```

## 初始化

### 构造函数

```python
def __init__(self, config: Optional[RequestConfig] = None):
    """
    初始化 MCP Gateway 客户端。
    
    参数:
        config: 可选的 RequestConfig 对象。如果未提供或未设置 base_url，
                客户端将使用控制平面端点。
    """
```

### 默认行为

- 如果未提供 `config`，将创建默认的 `RequestConfig`
- 如果未设置 `base_url`，客户端将使用控制平面端点：`{control_plane_endpoint}/v1/core`
- 默认禁用 SSL 验证 (`config.verify_ssl = False`)

## 网关方法

### create_mcp_gateway

创建新的 MCP 网关。

```python
def create_mcp_gateway(
    self,
    name: Optional[str] = None,
    description: Optional[str] = None,
    protocol_type: Optional[str] = "mcp",
    authorizer_type: Optional[str] = "iam",
    agency_name: Optional[str] = None,
    authorizer_configuration: Optional[Dict[str, Any]] = None,
    log_delivery_configuration: Optional[Dict[str, Any]] = None,
    outbound_network_configuration: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
) -> RequestResult:
```

**参数：**
- `name`：网关名称，默认为 `TestGateway-<random-string>`
- `description`：网关描述
- `protocol_type`：协议类型，默认为 "mcp"
- `authorizer_type`：授权器类型，可以是 "custom_jwt"、"iam" 或 "api_key"，默认为 "iam"
- `agency_name`：代理名称
- `authorizer_configuration`：授权器配置
- `log_delivery_configuration`：日志投递配置（默认：`{"enabled": False}`）
- `outbound_network_configuration`：出站网络配置（默认：`{"network_mode": "public"}`）
- `tags`：网关标签

**返回值：**
- `RequestResult`：API 调用的结果

**异常：**
- `ValueError`：如果代理创建失败且未提供 agency_name

### update_mcp_gateway

更新现有的 MCP 网关。

```python
def update_mcp_gateway(
    self,
    gateway_id: str,
    description: Optional[str] = None,
    authorizer_configuration: Optional[Dict[str, Any]] = None,
    log_delivery_configuration: Optional[Dict[str, Any]] = None,
    outbound_network_configuration: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
) -> RequestResult:
```

**参数：**
- `gateway_id`：网关 ID（必需）
- `description`：网关描述
- `authorizer_configuration`：授权器配置
- `log_delivery_configuration`：日志投递配置
- `outbound_network_configuration`：出站网络配置
- `tags`：网关标签

**返回值：**
- `RequestResult`：API 调用的结果

**异常：**
- `ValueError`：如果所有可选参数均为 None

### delete_mcp_gateway

删除 MCP 网关。

```python
def delete_mcp_gateway(self, gateway_id: str) -> RequestResult:
```

**参数：**
- `gateway_id`：网关 ID（必需）

**返回值：**
- `RequestResult`：API 调用的结果

### get_mcp_gateway

获取 MCP 网关的详细信息。

```python
def get_mcp_gateway(self, gateway_id: str) -> RequestResult:
```

**参数：**
- `gateway_id`：网关 ID（必需）

**返回值：**
- `RequestResult`：API 调用的结果

### list_mcp_gateways

列出 MCP 网关，可选择过滤条件。

```python
def list_mcp_gateways(
    self,
    name: Optional[str] = None,
    status: Optional[str] = None,
    gateway_id: Optional[str] = None,
    tags: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> RequestResult:
```

**参数：**
- `name`：网关名称过滤器
- `status`：网关状态过滤器
- `gateway_id`：网关 ID 过滤器
- `tags`：网关标签过滤器
- `limit`：结果的最大数量
- `offset`：分页偏移量

**返回值：**
- `RequestResult`：API 调用的结果

## 目标方法

### create_mcp_gateway_target

创建新的 MCP 网关目标。

```python
def create_mcp_gateway_target(
    self,
    gateway_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    target_configuration: Optional[Dict[str, Any]] = None,
    credential_provider_configuration: Optional[Dict[str, Any]] = None
) -> RequestResult:
```

**参数：**
- `gateway_id`：网关 ID（必需）
- `name`：目标名称，默认为 `TestGatewayTarget-<random-string>`
- `description`：目标描述
- `target_configuration`：目标配置
- `credential_provider_configuration`：凭证提供者配置（默认：`{"credential_provider_type": "none"}`）

**返回值：**
- `RequestResult`：API 调用的结果

### update_mcp_gateway_target

更新现有的 MCP 网关目标。

```python
def update_mcp_gateway_target(
    self,
    gateway_id: str,
    target_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    target_configuration: Optional[Dict[str, Any]] = None,
    credential_provider_configuration: Optional[Dict[str, Any]] = None
) -> RequestResult:
```

**参数：**
- `gateway_id`：网关 ID（必需）
- `target_id`：目标 ID（必需）
- `name`：目标名称
- `description`：目标描述
- `target_configuration`：目标配置
- `credential_provider_configuration`：凭证提供者配置

**返回值：**
- `RequestResult`：API 调用的结果

**异常：**
- `ValueError`：如果所有可选参数均为 None

### delete_mcp_gateway_target

删除 MCP 网关目标。

```python
def delete_mcp_gateway_target(self, gateway_id: str, target_id: str) -> RequestResult:
```

**参数：**
- `gateway_id`：网关 ID（必需）
- `target_id`：目标 ID（必需）

**返回值：**
- `RequestResult`：API 调用的结果

### get_mcp_gateway_target

获取 MCP 网关目标的详细信息。

```python
def get_mcp_gateway_target(self, gateway_id: str, target_id: str) -> RequestResult:
```

**参数：**
- `gateway_id`：网关 ID（必需）
- `target_id`：目标 ID（必需）

**返回值：**
- `RequestResult`：API 调用的结果

### list_mcp_gateway_targets

列出 MCP 网关目标，支持分页。

```python
def list_mcp_gateway_targets(
    self,
    gateway_id: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> RequestResult:
```

**参数：**
- `gateway_id`：网关 ID（必需）
- `limit`：结果的最大数量
- `offset`：分页偏移量

**返回值：**
- `RequestResult`：API 调用的结果

## RequestResult 结构

所有方法返回的 `RequestResult` 对象具有以下结构：

- `success`：布尔值，表示请求是否成功
- `data`：响应数据（字典或列表）
- `error`：如果请求失败，则为错误消息
- `status_code`：HTTP 状态码

## 使用示例

### 基本用法

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
        },
        credential_provider_configuration={
            "credential_provider_type": "none"
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
else:
    print(f"列出网关失败: {list_result.error}")
```
