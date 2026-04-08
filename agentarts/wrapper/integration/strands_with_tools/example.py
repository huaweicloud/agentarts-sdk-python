import json
import os 

import httpx
from strands import Agent, tool
from strands.model.openai import OpenAIModel

from hw_agentarts_sdk import HuaweiAgentRunApp
from hw_agentarts_sdk.tools import code_session, CodeInterpreter

app = HuaweiAgentRunApp()
SYSTEM_PROMPT = """你是一个通过代码执行验证所有答案的优秀AI助手

验证原则:
1. 当需要验证答案是否正确时，你需要编写代码阿里验证它们
2. 使用execute_python工具执行Python代码，验证答案是否正确
3. 返回答案前，使用测试脚本来验证你的代码是否正确
4. 只能通过实际的代码执行展示工作过程
5. 如果存在不确定的情况，详细说明限制条件并尽可能验证

工具：
- execute_python: 执行Python代码，返回执行结果

响应格式：execute_python将返回一个json响应，包括：
- is_error: 表示执行是否存在错误，错误返回True
- content: 内容对象的数组，每个对象包含type和text/data
- structured_data: 结构化数据对象，包含stdout，stderr，exit_code和executionTime

"""

@tool
def execute_python(code: str, description: str) -> str:
    """Execute Python code in sandbox"""

    if description:
        code = f" # {description}\n{code}"
    
    print(f"\n生成Python代码: {code}\n")

    with code_session("cn-north-4") as code_client:
        response = code_client.invoke(
            operate="execute_code",
            arguments={
                "code": code,
                "language": "python",
                "clearContext": False,
            }
        )
    
    for event_item in response["stream"]:
        return json.dumps(event_item["result"])


model = OpenAIModel(
    client_args={
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "base_url": os.getenv("BASE_URL_API", ""),
        "http_client": httpx.AsyncClient(verify=False)
    },
    model_id="Deepseek-V3",
    params={
        "temperature": 0.5,
        "max_tokens": 1024,
    }
)

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[execute_python],
    callback_handler=None
)

@app.entrypoint
def agent_chat():
    query = "告诉我1到100之间最大的随机质数"
    try:
        response = agent.chat(query)
        return response.message["content"][0]["text"]
    except Exception as e:
        print(f"Error occured: {str(e)}")
        return str(e)

if __name__ == "__main__":
    app.run()

       
