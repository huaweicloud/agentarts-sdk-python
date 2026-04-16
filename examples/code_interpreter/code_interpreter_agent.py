"""Code Interpreter Example - Agent with code execution capability"""

import os

from agentarts.sdk import AgentArtsRuntimeApp, CodeInterpreter

app = AgentArtsRuntimeApp()

code_interpreter = CodeInterpreter(
    region=os.getenv("HUAWEICLOUD_SDK_REGION", "cn-southwest-2"),
)


@app.entrypoint
def handler(payload: dict):
    """
    Execute code using Code Interpreter Service.

    This example demonstrates:
    - Starting a code interpreter session
    - Executing code
    - Managing execution sessions

    Required environment variables:
    - HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY: API Key for Code Interpreter
    - HUAWEICLOUD_SDK_REGION: Region (default: cn-southwest-2)
    - CODE_INTERPRETER_NAME: Code Interpreter name (or pass in payload)

    Args:
        payload: The input payload containing:
            - code: The code to execute
            - language: The programming language (default: python)
            - code_interpreter_name: Code Interpreter name
            - session_name: Optional session name

    Returns:
        dict: Response with execution result
    """
    code = payload.get("code", "")
    language = payload.get("language", "python")
    code_interpreter_name = payload.get("code_interpreter_name") or os.getenv("CODE_INTERPRETER_NAME")
    session_name = payload.get("session_name", "default-session")

    if not code:
        return {
            "error": "code is required",
            "session_id": "",
            "status": "error",
        }

    if not code_interpreter_name:
        return {
            "error": "code_interpreter_name is required. Set CODE_INTERPRETER_NAME env var or pass in payload.",
            "session_id": "",
            "status": "error",
        }

    session_id = code_interpreter.session_id
    if not session_id:
        try:
            session_id = code_interpreter.start_session(
                code_interpreter_name=code_interpreter_name,
                session_name=session_name,
            )
        except Exception as e:
            return {
                "error": f"Failed to start session: {e!s}",
                "session_id": "",
                "status": "error",
            }

    try:
        result = code_interpreter.execute_code(
            code=code,
            language=language,
        )

        return {
            "result": result,
            "session_id": session_id,
            "status": "completed",
        }
    except Exception as e:
        return {
            "error": str(e),
            "session_id": session_id,
            "status": "error",
        }


if __name__ == "__main__":
    print("Starting Code Interpreter Agent Example...")
    print("Required environment variables:")
    print("  - HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY: API Key for Code Interpreter")
    print("  - HUAWEICLOUD_SDK_REGION: Region (default: cn-southwest-2)")
    print("  - CODE_INTERPRETER_NAME: Code Interpreter name (or pass in payload)")
    print("")
    print("Endpoints:")
    print("  - POST /invocations - Invoke the agent")
    print("  - GET  /ping         - Health check")

    handler.run(host="0.0.0.0", port=8080)
