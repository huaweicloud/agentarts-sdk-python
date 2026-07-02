"""Code Interpreter billable sandbox session (RUN_BILLABLE tier).

Starts a real sandbox session against a *pre-provisioned* code interpreter via
the ``code_session`` context manager (auto-stops on exit → no session residue),
runs code + a shell command, round-trips a file (upload→download), and clears
context. Costs real money; gated behind ``AGENTARTS_TEST_RUN_BILLABLE=1``,
``HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY`` and
``AGENTARTS_TEST_CODE_INTERPRETER_NAME``.

All operations happen inside one ``code_session`` to minimise billable
sessions.
"""

from __future__ import annotations

import pytest

from agentarts.sdk import code_session

pytestmark = pytest.mark.integration

_FILE_PATH = "/home/user/aa-it-uploaded.txt"
_FILE_CONTENT = "hello-aa-it"


def test_code_session_full_workflow(
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
        # 1. execute_code
        code_result = client.execute_code("print(1 + 1)")
        assert isinstance(code_result, dict)
        assert "2" in str(code_result)

        # 2. execute_command (shell)
        cmd_result = client.execute_command(f"echo {_FILE_CONTENT}")
        assert isinstance(cmd_result, dict)

        # 3. upload_file then download_file (round-trip)
        up = client.upload_file(path=_FILE_PATH, content=_FILE_CONTENT)
        assert isinstance(up, dict)
        downloaded = client.download_file(path=_FILE_PATH)
        assert _FILE_CONTENT in (downloaded.decode() if isinstance(downloaded, bytes) else downloaded)

        # 4. get_session
        session = client.get_session(code_interpreter_name=code_interpreter_name)
        assert isinstance(session, dict)

        # 5. clear_context
        cleared = client.clear_context()
        assert isinstance(cleared, dict)
    # exiting the context manager calls stop_session() → session torn down
