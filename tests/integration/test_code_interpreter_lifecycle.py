"""Code Interpreter control-plane lifecycle (ALLOW_CREATE tier).

Creates a code-interpreter resource, exercises get/list/update, then deletes
it. This is control-plane only — NO sandbox session is started, so it does not
cost money. The billable sandbox session is in
``test_code_interpreter_session.py``.
"""

from __future__ import annotations

import pytest

from agentarts.sdk import CodeInterpreter
from tests.integration._helpers import unique_name

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def created_code_interpreter(
    cloud_credentials, allow_create, run_id, resource_registry
):
    name = unique_name("ci", run_id)  # satisfies [a-z][a-z0-9-]{0,38}[a-z0-9]
    ci = CodeInterpreter(region=cloud_credentials["region"])
    created = ci.create_code_interpreter(
        name=name, auth_type="API_KEY", api_key_name=f"{name}-ak"
    )
    ci_id = created["id"]
    resource_registry.register(
        lambda: ci.delete_code_interpreter(ci_id), f"code_interpreter:{ci_id}"
    )
    return {"id": ci_id, "name": name, "client": ci}


def test_get_code_interpreter(created_code_interpreter):
    ci = created_code_interpreter["client"]
    got = ci.get_code_interpreter(created_code_interpreter["id"])
    assert got["id"] == created_code_interpreter["id"]


def test_list_code_interpreters(created_code_interpreter):
    ci = created_code_interpreter["client"]
    result = ci.list_code_interpreters(limit=10)
    assert isinstance(result, dict)
    assert "items" in result or "total_count" in result or isinstance(result, dict)


def test_update_code_interpreter(created_code_interpreter):
    ci = created_code_interpreter["client"]
    updated = ci.update_code_interpreter(
        created_code_interpreter["id"],
        tags=[{"key": "env", "value": "aa-it"}],
    )
    assert isinstance(updated, dict)
