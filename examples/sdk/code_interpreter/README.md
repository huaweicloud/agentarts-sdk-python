# Code Interpreter Example

展示如何使用 AgentArts Code Interpreter 执行代码。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT="https://code-interpreter.cn-southwest-2.myhuaweicloud.com"

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

# 查看生成的文件
curl http://localhost:8080/sessions/session-id/files

# 下载文件
curl http://localhost:8080/sessions/session-id/files/output.txt
```

## 功能说明

- `/execute` - 执行代码（支持多种语言）
- `/execute-python` - 简化的 Python 执行接口
- `/sessions/{session_id}/files` - 列出会话生成的文件
- `/sessions/{session_id}/files/{filename}` - 下载文件

## 环境变量

| 变量名 | 说明 | 必需 |
|-------|------|------|
| `AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT` | Code Interpreter 地址 | 是 |