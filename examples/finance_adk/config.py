"""
Finance Agent Demo - Shared Configuration

Loads environment variables from .env file and reads
runtime configuration (memory space ID, LLM credentials,
Code Interpreter settings).

Usage:
    import config  # noqa: F401  (side-effect: loads .env)
    from config import SPACE_ID, API_KEY, ...
"""

import os
from pathlib import Path

# Load .env file
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_file)

# ---------------------------------------------------------------------------
# AgentArts Memory SDK endpoints
# ---------------------------------------------------------------------------
AGENTARTS_CONTROL_ENDPOINT = os.getenv(
    "AGENTARTS_CONTROL_ENDPOINT",
    "https://agentarts.cn-southwest-2.myhuaweicloud.com",
)
AGENTARTS_MEMORY_DATA_ENDPOINT = os.getenv("AGENTARTS_MEMORY_DATA_ENDPOINT")

# ---------------------------------------------------------------------------
# SSL verification
# ---------------------------------------------------------------------------
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"

# ---------------------------------------------------------------------------
# Memory Space credentials (set by setup_memory.py)
# ---------------------------------------------------------------------------
SPACE_ID = os.getenv("AGENTARTS_MEMORY_SPACE_ID")
API_KEY = os.getenv("HUAWEICLOUD_SDK_MEMORY_API_KEY")

# ---------------------------------------------------------------------------
# Code Interpreter credentials (set by setup_code_interpreter.py)
# ---------------------------------------------------------------------------
AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT = os.getenv(
    "AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT"
)
CODE_INTERPRETER_REGION = os.getenv("CODE_INTERPRETER_REGION", "cn-southwest-2")
CODE_INTERPRETER_NAME = os.getenv("CODE_INTERPRETER_NAME")
CODE_INTERPRETER_API_KEY = os.getenv("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

# ---------------------------------------------------------------------------
# LLM configuration (ADK uses LiteLLM provider/model format)
# ---------------------------------------------------------------------------
_raw_model = os.getenv("LLM_MODEL_NAME", "deepseek-v4-flash")
MODEL_NAME = _raw_model if "/" in _raw_model else f"openai/{_raw_model}"
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APP_NAME = "finance-adk-demo"
ACTOR_ID = "user-finance-demo"
ASSISTANT_ID = "finance-agent-demo"
SPACE_NAME = "memory-finance-agent-demo"
SPACE_DESCRIPTION = "Finance agent demo memory space"

# ---------------------------------------------------------------------------
# Memory strategies (all 4 builtin)
# ---------------------------------------------------------------------------
BUILTIN_STRATEGIES = ["semantic", "episodic", "user_preference", "summary"]

# ---------------------------------------------------------------------------
# Auto-recall configuration
# ---------------------------------------------------------------------------
AUTO_RECALL_TOP_K = 3       # 记忆自动注入条数
AUTO_RECALL_ENABLED = True  # 设为 False 可关闭自动注入

# ---------------------------------------------------------------------------
# Expense data storage
# ---------------------------------------------------------------------------
EXPENSES_FILE = Path(__file__).parent / "expenses.json"
