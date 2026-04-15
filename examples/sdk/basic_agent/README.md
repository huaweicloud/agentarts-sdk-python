# Basic Agent Example

最简单的 Agent 示例，展示如何使用 AgentArts SDK 创建一个基础 Agent。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行 Agent
python agent.py
```

## 测试

```bash
# 健康检查
curl http://localhost:8080/ping

# 调用 Agent
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, Agent!"}'
```

## 端点说明

- `POST /invocations` - 调用 Agent 入口点
- `GET /ping` - 健康检查端点

## 代码结构

```python
from agentarts.sdk import AgentArtsRuntimeApp

app = AgentArtsRuntimeApp()

@app.entrypoint
def handler(payload: dict):
    # 处理请求
    return {"response": "..."}

@app.ping
def health_check():
    return "healthy"

if __name__ == "__main__":
    handler.run(host="0.0.0.0", port=8080)
```

## 部署

使用 AgentArts Toolkit 部署：

```bash
# 初始化配置
agentarts init --name basic-agent --template basic

# 本地开发
agentarts dev

# 云端部署
agentarts deploy --mode cloud
```