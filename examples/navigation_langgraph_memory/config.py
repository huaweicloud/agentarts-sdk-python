"""
Navigation Agent Demo - Shared Configuration

Loads environment variables from .env file (if present) and reads
runtime configuration (memory space ID, LLM credentials, AMap key).

Sessions are created on demand by session_manager.py — no
SESSION_ID is needed in config. Each conversation gets its own
AgentArts Memory session at startup.

Usage:
    import config  # noqa: F401  (side-effect: loads .env)
    from config import SPACE_ID, API_KEY, ...
"""

import os
from pathlib import Path

# Load .env file from the demo directory
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
# Memory Space ID - set after running setup_memory.py (once).
# Sessions are created on demand by session_manager.py.
# ---------------------------------------------------------------------------
SPACE_ID = os.getenv("AGENTARTS_MEMORY_SPACE_ID")
API_KEY = os.getenv("HUAWEICLOUD_SDK_MEMORY_API_KEY")

# ---------------------------------------------------------------------------
# LLM configuration (OpenAI-compatible endpoint)
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "deepseek-v3.2")

# ---------------------------------------------------------------------------
# AMap (Gaode Maps) Web Service Key
# ---------------------------------------------------------------------------
AMAP_KEY = os.getenv("AMAP_KEY") or os.getenv("AMAP_WEBSERVICE_KEY")
AMAP_BASE = "https://restapi.amap.com"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BUILTIN_STRATEGIES = ["semantic", "episodic", "user_preference", "summary"]
ACTOR_ID = "user-nav-demo"
ASSISTANT_ID = "nav-agent-demo"
SPACE_NAME = "memory-nav-agent-demo"
SPACE_DESCRIPTION = "Navigation agent demo memory space"

# ---------------------------------------------------------------------------
# Auto-recall configuration (hybrid memory recall)
# The auto_recall node searches the Store for relevant long-term memories
# before each LLM call and injects them into the system prompt.
# ---------------------------------------------------------------------------
AUTO_RECALL_TOP_K = 3       # max memories to auto-inject per turn
AUTO_RECALL_ENABLED = True  # toggle auto-injection (for comparison/testing)
