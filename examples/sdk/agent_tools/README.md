# 使用华为AgentArts 代码解释器执行代码并集成到Agent教程

## 概述
本文主要演示基于华为Agent代码解释器开发一个python执行工具验证答案，并将其集成到Agent中

共有如下几个步骤：

1. 创建一个沙箱（sandbox）环境
2. 配置基于langgraph的Agent，用于生成代码
3. 在沙箱中使用代码解释器执行代码
4. Agent获取执行结果并处理返回给用户

## 前置条件
+ 拥有华为云AgentArts Tools的访问权限
+ 拥有创建和管理Tools资源所需的权限
+ 已安装必须的Python库，包括agentarts-sdk、langgraph、langchain-openai等
+ 拥有模型访问权限

## 详细步骤
### 1. 创建沙箱环境
导入必要的库并初始化代码解释器
```bash
pip install -r requirements.txt
```

```python
import os
import json
from typing import TypedDict, Union

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool

from langgraph.prebuilt import ToolNode
from agentarts.sdk.tools import code_session
from agentarts.sdk import AgentArtsRuntimeApp
```

### 2. 定义系统提示词
定义Agent的行为和能力
```python
app = AgentArtsRuntimeApp()
SYSTEM_PROMPT = """你是一个通过代码执行验证所有答案的优秀AI助手

验证原则：
1. 当需要代码，算法或者计算来验证时，你需要编写代码来验证它们。
2. 使用execute_python_tool工具来测试数学计算，算法和逻辑
3. 返回答案前，使用测试脚本来验证你的理解
4. 只能通过实际的代码执行展示工作过程
5. 如果存在不确定的情况，详细说明限制条件并尽可能做验证

方法：
- 如果问题涉及编程，通过代码实现
- 如果要求你计算，编写程序计算并显示具体代码
- 如果需要实现算法，你还要编写测试用例来进行确认
- 记录验证的过程展示给用户

工具：
- execute_python_tool: 执行Python代码并返回结果

响应格式：execute_python_tool, 包括：
- content: 内容对象的数组，每个对象包含type和text/data"""
```

### 3. 定义代码执行工具
将execute_python_tool工具添加到Agent中，用于在代码沙箱中运行代码
```python
@tool
def execute_python_tool(code: str, description: str) -> str | None:
    """Execute Python Code in the sandbox"""

    if description:
        code = f"# {description}\n{code}"
    
    print(f"\n Generated Code: {code}")

    with code_session("your_region", "your_code_interpreter_name") as code_client:
        response = code_client.invoke(
            operate_type="execute_code",
            arguments={
                "code": code,
                "language": "python",
                "clear_context": False,
            }
        )
    
    return json.dumps(response["result"])
```

### 4. 配置Agent
使用langgraph配置Agent，添加系统提示词和工具
```python
# 创建Agent
llm = ChatOpenAI(
    model="DeepSeek-V3",
    api_key=os.environ.get("MODEL_API_KEY", ""),
    base_url=os.environ.get("BASE_URL", ""),
    max_tokens=1000,
    temperature=0.7,
)

# 创建工具列表 
tools = [execute_python_tool]
# 工具绑定Agent
llm.bind_tools(tools)

# 定义graph状态
class AgentState(TypedDict):
    messages: list[Union[HumanMessage, SystemMessage, AIMessage]]

def call_model(state: AgentState):
    """调用模型并返回响应"""
    if not state["messages"] or all(not isinstance(msg, SystemMessage) for msg in state["messages"]):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    else:
        messages = state["messages"]
    
    response = llm.invoke(messages)
    return {"messages": [response]}

def should_continue(state):
    """判断是否继续使用工具"""
    last_message = state["messages"][-1]

    # 如果包含工具调用，则继续执行
    if last_message.tool_calls:
        return "tools"

    # 否则结束
    return END

# 创建LangGraph工作流
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))

# 设置入口
workflow.set_entry_point("agent")

# 添加边
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "__end__": "__end__"
    }
)
workflow.add_edge("tools", "agent")
agent = workflow.compile()
```

## 5. 定义问题
```python
query = "告诉我1到100之间最大的随机质数"
```

## 6. Agent执行与响应
```python
@app.entrypoint
def agent_chat():
    query = "告诉我1到100之间最大的随机质数"

    # 运行Agent
    result = agent.invoke({
        "messages": [HumanMessage(content=query)]
    })

    print(result["messages"][-1].content)

if __name__ == "__main__":
    app.run()
```
