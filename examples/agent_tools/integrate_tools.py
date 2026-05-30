import json
import os
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from agentarts.sdk import AgentArtsRuntimeApp
from agentarts.sdk.tools import code_session

app = AgentArtsRuntimeApp()
SYSTEM_PROMPT = """你是一个AI助手，可以使用Python代码执行工具来解决问题。

可用工具：
- execute_python_tool(code: str, description: str): 执行Python代码

使用原则：
1. 仅在需要精确计算或复杂逻辑时使用工具
2. 简单问题直接回答，无需工具验证
3. 工具调用最多1-2次，避免重复验证
4. 获得结果后立即返回答案
"""


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
    with code_session("your_region", "your_code_interpreter_name", api_key=api_key) as code_client:
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
    messages: Annotated[list[BaseMessage], add_messages]


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

    if isinstance(last_message, AIMessage):
        has_tool_calls = bool(last_message.tool_calls)
        if has_tool_calls:
            return "tools"

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


@app.entrypoint
def agent_chat(payload: dict):
    query = "告诉我1到100之间最大的质数"

    # 运行Agent
    result = agent.invoke({"messages": [HumanMessage(content=query)]})

    return result["messages"][-1].content


if __name__ == "__main__":
    app.run()
