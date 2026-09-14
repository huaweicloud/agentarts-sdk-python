"""Tests for Memory MCP startup and stdio entry points."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

from agentarts.toolkit.plugins.memory.mcp.cli import main as cli_main
from agentarts.toolkit.plugins.memory.mcp.config import ENV_API_KEY, ENV_SPACE_ID
from agentarts.toolkit.plugins.memory.mcp.server import main as server_main


def test_main_fails_fast_when_required_environment_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv(ENV_API_KEY, raising=False)
    monkeypatch.delenv(ENV_SPACE_ID, raising=False)

    with pytest.raises(SystemExit, match="2"):
        server_main()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert ENV_API_KEY in captured.err
    assert ENV_SPACE_ID in captured.err


def test_main_runs_explicit_stdio_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_API_KEY, "api-key")
    monkeypatch.setenv(ENV_SPACE_ID, "space-id")
    server = MagicMock()

    with patch(
        "agentarts.toolkit.plugins.memory.mcp.server.create_server",
        return_value=server,
    ):
        server_main()

    server.run.assert_called_once_with(transport="stdio")


def test_console_launcher_delegates_to_server() -> None:
    server_main_mock = MagicMock()

    with patch(
        "agentarts.toolkit.plugins.memory.mcp.cli._load_server_main",
        return_value=server_main_mock,
    ):
        cli_main()

    server_main_mock.assert_called_once_with()


def test_console_launcher_explains_missing_optional_dependency(
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_mcp = ModuleNotFoundError("No module named 'mcp'", name="mcp")

    with (
        patch(
            "agentarts.toolkit.plugins.memory.mcp.cli._load_server_main",
            side_effect=missing_mcp,
        ),
        pytest.raises(SystemExit, match="2"),
    ):
        cli_main()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "agentarts-sdk[memory-mcp]" in captured.err


@pytest.mark.asyncio
async def test_module_entrypoint_negotiates_all_tools_over_stdio() -> None:
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            filter(None, [str(Path("src").resolve()), os.environ.get("PYTHONPATH", "")])
        ),
        ENV_API_KEY: "api-key",
        ENV_SPACE_ID: "space-id",
    }
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "agentarts.toolkit.plugins.memory.mcp.server"],
        env=environment,
    )

    async with Client(stdio_client(parameters)) as client:
        tools = await client.list_tools()

    assert {tool.name for tool in tools.tools} == {
        "search_memories",
        "add_messages",
        "list_memories",
        "search_summary",
        "ltm_search",
    }
