# Runtime SDK 用户指南

## 概述

AgentArts Runtime SDK 提供了将 Agent 封装为 HTTP/WebSocket 服务的能力。通过 `AgentArtsRuntimeApp` 类，您可以快速构建一个符合华为云 AgentArts 控制面标准的 Agent 服务。

### 核心组件

| 组件 | 说明 |
|------|------|
| `AgentArtsRuntimeApp` | ASGI 应用程序，提供 HTTP/WebSocket 服务端点 |
| `RequestContext` | 请求上下文数据模型，包含 session_id、request_id 等信息 |
| `AgentArtsRuntimeContext` | 全局上下文管理器，基于 contextvars 实现，支持异步安全访问 |

### 服务端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/invocations` | POST | Agent 调用入口 |
| `/ping` | GET | 健康检查端点 |
| `/ws` | WebSocket | 双向流式通信端点 |

## 环境要求

- Python 3.10+
- 支持 ASGI 服务器（uvicorn、hypercorn 等）

### 框架版本要求

使用可选框架依赖时，请确保满足以下最低版本要求：

| 框架 | 最低版本 | 安装命令 |
|------|----------|----------|
| LangGraph | 1.0.0 | `pip install huaweicloud-agentarts-sdk[langgraph]` |
| LangChain | 0.1.0 | `pip install huaweicloud-agentarts-sdk[langchain]` |
| langchain-core | 0.1.0 | 随 langgraph/langchain 自动安装 |

> **注意：** LangGraph 1.0+ 引入了新的 Checkpoint 格式，包含必需字段（`step`、`pending_sends`、`parents`）。SDK 的集成模块兼容 LangGraph 1.0 及以上版本。

## 快速开始

### 基本示例

```python
from agentarts.sdk import AgentArtsRuntimeApp, RequestContext

app = AgentArtsRuntimeApp()


@app.entrypoint
async def handler(payload: dict, context: RequestContext = None) -> dict:
    """Agent 入口函数"""
    message = payload.get("message", "")
    return {"response": f"Received: {message}"}


if __name__ == "__main__":
    app.run()
```

### 启动服务

```bash
# 使用 agentarts CLI
agentarts dev

# 或直接运行
python agent.py

# 或使用 uvicorn
uvicorn agent:app --host 0.0.0.0 --port 8080
```

## AgentArtsRuntimeApp 类

### 初始化参数

```python
app = AgentArtsRuntimeApp(
    debug=False,           # 调试模式
    lifespan=None,         # 生命周期管理
    middleware=None,       # 中间件列表
    protocol="http",       # 协议类型: "http" 或 "https"
    max_concurrency=15,    # 最大并发请求数
)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `debug` | `bool` | `False` | 调试模式 |
| `lifespan` | `Lifespan` | `None` | 生命周期管理 |
| `middleware` | `Sequence[Middleware]` | `None` | 中间件列表 |
| `protocol` | `"http"` \| `"https"` | `"http"` | 协议类型 |
| `max_concurrency` | `int` | `15` | 最大并发请求数，超出返回 503 错误 |

### run() 方法

启动 ASGI 服务器：

```python
app.run(host="0.0.0.0", port=8080)
```

参数说明：
- `host`: 绑定地址，默认在 Docker 环境中为 `0.0.0.0`，本地为 `127.0.0.1`
- `port`: 绑定端口，默认 `8080`
- `**kwargs`: 传递给 uvicorn 的其他参数

## 装饰器

### @app.entrypoint

注册 Agent 主入口函数，处理 `/invocations` 端点的请求。

#### 基本用法

```python
@app.entrypoint
def handler(payload: dict) -> dict:
    """同步处理函数"""
    return {"result": payload["message"].upper()}


@app.entrypoint
async def async_handler(payload: dict) -> dict:
    """异步处理函数"""
    result = await some_async_operation(payload)
    return result
```

#### 使用请求上下文

```python
@app.entrypoint
async def handler(payload: dict, context: RequestContext = None) -> dict:
    """带上下文的处理函数"""
    session_id = context.session_id if context else None
    request_id = context.request_id if context else None
    
    return {
        "response": "OK",
        "session_id": session_id,
        "request_id": request_id,
    }
```

#### 流式响应

返回生成器以实现流式输出（SSE 格式）：

```python
@app.entrypoint
async def streaming_handler(payload: dict) -> AsyncGenerator:
    """流式响应处理函数"""
    message = payload.get("message", "")
    
    for char in message:
        await asyncio.sleep(0.1)
        yield {"chunk": char}


@app.entrypoint
def sync_streaming_handler(payload: dict) -> Generator:
    """同步流式响应"""
    for i in range(10):
        yield {"count": i}
