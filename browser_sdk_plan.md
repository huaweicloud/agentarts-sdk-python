# Browser 工具 SDK 实现方案

## 一、架构概览

Browser 工具与 Code Interpreter 并行，采用相同的分层架构：

```
用户代码
  ↓
Browser / browser_session          ← SDK 用户入口 (新增)
  ↓
ControlBrowserHttpClient           ← 控制面 HTTP (新增，放入 tools_http.py)
DataBrowserHttpClient              ← 数据面 HTTP (新增，放入 tools_http.py)
  ↓
华为云 Browser 沙箱 API
```

设计原则：
- 与 Code Interpreter 平级、独立，互不耦合
- HTTP 客户端放在同一个 `tools_http.py`，共享 `BaseHTTPClient` / `ToolsAPIError`，但各用各的类
- 现有 Code Interpreter 代码一行不动

---

## 二、Browser 控制面 API 全览

### 2.1 Browser 资源 CRUD

**create_browser(name, auth_type, api_key_name, description, execution_agency_name, observability, network_config, agent_gateway_id, tags) -> dict**

- `name`: `^[a-z][a-z0-9-]{0,38}[a-z0-9]$`（2-40 字符）
- `auth_type`: "API_KEY" / "IAM"
- `api_key_name`: API_KEY 模式必填，`^[a-zA-Z0-9_-]{1,64}$`
- `description`: 最长 4096 字符
- `execution_agency_name`: IAM 委托名称，1-64 字符
- `observability`: `{logs: {enabled, group_id, stream_id}, metrics: {enabled, instance_id}, tracing: {enabled, service_group}}`
- `network_config`: `{network_mode: "PUBLIC"/"VPC", vpc_config: {vpc_id, subnet_id, security_group_ids}}`
- `agent_gateway_id`: UUID
- `tags`: 最多 20 个 `{key, value}`，key 唯一

**返回**: `{id, name, description, auth_type, api_key_name, execution_agency_name, agent_gateway_id, observability, network_config, workload_identity: {urn}, access_endpoint, tags, created_at, updated_at}`

---

**list_browsers(name, offset, limit, sort_key, sort_dir, tag_key_exists, tag_key_matches, tag_value_matches, tag_match_policy) -> dict**

- `name`: 过滤名称，2-40 字符
- `offset`/`limit`: 分页
- `sort_key`: "created_at" / "updated_at"
- `sort_dir`: "asc" / "desc"
- `tag_*`: 标签过滤，`tag_key_matches` 必须与 `tag_value_matches` 配对使用
- `tag_match_policy`: "ALL" / "ANY"，仅标签过滤时生效

**返回**: `{items: [...], total_count}`

---

**get_browser(browser_id) -> dict**

- `browser_id`: UUID 格式

**返回**: 同 create 返回结构

---

**update_browser(browser_id, observability, tags) -> dict**

- 仅支持更新 `observability` 和 `tags`（不可修改 name/description/auth_type 等）
- `browser_id`: UUID 格式

**返回**: `{id, name, description, execution_agency_name, observability, workload_identity, access_endpoint, tags, created_at, updated_at, updated_by}`

---

**delete_browser(browser_id) -> bool**

- `browser_id`: UUID 格式
- 返回 True（HTTP 204）

---

### 2.2 Browser Profile 子资源 CRUD

Profile 是 Browser 下的独立子资源，用于持久化浏览器状态（cookie、localStorage 等）。

**create_browser_profile(name, description, tags) -> dict**

- `name`: `^[a-z][a-z0-9-]{0,38}[a-z0-9]$`
- `description`: 最长 4096 字符
- `tags`: 最多 20 个

**返回**: `{id, name, description, last_saved_browser_id, last_saved_browser_session_id, last_saved_at, tags, created_at}`

---

**list_browser_profiles(name, offset, limit, sort_key, sort_dir, tag_*) -> dict**

- 参数和 list_browsers 一致（分页、排序、标签过滤）
- `sort_key` 同样支持 "created_at" / "updated_at"

**返回**: `{items: [...], total_count}`

---

**get_browser_profile(profile_id) -> dict**

- `profile_id`: UUID 格式

**返回**: 同 create_profile 返回结构

---

**delete_browser_profile(profile_id) -> bool**

- `profile_id`: UUID 格式
- 返回 True（HTTP 204）

---

### 2.3 数据面（Session + 操作）

数据面接口对标 Code Interpreter 模式，包含：

