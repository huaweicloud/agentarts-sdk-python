"""Pure read-only list tests (default tier).

One list call per service, ``limit=1`` to minimise traffic. Creates nothing,
costs nothing — a cheap connectivity + auth probe for every control plane.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_list_spaces(memory_control_client):
    result = memory_control_client.list_spaces(limit=1)
    assert isinstance(result.items, list)


def test_list_mcp_gateways(mcp_gateway_client):
    result = mcp_gateway_client.list_mcp_gateways(limit=1)
    assert result.success, result.error


def test_list_runtime_agents(runtime_client):
    # runtime control plane rejects limit<10 ("limit too small"), use the default.
    agents = runtime_client.get_agents(limit=10)
    assert isinstance(agents, list)


def test_list_code_interpreters(cloud_credentials):
    from agentarts.sdk import CodeInterpreter

    ci = CodeInterpreter(region=cloud_credentials["region"])
    result = ci.list_code_interpreters(limit=1)
    assert isinstance(result, dict)
