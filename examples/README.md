# AgentArts SDK Examples

本目录包含 AgentArts SDK 的开箱即用示例代码。

## 目录结构

```
examples/
├── sdk/                          # SDK 使用示例
│   ├── basic_agent/              # 基础 Agent 示例
│   ├── memory_service/           # Memory 服务示例
│   ├── code_interpreter/         # Code Interpreter 示例
│   └── agent_identity/           # Agent Identity 示例（已存在）
│
├── integration/                  # 集成示例
│   ├── langgraph/                # LangGraph 集成示例
│   └── langchain/                # LangChain 集成示例
│
└── toolkit/                      # Toolkit CLI 使用示例
    └── cli_usage/                # CLI 命令使用示例
```

## 快速开始

### 1. 基础 Agent 示例

```bash
cd sdk/basic_agent
pip install -r requirements.txt
python agent.py
```

### 2. Memory 服务示例

```bash
cd sdk/memory_service
pip install -r requirements.txt
# 设置环境变量
export AGENTARTS_MEMORY_DATA_ENDPOINT="your-endpoint"
python memory_example.py
```

### 3. LangGraph 集成示例

```bash
cd integration/langgraph
pip install -r requirements.txt
# 设置环境变量
export OPENAI_API_KEY="your-api-key"
python langgraph_agent.py
```

## 环境变量配置

大多数示例需要配置以下环境变量：

| 环境变量 | 说明 | 示例 |
|---------|------|------|
| `HUAWEICLOUD_SDK_REGION` | 华为云区域 | `cn-southwest-2` |
| `AGENTARTS_RUNTIME_DATA_ENDPOINT` | Runtime 数据面地址 | `https://agentarts.cn-southwest-2.myhuaweicloud.com` |
| `AGENTARTS_MEMORY_DATA_ENDPOINT` | Memory 服务地址 | `https://your-space.memory.cn-southwest-2.agentarts.myhuaweicloud.com` |
| `AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT` | Code Interpreter 地址 | `https://code-interpreter.cn-southwest-2.myhuaweicloud.com` |
| `OPENAI_API_KEY` | OpenAI API Key（用于 LangGraph/LangChain） | `sk-xxx` |