- `start_session(browser_name, session_name, api_key)` -> 返回 session_id + stream 端点
- `stop_session(api_key)` -> 停止会话
- `get_session(api_key)` -> 查询会话状态
- `invoke(operate_type, arguments, api_key)` -> 核心派发，所有浏览器操作走这个入口
- `update_stream(...)` -> 更新 stream 端点
  - 对应 DataBrowserHttpClient 的 `update_stream` 方法
  - Browser 类暴露为 `update_automation_stream` 和 `update_live_view_stream` 两个便捷方法

Stream 端点（由 start_session 返回，缓存在 Browser 实例上）：
- `automation_endpoint` — 浏览器自动化 stream
- `live_view_endpoint` — 实时画面 stream

---

## 三、文件改动清单

### 新增文件 (3)

| # | 路径 | 说明 |
|---|------|------|
| 1 | `src/agentarts/sdk/tools/browser/__init__.py` | 导出 `Browser`, `browser_session` |
| 2 | `src/agentarts/sdk/tools/browser/browser_client.py` | `Browser` 类 + `browser_session` 上下文管理器 |
| 3 | `tests/unit/sdk/tools/test_browser_client.py` | 单元测试 |

### 修改文件 (4)

| # | 路径 | 改动 |
|---|------|------|
| 4 | `src/agentarts/sdk/service/tools_http.py` | **追加** `ControlBrowserHttpClient` + `DataBrowserHttpClient`（不动现有类） |
| 5 | `src/agentarts/sdk/utils/constant.py` | **追加** `ENV_AGENTARTS_BROWSER_DATA_ENDPOINT` 常量 + `get_browser_data_plane_endpoint()` 函数 |
| 6 | `src/agentarts/sdk/tools/__init__.py` | **追加** `Browser`, `browser_session` 导出 |
| 7 | `src/agentarts/sdk/__init__.py` | **追加** 顶层导出 |

---

## 四、各文件详细设计

### 4.1 `tools_http.py` — 新增两个 HTTP 客户端类

文件末尾追加。类名：`ControlBrowserHttpClient` / `DataBrowserHttpClient`。

#### ControlBrowserHttpClient

```python
class ControlBrowserHttpClient(BaseHTTPClient):
    """Browser 控制面 — AK/SK 签名"""

    def __init__(self, region_name, endpoint_url, verify_ssl=True):
        # open_ak_sk=True，与 ControlToolsHttpClient 结构一致

    # Browser 资源
    def create_browser(self, request_params: dict)         # POST   /v1/core/browsers
    def list_browsers(self, request_params: dict)          # GET    /v1/core/browsers
    def update_browser(self, browser_id, request_params)   # PUT    /v1/core/browsers/{id}
    def get_browser(self, browser_id)                      # GET    /v1/core/browsers/{id}
    def delete_browser(self, browser_id)                   # DELETE /v1/core/browsers/{id}

    # Browser Profile 子资源
    def create_browser_profile(self, request_params)       # POST   /v1/core/browser-profiles
    def list_browser_profiles(self, request_params)        # GET    /v1/core/browser-profiles
    def get_browser_profile(self, profile_id)              # GET    /v1/core/browser-profiles/{id}
    def delete_browser_profile(self, profile_id)           # DELETE /v1/core/browser-profiles/{id}
```

#### DataBrowserHttpClient

```python
class DataBrowserHttpClient(BaseHTTPClient):
    """Browser 数据面 — IAM(V11签名) 或 API_KEY(Bearer token)"""

    def __init__(self, region_name, endpoint_url, auth_type="API_KEY", verify_ssl=True)

    # Session
    def start_session(self, browser_name, request_params, api_key=None)
        # PUT  /v1/browsers/{name}/sessions-start
        # Header: Authorization: Bearer <api_key>

    def stop_session(self, browser_name, session_id, api_key=None)
        # PUT  /v1/browsers/{name}/sessions-stop
        # Header: x-HW-Agentarts-Browser-Session-Id

    def get_session(self, browser_name, session_id, api_key=None)
        # GET  /v1/browsers/{name}/sessions-get
        # Header: x-HW-Agentarts-Browser-Session-Id

    def invoke(self, browser_name, session_id, arguments, api_key=None)
        # POST /v1/browsers/{name}/invoke
        # Header: x-HW-Agentarts-Browser-Session-Id

    def update_stream(self, browser_name, session_id, arguments, api_key=None)
        # PUT  /v1/browsers/{name}/sessions-update
        # Header: x-HW-Agentarts-Browser-Session-Id
```

**与 Code Interpreter 的差异对照**：

