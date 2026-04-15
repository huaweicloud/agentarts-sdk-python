"""LangChain Integration Example - Agent with tools using AgentArts SDK"""

import os
from agentarts.sdk import AgentArtsRuntimeApp

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

app = AgentArtsRuntimeApp()


def create_agent_with_tools():
    """
    Create a LangChain agent with custom tools.
    
    This example demonstrates:
    - Creating custom tools using LangChain's @tool decorator
    - Building a tool-calling agent with LangChain
    - Using OpenAI as the LLM backend
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


@app.entrypoint
def handler(payload: dict):
    """
    Chat entrypoint using LangChain agent with tools.
    
    The agent can:
    - Perform mathematical calculations
    - Get current time
    - Count words in text
    
    Args:
        payload: The input payload containing:
            - message: The user message
            - include_intermediate_steps: Whether to include tool calls (default: false)
            
    Returns:
        dict: Response with reply and optional intermediate steps
    """
    message = payload.get("message", "")
    include_intermediate_steps = payload.get("include_intermediate_steps", False)
    
    if not message:
        return {
            "error": "message is required",
        }
    
    result = agent_executor.invoke({"input": message})
    
    intermediate_steps = None
    if include_intermediate_steps:
        intermediate_steps = [
            {
                "tool": step[0].tool,
                "input": step[0].tool_input,
                "output": step[1],
            }
            for step in result.get("intermediate_steps", [])
        ]
    
    return {
        "response": result["output"],
        "intermediate_steps": intermediate_steps,
    }


@app.ping
def health_check():
    """Health check handler."""
    return "healthy"


if __name__ == "__main__":
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
    print("")
    print("Endpoints:")
    print("  - POST /invocations - Invoke the agent")
    print("  - GET  /ping         - Health check")
    
    handler.run(host="0.0.0.0", port=8080)