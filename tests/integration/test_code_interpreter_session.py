"""Code Interpreter billable sandbox session (RUN_BILLABLE tier).

Starts a real sandbox session against a *pre-provisioned* code interpreter via
the ``code_session`` context manager (auto-stops on exit → no session residue),
runs one trivial code execution, and reads back the session. Costs real money;
gated behind ``AGENTARTS_TEST_RUN_BILLABLE=1``,
``HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY`` and
``AGENTARTS_TEST_CODE_INTERPRETER_NAME``.
"""

from __future__ import annotations

import pytest

from agentarts.sdk import code_session

pytestmark = pytest.mark.integration


def test_code_session_execute_and_get(
    cloud_credentials,
    allow_billable,
    code_interpreter_api_key,
    code_interpreter_name,
):
    region = cloud_credentials["region"]
    with code_session(
        region=region,
        code_interpreter_name=code_interpreter_name,
        auth_type="API_KEY",
        api_key=code_interpreter_api_key,
    ) as client:
        result = client.execute_code("print(1 + 1)")
        # response shape varies across backend versions; assert it ran and
        # the expected output is somewhere in the payload
        assert isinstance(result, dict)
        assert "2" in str(result)

        session = client.get_session(code_interpreter_name=code_interpreter_name)
        assert isinstance(session, dict)
        assert session.get("session_id") or session.get("session_name") or session
    # exiting the context manager calls stop_session() → session torn down
