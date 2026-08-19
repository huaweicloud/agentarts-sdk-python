"""Tests for startup validation and the real stdio transport."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

from agentarts_memory_mcp.config import ENV_API_KEY, ENV_SPACE_ID
from agentarts_memory_mcp.server import main


def test_main_fails_fast_when_required_environment_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv(ENV_API_KEY, raising=False)
    monkeypatch.delenv(ENV_SPACE_ID, raising=False)

    with pytest.raises(SystemExit, match="2"):
        main()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert ENV_API_KEY in captured.err
    assert ENV_SPACE_ID in captured.err


def test_main_runs_explicit_stdio_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_API_KEY, "api-key")
    monkeypatch.setenv(ENV_SPACE_ID, "space-id")
    server = MagicMock()

    with patch("agentarts_memory_mcp.server.create_server", return_value=server):
        main()

    server.run.assert_called_once_with(transport="stdio")


@pytest.mark.asyncio
async def test_module_entrypoint_negotiates_over_stdio() -> None:
    environment = {
        **os.environ,
        ENV_API_KEY: "api-key",
        ENV_SPACE_ID: "space-id",
    }
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "agentarts_memory_mcp"],
        env=environment,
    )

    async with Client(stdio_client(parameters)) as client:
        tools = await client.list_tools()

    assert [tool.name for tool in tools.tools] == ["ltm_search"]