```

### @app.ping

注册健康检查处理函数，处理 `/ping` 端点的请求。

```python
from agentarts.sdk.runtime.model import PingStatus


@app.ping
def health_check() -> PingStatus:
    """自定义健康检查"""
    if is_healthy():
        return PingStatus.HEALTHY
    else:
        return PingStatus.UNHEALTHY
```

#### PingStatus 状态值

| 状态 | 说明 |
|------|------|
| `HEALTHY` | 服务健康，无正在执行的任务 |
| `HEALTHY_BUSY` | 服务健康，有任务正在执行 |
| `UNHEALTHY` | 服务不健康 |

#### 强制设置状态

```python
# 设置维护模式
app.force_ping_status(PingStatus.UNHEALTHY)

# 恢复正常
app.force_ping_status(None)
```

### @app.websocket

注册 WebSocket 处理函数，处理 `/ws` 端点的连接。

```python
from starlette.websockets import WebSocket


@app.websocket
async def ws_handler(websocket: WebSocket, context: RequestContext = None):
    """WebSocket 处理函数"""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            response = await process_message(data)
            await websocket.send_json(response)
    except WebSocketDisconnect:
        print("Client disconnected")
```

#### WebSocket 示例：聊天应用

```python
@app.websocket
async def chat_handler(websocket: WebSocket, context: RequestContext = None):
    await websocket.accept()
    session_id = context.session_id if context else "default"
    
    try:
        while True:
            message = await websocket.receive_text()
            response = await agent.chat(session_id, message)
            await websocket.send_text(response)
    except WebSocketDisconnect:
        await agent.end_session(session_id)
```

### @app.async_task

注册异步后台任务，任务执行状态会被自动追踪。

```python
@app.async_task
async def background_job(payload: dict):
    """后台异步任务"""
    await asyncio.sleep(10)
    result = await process_data(payload)
    return result


@app.entrypoint
async def handler(payload: dict, context: RequestContext = None):
    # 启动后台任务
    asyncio.create_task(background_job(payload))
    
    # 检查是否有运行中的任务
    if app.has_running_tasks():
        print("有后台任务正在执行")
    
    return {"status": "accepted"}
```

## RequestContext

`RequestContext` 是请求数据的不可变快照，包含请求的元信息。

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `request_id` | `Optional[str]` | 请求唯一标识符 |
| `session_id` | `Optional[str]` | 会话标识符 |
| `request` | `Optional[Any]` | 原始请求对象 |

### 使用示例

```python
@app.entrypoint
async def handler(payload: dict, context: RequestContext = None):
    if context:
        print(f"Request ID: {context.request_id}")
        print(f"Session ID: {context.session_id}")
        
        # 访问原始请求对象
        if context.request:
            headers = context.request.headers
            client_host = context.request.client.host
    
    return {"status": "ok"}
```

## AgentArtsRuntimeContext

`AgentArtsRuntimeContext` 是全局上下文管理器，基于 Python 的 `contextvars` 实现，支持异步安全的上下文访问。

### 核心特性

- **协程安全**: 每个异步任务都有独立的上下文视图
- **全局访问**: 在调用栈的任何位置都可以访问上下文数据
- **无需实例化**: 直接使用类方法访问

### 可用方法

| 方法 | 说明 |
|------|------|
| `get_session_id()` | 获取会话 ID |
| `set_session_id(value)` | 设置会话 ID |
| `get_request_id()` | 获取请求 ID |
| `set_request_id(value)` | 设置请求 ID |
| `get_user_id()` | 获取用户 ID |
| `set_user_id(value)` | 设置用户 ID |
| `get_workload_access_token()` | 获取工作负载访问令牌 |
| `set_workload_access_token(value)` | 设置工作负载访问令牌 |
| `get_user_token()` | 获取用户令牌 |
| `set_user_token(value)` | 设置用户令牌 |
| `get_oauth2_callback_url()` | 获取 OAuth2 回调 URL |
| `set_oauth2_callback_url(value)` | 设置 OAuth2 回调 URL |
| `clear()` | 清除所有上下文变量 |

### 使用示例

```python
from agentarts.sdk.runtime.context import AgentArtsRuntimeContext


@app.entrypoint
async def handler(payload: dict, context: RequestContext = None):
    # 方式一：通过 context 参数获取
    session_id = context.session_id if context else None
    
    # 方式二：通过全局上下文获取
    session_id = AgentArtsRuntimeContext.get_session_id()
    request_id = AgentArtsRuntimeContext.get_request_id()
    user_id = AgentArtsRuntimeContext.get_user_id()
    
    # 在深层调用中使用
    result = await process_with_context()
    
    return {"session_id": session_id}


