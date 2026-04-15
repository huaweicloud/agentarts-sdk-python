"""LangChain Integration Example - Agent with tools using AgentArts SDK"""

import os
from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from agentarts.sdk.code_interpreter import CodeInterpreterClient

app = FastAPI(title="LangChain Agent with AgentArts Tools")

code_interpreter = CodeInterpreterClient()


@tool
def execute_python_code(code: str) -> str:
    """
    Execute Python code and return the result.
    
    Use this tool when you need to perform calculations,
    data analysis, or any Python operations.
    
    Args:
        code: Python code to execute
        
    Returns:
        Execution result including stdout and any errors
    """
    result = code_interpreter.execute_code(
        code=code,
        language="python",
        session_id="langchain-session",
    )
    
    output = result.get("stdout", "")
    error = result.get("stderr", "")
    
    if error:
        return f"Error: {error}\nOutput: {output}"
    return output


@tool
def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression.
    
    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 2", "sqrt(16)")
        
    Returns:
        The result of the calculation
    """
    code = f"""
import math
result = {expression}
print(result)
"""
    result = code_interpreter.execute_code(
        code=code,
        language="python",
        session_id="calc-session",
    )
    
    return result.get("stdout", "").strip() or "Could not evaluate expression"


def create_agent():
    """
    Create a LangChain agent with AgentArts tools.
    
    This example demonstrates:
    - Creating custom tools using AgentArts Code Interpreter
    - Building a tool-calling agent with LangChain
    - Using OpenAI as the LLM backend
    """
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        temperature=0,
    )
    
    tools = [execute_python_code, calculate]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant with access to Python code execution. "
                   "Use the tools to help answer questions that require calculations or data processing."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


agent_executor = create_agent()


class ChatRequest(BaseModel):
    message: str
    include_intermediate_steps: bool = False


class ChatResponse(BaseModel):
    response: str
    intermediate_steps: Optional[List[dict]] = None


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint using LangChain agent with code execution tools.
    
    The agent can:
    - Execute Python code for calculations
    - Perform data analysis
    - Solve mathematical problems
    """
    result = agent_executor.invoke({"input": request.message})
    
    intermediate_steps = None
    if request.include_intermediate_steps:
        intermediate_steps = [
            {
                "tool": step[0].tool,
                "input": step[0].tool_input,
                "output": step[1],
            }
            for step in result.get("intermediate_steps", [])
        ]
    
    return ChatResponse(
        response=result["output"],
        intermediate_steps=intermediate_steps,
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)