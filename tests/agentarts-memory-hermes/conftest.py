"""Pytest configuration: add plugin root to sys.path for top-level modules."""

import sys
from pathlib import Path

# From tests/agentarts-memory-hermes/ → ../../agentarts-memory-plugins/agentarts-memory-hermes
plugin_root = (
    Path(__file__).resolve().parent.parent.parent
    / "agentarts-memory-plugins"
    / "agentarts-memory-hermes"
)
sys.path.insert(0, str(plugin_root))