async def process_with_context():
    """在任意函数中访问上下文"""
    session_id = AgentArtsRuntimeContext.get_session_id()
    # 使用 session_id 进行业务处理
    return {"processed": True, "session": session_id}
```

### OAuth2 集成示例

```python
@app.entrypoint
async def oauth_handler(payload: dict, context: RequestContext = None):
    # 获取用户令牌
    user_token = AgentArtsRuntimeContext.get_user_token()
    
    if not user_token:
        # 设置 OAuth2 回调 URL
        AgentArtsRuntimeContext.set_oauth2_callback_url("https://my-app/callback")
        return {"status": "authorization_required"}
    
    # 使用用户令牌调用 API
    result = await call_api_with_token(user_token)
    return result
```

## 完整示例

### LangGraph Agent

```python
import os
import asyncio
from typing import Dict, Any, TypedDict, Annotated
from operator import add

from agentarts.sdk import AgentArtsRuntimeApp, RequestContext
from agentarts.sdk.runtime.context import AgentArtsRuntimeContext

app = AgentArtsRuntimeApp()


class State(TypedDict):
    messages: Annotated[list, add]
    query: str
    response: str


class LangGraphAgent:
    def __init__(self):
        self.model_name = os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini")
        self._graph = None

    def _build_graph(self):
        from langgraph.graph import StateGraph, END
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, AIMessage

        llm = ChatOpenAI(
            model=self.model_name,
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL"),
        )

        async def process_node(state: State) -> Dict[str, Any]:
            query = state.get("query", "")
            messages = state.get("messages", []) or [HumanMessage(content=query)]
            response = await llm.ainvoke(messages)
            return {
                "messages": [AIMessage(content=response.content)],
                "response": response.content,
            }

        workflow = StateGraph(State)
        workflow.add_node("process", process_node)
        workflow.set_entry_point("process")
        workflow.add_edge("process", END)
        return workflow.compile()

    async def run(self, query: str, session_id: str = None) -> Dict[str, Any]:
        graph = self._graph or self._build_graph()
        self._graph = graph
        result = await graph.ainvoke({
            "messages": [],
            "query": query,
            "response": ""
        })
        return {"response": result.get("response", "")}


_agent = LangGraphAgent()


@app.entrypoint
async def handler(payload: Dict[str, Any], context: RequestContext = None) -> Dict[str, Any]:
    query = payload.get("message", "")
    session_id = AgentArtsRuntimeContext.get_session_id()
    return await _agent.run(query, session_id)


@app.ping
def health_check():
    from agentarts.sdk.runtime.model import PingStatus
    return PingStatus.HEALTHY


if __name__ == "__main__":
    app.run()
```

### 流式输出 Agent

```python
import asyncio
from typing import AsyncGenerator
from agentarts.sdk import AgentArtsRuntimeApp, RequestContext

app = AgentArtsRuntimeApp()


@app.entrypoint
async def streaming_handler(payload: dict, context: RequestContext = None) -> AsyncGenerator:
    """流式输出示例"""
    message = payload.get("message", "")
    words = message.split()
    
    for i, word in enumerate(words):
        await asyncio.sleep(0.1)
        yield {
            "chunk": word,
            "index": i,
            "total": len(words),
        }
```

### WebSocket Agent

```python
from starlette.websockets import WebSocket
from agentarts.sdk import AgentArtsRuntimeApp, RequestContext
from agentarts.sdk.runtime.context import AgentArtsRuntimeContext

app = AgentArtsRuntimeApp()
sessions = {}


@app.websocket
async def ws_handler(websocket: WebSocket, context: RequestContext = None):
    await websocket.accept()
    session_id = context.session_id if context else "default"
    
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            
            # 处理消息
            response = await process_message(session_id, message)
            
            await websocket.send_json({
                "response": response,
                "session_id": session_id,
            })
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if session_id in sessions:
            del sessions[session_id]


async def process_message(session_id: str, message: str) -> str:
    return f"Echo: {message}"
```

## 注意事项

1. **并发限制**: 默认最大并发请求数为 15，可通过 `max_concurrency` 参数配置，超出返回 503 错误
2. **上下文隔离**: 每个请求的上下文相互隔离，不会互相干扰
3. **流式响应**: 流式输出使用 SSE (Server-Sent Events) 格式
4. **健康检查**: 建议实现自定义健康检查逻辑，特别是有状态 Agent
5. **WebSocket 生命周期**: 需要自行处理连接的 accept、receive、send、close
