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
import json
import os
from typing import TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from agentarts.sdk import AgentArtsRuntimeApp
from agentarts.sdk.tools import code_session
```

### 2. 定义系统提示词
定义Agent的行为和能力
```python
app = AgentArtsRuntimeApp()
SYSTEM_PROMPT = """你是一个优秀的AI助手，擅长通过代码执行验证答案的正确性。

验证原则：
1. 当需要精确计算、数值验证或算法验证时，必须编写代码来验证结果
2. 使用execute_python_tool工具执行代码进行验证
3. 返回答案前，使用测试脚本来验证你的理解和计算
4. 只能通过实际的代码执行展示工作过程
5. 如果存在不确定的情况，详细说明限制条件并尽可能做验证

需要代码验证的场景
- 数学计算：包括算术运算、代数计算、概率统计、数列求和、几何计算等
- 算法验证：需要验证算法正确性，实现逻辑或性能测试时
- 数据处理：对数据进行统计分析、排序、查找等操作时
- 任何需要精确结果的问题，当口算或者估算无法保证准确性时

强制要求：
- 你必须使用execute_python_tool工具来执行python代码
- 涉及计算的问题，编写程序计算并显示代码和结果
- 每次给出最终答案前，至少执行一次验证代码
- 如果工具调用失败，明确告知用户
- 将代码执行结果作为答案的重要依据

可用工具：
- execute_python_tool(code: str, description: str): 在沙箱环境中执行Python代码并返回结果
    * code: 要执行的Python代码
    * description: 对代码的描述，用于上下文理解

响应格式要求：
- 优先展示验证代码和执行结果
- 清晰说明每一步的计算逻辑
- 最终答案必须基于代码执行结果
"""
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

    # 需配置环境 HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY
    api_key = os.environ.get(
        "HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY", ""
    )  # 配置环境变量后，api_key无需在代码中传递亦可正常工作
    with code_session("your_region", "your_code_interpreter_name", api_key) as code_client:
        response = code_client.invoke(
            operate_type="execute_code",
            api_key=api_key,
            arguments={
                "code": code,
                "language": "python",
                "clear_context": False,
            },
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
llm = llm.bind_tools(tools)

# 定义graph状态
class AgentState(TypedDict):
    messages: list[HumanMessage | SystemMessage | AIMessage]


def call_model(state: AgentState):
    """调用模型并返回响应"""
    if not state["messages"] or all(
        not isinstance(msg, SystemMessage) for msg in state["messages"]
    ):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    else:
        messages = state["messages"]

    response = llm.invoke(messages)
    return {"messages": [response]}


def should_continue(state):
    """判断是否继续使用工具"""
    last_message = state["messages"][-1]

    # 如果包含工具调用，则继续执行
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
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
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "__end__": "__end__"})
workflow.add_edge("tools", "agent")
agent = workflow.compile()
```

## 5. 定义问题
```python
query = "告诉我1到100之间最大的质数"
```

## 6. Agent执行与响应
```python
@app.entrypoint
def agent_chat():
    query = "告诉我1到100之间最大的质数"

    # 运行Agent
    result = agent.invoke({"messages": [HumanMessage(content=query)]})

    print(result["messages"][-1].content)


if __name__ == "__main__":
    app.run()
```
