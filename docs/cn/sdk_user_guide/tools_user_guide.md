# Tools 使用指导

## 概述
支持CodeInterpreter生命周期管理和Session生命周期管理
部分场景支持分页，以确保在处理大型响应时，能够快速且成功的返回结果
> **Note** This document is designed to instruct user how to ues AgentArts Tools using SDK

---

## 环境要求

- Python 3.10+
- 已安装 AgentArts SDK：`pip install agentarts-sdk`

## 认证配置

### 华为云 AK/SK 认证

CodeInterpreter SDK 使用华为云 AK/SK 进行身份认证。请通过以下方式配置：

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

### 会话认证方式

CodeInterpreter 会话使用 API Key 进行认证，可通过以下方式配置：

**方式一：环境变量配置（推荐）**

```bash
export HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY="your-api-key"
```

**方式二：代码中传递参数**

```python
# 在 start_session 中传递
client.start_session(
    code_interpreter_name="my-code-interpreter",
    session_name="my-session",
    api_key="your-api-key"
)

# 在 code_session 中传递
with code_session("cn-southwest-2", "my-code-interpreter", api_key="your-api-key") as client:
    client.execute_code("print('Hello')")
```

**注意**：如果代码解释器创建时使用了 `auth_type="IAM"`，则会话方法将自动使用 IAM 认证，无需传递 `api_key` 参数。

### 数据面端点配置

CodeInterpreter 数据面端点可以通过以下方式配置（按优先级排序）：

1. **环境变量**（最高优先级）：
   ```bash
   export AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT="https://your-data-endpoint"
   ```

2. **初始化参数**：
   ```python
   client = CodeInterpreter(
       region="cn-southwest-2",
       data_endpoint="https://your-data-endpoint"
   )
   ```

3. **默认值**：使用 SDK 内置的默认端点

---

## 快速开始

### 使用 code_session 上下文管理器（推荐）

`code_session` 是一个上下文管理器，自动管理会话的启动和停止，推荐用于大多数场景：

```python
from agentarts.sdk.tools import code_session

# 使用环境变量中的 API Key
with code_session("cn-southwest-2", "my-code-interpreter-name") as client:
    # 执行代码
    result = client.execute_code("print('Hello, World!')")
    print(result)
    
    # 执行命令
    result = client.execute_command("ls -la")
    
    # 上传文件
    client.upload_file("/home/user/data.csv", "col1,col2\n1,2\n3,4")
    
    # 下载文件
    content = client.download_file("/home/user/output.txt")

# 传入 API Key
with code_session("cn-southwest-2", "my-code-interpreter-name", api_key="your-api-key") as client:
    result = client.execute_code("import pandas as pd; print(pd.__version__)")
```

### 手动管理会话

如果需要更细粒度的控制，可以手动管理会话：

```python
from agentarts.sdk.tools import CodeInterpreter

# 创建客户端
client = CodeInterpreter(region="cn-southwest-2")

# 启动会话
session_id = client.start_session(
    code_interpreter_name="my-code-interpreter-name",
    session_name="my-session",
    api_key="your-api-key"  # 可选，不传则从环境变量读取
)

# 执行操作
result = client.execute_code("print('Hello')")

# 停止会话
client.stop_session()  # 可选
```

---

## 类名
CodeInterpreter

### 初始化

```python
CodeInterpreter(region: Optional[str] = None, data_endpoint: Optional[str] = None)
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| region | str | 否 | 从环境变量获取 | 华为云区域名称 |
| data_endpoint | str | 否 | 从环境变量获取 | 数据面端点，优先从环境变量 AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT 读取 |

**使用示例**：

```python
# 使用环境变量配置
client = CodeInterpreter(region="cn-southwest-2")

# 通过参数指定数据面端点
client = CodeInterpreter(
    region="cn-southwest-2",
    data_endpoint="https://your-custom-endpoint.com"
)

