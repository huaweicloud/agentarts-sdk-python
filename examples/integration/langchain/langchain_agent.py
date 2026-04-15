"""LangChain Integration Example - Agent with tools using AgentArts SDK"""

import os
from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

app = FastAPI(title="LangChain Agent with AgentArts Tools")


class ChatRequest(BaseModel):
    message: str
    include_intermediate_steps: bool = False


class ChatResponse(BaseModel):
    response: str
    intermediate_steps: Optional[List[dict]] = None


def create_agent_with_tools():
    """
    Create a LangChain agent with custom tools.
    
    This example demonstrates:
    - Creating custom tools using LangChain's @tool decorator
    - Building a tool-calling agent with LangChain
    - Using OpenAI as the LLM backend
    
    Note: For Code Interpreter integration, you need to:
    1. Create a Code Interpreter instance in Huawei Cloud
    2. Set environment variables for authentication
    """
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        temperature=0,
    )
    
    @tool
    def calculate(expression: str) -> str:
        """
        Evaluate a mathematical expression.
        
        Use this tool for mathematical calculations.
        
        Args:
            expression: Mathematical expression to evaluate (e.g., "2 + 2", "sqrt(16)")
            
        Returns:
            The result of the calculation
        """
        import math
        
        allowed_names = {
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "pi": math.pi,
            "e": math.e,
            "log": math.log,
            "log10": math.log10,
            "exp": math.exp,
            "pow": pow,
            "abs": abs,
            "round": round,
            "floor": math.floor,
            "ceil": math.ceil,
        }
        
        try:
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return str(result)
        except Exception as e:
            return f"Error evaluating expression: {str(e)}"
    
    @tool
    def get_current_time() -> str:
        """
        Get the current date and time.
        
        Returns:
            Current date and time as a string
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @tool
    def word_count(text: str) -> str:
        """
        Count the number of words in a text.
        
        Args:
            text: The text to count words in
            
        Returns:
            The word count
        """
        words = text.split()
        return f"The text contains {len(words)} words."
    
    tools = [calculate, get_current_time, word_count]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant with access to tools for calculations, "
                   "time, and text analysis. Use the tools when appropriate to help answer questions."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


agent_executor = create_agent_with_tools()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint using LangChain agent with tools.
    
    The agent can:
    - Perform mathematical calculations
    - Get current time
    - Count words in text
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
    
    print("Starting LangChain Agent Example...")
    print("")
    print("Required environment variables:")
    print("  - OPENAI_API_KEY: OpenAI API Key")
    print("  - OPENAI_MODEL_NAME: Model name (default: gpt-4o-mini)")
    print("  - OPENAI_BASE_URL: API Base URL (optional)")
    print("")
    print("Available tools:")
    print("  - calculate: Evaluate mathematical expressions")
    print("  - get_current_time: Get current date and time")
    print("  - word_count: Count words in text")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)