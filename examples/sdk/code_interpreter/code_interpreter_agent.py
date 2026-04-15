"""Code Interpreter Example - Agent with code execution capability"""

import os
import json
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel

from agentarts.sdk.code_interpreter import CodeInterpreterClient

app = FastAPI(title="Code Interpreter Agent Example")

code_interpreter = CodeInterpreterClient()


class CodeRequest(BaseModel):
    code: str
    language: str = "python"
    session_id: Optional[str] = None


class CodeResponse(BaseModel):
    result: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    session_id: str
    status: str


@app.post("/execute", response_model=CodeResponse)
async def execute_code(request: CodeRequest):
    """
    Execute code using Code Interpreter Service.
    
    This example demonstrates:
    - Submitting code for execution
    - Retrieving execution results
    - Managing execution sessions
    """
    session_id = request.session_id or os.urandom(8).hex()
    
    result = code_interpreter.execute_code(
        code=request.code,
        language=request.language,
        session_id=session_id,
    )
    
    return CodeResponse(
        result=result.get("result", ""),
        stdout=result.get("stdout"),
        stderr=result.get("stderr"),
        session_id=session_id,
        status=result.get("status", "completed"),
    )


@app.post("/execute-python")
async def execute_python(code: str, session_id: Optional[str] = None):
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
    session_id = session_id or os.urandom(8).hex()
    
    result = code_interpreter.execute_code(
        code=code,
        language="python",
        session_id=session_id,
    )
    
    return {
        "session_id": session_id,
        "output": result.get("stdout", ""),
        "error": result.get("stderr", ""),
        "status": result.get("status", "completed"),
    }


@app.get("/sessions/{session_id}/files")
async def list_session_files(session_id: str):
    """List files generated in a code execution session."""
    files = code_interpreter.list_files(session_id)
    
    return {
        "session_id": session_id,
        "files": files,
    }


@app.get("/sessions/{session_id}/files/{filename}")
async def download_session_file(session_id: str, filename: str):
    """Download a file generated in a code execution session."""
    content = code_interpreter.download_file(session_id, filename)
    
    return {
        "session_id": session_id,
        "filename": filename,
        "content": content,
    }


@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear a code execution session."""
    code_interpreter.clear_session(session_id)
    
    return {"status": "cleared", "session_id": session_id}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)