```

### 功能特性
- 管理CodeInterpreter实例
- 管理Session生命周期

### 属性
- control_plane_client: 控制面客户端
- data_plane_client: 数据面客户端

### 方法

#### 1. 创建代码解释器
**方法名** `create_code_interpreter`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|name |str| **Required**  代码解释器的名称，必须符合特定的命名规则|
|auth_type |str| 认证类型，支持 "API_KEY" 或 "IAM"，默认 "API_KEY"|
|api_key_name |str| API Key 的名称，当 auth_type 为 "API_KEY" 时必填|
|description |str| 代码解释器的描述信息, default: `None`|
|execution_agency_name |str| 执行机构的名称, default: `None`|
|observability |Dict| 可观测性配置，例如日志和监控设置, default: `None`|
|network_config |Dict| 网络配置，例如 VPC 和安全组设置, default: `None`|
|agent_gateway_id |str| 关联的 Agent Gateway ID, default: `None`|
|tags |List[Dict]| 标签列表，每个标签是一个包含 "key" 和 "value" 的字典, default: `None`|

**返回值**
包含代码解释器信息的字典，包括：
+ id(str): 代码解释器的ID
+ name(str): 代码解释器的名称
+ description(str): 代码解释器的描述信息
+ created_at(str): 代码解释器的创建时间
+ updated_at(str): 代码解释器的更新时间
+ execution_agency_name(str): IAM委托名
+ workload_identity(Dict): 工作负载认证信息
+ access_endpoint(str): 代码解释器的访问域名
+ observability(Dict): 可观测性配置(日志+指标)
+ tags(List[Dict]): 标签列表，每个标签是一个包含 "key" 和 "value" 的字典
+ network_config(Dict): 网络配置，例如 VPC 和安全组设置

**样例**
```python
# 使用 API Key 认证创建代码解释器
code_interpreter = client.create_code_interpreter(
    name="my-code-interpreter",
    auth_type="API_KEY",
    api_key_name="my-api-key-name"
)
code_interpreter_id = code_interpreter["id"]

# 使用 IAM 认证创建代码解释器
code_interpreter = client.create_code_interpreter(
    name="my-code-interpreter",
    auth_type="IAM"
)
```

#### 2. 查询代码解释器列表
**方法名** `list_code_interpreters`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|name |str| 根据名称模糊查询代码解释器列表, default: `None`|
|limit |int| 每页返回的代码解释器数量，默认10|
|offset |int| 分页偏移量，默认0|
|sort_key |str| 排序字段，必须是created_at或updated_at, default: `None`|
|sort_dir |str| 排序方向，必须是asc或desc, default: `None`|

**返回值**
包含代码解释器列表和分页信息的字典：
+ total_count(int): 符合查询条件的代码解释器总数
+ items(List[Dict]): 代码解释器列表

**样例**
```python
result = client.list_code_interpreters(
    name="my-code-interpreter",
    sort_key="created_at",
    sort_dir="asc"
)
```

#### 3. 更新代码解释器
**方法名** `update_code_interpreter`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|code_interpreter_id |str| **Required**  代码解释器的ID|
|observability |Dict| 可观测性配置(日志+指标)，可选|
|tags |List[Dict]| 标签列表，每个标签是一个包含 "key" 和 "value" 的字典，可选|

**返回值**
包含更新后代码解释器信息的字典：
+ id(str): 代码解释器的ID
+ name(str): 代码解释器的名称
+ description(str): 代码解释器的描述信息
+ created_at(str): 代码解释器的创建时间
+ updated_at(str): 代码解释器的更新时间
+ execution_agency_name(str): IAM委托名
+ agent_gateway_id(str): 代码解释器所属的智能体网关ID
+ workload_identity(Dict): 工作负载认证信息
+ access_endpoint(str): 代码解释器的访问域名
+ observability(Dict): 可观测性配置(日志+指标)
+ tags(List[Dict]): 标签列表，每个标签是一个包含 "key" 和 "value" 的字典

**样例**
```python
result = client.update_code_interpreter(
    code_interpreter_id="my-code-interpreter",
    observability=None,
    tags=[{"key": "env", "value": "dev"}]
)
```

#### 4. 获取代码解释器详情
**方法名** `get_code_interpreter`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|code_interpreter_id |str| **Required**  代码解释器的ID|

**返回值**
包含代码解释器详情的字典：
+ id(str): 代码解释器的ID
+ name(str): 代码解释器的名称
+ description(str): 代码解释器的描述信息
+ created_at(str): 代码解释器的创建时间
+ updated_at(str): 代码解释器的更新时间
+ execution_agency_name(str): IAM委托名
+ agent_gateway_id(str): 代码解释器所属的智能体网关ID
+ workload_identity(Dict): 工作负载认证信息
+ access_endpoint(str): 代码解释器的访问域名
+ observability(Dict): 可观测性配置(日志+指标)
+ tags(List[Dict]): 标签列表，每个标签是一个包含 "key" 和 "value" 的字典
+ auth_type(str): 工具认证方式
+ api_key_name(str): API Key名称
+ network_config(Dict): 网络配置，例如 VPC 和安全组设置

**样例**
```python
result = client.get_code_interpreter(
    code_interpreter_id="my-code-interpreter-id"
)
```

#### 5. 删除代码解释器
**方法名** `delete_code_interpreter`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|code_interpreter_id |str| **Required**  代码解释器的ID|

**样例**
```python
client.delete_code_interpreter(
    code_interpreter_id="my-code-interpreter-id"
)
```

#### 6. 启动代码解释器会话
**方法名** `start_session`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|code_interpreter_name |str| **Required**  代码解释器的名称，用于识别和管理会话，名称唯一|
|session_name |str|  **Required**  会话名称|
|api_key |str| 认证使用的API Key，如果代码解释器创建时使用 API_KEY 认证，则需要提供此参数；如果不提供则从环境变量HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY中获取；如果代码解释器创建时使用 IAM 认证，则无需提供此参数, default: `None`|
|session_timeout |int| 会话超时时间，单位为秒，默认15分钟，最小值为60秒，最大值为86400秒（24小时）, default: `900`|

**返回值**
session_id (str): 会话ID

**样例**
```python
# 使用环境变量中的 API Key（代码解释器创建时使用 API_KEY 认证）
session_id = client.start_session(
    code_interpreter_name="my-code-interpreter-name",
    session_name="my-session-name"
)