| 项 | Code Interpreter | Browser |
|----|------------------|---------|
| 控制面路径 | `/v1/core/code-interpreters/` | `/v1/core/browsers/` |
| Profile 路径 | 无 | `/v1/core/browser-profiles/` |
| 数据面路径 | `/v1/code-interpreters/{name}/` | `/v1/browsers/{name}/` |
| Session Header | `x-HW-Agentarts-Code-Interpreter-Session-Id` | `x-HW-Agentarts-Browser-Session-Id` |
| 数据面环境变量 | `AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT` | `AGENTARTS_BROWSER_DATA_ENDPOINT` |

---

### 4.2 `constant.py` — 新增 Browser 端点

```python
# 已有（步骤一完成）
ENV_AGENTARTS_BROWSER_DATA_ENDPOINT = "AGENTARTS_BROWSER_DATA_ENDPOINT"

def get_browser_data_plane_endpoint(endpoint: str | None = None) -> str:
    """优先级: env AGENTARTS_BROWSER_DATA_ENDPOINT > 参数 > RUNTIME_DATA_ENDPOINT 兜底"""
```

---

### 4.3 `browser_client.py` — Browser 核心客户端

#### 导入

```python
from agentarts.sdk.service.tools_http import (
    ControlBrowserHttpClient,
    DataBrowserHttpClient,
)
from agentarts.sdk.utils.constant import (
    get_control_plane_endpoint,
    get_region,
)
```

#### Browser 类

**构造函数 `__init__(self, region, data_endpoint=None, auth_type="API_KEY", verify_ssl=True)`**

- 创建 `ControlBrowserHttpClient`（控制面，AK/SK）
- 创建 `DataBrowserHttpClient`（数据面，IAM 或 API_KEY）
- 端点优先级：`data_endpoint` 参数 > 环境变量 `AGENTARTS_BROWSER_DATA_ENDPOINT`
- 缓存属性：`_browser_name`, `_session_id`, `_automation_endpoint`, `_live_view_endpoint`

**属性**

| 属性 | 类型 | 说明 |
|------|------|------|
| `browser_name` | `str \| None` | 当前会话的 Browser 名称 |
| `session_id` | `str \| None` | 当前会话 ID |
| `automation_endpoint` | `str \| None` | 自动化 Stream 端点（start_session 后设置） |
| `live_view_endpoint` | `str \| None` | 实时画面 Stream 端点（start_session 后设置） |

**控制面方法**

| 方法 | 参数 | 说明 |
|------|------|------|
| `create_browser` | name, auth_type, api_key_name, description, execution_agency_name, observability, network_config, agent_gateway_id, tags | 创建 Browser 资源，含参数校验 |
| `list_browsers` | name, offset, limit, sort_key, sort_dir, tag_key_exists, tag_key_matches, tag_value_matches, tag_match_policy | 列表查询 + 标签过滤 |
| `get_browser` | browser_id (UUID) | 获取详情 |
| `update_browser` | browser_id, observability, tags | 更新（仅 observability + tags） |
| `delete_browser` | browser_id (UUID) | 删除，返回 True |

**Profile 子资源方法**

| 方法 | 参数 | 说明 |
|------|------|------|
| `create_browser_profile` | name, description, tags | 创建 Profile |
| `list_browser_profiles` | name, offset, limit, sort_key, sort_dir, tag_* | 列表查询 |
| `get_browser_profile` | profile_id (UUID) | 获取详情 |
| `delete_browser_profile` | profile_id (UUID) | 删除，返回 True |

**数据面方法**（待实现）

| 方法 | 说明 |
|------|------|
| `start_session(browser_name, session_name, api_key)` | 启动会话，缓存 session_id 和 stream 端点 |
| `stop_session(api_key)` | 停止当前会话 |
| `get_session(api_key)` | 查询会话状态 |
| `invoke(operate_type, arguments, api_key)` | 核心派发方法，所有浏览器操作走这个入口 |
| `update_automation_stream(api_key)` | 更新自动化 Stream |
| `update_live_view_stream(api_key)` | 更新实时画面 Stream |

**参数校验逻辑**

- `name` 格式：`^[a-z][a-z0-9-]{0,38}[a-z0-9]$`（browser 和 profile 共用）
- `auth_type` 仅允许 "API_KEY" / "IAM"
- `api_key_name` 格式：`^[a-zA-Z0-9_-]{1,64}$`，API_KEY 模式必填
- `description` 最长 4096 字符
- `browser_id` / `profile_id`：UUID 格式
- `tags`：最多 20 个，key 唯一
- `sort_key` 仅 "created_at" / "updated_at"
- `sort_dir` 仅 "asc" / "desc"
- `tag_match_policy` 仅 "ALL" / "ANY"
- tag 过滤数组：最多 10 项，项唯一
- `tag_key_matches` 和 `tag_value_matches` 必须配对使用，长度一致

