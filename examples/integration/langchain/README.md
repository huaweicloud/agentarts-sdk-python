# LangChain Integration Example

展示如何使用 LangChain 创建带有工具的 Agent。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL_NAME="gpt-4o-mini"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选

# 运行 Agent
python langchain_agent.py
```

## 测试

```bash
# 简单计算
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the square root of 144?"}'

# 获取时间
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "What time is it?"}'

# 文本分析
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "Count the words in: Hello World, this is a test."}'

# 查看中间步骤
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2^10?", "include_intermediate_steps": true}'
```

## 端点说明

- `POST /invocations` - 调用 Agent，可以使用工具来回答问题
- `GET /ping` - 健康检查端点

## 请求参数

| 参数 | 说明 | 必需 |
|------|------|------|
| `message` | 用户消息 | 是 |
| `include_intermediate_steps` | 是否包含工具调用步骤 | 否（默认 false） |

## 可用工具

Agent 配备了三个工具：

1. **calculate** - 计算数学表达式（支持 sqrt, sin, cos, tan, log 等）
2. **get_current_time** - 获取当前日期和时间
3. **word_count** - 统计文本中的单词数

## 环境变量

| 变量名 | 说明 | 必需 |
|-------|------|------|
| `OPENAI_API_KEY` | OpenAI API Key | 是 |
| `OPENAI_MODEL_NAME` | 模型名称 | 否（默认 gpt-4o-mini） |
| `OPENAI_BASE_URL` | API Base URL | 否 |

## 示例对话

```
User: What is the factorial of 10?
Agent: Let me calculate that for you.
[Uses calculate tool]
Agent: The factorial of 10 is 3,628,800.

User: What time is it?
Agent: [Uses get_current_time tool]
Agent: The current time is 2024-01-15 10:30:45.
```