# 传入 API Key（代码解释器创建时使用 API_KEY 认证）
session_id = client.start_session(
    code_interpreter_name="my-code-interpreter-name",
    session_name="my-session-name",
    api_key="your-api-key"
)

# 代码解释器创建时使用 IAM 认证，无需传入 api_key
session_id = client.start_session(
    code_interpreter_name="my-code-interpreter-name",
    session_name="my-session-name"
)
```

#### 7. 获取代码解释器会话详情
**方法名** `get_session`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|code_interpreter_name |str| **Required**  代码解释器的名称，用于识别和管理会话，名称唯一|
|session_id |str| 会话ID，默认使用当前会话ID, default: `None`|
|api_key |str| 认证使用的API Key，如果代码解释器创建时使用 API_KEY 认证，则需要提供此参数；如果不提供则从环境变量HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY中获取；如果代码解释器创建时使用 IAM 认证，则无需提供此参数, default: `None`|

**返回值**
包含会话详情的字典：
+ code_interpreter_id(str): 代码解释器的ID
+ created_at(str): 会话的创建时间
+ session_name(str): 会话名称
+ session_id(str): 会话ID
+ session_timeout(int): 会话超时时间，单位为秒

**样例**
```python
# 使用环境变量中的 API Key（代码解释器创建时使用 API_KEY 认证）
session_info = client.get_session(
    code_interpreter_name="my-code-interpreter-name"
)

# 代码解释器创建时使用 IAM 认证，无需传入 api_key
session_info = client.get_session(
    code_interpreter_name="my-code-interpreter-name"
)
```

#### 8. 停止当前代码解释器会话
**方法名** `stop_session`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|api_key |str| 认证使用的API Key，如果代码解释器创建时使用 API_KEY 认证，则需要提供此参数；如果不提供则从环境变量HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY中获取；如果代码解释器创建时使用 IAM 认证，则无需提供此参数, default: `None`|

**返回值**
bool: 没有活跃会话时返回True，否则返回False

**样例**
```python
# 使用环境变量中的 API Key（代码解释器创建时使用 API_KEY 认证）
client.stop_session()

# 传入 API Key（代码解释器创建时使用 API_KEY 认证）
client.stop_session(api_key="your-api-key")

# 代码解释器创建时使用 IAM 认证，无需传入 api_key
client.stop_session()
```

#### 9. 调用代码解释器会话
**方法名** `invoke`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|operate_type |str| **Required**  调用方法名，"execute_code"或"execute_command"等|
|arguments |Dict| **Required**  调用参数，根据operate_type不同而不同|
|api_key |str| 认证使用的API Key，如果代码解释器创建时使用 API_KEY 认证，则需要提供此参数；如果不提供则从环境变量HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY中获取；如果代码解释器创建时使用 IAM 认证，则无需提供此参数, default: `None`|

**返回值**
result[Dict]: 包含调用结果的字典

**样例**
```python
# 使用环境变量中的 API Key（代码解释器创建时使用 API_KEY 认证）
result = client.invoke(
    operate_type="execute_code",
    arguments={
        "clear_context": False,
        "code": "print('Hello, World!')",
        "language": "python"
    }
)

# 代码解释器创建时使用 IAM 认证，无需传入 api_key
result = client.invoke(
    operate_type="execute_code",
    arguments={
        "clear_context": False,
        "code": "print('Hello, World!')",
        "language": "python"
    }
)
```

#### 10. 在代码解释器中执行代码
**方法名** `execute_code`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|code |str| **Required**  要执行的代码|
|language |str| 代码的语言，默认"python"，当前支持python, default: `"python"`|
|clear_context |bool| 是否在执行前清除上下文，默认False, default: `False`|

**返回值**
result[Dict]: 包含stdout， stderr， exitcode信息的字典

**样例**
```python
# 执行Python代码
result = client.execute_code('''
    import pandas as pd
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    print(df.describe())
''')

# 清除上下文
result = client.execute_code("x = 10", clear_context=True)
```

#### 11. 在代码解释器中执行命令
**方法名** `execute_command`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|command |str| **Required**  要执行的命令|

**返回值**
result[Dict]: 包含命令执行结果的字典

**样例**
```python
# 列出所有文件
result = client.execute_command("ls -la")

