# Toolkit CLI Usage Examples

AgentArts Toolkit CLI 的完整使用示例。

## 查看示例

```bash
python cli_examples.py
```

## 主要命令

### 1. init - 初始化项目

```bash
agentarts init --name my-agent --template basic
agentarts init --name langgraph-agent --template langgraph --region cn-north-4
```

### 2. config - 配置管理

```bash
agentarts config list
agentarts config add --name new-agent --entrypoint agent:app
agentarts config set base.region cn-east-3 my-agent
agentarts config set-default my-agent
```

### 3. dev - 本地开发

```bash
agentarts dev
agentarts dev --agent my-agent --port 9000
```

### 4. deploy - 部署

```bash
agentarts deploy --mode local
agentarts deploy --mode cloud --agent my-agent
```

### 5. invoke - 调用

```bash
agentarts invoke --mode local --payload '{"message": "hello"}'
agentarts invoke --mode cloud --bearer-token my-token --payload '{"message": "hello"}'
```

### 6. status - 状态检查

```bash
agentarts status --mode local
agentarts status --mode cloud --agent my-agent
```

## 环境变量

| 变量名 | 说明 |
|-------|------|
| `HUAWEICLOUD_SDK_REGION` | 华为云区域 |
| `AGENTARTS_RUNTIME_DATA_ENDPOINT` | Runtime 数据面地址 |
| `AGENTARTS_MEMORY_DATA_ENDPOINT` | Memory 服务地址 |
| `AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT` | Code Interpreter 地址 |
| `BEARER_TOKEN` | Bearer Token（用于 invoke/status） |

## 完整工作流

```bash
# 1. 初始化
agentarts init --name my-agent --template basic

# 2. 开发
cd my-agent
agentarts dev

# 3. 配置
agentarts config set swr_config.organization my-org my-agent

# 4. 部署
agentarts deploy --mode cloud

# 5. 调用
agentarts invoke --mode cloud --payload '{"message": "hello"}'
```