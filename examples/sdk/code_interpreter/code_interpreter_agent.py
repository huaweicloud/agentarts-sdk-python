"""Code Interpreter Example - Agent with code execution capability"""

import os
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel

from agentarts.sdk import CodeInterpreter

app = FastAPI(title="Code Interpreter Agent Example")

code_interpreter = CodeInterpreter(
    region=os.getenv("HUAWEICLOUD_SDK_REGION", "cn-southwest-2"),
)


class CodeRequest(BaseModel):
    code: str
    language: str = "python"
    code_interpreter_name: Optional[str] = None
    session_name: Optional[str] = None


class CodeResponse(BaseModel):
    result: dict
    session_id: str
    status: str


@app.post("/execute", response_model=CodeResponse)
async def execute_code(request: CodeRequest):
    """
    Execute code using Code Interpreter Service.
    
    This example demonstrates:
    - Starting a code interpreter session
    - Executing code
    - Managing execution sessions
    
    Required environment variables:
    - HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY: API Key for Code Interpreter
    - HUAWEICLOUD_SDK_REGION: Region (default: cn-southwest-2)
    """
    code_interpreter_name = request.code_interpreter_name or os.getenv("CODE_INTERPRETER_NAME")
    if not code_interpreter_name:
        return CodeResponse(
            result={"error": "code_interpreter_name is required. Set CODE_INTERPRETER_NAME env var or pass in request."},
            session_id="",
            status="error",
        )
    
    session_id = code_interpreter.session_id
    if not session_id:
        session_name = request.session_name or "default-session"
        try:
            session_id = code_interpreter.start_session(
                code_interpreter_name=code_interpreter_name,
                session_name=session_name,
            )
        except Exception as e:
            return CodeResponse(
                result={"error": f"Failed to start session: {str(e)}"},
                session_id="",
                status="error",
            )
    
    try:
        result = code_interpreter.execute_code(
            code=request.code,
            language=request.language,
        )
        
        return CodeResponse(
            result=result,
            session_id=session_id,
            status="completed",
        )
    except Exception as e:
        return CodeResponse(
            result={"error": str(e)},
            session_id=session_id,
            status="error",
        )


@app.post("/execute-python")
async def execute_python(code: str, code_interpreter_name: Optional[str] = None):
    """
    Simplified endpoint for Python code execution.
    
    Example usage:
    ```python
    code = '''
    import math
    result = math.sqrt(16)
    print(f"Square root of 16 is {result}")
    '''
    ```
    """
    code_interpreter_name = code_interpreter_name or os.getenv("CODE_INTERPRETER_NAME")
    if not code_interpreter_name:
        return {
            "error": "code_interpreter_name is required. Set CODE_INTERPRETER_NAME env var.",
            "output": "",
            "status": "error",
        }
    
    session_id = code_interpreter.session_id
    if not session_id:
        try:
            session_id = code_interpreter.start_session(
                code_interpreter_name=code_interpreter_name,
                session_name="python-session",
            )
        except Exception as e:
            return {
                "error": f"Failed to start session: {str(e)}",
                "output": "",
                "status": "error",
            }
    
    try:
        result = code_interpreter.execute_code(code=code, language="python")
        
        return {
            "session_id": session_id,
            "output": result.get("stdout", ""),
            "error": result.get("stderr", ""),
            "status": "completed",
        }
    except Exception as e:
        return {
            "session_id": session_id,
            "output": "",
            "error": str(e),
            "status": "error",
        }


@app.post("/stop-session")
async def stop_session():
    """Stop the current code interpreter session."""
    code_interpreter.stop_session()
    return {"status": "stopped"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    print("Starting Code Interpreter Agent Example...")
    print("Required environment variables:")
    print("  - HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY: API Key for Code Interpreter")
    print("  - HUAWEICLOUD_SDK_REGION: Region (default: cn-southwest-2)")
    print("  - CODE_INTERPRETER_NAME: Code Interpreter name (or pass in request)")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)