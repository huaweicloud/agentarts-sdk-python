# 环境变量配置指南

## 概述

AgentArts SDK 通过环境变量进行配置，包括华为云认证、服务端点和运行时设置。所有环境变量可通过以下方式配置：

- 系统环境变量
- `.env` 文件（由 python-dotenv 加载）
- IDE 配置

## 华为云认证配置

### AK/SK 认证

华为云 Access Key 和 Secret Key 是最基本的认证凭据，用于访问华为云服务。

| 环境变量 | 说明 | 必填 |
|----------|------|------|
| `HUAWEICLOUD_SDK_AK` | 华为云 Access Key ID | 是 |
| `HUAWEICLOUD_SDK_SK` | 华为云 Secret Access Key | 是 |

**配置示例：**

```bash
# Linux/macOS
export HUAWEICLOUD_SDK_AK="your-access-key"
export HUAWEICLOUD_SDK_SK="your-secret-key"

# Windows PowerShell
$env:HUAWEICLOUD_SDK_AK = "your-access-key"
$env:HUAWEICLOUD_SDK_SK = "your-secret-key"

# Windows CMD
set HUAWEICLOUD_SDK_AK=your-access-key
set HUAWEICLOUD_SDK_SK=your-secret-key
```

**获取 AK/SK：**
1. 登录 [华为云控制台](https://console.huaweicloud.com/)
2. 进入「我的凭证」页面
3. 在「访问密钥」标签页创建或查看 AK/SK

### 临时安全令牌 (STS)

当使用临时安全令牌进行认证时，需要配置以下环境变量：

| 环境变量 | 说明 | 必填 |
|----------|------|------|
| `HUAWEICLOUD_SDK_SECURITY_TOKEN` | 临时安全令牌 | 使用 STS 时必填 |

**配置示例：**

```bash
export HUAWEICLOUD_SDK_SECURITY_TOKEN="your-security-token"
```

### 区域配置

SDK 支持多种区域配置方式，按以下优先级顺序读取：

| 优先级 | 环境变量 | 说明 |
|--------|----------|------|
| 1 | `HUAWEICLOUD_SDK_REGION` | 华为云 SDK 标准区域变量（推荐） |
| 2 | `HUAWEICLOUD_REGION` | 华为云区域变量 |
| 3 | `OS_REGION_NAME` | OpenStack 兼容区域变量 |

**默认区域：** 如果未配置任何区域变量，SDK 默认使用 `cn-southwest-2`。

**配置示例：**

```bash
export HUAWEICLOUD_SDK_REGION="cn-north-4"
```

**常用区域列表：**

| 区域 ID | 区域名称 |
|---------|----------|
| `cn-north-4` | 华北-北京四 |
| `cn-southwest-2` | 西南-贵阳一 |
| `cn-east-3` | 华东-上海一 |
| `cn-south-1` | 华南-广州 |
| `ap-southeast-4` | 亚太-新加坡 |

### 项目 ID 配置

部分华为云服务需要项目 ID：

| 环境变量 | 说明 |
|----------|------|
| `HUAWEICLOUD_SDK_PROJECT_ID` | 华为云项目 ID |

**获取项目 ID：**
1. 登录华为云控制台
2. 进入「我的凭证」页面
3. 在「项目列表」中查看对应区域的项目 ID

### 身份提供商配置

用于联邦身份认证场景：

| 环境变量 | 说明 |
|----------|------|
| `HUAWEICLOUD_SDK_IDP_ID` | 身份提供商 ID |
| `HUAWEICLOUD_SDK_ID_TOKEN_FILE` | ID Token 文件路径 |

---

## AgentArts 服务端点配置

SDK 支持自定义服务端点，适用于私有化部署或测试环境。

### 控制面端点

控制面端点用于管理操作（如创建/删除资源）：

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `AGENTARTS_CONTROL_ENDPOINT` | AgentArts 控制面端点 | `https://agentarts.{region}.myhuaweicloud.com` |

**配置示例：**

```bash
export AGENTARTS_CONTROL_ENDPOINT="https://agentarts.cn-north-4.myhuaweicloud.com"
```

### 数据面端点

数据面端点用于实际的数据操作（如执行代码、存储记忆）：

#### Runtime 数据面端点

| 环境变量 | 说明 |
|----------|------|
| `AGENTARTS_RUNTIME_DATA_ENDPOINT` | Runtime 数据面端点 |

**配置示例：**

```bash
export AGENTARTS_RUNTIME_DATA_ENDPOINT="https://your-runtime-endpoint.com"
```

#### Memory 数据面端点

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `AGENTARTS_MEMORY_DATA_ENDPOINT` | Memory 数据面端点 | `https://memory.{region}.huaweicloud-agentarts.com` |

**配置示例：**

```bash
export AGENTARTS_MEMORY_DATA_ENDPOINT="https://memory.cn-north-4.huaweicloud-agentarts.com"
```

#### CodeInterpreter 数据面端点

| 环境变量 | 说明 |
|----------|------|
| `AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT` | CodeInterpreter 数据面端点 |

**配置示例：**

```bash
export AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT="https://your-code-interpreter-endpoint.com"
```

---

## 华为云服务端点配置

SDK 支持自定义华为云服务端点：

### IAM 端点

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `HUAWEICLOUD_SDK_IAM_ENDPOINT` | IAM 服务端点 | `https://iam.{region}.myhuaweicloud.com` |

**配置示例：**

```bash
export HUAWEICLOUD_SDK_IAM_ENDPOINT="https://iam.cn-north-4.myhuaweicloud.com"
```

### SWR 端点

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `HUAWEICLOUD_SDK_SWR_ENDPOINT` | SWR（容器镜像仓库）端点 | `https://swr-api.{region}.myhuaweicloud.com` |

**配置示例：**

```bash
export HUAWEICLOUD_SDK_SWR_ENDPOINT="https://swr-api.cn-north-4.myhuaweicloud.com"
```

### Agent Identity 端点

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `HUAWEICLOUD_SDK_AGENTIDENTITY_ENDPOINT` | Agent Identity 服务端点 | `https://agent-identity.{region}.myhuaweicloud.com` |

**配置示例：**

```bash
export HUAWEICLOUD_SDK_AGENTIDENTITY_ENDPOINT="https://agent-identity.cn-north-4.myhuaweicloud.com"
```

---

## 其他配置

### SDK 日志级别

用于控制 SDK 的日志输出级别：

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `AGENTARTS_LOG_LEVEL` | SDK 日志级别 | `INFO` |

**可选值：** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**配置示例：**

```bash
# 开启详细日志（调试模式）
export AGENTARTS_LOG_LEVEL="DEBUG"

# 只显示警告及以上级别的日志
export AGENTARTS_LOG_LEVEL="WARNING"
```

**代码配置方式：**

```python
from agentarts.sdk.utils.logging import setup_logging

# 设置日志级别
setup_logging(level="DEBUG")

# 或使用环境变量（自动读取 AGENTARTS_LOG_LEVEL）
setup_logging()

# 自定义日志输出到文件
import logging
setup_logging(
    level="DEBUG",
    handler=logging.FileHandler("/var/log/agentarts/app.log")
)
```

### Python 基础镜像

用于指定 Agent 部署时的 Python 基础镜像：

| 环境变量 | 说明 |
|----------|------|
| `PYTHON_BASE_IMAGE` | Python 基础镜像名称 |

**配置示例：**

```bash
export PYTHON_BASE_IMAGE="python:3.11-slim"
```

---

## 环境变量优先级说明

### 端点配置优先级

对于各服务端点，SDK 按以下优先级确定最终使用的端点：

1. **环境变量**（最高优先级）- 如 `AGENTARTS_MEMORY_DATA_ENDPOINT`
2. **代码参数** - 如 `MemoryClient(endpoint="...")`
3. **默认值**（最低优先级）- SDK 内置的默认端点

### 区域配置优先级

区域配置按以下优先级读取：

1. `HUAWEICLOUD_SDK_REGION`
2. `HUAWEICLOUD_REGION`
3. `OS_REGION_NAME`
4. 默认值 `cn-southwest-2`

---

## 配置示例

### 基础配置

```bash
# .env 文件示例

# 华为云认证
HUAWEICLOUD_SDK_AK=your-access-key
HUAWEICLOUD_SDK_SK=your-secret-key
HUAWEICLOUD_SDK_REGION=cn-north-4

# 项目 ID（可选）
HUAWEICLOUD_SDK_PROJECT_ID=your-project-id
```

### 完整配置

```bash
# .env 文件示例（完整配置）

# 华为云认证
HUAWEICLOUD_SDK_AK=your-access-key
HUAWEICLOUD_SDK_SK=your-secret-key
HUAWEICLOUD_SDK_SECURITY_TOKEN=your-security-token
HUAWEICLOUD_SDK_REGION=cn-north-4
HUAWEICLOUD_SDK_PROJECT_ID=your-project-id

# AgentArts 端点（可选，用于自定义端点）
AGENTARTS_CONTROL_ENDPOINT=https://agentarts.cn-north-4.myhuaweicloud.com
AGENTARTS_RUNTIME_DATA_ENDPOINT=https://your-runtime-endpoint.com
AGENTARTS_MEMORY_DATA_ENDPOINT=https://memory.cn-north-4.huaweicloud-agentarts.com
AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT=https://your-code-interpreter-endpoint.com

# 华为云服务端点（可选，用于自定义端点）
HUAWEICLOUD_SDK_IAM_ENDPOINT=https://iam.cn-north-4.myhuaweicloud.com
HUAWEICLOUD_SDK_SWR_ENDPOINT=https://swr-api.cn-north-4.myhuaweicloud.com
HUAWEICLOUD_SDK_AGENTIDENTITY_ENDPOINT=https://agent-identity.cn-north-4.myhuaweicloud.com

# 其他配置
PYTHON_BASE_IMAGE=python:3.11-slim
```

### 测试环境配置

```bash
# 测试环境示例

# 华为云认证
HUAWEICLOUD_SDK_AK=test-ak
HUAWEICLOUD_SDK_SK=test-sk
HUAWEICLOUD_SDK_REGION=cn-southwest-2

# 使用测试端点
AGENTARTS_MEMORY_DATA_ENDPOINT=https://memory-test.example.com
AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT=https://code-interpreter-test.example.com
```

---

## 常见问题

### Q1: 如何验证环境变量是否正确配置？

```python
from agentarts.sdk.utils.constant import get_ak, get_sk, get_region

print(f"AK: {get_ak()}")
print(f"SK: {get_sk()}")
print(f"Region: {get_region()}")
```

### Q2: 端点配置不生效怎么办？

检查：
1. 环境变量名称是否正确（注意大小写）
2. 环境变量是否已正确设置（重启终端或 IDE）
3. 是否有其他配置覆盖了环境变量

### Q3: 如何在代码中覆盖环境变量配置？

大多数 SDK 类支持通过参数直接指定配置：

```python
from agentarts.sdk.memory import MemoryClient

# 通过参数指定端点，优先级高于环境变量
client = MemoryClient(
    region_name="cn-north-4",
    endpoint="https://custom-endpoint.com"
)
```

### Q4: 临时安全令牌何时需要？

临时安全令牌（STS）通常用于：
- 临时授权场景
- 跨账号访问
- 安全性要求较高的场景

---

## 相关文档

- [Memory SDK 使用指南](memory_user_guide.md)
- [CodeInterpreter 使用指南](tools_user_guide.md)
- [Agent Identity 使用指南](agent_identity_guide.md)
- [Runtime 使用指南](runtime_user_guide.md)