# 检查python版本
result = client.execute_command("python --version")
```

#### 12. 上传文件到代码解释器
**方法名** `upload_file`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|path |str| **Required**  文件路径，支持绝对路径和相对路径，必须以"/"开头，当前仅支持/home/user路径下文件上传|
|content |Union[str, bytes]| **Required**  文件内容，可以是字符串或二进制数据，二进制内容将被Base64编码|
|description |str| 文件描述，此字段可用于LLMs理解数据结构（例如： "CSV" with columns: data, revenue, product_id）, default: `""`|

**返回值**
result[Dict]: 包含文件上传结果的字典

**样例**
```python
# 上传CSV文件
result = client.upload_file(
    path="/home/user/my-file.csv",
    content="data, revenue\n2026-01-01, 1000\n2026-01-02, 2000",
    description='Daily sales data with columns: data, revenue'
)
```

#### 13. 上传多个文件到代码解释器
**方法名** `upload_files`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|files |List[Dict[str, str]]| **Required**  文件路径和内容的列表，每个文件包含"path"和"content"键
  - "path": 文件路径，支持绝对路径和相对路径，必须以"/"开头，当前仅支持/home/user路径下文件上传
  - "content": 文件内容（string 或 bytes）
  - "description": 文件描述，此字段可用于LLMs理解数据结构|

**返回值**
result[Dict]: 包含文件上传结果的字典

**样例**
```python
# 上传多个文件
result = client.upload_files([
    {"path": "/data.txt", "content": "Hello, World!"},
    {"path": "/home/user/my-binary-file", "content": b"123456"}
])
```

#### 14. 从代码解释器下载文件
**方法名** `download_file`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|path |str| **Required**  文件路径，必须以"/"开头，当前仅支持/home/user路径下文件下载|

**返回值**
content[Union[str, bytes]]: 文件内容, 文本文件或字节文件（图片，PDF等）

**样例**
```python
# 下载文件
content = client.download_file("/home/user/data.txt")
```

#### 15. 从代码解释器下载多个文件
**方法名** `download_files`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|paths |List[str]| **Required**  文件路径列表，每个路径必须以"/"开头，当前仅支持/home/user路径下文件下载|

**返回值**
files[Dict[str, Union[str, bytes]]]: 包含文件路径和内容的字典，键为文件路径，值为文件内容（文本或字节）

**样例**
```python
# 下载多个文件
files = client.download_files(["/home/user/data.txt", "/home/user/my-binary-file"])
```

#### 16. 在代码解释器中安装Python包
**方法名** `install_packages`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|packages |List[str]| **Required**  要安装的Python包列表，支持版本指定，如["requests", "numpy==1.24.3"]|
|upgrade |bool| 是否升级已安装的包，默认False, default: `False`|

**返回值**
result[Dict[str, Any]]: 包含命令执行结果的字典

**样例**
```python
# 安装多个Python包
result = client.install_packages(["requests", "numpy"])

# 安装指定版本的包
result = client.install_packages(["requests==2.26.0", "numpy==1.24.3"])

# 升级已安装的包
result = client.install_packages(["requests", "numpy"], upgrade=True)
```

#### 17. 清除代码解释器上下文
**方法名** `clear_context`

**返回值**
result[Dict[str, Any]]: 包含命令执行结果的字典

**样例**
```python
client.execute_code("x = 10")
client.execute_code("print(x)")
# 清除上下文
result = client.clear_context()
client.execute_code("print(x)")
```

###上下文管理器
**方法名** `code_session`

**参数**
| 参数名 | 类型 | 描述 |
| --- | --- | --- |
|region |str| **Required**  region名称，如"cn-southwest-2"|
|code_interpreter_name |str| **Required**  代码解释器名称|
|api_key |str| 认证使用的API Key，如果代码解释器创建时使用 API_KEY 认证，则需要提供此参数；如果不提供则从环境变量HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY中获取；如果代码解释器创建时使用 IAM 认证，则无需提供此参数, default: `None`|

**样例**
```python
# 使用环境变量中的 API Key（代码解释器创建时使用 API_KEY 认证）
with code_session("cn-southwest-2", "my-code-interpreter-name") as client:
    client.execute_code("print('Hello, World!')")

# 传入 API Key（代码解释器创建时使用 API_KEY 认证）
with code_session("cn-southwest-2", "my-code-interpreter-name", api_key="your-api-key") as client:
    client.execute_code("print('Hello, World!')")

# 代码解释器创建时使用 IAM 认证，无需传入 api_key
with code_session("cn-southwest-2", "my-code-interpreter-name") as client:
    client.execute_code("print('Hello, World!')")
```
