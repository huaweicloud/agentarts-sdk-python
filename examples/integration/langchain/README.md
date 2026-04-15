# LangChain Integration Example

展示如何将 LangChain 与 AgentArts Code Interpreter 集成，创建具有代码执行能力的 Agent。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL_NAME="gpt-4o-mini"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选
export AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT="https://code-interpreter.cn-southwest-2.myhuaweicloud.com"

# 运行 Agent
python langchain_agent.py
```

## 测试

```bash
# 简单计算
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the square root of 144?"}'

# 数据分析
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate the average of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]"}'

# 查看中间步骤
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2^10?", "include_intermediate_steps": true}'
```

## 功能说明

- `/chat` - 聊天接口，Agent 可以执行 Python 代码来回答问题
- `/health` - 健康检查

## 工具说明

Agent 配备了两个工具：

1. **execute_python_code** - 执行任意 Python 代码
2. **calculate** - 计算数学表达式

## 环境变量

| 变量名 | 说明 | 必需 |
|-------|------|------|
| `OPENAI_API_KEY` | OpenAI API Key | 是 |
| `OPENAI_MODEL_NAME` | 模型名称 | 否（默认 gpt-4o-mini） |
| `OPENAI_BASE_URL` | API Base URL | 否 |
| `AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT` | Code Interpreter 地址 | 是 |

## 示例对话

```
User: What is the factorial of 10?
Agent: Let me calculate that for you.
[Uses execute_python_code tool]
Agent: The factorial of 10 is 3,628,800.

User: Generate a plot of sin(x) for x from 0 to 2π
Agent: [Uses execute_python_code tool to generate and save the plot]
Agent: I've created a plot of sin(x). You can find it in the session files.
```