#### browser_session 上下文管理器（待实现）

```python
@contextmanager
def browser_session(region, browser_name, auth_type="API_KEY", api_key=None, verify_ssl=True):
    client = Browser(region, auth_type=auth_type, verify_ssl=verify_ssl)
    client.start_session(browser_name=browser_name, api_key=api_key)
    try:
        yield client
    finally:
        client.stop_session(api_key=api_key)
```

---

### 4.4 导出链

```
sdk/tools/browser/__init__.py   →  from .browser_client import Browser, browser_session
sdk/tools/__init__.py           →  from .browser import Browser, browser_session
sdk/__init__.py                 →  from agentarts.sdk.tools import Browser, browser_session
```

最终用法：

```python
from agentarts.sdk import Browser, browser_session

# 控制面 — 管理资源
client = Browser(region="cn-southwest-2")
client.create_browser(name="my-browser", auth_type="API_KEY", api_key_name="my-key")
client.list_browsers()
client.create_browser_profile(name="my-profile")

# 数据面 — 执行操作
with browser_session("cn-southwest-2", "my-browser") as b:
    b.invoke("navigate", {"url": "https://example.com"})
    b.invoke("get_content", {})
```

---

## 五、与 Code Interpreter 的结构对照

```
tools_http.py                              constant.py
├── ControlToolsHttpClient    (不动)       ├── CI 端点常量          (不动)
├── DataToolsHttpClient       (不动)       ├── CI 端点函数          (不动)
├── ControlBrowserHttpClient  (新增)       ├── Browser 端点常量      (新增)
└── DataBrowserHttpClient     (新增)       └── Browser 端点函数      (新增)

code_interpreter/                          browser/ (新增)
├── __init__.py                            ├── __init__.py
└── code_interpreter_client.py             └── browser_client.py
    ├── CodeInterpreter                        ├── Browser
    ├── create/list/get/update/delete          ├── create/list/get/update/delete (Browser)
    ├── start/stop/get_session                 ├── create/list/get/delete (Profile)
    ├── invoke                                ├── start/stop/get_session
    ├── execute_code/command/                  ├── invoke
    │   upload/download/install/clear          ├── update_automation/live_view_stream
    └── code_session                           └── browser_session
```

关键差异：Browser 多了 Profile 子资源管理 + Stream 端点管理，少了代码解释器的 execute_code/upload/download 等具体操作封装（这些在 Browser 中通过 `invoke(operate_type, args)` 调用，不封装便捷方法）。

---

## 六、不改动的文件

以下文件保持不变：

- `src/agentarts/sdk/tools/code_interpreter/` — 所有文件
- `src/agentarts/sdk/service/tools_http.py` — `ControlToolsHttpClient` 和 `DataToolsHttpClient` 的现有代码
- `src/agentarts/sdk/service/http_client.py` — 基础 HTTP 客户端
- `src/agentarts/sdk/runtime/` — 运行时模块
- `src/agentarts/toolkit/` — CLI 工具层

---

## 七、实现状态

| 步骤 | 内容 | 状态 |
|------|------|------|
| 1 | `constant.py` — Browser 端点常量和函数 | 已完成 |
| 2 | `tools_http.py` — `ControlBrowserHttpClient` + `DataBrowserHttpClient` | 待实现 |
| 3 | `browser_client.py` — `Browser` 类控制面部分（CRUD + Profile） | 已完成 |
| 4 | `browser_client.py` — Browser 类数据面部分（session + invoke + stream） | 待实现 |
| 5 | `browser_client.py` — `browser_session` 上下文管理器 | 待实现 |
| 6 | `browser/__init__.py` — 导出 | 已完成 |
| 7 | `tools/__init__.py` — 上层导出 | 待实现 |
| 8 | `sdk/__init__.py` — 顶层导出 | 待实现 |
| 9 | `test_browser_client.py` — 单元测试 | 待实现 |

---

## 八、环境变量汇总

| 变量 | 用途 |
|------|------|
| `AGENTARTS_CONTROL_ENDPOINT` | 控制面端点（Browser 和 CI 共用） |
| `AGENTARTS_BROWSER_DATA_ENDPOINT` | Browser 数据面端点（新增） |
| `AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT` | Code Interpreter 数据面端点（已有） |
| `AGENTARTS_RUNTIME_DATA_ENDPOINT` | 通用兜底端点（已有） |
| `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` | AK/SK 认证（已有） |
| `HUAWEICLOUD_SDK_BROWSER_API_KEY` | Browser 数据面 API Key |
