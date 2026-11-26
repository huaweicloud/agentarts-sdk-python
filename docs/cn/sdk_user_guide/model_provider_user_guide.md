# 模型提供商 SDK 使用指南

## 概述

模型提供商 SDK 提供模型网关下的模型提供商、模型服务与模型代理管理能力，支持创建、配置和管理自定义模型提供商及其模型服务，并为模型提供商创建模型代理。本文档介绍如何使用 CustomModelProviderClient 进行模型提供商、模型服务、模型代理的完整生命周期管理以及模型管理配额查询。

## 环境要求

- Python 3.10+
- 已安装 AgentArts SDK：`pip install agentarts-sdk`

## 认证配置

### 华为云 AK/SK 认证

模型提供商 SDK 使用华为云 AK/SK 进行身份认证。请通过以下方式配置：

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
from agentarts.sdk import CustomModelProviderClient

# 初始化客户端
client = CustomModelProviderClient()

# 创建模型提供商
provider_result = client.create_model_provider(
    name="my-provider",
    base_url="https://example.com/v1",
    credential_configuration={
        "provider_configuration": {
            "credential_provider_type": "api_key",
            "credential_provider": {
                "api_key_credential_provider": {
                    "provider_name": "my-provider-key",
                    "credential_location": "header",
                }
            },
        }
    },
    description="我的模型提供商",
)

provider_id = None
if provider_result.success:
    provider_id = provider_result.data.get("id")
    print(f"模型提供商创建成功，ID: {provider_id}")
else:
    print(f"创建模型提供商失败: {provider_result.error}")

# 创建模型服务
model_id = None
if provider_id is not None:
    model_result = client.create_model(
        model_provider_id=provider_id,
        model="qwen2.5-72b",
        model_service_name="my-model",
        type_=["completions"],
        protocol="openai",
        description="我的模型服务",
    )

    if model_result.success:
        model_id = model_result.data.get("id")
        print(f"模型服务创建成功，ID: {model_id}")
    else:
        print(f"创建模型服务失败: {model_result.error}")

# 创建模型代理
gateway_id = None
if provider_id is not None:
    proxy_result = client.create_model_proxy(
        custom_model_provider_id=provider_id,
        description="我的模型代理",
        agency_name="AgentArtsCoreGateway",
    )

    if proxy_result.success:
        gateway_id = proxy_result.data.get("gateway_id")
        print(f"模型代理创建成功，ID: {gateway_id}")
    else:
        print(f"创建模型代理失败: {proxy_result.error}")

# 列出模型提供商
list_result = client.list_model_providers()
if list_result.success:
    print(f"总模型提供商数: {list_result.data.get('total', 0)}")
    for provider in list_result.data.get("model_providers", []):
        print(f"- {provider.get('name')} (ID: {provider.get('id')})")

# 列出模型服务
if provider_id is not None:
    models_result = client.list_models(model_provider_id=provider_id)
    if models_result.success:
        print(f"总模型服务数: {models_result.data.get('total', 0)}")
        for model in models_result.data.get("models", []):
            print(f"- {model.get('model_service_name')} (ID: {model.get('id')})")

# 查询模型管理配额
quotas_result = client.list_model_management_quotas()
if quotas_result.success:
    print(f"配额总数: {quotas_result.data.get('total', 0)}")
    for quota in quotas_result.data.get("quotas", []):
        print(f"- {quota.get('type')}: {quota.get('used')}/{quota.get('quota')}")
```

## API 参考

### CustomModelProviderClient 类

#### 初始化

```python
CustomModelProviderClient(verify_ssl: bool = True)
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| verify_ssl | bool | 否 | True | 是否验证 SSL 证书 |

**默认行为**：
- 默认启用 SSL 验证（verify_ssl=True）

### 模型提供商管理方法

#### create_model_provider

创建新的模型提供商。

