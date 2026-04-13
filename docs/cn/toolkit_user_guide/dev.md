# dev 命令使用文档

## 命令用途

`dev` 命令用于在本地启动开发服务器，方便开发者快速测试和调试 Agent 应用。支持热重载、自定义端口和环境变量配置。

## 参数解释

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--port` | `-p` | 服务器端口 | `8080` |
| `--host` | `-h` | 服务器主机地址 | `0.0.0.0` |
| `--reload` | - | 启用热重载（代码变更自动重启） | `False` |
| `--config` | `-c` | 配置文件路径 | `.agentarts_config.yaml` |
| `--env` | `-e` | 环境变量（格式：KEY=VALUE），可多次使用 | 从配置文件读取 |

## 环境变量配置

### 方式一：命令行参数

使用 `--env` 或 `-e` 参数直接传递环境变量：

```bash
agentarts dev --env OPENAI_API_KEY=sk-xxx --env OPENAI_MODEL_NAME=gpt-4o
```

### 方式二：配置文件

在 `.agentarts_config.yaml` 中配置环境变量：

```yaml
runtime:
  environment_variables:
    - key: OPENAI_API_KEY
      value: "your-api-key"
    - key: OPENAI_MODEL_NAME
      value: "gpt-4o-mini"
    - key: OPENAI_BASE_URL
      value: ""
```

### 优先级

命令行 `--env` 参数优先级高于配置文件，相同变量会使用命令行传入的值。

## 执行效果

启动开发服务器后，会显示以下信息：

```
╭──────────────────────────────────────────────────────────────────────────────╮
│ Development Server                                                            │
│ Host: 0.0.0.0                                                                 │
│ Port: 8080                                                                    │
│ Config: .agentarts_config.yaml                                                │
│ Entrypoint: agent:create_app                                                  │
│ Auto-reload: enabled                                                          │
│ Environment Variables:                                                        │
│   OPENAI_API_KEY=sk-xxxx****xxxx (CLI)                                        │
│   OPENAI_MODEL_NAME=gpt-4o (CLI)                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

Invocation Endpoint: POST http://0.0.0.0:8080/invocations
Health Check: GET http://0.0.0.0:8080/ping
```

## 使用示例

### 示例 1: 基本启动

```bash
agentarts dev
```

### 示例 2: 指定端口

```bash
agentarts dev --port 3000
```

### 示例 3: 启用热重载

```bash
agentarts dev --reload
```

### 示例 4: 传递环境变量

```bash
agentarts dev --env OPENAI_API_KEY=sk-xxx --env OPENAI_MODEL_NAME=gpt-4o
```

### 示例 5: 使用简写参数

```bash
agentarts dev -p 3000 -e OPENAI_API_KEY=sk-xxx -e OPENAI_MODEL_NAME=gpt-4o
```

### 示例 6: 指定配置文件

```bash
agentarts dev --config ./config/agentarts_config.yaml
```

### 示例 7: 完整参数示例

```bash
agentarts dev \
  --port 3000 \
  --host 127.0.0.1 \
  --reload \
  --env OPENAI_API_KEY=sk-xxx \
  --env OPENAI_MODEL_NAME=gpt-4o \
  --env OPENAI_BASE_URL=https://api.openai.com/v1
```

## 端点说明

开发服务器启动后，提供以下端点：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/invocations` | POST | Agent 调用入口 |
| `/ping` | GET | 健康检查 |

### 调用示例

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, Agent!"}'
```

### 健康检查示例

```bash
curl http://localhost:8080/ping
```

## 热重载

启用 `--reload` 参数后，当检测到代码文件变更时，服务器会自动重启：

```bash
agentarts dev --reload
```

适用于开发阶段快速迭代。

## 注意事项

1. **环境变量安全**: 敏感信息（如 API Key）在显示时会被脱敏处理
2. **端口占用**: 确保指定端口未被其他程序占用
3. **配置文件**: 默认读取当前目录下的 `.agentarts_config.yaml`
4. **模块路径**: 确保 `entrypoint` 指向的模块文件存在
5. **依赖安装**: 启动前请确保已安装所有依赖 `pip install -r requirements.txt`
