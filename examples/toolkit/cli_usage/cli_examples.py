"""Toolkit CLI Usage Example - Demonstrates common CLI commands"""

"""
AgentArts Toolkit CLI 使用示例

本文件展示了 AgentArts Toolkit CLI 的常用命令和用法。

## 1. 初始化项目

创建一个新的 Agent 项目：

```bash
# 创建 basic 模板项目
agentarts init --name my-agent --template basic

# 创建 LangGraph 模板项目
agentarts init --name langgraph-agent --template langgraph

# 创建 LangChain 模板项目
agentarts init --name langchain-agent --template langchain

# 创建 Google ADK 模板项目
agentarts init --name google-adk-agent --template google-adk

# 指定区域和 SWR 配置
agentarts init --name my-agent --region cn-north-4 --swr-org my-org --swr-repo my-repo
```

## 2. 配置管理

查看和管理 Agent 配置：

```bash
# 列出所有 Agent
agentarts config list

# 添加新的 Agent 配置
agentarts config add --name new-agent --entrypoint agent:app --region cn-north-4

# 设置默认 Agent
agentarts config set-default my-agent

# 获取配置值
agentarts config get base.region my-agent

# 设置配置值
agentarts config set base.region cn-east-3 my-agent

# 重命名 Agent
agentarts config set base.name new-name old-name

# 删除 Agent 配置
agentarts config remove my-agent

# 生成 Dockerfile
agentarts config generate-dockerfile --output Dockerfile
```

## 3. 本地开发

在本地运行 Agent 进行开发测试：

```bash
# 使用默认配置启动开发服务器
agentarts dev

# 指定 Agent 名称
agentarts dev --agent my-agent

# 指定端口
agentarts dev --port 9000

# 指定 host
agentarts dev --host 127.0.0.1

# 禁用自动重载
agentarts dev --no-reload
```

## 4. 部署 Agent

将 Agent 部署到云端：

```bash
# 本地模式部署（仅构建镜像并本地运行）
agentarts deploy --mode local

# 云端模式部署
agentarts deploy --mode cloud

# 指定 Agent
agentarts deploy --agent my-agent --mode cloud

# 指定 SWR 镜像
agentarts deploy --swr-image swr.cn-north-4.myhuaweicloud.com/org/repo:v1

# 指定描述
agentarts deploy --description "My production agent"

# 跳过镜像构建（使用已有镜像）
agentarts deploy --skip-build --swr-image existing-image:v1
```

## 5. 调用 Agent

调用已部署的 Agent：

```bash
# 本地模式调用
agentarts invoke --mode local --payload '{"message": "hello"}'

# 云端模式调用
agentarts invoke --mode cloud --payload '{"message": "hello"}'

# 指定 Agent
agentarts invoke --agent my-agent --payload '{"message": "hello"}'

# 指定 session
agentarts invoke --session my-session-123 --payload '{"message": "hello"}'

# 使用 bearer token
agentarts invoke --bearer-token my-token --payload '{"message": "hello"}'

# 或使用环境变量
export BEARER_TOKEN=my-token
agentarts invoke --payload '{"message": "hello"}'

# 指定 endpoint
agentarts invoke --endpoint https://custom-endpoint.com --payload '{"message": "hello"}'
```

## 6. 检查 Agent 状态

检查 Agent 运行状态：

```bash
# 本地模式
agentarts status --mode local

# 云端模式
agentarts status --mode cloud

# 指定 Agent
agentarts status --agent my-agent

# 指定 session
agentarts status --session my-session-123

# 使用 bearer token
agentarts status --bearer-token my-token
```

## 7. 环境变量配置

可以通过环境变量配置默认值：

```bash
# 区域
export HUAWEICLOUD_SDK_REGION=cn-southwest-2

# Runtime 数据面 endpoint
export AGENTARTS_RUNTIME_DATA_ENDPOINT=https://agentarts.cn-southwest-2.myhuaweicloud.com

# Memory 服务 endpoint
export AGENTARTS_MEMORY_DATA_ENDPOINT=https://your-space.memory.cn-southwest-2.agentarts.myhuaweicloud.com

# Code Interpreter endpoint
export AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT=https://code-interpreter.cn-southwest-2.myhuaweicloud.com

# IAM endpoint
export HUAWEICLOUD_SDK_IAM_ENDPOINT=https://iam.cn-southwest-2.myhuaweicloud.com

# SWR endpoint
export HUAWEICLOUD_SDK_SWR_ENDPOINT=https://swr-api.cn-southwest-2.myhuaweicloud.com

# Bearer token（用于 invoke/status 命令）
export BEARER_TOKEN=your-bearer-token
```

## 8. 完整工作流示例

```bash
# 1. 初始化项目
agentarts init --name my-agent --template basic --region cn-north-4

# 2. 进入项目目录
cd my-agent

# 3. 本地开发测试
agentarts dev

# 4. 配置 SWR
agentarts config set swr_config.organization my-org my-agent
agentarts config set swr_config.repository agent_my-agent my-agent

# 5. 部署到云端
agentarts deploy --mode cloud

# 6. 调用 Agent
agentarts invoke --mode cloud --payload '{"message": "hello"}'

# 7. 检查状态
agentarts status --mode cloud
```
"""

if __name__ == "__main__":
    print(__doc__)