# Code Interpreter Example

展示如何使用 AgentArts Code Interpreter 执行代码。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY="your-api-key"
export HUAWEICLOUD_SDK_REGION="cn-southwest-2"
export CODE_INTERPRETER_NAME="your-code-interpreter-name"

# 运行 Agent
python code_interpreter_agent.py
```

## 测试

```bash
# 执行 Python 代码
curl -X POST http://localhost:8080/execute-python \
  -d "code=import math; print(math.sqrt(16))"

# 执行任意代码
curl -X POST http://localhost:8080/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "import math\nresult = math.pi * 2\nprint(result)", "language": "python"}'

# 停止会话
curl -X POST http://localhost:8080/stop-session
```

## 功能说明

- `/execute` - 执行代码（支持多种语言）
- `/execute-python` - 简化的 Python 执行接口
- `/stop-session` - 停止当前会话
- `/health` - 健康检查

## 环境变量

| 变量名 | 说明 | 必需 |
|-------|------|------|
| `HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY` | Code Interpreter API Key | 是 |
| `HUAWEICLOUD_SDK_REGION` | 华为云区域 | 否（默认 cn-southwest-2） |
| `CODE_INTERPRETER_NAME` | Code Interpreter 名称 | 是（或在请求中传递） |

## 前置条件

1. 在华为云上创建 Code Interpreter 实例
2. 获取 Code Interpreter 的 API Key
3. 记录 Code Interpreter 的名称