```python
create_model_provider(
    name: str,
    base_url: str,
    credential_configuration: Dict[str, Any],
    network_configuration: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None,
    tags: Optional[List[Dict[str, str]]] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| name | str | 是 | - | 模型提供商名称，账户下唯一（不区分大小写），2-40 个字符 |
| base_url | str | 是 | - | 模型提供商的默认 API 基础地址，以 https:// 开头的完整 URL |
| credential_configuration | Dict | 是 | - | 模型提供商的凭证信息 |
| network_configuration | Dict | 否 | {"network_mode": "public"} | 网络配置信息，network_mode 可为 public 或 vpc |
| description | str | 否 | None | 模型提供商的详细描述，0-1000 个字符 |
| tags | List[Dict] | 否 | None | 资源标签列表，数组长度 0-20 |

**返回值**：`RequestResult` 对象

#### update_model_provider

更新现有的模型提供商。

```python
update_model_provider(
    model_provider_id: str,
    name: Optional[str] = None,
    base_url: Optional[str] = None,
    credential_configuration: Optional[Dict[str, Any]] = None,
    network_configuration: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None,
    tags: Optional[List[Dict[str, str]]] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | str | 是 | - | 模型提供商 ID |
| name | str | 否 | None | 模型提供商名称 |
| base_url | str | 否 | None | 模型提供商的默认 API 基础地址 |
| credential_configuration | Dict | 否 | None | 模型提供商的凭证信息 |
| network_configuration | Dict | 否 | None | 网络配置信息 |
| description | str | 否 | None | 模型提供商的详细描述 |
| tags | List[Dict] | 否 | None | 资源标签列表 |

**返回值**：`RequestResult` 对象

**异常**：`ValueError` - 如果所有可选参数均为 None

#### delete_model_provider

删除模型提供商。

```python
delete_model_provider(model_provider_id: str) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | str | 是 | - | 模型提供商 ID |

**返回值**：`RequestResult` 对象

#### get_model_provider

获取模型提供商的详细信息。

```python
get_model_provider(model_provider_id: str) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | str | 是 | - | 模型提供商 ID |

**返回值**：`RequestResult` 对象

#### list_model_providers

列出模型提供商，可选择过滤条件。

```python
list_model_providers(
    name: Optional[str] = None,
    model_provider_id: Optional[str] = None,
    tag_key_exists: Optional[List[str]] = None,
    tag_key_matches: Optional[List[str]] = None,
    tag_value_matches: Optional[List[str]] = None,
    tag_match_policy: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| name | str | 否 | None | 模型提供商名称过滤器，支持模糊匹配 |
| model_provider_id | str | 否 | None | 模型提供商 ID 过滤器（对应 API 的 id 参数） |
| tag_key_exists | List[str] | 否 | None | 按标签键存在过滤 |
| tag_key_matches | List[str] | 否 | None | 按标签键值对过滤（键） |
| tag_value_matches | List[str] | 否 | None | 按标签键值对过滤（值） |
| tag_match_policy | str | 否 | None | 标签匹配模式（ALL/ANY） |
| limit | int | 否 | None | 结果的最大数量（1-100） |
| offset | int | 否 | None | 分页偏移量 |

**返回值**：`RequestResult` 对象

### 模型服务管理方法

#### create_model

在模型提供商下创建新的模型服务。

```python
create_model(
    model_provider_id: str,
    model: str,
    model_service_name: str,
    type_: List[str],
    protocol: str,
    description: Optional[str] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | str | 是 | - | 模型提供商 ID |
| model | str | 是 | - | 模型名称，如 qwen2.5-72b，支持 * 前缀/后缀通配 |
| model_service_name | str | 是 | - | 显示名称，2-64 个字符，支持中英文、数字及符号 . _ / \| - |
| type_ | List[str] | 是 | - | 模型的类型列表，如 ["completions"]，数组长度 1-10 |
| protocol | str | 是 | - | API 接口协议（openai/anthropic/maas_v1） |
| description | str | 否 | None | 模型的详细描述，0-1000 个字符 |

**返回值**：`RequestResult` 对象

#### update_model

更新模型提供商下现有的模型服务。

```python
update_model(
    model_provider_id: str,
    model_id: str,
    model: Optional[str] = None,
    model_service_name: Optional[str] = None,
    type_: Optional[List[str]] = None,
    protocol: Optional[str] = None,
    description: Optional[str] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | str | 是 | - | 模型提供商 ID |
| model_id | str | 是 | - | 模型 ID |
| model | str | 否 | None | 模型名称 |
| model_service_name | str | 否 | None | 显示名称 |
| type_ | List[str] | 否 | None | 模型的类型列表 |
| protocol | str | 否 | None | API 接口协议（openai/anthropic/maas_v1） |
| description | str | 否 | None | 模型的详细描述 |

**返回值**：`RequestResult` 对象

**异常**：`ValueError` - 如果所有可选参数均为 None

#### delete_model

删除模型提供商下的模型服务。

```python
delete_model(model_provider_id: str, model_id: str) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | str | 是 | - | 模型提供商 ID |
| model_id | str | 是 | - | 模型 ID |

**返回值**：`RequestResult` 对象

#### get_model

获取模型提供商下模型服务的详细信息。

```python
get_model(model_provider_id: str, model_id: str) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | str | 是 | - | 模型提供商 ID |
| model_id | str | 是 | - | 模型 ID |

**返回值**：`RequestResult` 对象

#### list_models

列出模型提供商下的模型服务，支持分页。

```python
list_models(
    model_provider_id: str,
    model_service_name: Optional[str] = None,
    model_id: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| model_provider_id | str | 是 | - | 模型提供商 ID |
| model_service_name | str | 否 | None | 显示名称过滤器，支持模糊匹配 |
| model_id | str | 否 | None | 模型 ID 过滤器（对应 API 的 id 参数） |
| limit | int | 否 | None | 结果的最大数量（1-100） |
| offset | int | 否 | None | 分页偏移量 |

**返回值**：`RequestResult` 对象

### 模型代理管理方法

#### create_model_proxy

为模型提供商创建新的模型代理。

```python
create_model_proxy(
    custom_model_provider_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    inbound_authorizer_type: Optional[str] = "iam",
    agency_name: Optional[str] = None,
    inbound_authorizer_configuration: Optional[Dict[str, Any]] = None,
    agent_gateway_id: Optional[str] = None,
    tags: Optional[List[Dict[str, str]]] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| custom_model_provider_id | str | 是 | - | 模型提供商 ID |
| name | str | 否 | model-proxy-{random} | 模型代理名称，账户下唯一（不区分大小写） |
| description | str | 否 | None | 模型代理的详细描述，0-1000 个字符 |
| inbound_authorizer_type | str | 否 | iam | 入站认证类型（iam/api_key） |
| agency_name | str | 否 | None | 委托名称。未提供时自动创建名为 AgentArtsCoreGateway 的委托 |
| inbound_authorizer_configuration | Dict | 否 | None | 授权器配置，inbound_authorizer_type 为 api_key 时须配置 key_auth |
| agent_gateway_id | str | 否 | None | 入网配置 ID，关联底层 AgentGateway 实例 |
| tags | List[Dict] | 否 | None | 资源标签列表，数组长度 0-20 |

**返回值**：`RequestResult` 对象

**异常**：`ValueError` - 如果委托创建失败且未提供 agency_name

#### update_model_proxy

更新现有的模型代理。

```python
update_model_proxy(
    gateway_id: str,
    tags: Optional[List[Dict[str, str]]] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| gateway_id | str | 是 | - | 模型代理网关 ID |
| tags | List[Dict] | 否 | None | 资源标签列表 |

**返回值**：`RequestResult` 对象

**异常**：`ValueError` - 如果所有可选参数均为 None

#### batch_disassociate_model_proxies

批量解绑模型代理。当模型代理没有任何模型提供商关联时，会自动删除。

```python
batch_disassociate_model_proxies(
    unbindings: List[Dict[str, str]]
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| unbindings | List[Dict] | 是 | - | 解绑详情列表，每项为 {"custom_model_provider_id": "...", "gateway_id": "..."} |

**返回值**：`RequestResult` 对象

### 配额管理方法

#### list_model_management_quotas

查询当前认证账号的模型提供商、模型代理、模型的有效配额信息。

```python
list_model_management_quotas(
    custom_model_provider_id: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> RequestResult
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| custom_model_provider_id | str | 否 | None | 模型提供商 ID。指定时仅返回按提供商维度的配额 |
| limit | int | 否 | None | 结果的最大数量（1-100） |
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
from agentarts.sdk import CustomModelProviderClient

try:
    client = CustomModelProviderClient()
    result = client.create_model_provider(
        name="my-provider",
        base_url="https://example.com/v1",
        credential_configuration={"provider_configuration": {}},
    )

    if not result.success:
        logging.error(f"创建模型提供商失败: {result.error}")

except ValueError as e:
    # 参数验证错误（如更新时未提供任何参数、委托创建失败）
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

### 2. 模型提供商命名规范

- 使用有意义的模型提供商名称，便于识别和管理
- 名称需以小写字母开头、以小写字母或数字结尾，中间可包含小写字母、数字或连字符
- 例如：`myapp-prod-openai-compatible`

### 3. 凭证配置

- api_key 类型：适合提供 OpenAI 兼容 API 的外部模型服务
- iam 类型：适合华为云内部服务调用
- 凭证传递位置（credential_location）支持 header 与 query

### 4. 网络配置

- 公网模式（public）：适合公网可访问的模型服务
- VPC 内网模式（vpc）：适合 VPC 内部服务调用，安全性更高，需配置 vpc_config

### 5. 资源管理

- 及时解绑并清理不再使用的模型代理（无关联的模型代理会自动删除）
- 先删除模型提供商下的模型服务，再删除模型提供商
- 使用标签进行资源分类和管理
- 定期检查模型管理配额的使用情况

## 常见问题

### Q1: 创建模型代理时提示委托创建失败？

**原因**：系统自动创建委托失败，可能是权限不足。

**解决方案**：
1. 检查 AK/SK 是否有 IAM 权限
2. 手动创建委托并提供 `agency_name` 参数

### Q2: 更新模型提供商时提示参数错误？

**原因**：未提供任何更新参数。

**解决方案**：
确保至少提供一个更新参数（name、description 等）。

### Q3: 如何选择模型服务的协议类型？

根据模型服务端点支持的 API 风格选择：
- **openai**：标准 OpenAI 协议，兼容性最好
- **anthropic**：Anthropic 协议
- **maas_v1**：MaaS 标准 API V1

### Q4: 创建模型提供商时返回 409（名称重复）？

**原因**：账户下模型提供商名称唯一（不区分大小写）。

**解决方案**：
更换名称后重试，可通过 `list_model_providers` 查看已有名称。

### Q5: 如何清理模型代理？

模型代理通过解绑（batch_disassociate_model_proxies）而非直接删除：
1. 调用 `batch_disassociate_model_proxies`，传入 [{"custom_model_provider_id": "...", "gateway_id": "..."}]
2. 当模型代理没有任何模型提供商关联时，系统会自动删除该代理
