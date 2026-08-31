"""Pytest configuration: add plugin root to sys.path for top-level modules."""

import sys
from pathlib import Path

# From tests/unit/toolkit/plugins/memory/hermes/ → repo root → src/.../ai_agent/hermes
plugin_root = (
    Path(__file__).resolve().parents[6]
    / "src"
    / "agentarts"
    / "toolkit"
    / "plugins"
    / "memory"
    / "ai_agent"
    / "hermes"
)
sys.path.insert(0, str(plugin_root))
